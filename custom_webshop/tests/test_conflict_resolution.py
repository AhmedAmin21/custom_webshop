# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for the staff side of the identity queue.

The signup flow's job ends at "I cannot tell these two apart, here is a
working account and a note for somebody who can". This is what that
somebody does next, and the tests are written around the fact that half
of it cannot be undone: a merge deletes a Customer record, so the
arguments are checked before anything moves, the whole thing is one
savepoint, and the invariant is re-read from the database afterwards
rather than assumed.

The fixtures deliberately go through the real signup rather than building
a conflict by hand. The interesting shape - one Contact holding a number,
another with it merely recorded as pending - is produced by the flow, and
a hand-built approximation of it would stop matching the day the flow
changed.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.api import conflicts as conflicts_api
from custom_webshop.api import signup as signup_api
from custom_webshop.signup import merge, session
from custom_webshop.signup.identity import to_e164
from custom_webshop.tests.utils import (
	conflict_with,
	problem_types,
	answer_name_card,
	make_customer_with_contact,
	signup_enabled,
	start_signup,
	unique_email,
	unique_name,
	unique_phone,
	verify_both_channels,
)

PASSWORD = "Str0ng-Passw0rd!x7"


class ConflictTestCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def rejected_signup(self):
		"""Run a signup that is offered a match and declines it.

		Returns:
			A dict of everything the tests need to look at afterwards.
		"""
		phone = unique_phone()
		name = unique_name("Ahmed")
		existing, existing_contact = make_customer_with_contact(customer_name=name, phone=phone)
		email = unique_email()

		with signup_enabled():
			client, resolved = self.run_flow(name, phone, email)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=False)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		identity = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, ["customer", "contact"], as_dict=True
		)
		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PHONE_ALREADY_ASSOCIATED", phone_e164=to_e164(phone)),
			"name",
		)

		self.assertTrue(conflict, "the withheld number raised no conflict")
		return {
			"phone": to_e164(phone),
			"email": email,
			"conflict": conflict,
			"existing_customer": existing.name,
			"existing_contact": existing_contact.name,
			"new_customer": identity.customer,
			"new_contact": identity.contact,
		}

	def run_flow(self, name, phone, email):
		client, _started = start_signup(full_name=name, phone=phone, email=email)
		verify_both_channels(client)
		return client, client.call(signup_api.resolve)

	def submit_an_order(self, customer):
		"""Give a Customer one submitted Sales Order, so it has history."""
		item = frappe.db.get_value("Item", {"is_stock_item": 0, "disabled": 0}, "name")
		if not item:
			self.skipTest("no non-stock Item on this site to build an order from")

		order = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"customer": customer,
				"transaction_date": frappe.utils.nowdate(),
				"delivery_date": frappe.utils.nowdate(),
				"company": frappe.defaults.get_user_default("Company"),
				"items": [{"item_code": item, "qty": 1, "rate": 100, "delivery_date": frappe.utils.nowdate()}],
			}
		)
		order.flags.ignore_permissions = True
		order.flags.ignore_mandatory = True
		order.insert(ignore_permissions=True)
		order.submit()
		return order


class TestWhatTheQueueShows(ConflictTestCase):
	def test_both_records_are_offered(self):
		state = self.rejected_signup()
		options = conflicts_api.get_resolution_options(state["conflict"])

		names = {party["customer"] for party in options["parties"]}
		self.assertIn(state["existing_customer"], names)
		self.assertIn(state["new_customer"], names)
		self.assertTrue(options["mergeable"])

	def test_it_says_which_record_holds_the_number(self):
		state = self.rejected_signup()
		options = conflicts_api.get_resolution_options(state["conflict"])
		by_name = {party["customer"]: party for party in options["parties"]}

		self.assertTrue(by_name[state["existing_customer"]]["holds_verified_phone"])
		self.assertFalse(by_name[state["new_customer"]]["holds_verified_phone"])
		self.assertEqual(by_name[state["new_customer"]]["pending_phone"], state["phone"])

	def test_a_footprint_counts_only_submitted_documents(self):
		customer, _contact = make_customer_with_contact()
		self.assertEqual(merge.financial_footprint(customer.name)["total"], 0)

		self.submit_an_order(customer.name)
		footprint = merge.financial_footprint(customer.name)
		self.assertEqual(footprint["Sales Order"], 1)
		self.assertEqual(footprint["total"], 1)

	def test_the_record_with_history_is_the_one_suggested(self):
		state = self.rejected_signup()
		self.submit_an_order(state["new_customer"])

		options = conflicts_api.get_resolution_options(state["conflict"])
		self.assertEqual(options["suggested_survivor"], state["new_customer"])
		self.assertIn("submitted documents", options["suggestion_reason"])

	def test_with_no_history_it_says_so_rather_than_inventing_a_reason(self):
		# The usual case on this site: nobody has ordered anything yet, so
		# there is nothing to weigh and the suggestion should admit it
		# instead of dressing up an arbitrary pick.
		state = self.rejected_signup()
		options = conflicts_api.get_resolution_options(state["conflict"])

		self.assertEqual(options["suggested_survivor"], state["existing_customer"])
		self.assertIn("Neither record has any submitted documents", options["suggestion_reason"])
		self.assertIn("older", options["suggestion_reason"])


class TestMerging(ConflictTestCase):
	def test_it_leaves_one_customer_holding_everything(self):
		state = self.rejected_signup()
		survivor = state["existing_customer"]

		conflicts_api.resolve_conflict(state["conflict"], "merge", survivor=survivor)

		self.assertTrue(frappe.db.exists("Customer", survivor))
		self.assertFalse(frappe.db.exists("Customer", state["new_customer"]))
		self.assertEqual(
			frappe.db.get_value("Webshop Account Identity", {"user": state["email"]}, "customer"),
			survivor,
		)

	def test_the_account_keeps_its_portal_access(self):
		"""The merge drops it, so the merge has to put it back.

		`rename_doc` re-points Link fields but does not merge child
		tables, so every Portal User row on the losing Customer is deleted
		with it. Without the repair a person keeps their login and loses
		sight of their own orders.
		"""
		state = self.rejected_signup()
		survivor = state["existing_customer"]

		conflicts_api.resolve_conflict(state["conflict"], "merge", survivor=survivor)

		self.assertTrue(
			frappe.db.exists(
				"Portal User",
				{"parenttype": "Customer", "parent": survivor, "user": state["email"]},
			)
		)

	def test_the_number_ends_up_on_one_contact_with_nothing_pending(self):
		state = self.rejected_signup()

		conflicts_api.resolve_conflict(
			state["conflict"], "merge", survivor=state["existing_customer"]
		)

		holders = frappe.get_all(
			"Contact Phone",
			filters={"parenttype": "Contact", "phone": state["phone"]},
			pluck="parent",
		)
		self.assertEqual(holders, [state["existing_contact"]])
		self.assertFalse(
			frappe.db.get_value(
				"Contact", state["existing_contact"], "custom_pending_phone_e164"
			)
		)

	def test_the_website_account_follows_the_contact(self):
		state = self.rejected_signup()

		conflicts_api.resolve_conflict(
			state["conflict"], "merge", survivor=state["existing_customer"]
		)

		self.assertEqual(
			frappe.db.get_value("Contact", state["existing_contact"], "user"), state["email"]
		)
		merge.assert_account_is_consistent(state["existing_customer"])

	def test_the_conflict_closes_with_an_account_of_what_happened(self):
		state = self.rejected_signup()

		conflicts_api.resolve_conflict(
			state["conflict"], "merge", survivor=state["existing_customer"], note="checked by hand"
		)

		row = frappe.db.get_value(
			"Webshop Identity Conflict",
			state["conflict"],
			["status", "resolved_by", "resolved_on", "resolution_notes"],
			as_dict=True,
		)
		self.assertEqual(row.status, "Resolved")
		self.assertTrue(row.resolved_by)
		self.assertTrue(row.resolved_on)
		self.assertIn(state["new_customer"], row.resolution_notes)
		self.assertIn("checked by hand", row.resolution_notes)

	def test_either_record_may_be_kept(self):
		# The suggestion is a suggestion. Keeping the new one has to work
		# exactly as well, or the choice is not really being offered.
		state = self.rejected_signup()
		survivor = state["new_customer"]

		conflicts_api.resolve_conflict(state["conflict"], "merge", survivor=survivor)

		self.assertTrue(frappe.db.exists("Customer", survivor))
		self.assertFalse(frappe.db.exists("Customer", state["existing_customer"]))
		merge.assert_account_is_consistent(survivor)


class TestMergingRefusesToGuess(ConflictTestCase):
	def test_it_will_not_merge_without_being_told_what_to_keep(self):
		state = self.rejected_signup()

		with self.assertRaises(frappe.ValidationError) as caught:
			conflicts_api.resolve_conflict(state["conflict"], "merge")

		self.assertIn("Choose which customer record to keep", str(caught.exception))
		self.assertTrue(frappe.db.exists("Customer", state["new_customer"]))

	def test_it_will_not_merge_into_an_unrelated_record(self):
		state = self.rejected_signup()
		bystander, _c = make_customer_with_contact()

		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(
				state["conflict"], "merge", survivor=bystander.name
			)

		self.assertTrue(frappe.db.exists("Customer", state["existing_customer"]))
		self.assertTrue(frappe.db.exists("Customer", state["new_customer"]))

	def test_an_unknown_action_changes_nothing(self):
		state = self.rejected_signup()

		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(state["conflict"], "delete_everything")

		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"), "Open"
		)

	def test_a_conflict_cannot_be_resolved_twice(self):
		state = self.rejected_signup()
		conflicts_api.resolve_conflict(state["conflict"], "keep_separate")

		with self.assertRaises(frappe.ValidationError) as caught:
			conflicts_api.resolve_conflict(
				state["conflict"], "merge", survivor=state["existing_customer"]
			)

		self.assertIn("already", str(caught.exception))
		self.assertTrue(frappe.db.exists("Customer", state["new_customer"]))


class TestApplyingTheNameTheyGave(ConflictTestCase):
	"""The other half of "that name isn't mine".

	The signup deliberately changes nothing at the time: a name typed into
	a form is a claim, and the record it disagrees with may be a company
	account, a relative's, or simply right. This is the click that decides
	it was the person's own name after all.
	"""

	def disputed_name(self):
		"""Sign back into an account while denying the name on it."""
		phone, email = unique_phone(), unique_email()
		stored = unique_name("Ahmed")
		claimed = unique_name("Mohamed")
		chosen = "An0ther-Passw0rd!q4"

		with signup_enabled():
			c1, _s = start_signup(full_name=stored, phone=phone, email=email)
			verify_both_channels(c1)
			c1.call(signup_api.resolve)
			c1.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

			c2, _s2 = start_signup(full_name=claimed, phone=phone, email=email)
			verify_both_channels(c2)
			review = c2.call(signup_api.resolve)
			self.assertEqual(review["state"], session.MATCH_REVIEW)
			c2.call(signup_api.decide, accept=False)
			c2.call(signup_api.complete, password=chosen, confirm_password=chosen)

		identity = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, ["customer", "contact"], as_dict=True
		)
		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PROFILE_DISCREPANCY", created_user=email),
			"name",
		)
		self.assertTrue(conflict, "denying the name raised nothing for staff")
		return {
			"email": email,
			"stored": stored,
			"claimed": claimed,
			"conflict": conflict,
			"customer": identity.customer,
			"contact": identity.contact,
		}

	def test_the_dialog_offers_it_and_shows_both_names(self):
		state = self.disputed_name()
		options = conflicts_api.get_resolution_options(state["conflict"])

		self.assertTrue(options["nameable"])
		self.assertEqual(options["submitted_name"], state["claimed"])
		self.assertEqual(options["stored_name"], state["stored"])

	def test_it_puts_the_name_on_the_contact_customer_and_account(self):
		state = self.disputed_name()

		conflicts_api.resolve_conflict(state["conflict"], "apply_name")

		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "full_name"), state["claimed"]
		)
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_name"), state["claimed"]
		)
		self.assertEqual(
			frappe.db.get_value("User", state["email"], "first_name"), state["claimed"]
		)
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"),
			"Resolved",
		)

	def test_a_company_keeps_its_trading_name(self):
		"""The person signing up is a contact there, not the company."""
		state = self.disputed_name()
		frappe.db.set_value(
			"Customer", state["customer"], "customer_type", "Company", update_modified=False
		)

		conflicts_api.resolve_conflict(state["conflict"], "apply_name")

		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_name"), state["stored"]
		)
		# The Contact is still the person, so their name goes on it.
		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "full_name"), state["claimed"]
		)

	def test_it_refuses_a_conflict_with_no_name_to_apply(self):
		state = self.disputed_name()
		frappe.db.set_value(
			"Webshop Identity Conflict", state["conflict"], "submitted_name", "", update_modified=False
		)

		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(state["conflict"], "apply_name")

		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"), "Open"
		)


class TestOnePersonTwoScripts(ConflictTestCase):
	"""An Arabic record and an English signup are not two names.

	The common shape on a shop selling in Egypt: staff entered the Contact
	in Arabic, the person signed up in Latin letters. Neither spelling is
	wrong and neither should overwrite the other, so the queue offers to
	keep both - the Arabic where it is, theirs in the contact's Foreign
	Name field.
	"""

	def arabic_record_latin_signup(self, submitted="Omar Ahmed Sabry"):
		phone, email = unique_phone(), unique_email()
		arabic = "عمر احمد صبرى"
		customer, contact = make_customer_with_contact(
			customer_name=arabic, phone=phone, email=email
		)

		with signup_enabled():
			client, review = self.run_flow(submitted, phone, email)
			self.assertEqual(review["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.choose_name, use_submitted=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PROFILE_DISCREPANCY", created_user=email),
			"name",
		)
		self.assertTrue(conflict, "no conflict was queued to act on")
		return {
			"conflict": conflict,
			"contact": contact.name,
			"customer": customer.name,
			"arabic": arabic,
			"submitted": submitted,
			"email": email,
		}

	def test_the_queue_offers_it(self):
		state = self.arabic_record_latin_signup()
		options = conflicts_api.get_resolution_options(state["conflict"])
		self.assertEqual(options["foreign_name"], state["submitted"])

	def test_it_keeps_both_spellings(self):
		state = self.arabic_record_latin_signup()

		conflicts_api.resolve_conflict(state["conflict"], "add_foreign_name")

		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "custom_foreign_name"),
			state["submitted"],
		)
		# The Arabic name is untouched, on the contact and the customer.
		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "full_name"), state["arabic"]
		)
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_name"),
			state["arabic"],
		)
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"),
			"Resolved",
		)

	def test_a_chinese_name_counts_as_foreign_too(self):
		state = self.arabic_record_latin_signup(submitted="陈 伟 明")
		options = conflicts_api.get_resolution_options(state["conflict"])
		self.assertEqual(options["foreign_name"], "陈 伟 明")

	def test_it_is_not_offered_when_both_names_are_arabic(self):
		from custom_webshop.signup import merge

		self.assertTrue(merge.is_arabic("عمر احمد صبرى"))
		self.assertFalse(merge.is_foreign_to_arabic("عمر احمد صبرى"))
		# A string of digits is neither script.
		self.assertFalse(merge.is_foreign_to_arabic("12345"))
		self.assertTrue(merge.is_foreign_to_arabic("Omar Sabry"))

	def test_it_refuses_when_the_record_is_not_arabic(self):
		phone, email = unique_phone(), unique_email()
		make_customer_with_contact(
			customer_name=unique_name("Ahmed"), phone=phone, email=email
		)
		with signup_enabled():
			client, _r = self.run_flow(unique_name("Mohamed"), phone, email)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.choose_name, use_submitted=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PROFILE_DISCREPANCY", created_user=email),
			"name",
		)
		options = conflicts_api.get_resolution_options(conflict)
		self.assertIsNone(options["foreign_name"])

		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(conflict, "add_foreign_name")


class TestTheForeignNameOfferIsEarned(ConflictTestCase):
	"""Two names are one person's only if something verified says so.

	The offer used to check the two scripts and nothing else, which is
	true of every stranger who ever typed Latin letters. What makes it a
	real pair is a verified channel reaching the record, so that is what
	is checked - and which channel it was is reported, because a
	phone-only match is the weaker one.
	"""

	def arabic_record_reached_by(self, *, by_phone, by_email):
		"""An Arabic customer, reached by whichever channels are asked for."""
		arabic = "عمر احمد صبرى"
		record_phone, record_email = unique_phone(), unique_email()
		customer, contact = make_customer_with_contact(
			customer_name=arabic, phone=record_phone, email=record_email
		)

		# What the signup proves: the record's own channel where it should
		# match, a brand-new one where it should not.
		phone = record_phone if by_phone else unique_phone()
		email = record_email if by_email else unique_email()

		with signup_enabled():
			client, review = self.run_flow("Omar Ahmed Sabry", phone, email)
			self.assertEqual(review["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=True)
			# Carrying the typed name is what queues a conflict when both
			# channels agree: a match nobody disputes has nothing to
			# review, so there would be no row to act on.
			client.call(signup_api.choose_name, use_submitted=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		return {"customer": customer.name, "contact": contact.name, "arabic": arabic,
		        "email": email, "phone": phone}

	def conflict_about(self, customer):
		return frappe.db.get_value(
			"Webshop Identity Conflict",
			{"created_customer": customer, "status": ["in", ("Open", "In Review")]},
			"name",
		)

	def test_a_phone_only_match_is_still_offered_and_says_so(self):
		# Staff asked for the button on any match, not only on both. The
		# weaker case is named rather than hidden.
		state = self.arabic_record_reached_by(by_phone=True, by_email=False)
		conflict = self.conflict_about(state["customer"])
		self.assertTrue(conflict, "the phone-only link raised no conflict to act on")

		options = conflicts_api.get_resolution_options(conflict)
		self.assertEqual(options["foreign_name"], "Omar Ahmed Sabry")
		self.assertEqual(options["foreign_name_channels"], ["phone"])

	def test_both_channels_are_reported_when_both_matched(self):
		state = self.arabic_record_reached_by(by_phone=True, by_email=True)
		conflict = self.conflict_about(state["customer"])
		self.assertTrue(conflict)

		options = conflicts_api.get_resolution_options(conflict)
		self.assertEqual(options["foreign_name_channels"], ["email", "phone"])

	def test_it_is_refused_when_no_verified_channel_reaches_the_record(self):
		"""The guard itself, exercised directly.

		Reaching this through a signup is not possible by design - a
		record nothing matches is never the candidate - so the conflict is
		built pointing at an Arabic customer whose channels are both
		strangers, which is the shape a stale or hand-made row would have.
		"""
		arabic = "عمر احمد صبرى"
		customer, contact = make_customer_with_contact(
			customer_name=arabic, phone=unique_phone(), email=unique_email()
		)

		conflict = frappe.get_doc({
			"doctype": "Webshop Identity Conflict",
			"conflict_type": "PROFILE_DISCREPANCY",
			"status": "Open",
			"submitted_name": "Omar Ahmed Sabry",
			"phone_e164": to_e164(unique_phone()),
			"email_normalized": unique_email(),
			"created_customer": customer.name,
		})
		conflict.flags.ignore_permissions = True
		conflict.insert(ignore_permissions=True)

		self.assertEqual(merge.channels_reaching(conflict), [])
		self.assertIsNone(merge.foreign_name_offer(conflict))
		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(conflict.name, "add_foreign_name")
		self.assertIsNone(
			frappe.db.get_value("Contact", contact.name, "custom_foreign_name")
		)


class TestReplacingAForeignNameSaysWhatWent(ConflictTestCase):
	"""A field that already held a spelling must not lose it quietly."""

	def filed_conflict(self):
		arabic = "عمر احمد صبرى"
		phone, email = unique_phone(), unique_email()
		customer, contact = make_customer_with_contact(
			customer_name=arabic, phone=phone, email=email
		)
		with signup_enabled():
			client, review = self.run_flow("Omar A Sabry", phone, email)
			self.assertEqual(review["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.choose_name, use_submitted=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			{"created_customer": customer.name, "status": ["in", ("Open", "In Review")]},
			"name",
		)
		self.assertTrue(conflict, "no conflict was queued to act on")
		return conflict, contact.name

	def test_the_replaced_spelling_is_named_in_the_notes(self):
		conflict, contact = self.filed_conflict()
		frappe.db.set_value("Contact", contact, "custom_foreign_name", "Omar Sabry")

		conflicts_api.resolve_conflict(conflict, "add_foreign_name")

		self.assertEqual(
			frappe.db.get_value("Contact", contact, "custom_foreign_name"), "Omar A Sabry"
		)
		notes = frappe.db.get_value("Webshop Identity Conflict", conflict, "resolution_notes")
		self.assertIn("Omar A Sabry", notes)
		self.assertIn("Omar Sabry", notes, "the spelling that was replaced went unrecorded")

	def test_an_identical_value_is_not_written_twice(self):
		conflict, contact = self.filed_conflict()
		frappe.db.set_value("Contact", contact, "custom_foreign_name", "Omar A Sabry")

		steps = merge.add_foreign_name(
			frappe.get_doc("Webshop Identity Conflict", conflict)
		)

		self.assertEqual(len(steps), 1)
		self.assertIn("already carried", steps[0])


class TestKeepingThemSeparate(ConflictTestCase):
	def test_nothing_is_changed_and_the_pair_stops_resurfacing(self):
		state = self.rejected_signup()

		conflicts_api.resolve_conflict(state["conflict"], "keep_separate")

		self.assertTrue(frappe.db.exists("Customer", state["existing_customer"]))
		self.assertTrue(frappe.db.exists("Customer", state["new_customer"]))
		# The pending marker stays: it is still true that this account
		# proved a number its own Contact cannot hold.
		self.assertEqual(
			frappe.db.get_value("Contact", state["new_contact"], "custom_pending_phone_e164"),
			state["phone"],
		)
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"),
			"Resolved",
		)

	def test_dismissing_marks_it_dismissed(self):
		state = self.rejected_signup()

		conflicts_api.resolve_conflict(state["conflict"], "dismiss", note="raised in error")

		row = frappe.db.get_value(
			"Webshop Identity Conflict",
			state["conflict"],
			["status", "resolution_notes"],
			as_dict=True,
		)
		self.assertEqual(row.status, "Dismissed")
		self.assertIn("raised in error", row.resolution_notes)


class TestTheInvariant(ConflictTestCase):
	def test_it_notices_an_account_with_no_portal_access(self):
		state = self.rejected_signup()
		frappe.db.delete(
			"Portal User",
			{"parenttype": "Customer", "parent": state["new_customer"], "user": state["email"]},
		)

		with self.assertRaises(frappe.ValidationError) as caught:
			merge.assert_account_is_consistent(state["new_customer"])

		self.assertIn("portal access", str(caught.exception))

	def test_it_notices_a_contact_that_belongs_to_somebody_else(self):
		state = self.rejected_signup()
		intruder = frappe.db.get_value("User", {"name": ("!=", state["email"])}, "name")
		frappe.db.set_value("Contact", state["new_contact"], "user", intruder, update_modified=False)

		with self.assertRaises(frappe.ValidationError) as caught:
			merge.assert_account_is_consistent(state["new_customer"])

		self.assertIn(state["new_contact"], str(caught.exception))


def tearDownModule():
	"""Remove accounts the deliberate commits in this flow left behind."""
	from custom_webshop.tests.utils import purge_test_accounts, purge_test_sessions

	purge_test_sessions()
	purge_test_accounts()


class TestPersonAndBusinessDisagree(ConflictTestCase):
	"""One rule for both directions, raised on the type alone.

	Neither direction is an error. A real person is very often the
	contact on a company account, and somebody trading under a business
	name may have been entered as an individual years ago. So the account
	links and the customer is left exactly as it was - but the queue is
	told, because the types disagreeing is not something anybody would
	otherwise notice.

	Raised on the type by itself, not folded into a name conflict: the
	names can agree perfectly while the types do not, and that case would
	go through with nobody told.
	"""

	def signup_against(self, *, record_type, as_company, same_name=False):
		person = unique_name("Ahmed")
		stored = person if same_name else unique_name("Mohamed")
		phone = unique_phone()
		customer, contact = make_customer_with_contact(customer_name=stored, phone=phone)
		frappe.db.set_value("Customer", customer.name, "customer_type", record_type)

		company = unique_name("Acme") if as_company else None
		with signup_enabled():
			client, _started = start_signup(
				full_name=person, phone=phone, email=unique_email(),
				account_type="Company" if as_company else "Individual",
				company_name=company,
			)
			verify_both_channels(client)
			review = client.call(signup_api.resolve)
			if review["state"] == session.MATCH_REVIEW:
				answer_name_card(client, client.call(signup_api.decide, accept=True))
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		return {"customer": customer.name, "contact": contact.name, "stored": stored,
		        "company": company, "person": person}

	def conflict_for(self, customer):
		return frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("ACCOUNT_TYPE_MISMATCH", created_customer=customer),
			["name", "resolution_notes", "claimed_company_name"],
			as_dict=True,
		)

	def test_an_individual_signing_in_to_a_company_is_queued(self):
		state = self.signup_against(record_type="Company", as_company=False)
		found = self.conflict_for(state["customer"])
		self.assertTrue(found, "an individual signup on a company record raised nothing")
		self.assertIn("individual", found.resolution_notes.lower())
		self.assertIn("company", found.resolution_notes.lower())

	def test_a_company_signing_in_to_an_individual_keeps_the_business_name(self):
		state = self.signup_against(record_type="Individual", as_company=True)
		found = self.conflict_for(state["customer"])
		self.assertTrue(found, "a company signup on an individual record raised nothing")
		self.assertEqual(found.claimed_company_name, state["company"])
		self.assertIn(state["company"], found.resolution_notes)
		# And it is on the contact too, which is where a person's employer
		# belongs - the link path used to drop it entirely.
		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "company_name"), state["company"]
		)

	def test_it_is_raised_even_when_the_names_agree(self):
		# The case a name conflict would never catch.
		state = self.signup_against(record_type="Company", as_company=False, same_name=True)
		self.assertTrue(self.conflict_for(state["customer"]))

	def test_partnership_counts_as_a_disagreement(self):
		# The signup form cannot express it, so it can never agree.
		state = self.signup_against(record_type="Partnership", as_company=False)
		found = self.conflict_for(state["customer"])
		self.assertTrue(found)
		self.assertIn("partnership", found.resolution_notes.lower())

	def test_matching_types_raise_nothing(self):
		state = self.signup_against(record_type="Individual", as_company=False)
		self.assertIsNone(self.conflict_for(state["customer"]))

	def test_the_signup_never_changes_the_customer_type(self):
		state = self.signup_against(record_type="Individual", as_company=True)
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_type"), "Individual"
		)
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_name"), state["stored"]
		)


class TestConvertingARecordToACompany(ConflictTestCase):
	"""The one direction with a button, and the only place type is written."""

	def company_claim_on_an_individual(self):
		person, company = unique_name("Ahmed"), unique_name("Acme")
		stored, phone = unique_name("Mohamed"), unique_phone()
		customer, contact = make_customer_with_contact(customer_name=stored, phone=phone)

		with signup_enabled():
			client, _started = start_signup(
				full_name=person, phone=phone, email=unique_email(),
				account_type="Company", company_name=company,
			)
			verify_both_channels(client)
			review = client.call(signup_api.resolve)
			if review["state"] == session.MATCH_REVIEW:
				answer_name_card(client, client.call(signup_api.decide, accept=True))
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("ACCOUNT_TYPE_MISMATCH", created_customer=customer.name),
			"name",
		)
		self.assertTrue(conflict)
		return {"conflict": conflict, "customer": customer.name, "contact": contact.name,
		        "company": company, "stored": stored}

	def test_the_queue_offers_it(self):
		state = self.company_claim_on_an_individual()
		options = conflicts_api.get_resolution_options(state["conflict"])
		self.assertEqual(options["company_conversion"], state["company"])

	def test_it_converts_the_type_and_the_name_together(self):
		state = self.company_claim_on_an_individual()

		conflicts_api.resolve_conflict(state["conflict"], "make_company")

		row = frappe.db.get_value(
			"Customer", state["customer"], ["customer_type", "customer_name",
			                                "customer_primary_contact"], as_dict=True
		)
		self.assertEqual(row.customer_type, "Company")
		self.assertEqual(row.customer_name, state["company"])
		# The person stays as its contact - that is what a company
		# account looks like - and their own name is untouched.
		self.assertEqual(row.customer_primary_contact, state["contact"])
		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "full_name"), state["stored"]
		)
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"),
			"Resolved",
		)

	def test_it_is_not_offered_the_other_way_round(self):
		# An individual signing in to a company needs nothing done, so
		# there is no button to press.
		phone = unique_phone()
		customer, _c = make_customer_with_contact(customer_name=unique_name("Acme"), phone=phone)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		with signup_enabled():
			client, _started = start_signup(
				full_name=unique_name("Ahmed"), phone=phone, email=unique_email()
			)
			verify_both_channels(client)
			review = client.call(signup_api.resolve)
			if review["state"] == session.MATCH_REVIEW:
				answer_name_card(client, client.call(signup_api.decide, accept=True))
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("ACCOUNT_TYPE_MISMATCH", created_customer=customer.name),
			"name",
		)
		options = conflicts_api.get_resolution_options(conflict)
		self.assertIsNone(options["company_conversion"])
		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(conflict, "make_company")


class TestOneConflictPerSignup(ConflictTestCase):
	"""A signup wrong in several ways is one case, not several.

	Each problem is still a separate decision - applying a name settles
	nothing about whether the customer is a company - so each is a row on
	the conflict with its own section and its own buttons. What is gone is
	the queue holding the same signup two or three times, each row showing
	actions belonging to a problem it did not describe.
	"""

	def a_company_record_and_a_disputed_name(self):
		company, person = unique_name("Acme"), unique_name("Ahmed")
		phone, email = unique_phone(), unique_email()
		customer, contact = make_customer_with_contact(
			customer_name=company, contact_name=person, phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		mine = unique_name("Mohamed")
		with signup_enabled():
			client, review = self.run_flow(mine, phone, email)
			self.assertEqual(review["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.choose_name, use_submitted=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		sess = frappe.db.get_value("Webshop Signup Session", {"email_normalized": email}, "name")
		rows = frappe.get_all("Webshop Identity Conflict",
		                      filters={"signup_session": sess}, pluck="name")
		return {"session": sess, "conflicts": rows, "customer": customer.name,
		        "contact": contact.name, "mine": mine, "company": company}

	def test_the_queue_holds_one_row_for_the_signup(self):
		state = self.a_company_record_and_a_disputed_name()
		self.assertEqual(len(state["conflicts"]), 1, "the signup was filed as several cases")

	def test_the_headline_is_one_of_its_own_problems(self):
		"""The queue lists the row under a type it actually has.

		`conflict_type` is `reqd` and its options begin with a real value,
		so `new_doc` pre-fills it - and an "if empty" check never fired,
		which titled every case PHONE_NAME_MISMATCH whatever was wrong
		with it.
		"""
		state = self.a_company_record_and_a_disputed_name()
		conflict = state["conflicts"][0]
		headline = frappe.db.get_value("Webshop Identity Conflict", conflict, "conflict_type")

		self.assertIn(headline, problem_types(conflict))
		# The first thing found, which is what the queue sorts on.
		self.assertEqual(headline, "ACCOUNT_TYPE_MISMATCH")

	def test_that_row_carries_every_problem(self):
		state = self.a_company_record_and_a_disputed_name()
		self.assertEqual(
			problem_types(state["conflicts"][0]),
			["ACCOUNT_TYPE_MISMATCH", "PROFILE_DISCREPANCY"],
		)

	def test_settling_one_problem_leaves_the_others_open(self):
		"""The reason they are rows and not one verdict."""
		state = self.a_company_record_and_a_disputed_name()
		conflict = state["conflicts"][0]

		result = conflicts_api.resolve_conflict(conflict, "apply_name")

		self.assertFalse(result["closed"], "the case closed with a question still open")
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", conflict, "status"), "Open"
		)
		settled = frappe.get_all("Webshop Identity Problem",
		                         filters={"parent": conflict, "resolved": 1},
		                         pluck="problem_type")
		self.assertEqual(settled, ["PROFILE_DISCREPANCY"])

	def test_the_case_closes_once_nothing_is_outstanding(self):
		state = self.a_company_record_and_a_disputed_name()
		conflict = state["conflicts"][0]

		conflicts_api.resolve_conflict(conflict, "apply_name")
		result = conflicts_api.resolve_conflict(conflict, "keep_type")

		self.assertTrue(result["closed"])
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", conflict, "status"), "Resolved"
		)

	def test_applying_the_name_does_not_rename_the_company(self):
		state = self.a_company_record_and_a_disputed_name()
		conflicts_api.resolve_conflict(state["conflicts"][0], "apply_name")

		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "full_name"), state["mine"]
		)
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_name"),
			state["company"],
		)

	def test_dismiss_settles_the_whole_case(self):
		# "None of this was a real problem" answers every question at once.
		state = self.a_company_record_and_a_disputed_name()
		conflict = state["conflicts"][0]

		conflicts_api.resolve_conflict(conflict, "dismiss")

		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", conflict, "status"), "Dismissed"
		)
		self.assertEqual(
			frappe.get_all("Webshop Identity Problem",
			               filters={"parent": conflict, "resolved": 0}, pluck="name"),
			[],
		)


class TestASettledQuestionIsNotAskedAgain(ConflictTestCase):
	"""A case stays open while other questions are outstanding.

	So being open is no longer proof that this particular question is,
	and the old "already resolved" guard would let a second merge, or a
	name applied twice, through on a case somebody is still working.
	"""

	def two_questions(self):
		company, person = unique_name("Acme"), unique_name("Ahmed")
		phone, email = unique_phone(), unique_email()
		customer, _c = make_customer_with_contact(
			customer_name=company, contact_name=person, phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		with signup_enabled():
			client, _r = self.run_flow(unique_name("Mohamed"), phone, email)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.choose_name, use_submitted=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		sess = frappe.db.get_value("Webshop Signup Session", {"email_normalized": email}, "name")
		return frappe.get_all("Webshop Identity Conflict",
		                      filters={"signup_session": sess}, pluck="name")[0]

	def test_the_same_answer_is_refused_a_second_time(self):
		conflict = self.two_questions()
		conflicts_api.resolve_conflict(conflict, "apply_name")

		with self.assertRaises(frappe.ValidationError) as caught:
			conflicts_api.resolve_conflict(conflict, "apply_name")

		self.assertIn("already been settled", str(caught.exception))

	def test_the_other_question_can_still_be_answered(self):
		# Refusing the settled one must not lock the case.
		conflict = self.two_questions()
		conflicts_api.resolve_conflict(conflict, "apply_name")

		result = conflicts_api.resolve_conflict(conflict, "keep_type")

		self.assertTrue(result["closed"])
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", conflict, "status"), "Resolved"
		)

	def test_a_note_never_holds_the_case_open(self):
		"""INCOMPLETE_PROFILE has no answer a button could give.

		It is recorded so the case is complete and skipped when deciding
		whether anything is outstanding - otherwise every signup that
		made its own customer would sit in the queue forever.
		"""
		state = self.rejected_signup()
		self.assertIn("INCOMPLETE_PROFILE", problem_types(state["conflict"]))

		conflicts_api.resolve_conflict(state["conflict"], "keep_separate")

		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"),
			"Resolved",
		)


class TestComingBackAsABusiness(ConflictTestCase):
	"""A returning owner can disagree about the type too.

	The account-type check ran only where a signup *linked* to a record,
	so somebody coming back to their own account and saying they are a
	business never had the disagreement recorded. With the queue asking
	each question in its own section, a problem that is never raised has
	no section and therefore no buttons - which left the case
	half-answerable: the name could be settled and the type could not.
	"""

	def returning_owner_says_company(self):
		person, company = unique_name("Khaled"), unique_name("Qarafa")
		phone, email = unique_phone(), unique_email()
		make_customer_with_contact(customer_name=person, contact_name=person, phone=phone)

		# First signup makes the account against the individual record.
		with signup_enabled():
			client, _r = self.run_flow(person, phone, email)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		# Coming back: both channels reach their own account, and this
		# time they say they are a business.
		with signup_enabled():
			client, review = start_signup(
				full_name=person, phone=phone, email=email,
				account_type="Company", company_name=company,
			)
			verify_both_channels(client)
			resolved = client.call(signup_api.resolve)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=False)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		sess = frappe.get_all("Webshop Signup Session",
		                      filters={"email_normalized": email}, pluck="name",
		                      order_by="creation desc")[0]
		conflict = frappe.get_all("Webshop Identity Conflict",
		                          filters={"signup_session": sess}, pluck="name")
		self.assertTrue(conflict, "coming back as a business raised nothing")
		return conflict[0], company

	def test_the_type_disagreement_is_recorded(self):
		conflict, _company = self.returning_owner_says_company()
		self.assertIn("ACCOUNT_TYPE_MISMATCH", problem_types(conflict))

	def test_both_type_answers_are_offered(self):
		conflict, company = self.returning_owner_says_company()
		options = conflicts_api.get_resolution_options(conflict)

		# Switch it to a company...
		self.assertEqual(options["company_conversion"], company)
		# ...and the section exists for the buttons to live in.
		self.assertIn("ACCOUNT_TYPE_MISMATCH", [p["problem_type"] for p in options["problems"]])

	def test_the_case_can_be_answered_all_the_way(self):
		conflict, company = self.returning_owner_says_company()

		conflicts_api.resolve_conflict(conflict, "make_company")
		outstanding = frappe.get_all("Webshop Identity Problem",
		                             filters={"parent": conflict, "resolved": 0},
		                             pluck="problem_type")
		for problem in list(outstanding):
			conflicts_api.resolve_conflict(conflict, "apply_name")
			break

		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", conflict, "status"), "Resolved"
		)
		customer = frappe.db.get_value("Webshop Identity Conflict", conflict, "created_customer")
		self.assertEqual(frappe.db.get_value("Customer", customer, "customer_type"), "Company")
		self.assertEqual(frappe.db.get_value("Customer", customer, "customer_name"), company)


class TestEveryQuestionCanBeAnswered(ConflictTestCase):
	"""A section with no answer leaves the case stuck open forever.

	Some questions have no button of their own: a dispute about an
	address rather than a name has no name to apply, and a record already
	of the right kind has nothing to convert. Marking one settled with
	nothing changed is the answer in those cases.
	"""

	def a_dispute_with_no_name_to_apply(self):
		person = unique_name("Khaled")
		phone, email = unique_phone(), unique_email()
		make_customer_with_contact(customer_name=person, contact_name=person, phone=phone)

		with signup_enabled():
			client, _r = self.run_flow(person, phone, email)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		# Back again, same name, disputing what is stored.
		with signup_enabled():
			client, _r = start_signup(full_name=person, phone=phone, email=email)
			verify_both_channels(client)
			client.call(signup_api.resolve)
			client.call(signup_api.decide, accept=False)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		sess = frappe.get_all("Webshop Signup Session", filters={"email_normalized": email},
		                      pluck="name", order_by="creation desc")[0]
		return frappe.get_all("Webshop Identity Conflict",
		                      filters={"signup_session": sess}, pluck="name")[0]

	def test_the_name_question_has_no_button_of_its_own(self):
		# The premise: the names agree, so there is nothing to apply.
		conflict = self.a_dispute_with_no_name_to_apply()
		options = conflicts_api.get_resolution_options(conflict)

		self.assertIn("PROFILE_DISCREPANCY", problem_types(conflict))
		self.assertFalse(options["nameable"])
		self.assertIsNone(options["foreign_name"])

	def test_it_can_still_be_settled_and_closes_the_case(self):
		conflict = self.a_dispute_with_no_name_to_apply()

		result = conflicts_api.resolve_conflict(
			conflict, "settle_one", problem="PROFILE_DISCREPANCY"
		)

		self.assertTrue(result["closed"], "the case could not be closed")
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", conflict, "status"), "Resolved"
		)

	def test_it_settles_only_the_one_named(self):
		state = self.rejected_signup()
		before = problem_types(state["conflict"])
		self.assertIn("USER_REJECTED_MATCH", before)
		self.assertIn("PHONE_ALREADY_ASSOCIATED", before)

		conflicts_api.resolve_conflict(
			state["conflict"], "settle_one", problem="USER_REJECTED_MATCH"
		)

		outstanding = frappe.get_all("Webshop Identity Problem",
		                             filters={"parent": state["conflict"], "resolved": 0},
		                             pluck="problem_type")
		self.assertIn("PHONE_ALREADY_ASSOCIATED", outstanding)
		self.assertNotIn("USER_REJECTED_MATCH", outstanding)
		self.assertEqual(
			frappe.db.get_value("Webshop Identity Conflict", state["conflict"], "status"),
			"Open",
		)

	def test_it_refuses_without_saying_which(self):
		state = self.rejected_signup()
		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(state["conflict"], "settle_one")


class TestConvertingBetweenPersonAndBusiness(ConflictTestCase):
	"""Both directions, and the contact kept in step with the customer.

	A Customer of type Individual *is* a person and a Company *is* a
	business, so converting one to the other has to move the name as well
	as the type - and the Contact's own company name has to follow, since
	that is what says which business the person belongs to.
	"""

	def returning_owner_claims_a_business(self):
		"""The path that had the bug: coming back to an account you own.

		The signup writes `Contact.company_name` when it builds or reuses
		a Contact, but not when somebody signs back in to an account they
		already have - so the claim never reached the record.
		"""
		person, company = unique_name("Khaled"), unique_name("Qarafa")
		phone, email = unique_phone(), unique_email()
		customer, contact = make_customer_with_contact(
			customer_name=person, contact_name=person, phone=phone
		)

		with signup_enabled():
			client, _r = self.run_flow(person, phone, email)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		with signup_enabled():
			client, _r = start_signup(
				full_name=person, phone=phone, email=email,
				account_type="Company", company_name=company,
			)
			verify_both_channels(client)
			client.call(signup_api.resolve)
			client.call(signup_api.decide, accept=False)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		sess = frappe.get_all("Webshop Signup Session", filters={"email_normalized": email},
		                      pluck="name", order_by="creation desc")[0]
		conflict = frappe.get_all("Webshop Identity Conflict",
		                          filters={"signup_session": sess}, pluck="name")[0]
		return {"conflict": conflict, "customer": customer.name,
		        "contact": contact.name, "company": company, "person": person}

	def test_switching_to_a_company_puts_it_on_the_contact(self):
		state = self.returning_owner_claims_a_business()
		# The premise: this path left it empty.
		self.assertIsNone(frappe.db.get_value("Contact", state["contact"], "company_name"))

		conflicts_api.resolve_conflict(state["conflict"], "make_company")

		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "company_name"), state["company"]
		)
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_type"), "Company"
		)
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_name"), state["company"]
		)
		# The person's own name is not touched by any of it.
		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "full_name"), state["person"]
		)

	def a_business_record_signed_into_as_a_person(self):
		person, business = unique_name("Khaled"), unique_name("Acme")
		phone, email = unique_phone(), unique_email()
		customer, contact = make_customer_with_contact(
			customer_name=business, contact_name=person, phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")
		frappe.db.set_value("Contact", contact.name, "company_name", business)

		with signup_enabled():
			client, review = self.run_flow(person, phone, email)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		sess = frappe.db.get_value("Webshop Signup Session", {"email_normalized": email}, "name")
		conflict = frappe.get_all("Webshop Identity Conflict",
		                          filters={"signup_session": sess}, pluck="name")[0]
		return {"conflict": conflict, "customer": customer.name,
		        "contact": contact.name, "business": business, "person": person}

	def test_the_reverse_switch_is_offered(self):
		state = self.a_business_record_signed_into_as_a_person()
		options = conflicts_api.get_resolution_options(state["conflict"])

		self.assertEqual(options["individual_conversion"], state["person"])
		# The other direction has nothing to offer here.
		self.assertIsNone(options["company_conversion"])

	def test_switching_to_an_individual_takes_the_persons_name(self):
		state = self.a_business_record_signed_into_as_a_person()

		conflicts_api.resolve_conflict(state["conflict"], "make_individual")

		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_type"), "Individual"
		)
		# An Individual customer is a person, so it carries a person's name.
		self.assertEqual(
			frappe.db.get_value("Customer", state["customer"], "customer_name"), state["person"]
		)

	def test_it_clears_a_company_name_that_named_this_record(self):
		state = self.a_business_record_signed_into_as_a_person()

		conflicts_api.resolve_conflict(state["conflict"], "make_individual")

		self.assertIsNone(frappe.db.get_value("Contact", state["contact"], "company_name"))

	def test_it_leaves_a_company_name_that_names_somewhere_else(self):
		# Where they work is none of this app's business.
		state = self.a_business_record_signed_into_as_a_person()
		elsewhere = unique_name("Beta")
		frappe.db.set_value("Contact", state["contact"], "company_name", elsewhere)

		conflicts_api.resolve_conflict(state["conflict"], "make_individual")

		self.assertEqual(
			frappe.db.get_value("Contact", state["contact"], "company_name"), elsewhere
		)

	def test_neither_switch_is_offered_when_the_types_agree(self):
		person = unique_name("Khaled")
		phone, email = unique_phone(), unique_email()
		customer, _c = make_customer_with_contact(
			customer_name=person, contact_name=person, phone=phone
		)
		with signup_enabled():
			client, _r = self.run_flow(unique_name("Mohamed"), phone, email)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		conflict = conflict_with("ACCOUNT_TYPE_MISMATCH", created_customer=customer.name)
		self.assertIsNone(conflict, "types that agree should raise no type problem")

	def test_the_reverse_switch_refuses_when_it_does_not_apply(self):
		state = self.returning_owner_claims_a_business()
		with self.assertRaises(frappe.ValidationError):
			conflicts_api.resolve_conflict(state["conflict"], "make_individual")
