# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""End-to-end tests for the verified signup API.

Covers the scenario list the flow was specified against, each one asserting
the resulting database state rather than just the response - the thing that
matters is what ended up in ERPNext, not what the endpoint said.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from custom_webshop.api import signup as signup_api
from custom_webshop.signup import linking, matching, otp, session
from custom_webshop.signup.identity import to_e164
from custom_webshop.tests.test_matching import make_identity, make_website_user
from custom_webshop.tests.utils import (
	conflict_with,
	answer_name_card,
	make_customer_sharing_a_phone,
	make_customer_with_contact,
	signup_enabled,
	signup_settings_as,
	start_signup,
	unique_email,
	unique_name,
	unique_phone,
	verify_both_channels,
)

PASSWORD = "Str0ng-Passw0rd!x7"


class SignupFlowTestCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def run_to_ready(self, **kwargs):
		"""Start a signup and take it through both verifications and resolution.

		Returns:
			A (client, envelope) tuple, where the envelope is from resolve.
		"""
		client, _started = start_signup(**kwargs)
		verify_both_channels(client)
		return client, client.call(signup_api.resolve)

	def complete(self, client, password=PASSWORD):
		"""Finish a signup that has reached READY."""
		return client.call(
			signup_api.complete, password=password, confirm_password=password
		)


class TestNewAccounts(SignupFlowTestCase):
	def test_scenario_1_new_individual(self):
		name, email, phone = unique_name(), unique_email(), unique_phone()

		with signup_enabled():
			client, resolved = self.run_to_ready(full_name=name, email=email, phone=phone)
			self.assertEqual(resolved["state"], session.READY)
			result = self.complete(client)

		self.assertEqual(result["state"], session.COMPLETED)
		self.assertEqual(result["data"]["redirect_to"], "/shop")

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.resolution, linking.CREATE_NEW)
		self.assertEqual(doc.match_result, matching.NO_MATCH)

		self.assertTrue(frappe.db.exists("User", email))
		self.assertEqual(frappe.db.get_value("User", email, "user_type"), "Website User")

		identity = frappe.db.get_value(
			"Webshop Account Identity",
			{"user": email},
			["customer", "phone_e164", "email_normalized", "linked_existing_customer"],
			as_dict=True,
		)
		self.assertEqual(identity.phone_e164, to_e164(phone))
		self.assertEqual(identity.email_normalized, email)
		self.assertFalse(identity.linked_existing_customer)

		customer = frappe.get_doc("Customer", identity.customer)
		self.assertEqual(customer.customer_name, name)
		self.assertEqual(customer.customer_type, "Individual")
		self.assertTrue(customer.customer_primary_contact)
		self.assertTrue(
			frappe.db.exists(
				"Portal User", {"parent": customer.name, "user": email, "parenttype": "Customer"}
			)
		)

	def test_scenario_2_new_company(self):
		company = unique_name("Acme")
		person = unique_name("Ahmed")
		email = unique_email()

		with signup_enabled():
			client, _resolved = self.run_to_ready(
				account_type="Company", full_name=person, company_name=company, email=email
			)
			self.complete(client)

		identity = frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer")
		customer = frappe.get_doc("Customer", identity)
		self.assertEqual(customer.customer_name, company)
		self.assertEqual(customer.customer_type, "Company")

		# The Contact is always a person, even for a company account.
		contact = frappe.get_doc("Contact", customer.customer_primary_contact)
		self.assertEqual(contact.first_name, person)

	def test_created_customer_is_saveable_from_the_desk(self):
		"""The contact_enhancements compatibility guarantee.

		A Customer created with ignore_mandatory that staff then cannot
		re-save is a trap; only the address may legitimately be missing.
		"""
		with signup_enabled():
			client, _resolved = self.run_to_ready()
			self.complete(client)

		customer_name = frappe.db.get_value(
			"Webshop Account Identity", {"signup_session": ["is", "set"]}, "customer"
		)
		customer = frappe.get_doc("Customer", customer_name)
		self.assertTrue(customer.customer_primary_contact, "primary contact must be set")

		# Everything except the deferred address must already satisfy the
		# mandatory rules, so adding one makes the record fully saveable.
		address = frappe.new_doc("Address")
		address.update(
			{
				"address_title": customer.customer_name,
				"address_type": "Shipping",
				"address_line1": "1 Test Street",
				"city": "Damietta",
				"country": "Egypt",
			}
		)
		address.append("links", {"link_doctype": "Customer", "link_name": customer.name})
		address.flags.ignore_permissions = True
		address.insert(ignore_permissions=True)

		customer.customer_primary_address = address.name
		customer.save(ignore_permissions=True)


class TestExistingCustomerMatching(SignupFlowTestCase):
	def test_scenario_3_exact_match_links_after_confirmation(self):
		name, phone = unique_name("Ahmed"), unique_phone()
		existing, _contact = make_customer_with_contact(customer_name=name, phone=phone)
		email = unique_email()

		with signup_enabled():
			client, resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			# Only the first token is shown, even here where the names
			# agree - `names_match` accepts a stored name with tokens the
			# person never typed.
			self.assertEqual(
				resolved["data"]["recognition"]["name"].split()[0], name.split()[0]
			)

			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		identity = frappe.db.get_value(
			"Webshop Account Identity",
			{"user": email},
			["customer", "linked_existing_customer"],
			as_dict=True,
		)
		self.assertEqual(identity.customer, existing.name)
		self.assertTrue(identity.linked_existing_customer)

		# No duplicate Customer was created for this person.
		self.assertEqual(
			frappe.db.count("Customer", {"customer_name": name}),
			1,
			"a duplicate Customer was created despite an exact match",
		)

	def test_scenario_3_link_preserves_the_existing_customers_identity(self):
		"""Rule 8: linking must never rewrite existing business data."""
		name, phone = unique_name("Ahmed"), unique_phone()
		existing, contact = make_customer_with_contact(customer_name=name, phone=phone)
		before = frappe.db.get_value(
			"Customer", existing.name, ["customer_name", "customer_type", "customer_group"], as_dict=True
		)
		contact_name_before = frappe.db.get_value("Contact", contact.name, "first_name")

		with signup_enabled():
			client, _resolved = self.run_to_ready(full_name=name, phone=phone)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		after = frappe.db.get_value(
			"Customer", existing.name, ["customer_name", "customer_type", "customer_group"], as_dict=True
		)
		self.assertEqual(before, after)
		self.assertEqual(
			frappe.db.get_value("Contact", contact.name, "first_name"), contact_name_before
		)

	def test_scenario_4_phone_name_mismatch_is_asked_about(self):
		"""The person decides, and the engine never does.

		This used to skip the question and always create a new Customer,
		on the reasoning that the answer would not change the outcome. It
		does change it - a name can be a maiden name, a transliteration,
		or simply out of date, and only the person can say so - so the
		card is shown, with the stored name on it: a verified phone is
		trusted to identify its holder, and the disagreement is the very
		thing they need to see in order to answer.
		"""
		phone = unique_phone()
		other_name = unique_name("Mohamed")
		existing, _c = make_customer_with_contact(customer_name=other_name, phone=phone)
		email = unique_email()

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Ahmed"), phone=phone, email=email
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			self.assertEqual(resolved["data"]["recognition"]["name"], other_name)

			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		identity = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, ["customer", "linked_existing_customer"], as_dict=True
		)
		self.assertEqual(identity.customer, existing.name)
		self.assertTrue(identity.linked_existing_customer)

		# Linked, and the record keeps its own name. `answer_name_card`
		# takes the stored spelling, which disputes nothing - so nothing
		# is queued, and the assertion that matters is that the older
		# record was not quietly rewritten to agree with the signup.
		self.assertEqual(
			frappe.get_all(
				"Webshop Identity Conflict",
				filters={"phone_e164": to_e164(phone)},
				pluck="conflict_type",
			),
			[],
		)
		self.assertEqual(
			frappe.db.get_value("Customer", existing.name, "customer_name"),
			other_name,
			"the existing record was rewritten to agree with the signup",
		)

	def test_linking_never_renames_the_records_it_links_to(self):
		"""The overwrite this whole design exists to prevent.

		Frappe's `User.on_update` enqueues `create_contact`, which finds
		the Contact holding the new account's email - the existing one,
		after a link - and assigns `first_name`, `last_name` and `gender`
		from the User outright. contact_enhancements then propagates the
		name onto the Customer. So confirming "yes, that is me" used to
		rename a stranger's Contact and Customer to whatever was typed,
		and blank their surname and gender along with it, because the new
		account carried none.

		Asserted on every field that job touches rather than just the one
		that was noticed, and on both records, because the propagation
		means either can be the first place it shows.
		"""
		phone = unique_phone()
		other_name = unique_name("Mohamed")
		existing, contact = make_customer_with_contact(customer_name=other_name, phone=phone)
		# Saved as a document, not written behind its back: `full_name` is
		# derived on save, and contact_enhancements propagates it onto the
		# Customer, so a field poked straight into the column would only
		# take effect part-way through the signup and look like our doing.
		contact.last_name = "Elgendy"
		contact.flags.ignore_permissions = True
		contact.save(ignore_permissions=True)

		# Whatever the records say once they are set up is what they must
		# still say afterwards.
		before = frappe.db.get_value(
			"Contact", contact.name, ["first_name", "last_name", "gender"], as_dict=True
		)
		customer_name_before = frappe.db.get_value("Customer", existing.name, "customer_name")

		email = unique_email()
		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Ahmed"), phone=phone, email=email
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		after = frappe.db.get_value(
			"Contact", contact.name, ["first_name", "last_name", "gender"], as_dict=True
		)
		self.assertEqual(after, before, "the linked contact was rewritten")
		self.assertEqual(
			frappe.db.get_value("Customer", existing.name, "customer_name"),
			customer_name_before,
			"the linked customer was renamed",
		)
		# And the account still exists and points at that record.
		self.assertEqual(
			frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer"),
			existing.name,
		)

	def test_scenario_4_a_disagreeing_name_is_shown_and_offered_as_a_choice(self):
		other_name = unique_name("Mohamed")
		phone = unique_phone()
		make_customer_with_contact(customer_name=other_name, phone=phone)

		with signup_enabled():
			client, resolved = self.run_to_ready(full_name=unique_name("Ahmed"), phone=phone)
			self.assertEqual(resolved["data"]["recognition"]["name"], other_name)

			# Seeing it is only half of it: the point of showing the name
			# is that they can then say which one their account carries.
			answered = client.call(signup_api.decide, accept=True)

		self.assertIn("name_choice", answered["data"])
		self.assertEqual(answered["data"]["name_choice"]["stored"], other_name)

	def test_scenario_5_user_rejects_the_match(self):
		name, phone = unique_name("Ahmed"), unique_phone()
		existing, _c = make_customer_with_contact(customer_name=name, phone=phone)
		email = unique_email()

		with signup_enabled():
			client, resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=False)
			self.complete(client)

		identity = frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer")
		self.assertNotEqual(identity, existing.name)
		self.assertTrue(
			conflict_with("USER_REJECTED_MATCH", phone_e164=to_e164(phone)) is not None
		)

	def test_scenario_6_multiple_customers_on_one_phone(self):
		phone = unique_phone()
		first, _a = make_customer_with_contact(phone=phone)
		second = make_customer_sharing_a_phone(phone)
		email = unique_email()

		with signup_enabled():
			client, resolved = self.run_to_ready(phone=phone, email=email)
			self.assertEqual(resolved["state"], session.READY)
			self.complete(client)

		identity = frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer")
		self.assertNotIn(identity, (first.name, second.name), "the engine picked a winner")

		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("MULTIPLE_PHONE_MATCHES", phone_e164=to_e164(phone)),
			["status", "candidate_customers"],
			as_dict=True,
		)
		self.assertEqual(conflict.status, "Open")
		self.assertIn(first.name, conflict.candidate_customers)
		self.assertIn(second.name, conflict.candidate_customers)

	def test_scenario_7_customer_already_has_an_account(self):
		phone = unique_phone()
		existing, _c = make_customer_with_contact(customer_name=unique_name("Ahmed"), phone=phone)
		other_user = make_website_user(unique_email())
		make_identity(other_user.name, existing.name, to_e164(unique_phone()), other_user.name)

		email = unique_email()
		with signup_enabled():
			_client, resolved = self.run_to_ready(phone=phone, email=email)

		self.assertEqual(resolved["state"], session.BLOCKED)
		self.assertFalse(frappe.db.exists("User", email), "a blocked signup created an account")
		self.assertTrue(
			conflict_with(matching.CUSTOMER_ALREADY_LINKED) is not None
		)


class TestARecordWithNoAccountYet(SignupFlowTestCase):
	"""A Customer and Contact that nobody has ever signed up against.

	The ordinary shape of an existing shop: staff entered the customer, or
	a phone order left the records behind, and the person is only now
	creating a login. Both their email and their phone are already on that
	record, so proving them proves the record is theirs - but there is no
	account yet, so "yes" has to make one, and making one needs a password.
	"""

	def record_without_an_account(self, name=None):
		phone, email = unique_phone(), unique_email()
		stored = name or unique_name("Ahmed")
		customer, contact = make_customer_with_contact(
			customer_name=stored, phone=phone, email=email
		)
		self.assertFalse(frappe.db.exists("User", email), "fixture already has an account")
		return {
			"phone": phone,
			"email": email,
			"stored": stored,
			"customer": customer.name,
			"contact": contact.name,
		}

	def test_yes_creates_the_account_against_the_existing_records(self):
		record = self.record_without_an_account()

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=record["stored"], phone=record["phone"], email=record["email"]
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			decided = answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.assertEqual(decided["state"], session.READY)
			self.complete(client)

		identity = frappe.db.get_value(
			"Webshop Account Identity",
			{"user": record["email"]},
			["customer", "contact", "linked_existing_customer"],
			as_dict=True,
		)
		self.assertTrue(frappe.db.exists("User", record["email"]), "no account was created")
		self.assertEqual(identity.customer, record["customer"])
		self.assertEqual(identity.contact, record["contact"])
		self.assertTrue(identity.linked_existing_customer)
		# No duplicate was made alongside it.
		self.assertEqual(
			frappe.db.count("Customer", {"customer_name": record["stored"]}), 1
		)

	def test_the_password_step_is_asked_for_and_is_the_login(self):
		from frappe.utils.password import check_password

		record = self.record_without_an_account()

		with signup_enabled():
			client, _resolved = self.run_to_ready(
				full_name=record["stored"], phone=record["phone"], email=record["email"]
			)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			# No `recovering` flag: this is a first password, not a
			# replacement, and the step is labelled accordingly.
			doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
			self.assertEqual(doc.resolution, linking.LINK_EXISTING)
			self.complete(client)

		check_password(record["email"], PASSWORD)

	def test_accepting_a_name_you_were_shown_raises_nothing(self):
		"""A4. They read the stored name and said yes to it.

		Names disagreeing is not on its own worth anybody's time - a
		maiden name, a transliteration, an old spelling. Queuing it
		anyway only buried the conflicts that do need a person.
		"""
		record = self.record_without_an_account()

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=record["phone"], email=record["email"]
			)
			# The name is on the card, so saying yes is saying yes to it.
			self.assertEqual(resolved["data"]["recognition"]["name"], record["stored"])
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.resolution, linking.LINK_EXISTING)
		self.assertFalse(
			conflict_with("PROFILE_DISCREPANCY", signup_session=doc.name) is not None,
			"a name the person read and accepted was queued for staff anyway",
		)
		# Still linked to the existing record, still under its own name.
		self.assertEqual(
			frappe.db.get_value("Webshop Account Identity", {"user": record["email"]}, "customer"),
			record["customer"],
		)
		self.assertEqual(
			frappe.db.get_value("Customer", record["customer"], "customer_name"), record["stored"]
		)

	def test_keeping_the_stored_name_queues_nothing(self):
		"""A5, under the phone-trust rule.

		The name is shown now, so a "yes" is an answer to something the
		person actually read. Keeping the record's own spelling changes
		nothing and disputes nothing, so there is nothing for staff to
		look at - the queue stays for the cases that need a person.
		"""
		record = self.record_without_an_account()

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=record["phone"], email=unique_email()
			)
			self.assertEqual(resolved["data"]["recognition"]["name"], record["stored"])
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(
			frappe.get_all(
				"Webshop Identity Conflict",
				filters={"signup_session": doc.name},
				pluck="conflict_type",
			),
			[],
		)
		self.assertEqual(
			frappe.db.get_value("Customer", record["customer"], "customer_name"), record["stored"]
		)

	def test_taking_the_name_for_your_own_account_is_queued(self):
		"""The half that still needs a person.

		Saying "use the name I just entered" is a claim against a record
		that disagrees, so the account takes it and the business records
		wait for somebody to agree.
		"""
		record = self.record_without_an_account()
		mine = unique_name("Mohamed")

		with signup_enabled():
			client, _resolved = self.run_to_ready(
				full_name=mine, phone=record["phone"], email=unique_email()
			)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.choose_name, use_submitted=True)
			self.complete(client)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertTrue(
			conflict_with("PROFILE_DISCREPANCY", signup_session=doc.name) is not None,
			"a name taken from a disagreeing record was not queued",
		)
		# The account carries it; the business records do not.
		self.assertEqual(frappe.db.get_value("User", doc.email_normalized, "full_name"), mine)
		self.assertEqual(
			frappe.db.get_value("Customer", record["customer"], "customer_name"), record["stored"]
		)

	def test_the_card_shows_the_name_even_when_it_disagrees(self):
		"""Both channels reach this one record, so there is nobody to protect.

		The phone alone is now enough to show the name, so this is no
		longer the case that distinguishes disclosure - it is kept
		because reaching a record by both channels is a different fact
		about the world, and the card must show the name for that reason
		too, not only by the phone rule.
		"""
		record = self.record_without_an_account()

		with signup_enabled():
			_client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=record["phone"], email=record["email"]
			)

		self.assertEqual(resolved["state"], session.MATCH_REVIEW)
		self.assertEqual(resolved["data"]["recognition"]["name"], record["stored"])

	def test_a_record_reached_by_the_phone_alone_shows_its_name(self):
		"""The phone is trusted on its own, by decision.

		It used to be withheld here, on the grounds that a reassigned
		number would hand a stranger's name over. That risk is accepted:
		the number is treated as identifying its holder, and the name is
		what makes the following question answerable.
		"""
		record = self.record_without_an_account()

		with signup_enabled():
			_client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=record["phone"], email=unique_email()
			)

		self.assertEqual(resolved["state"], session.MATCH_REVIEW)
		self.assertEqual(resolved["data"]["recognition"]["name"], record["stored"])


class TestComingBackToYourOwnAccount(SignupFlowTestCase):
	"""Both channels proving one account is the owner, not a collision.

	Signing up again with the email *and* the phone of an existing account
	used to end at "an account already exists, please sign in" - which is
	no help at all to the person who came here precisely because they
	could not sign in, and a dead end they could not get out of.

	It is safe to offer the account back, because reaching this point
	means verifying both channels in one session, and Frappe's own
	password reset asks for the mailbox alone. The name they type does not
	come into it: they are being let into a record, not editing one.
	"""

	def existing_account(self):
		"""Run one full signup and return what it produced."""
		phone, email = unique_phone(), unique_email()
		name = unique_name("Ahmed")
		with signup_enabled():
			client, _resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			self.complete(client)

		identity = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, ["customer", "contact"], as_dict=True
		)
		return {
			"phone": phone,
			"email": email,
			"name": name,
			"customer": identity.customer,
			"contact": identity.contact,
		}

	def come_back(self, first, accept):
		"""Sign up again with the same details under a different name."""
		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=first["phone"], email=first["email"]
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			decided = client.call(signup_api.decide, accept=accept)
			decided = answer_name_card(client, decided)
			return client, resolved, decided

	def test_the_card_is_shown_rather_than_a_dead_end(self):
		first = self.existing_account()
		_client, resolved, _decided = self.come_back(first, accept=True)

		card = resolved["data"]["recognition"]
		self.assertEqual(card["kind"], "own_account")
		self.assertIn("decide", resolved["allowed_actions"])
		# Their own account, so their own name is not withheld from them -
		# but the phone is still masked and the governorate still hidden.
		self.assertTrue(card["name"].startswith(first["name"].split()[0]))
		self.assertNotIn(first["phone"].lstrip("0"), card["phone"])

	def test_yes_still_asks_for_a_password(self):
		"""Every route through the card ends at the password step.

		The card is shown for records with no website account at all - a
		Customer and Contact staff created, or a previous order left
		behind - and those need one made. Where an account does exist the
		person is replacing a password they could not remember, which is
		why they are here at all.
		"""
		first = self.existing_account()

		_client, _resolved, decided = self.come_back(first, accept=True)

		self.assertEqual(decided["state"], session.READY)
		self.assertIn("complete", decided["allowed_actions"])
		# The step is labelled from this, so that it reads as replacing a
		# password rather than being handed a second account.
		self.assertEqual(decided["data"]["recovering"], "accepted")

	def test_yes_signs_them_back_in_and_creates_nothing(self):
		from frappe.utils.password import check_password

		first = self.existing_account()
		replacement = "An0ther-Passw0rd!q4"

		client, _resolved, _decided = self.come_back(first, accept=True)
		with signup_enabled():
			done = client.call(
				signup_api.complete, password=replacement, confirm_password=replacement
			)

		self.assertEqual(done["state"], session.COMPLETED)
		self.assertEqual(frappe.db.count("User", {"email": first["email"]}), 1)
		self.assertEqual(
			frappe.db.count("Webshop Account Identity", {"user": first["email"]}), 1
		)
		self.assertTrue(frappe.db.exists("Customer", first["customer"]))
		# The password they just chose is the one that works from now on.
		check_password(first["email"], replacement)

	def test_yes_still_refuses_a_weak_or_mismatched_password(self):
		# The step is real, not a formality it waves through.
		first = self.existing_account()
		client, _resolved, _decided = self.come_back(first, accept=True)

		with signup_enabled():
			self.assertRaises(
				frappe.ValidationError,
				client.call,
				signup_api.complete,
				password="An0ther-Passw0rd!q4",
				confirm_password="something-else",
			)

		self.assertEqual(
			frappe.db.get_value(
				"Webshop Signup Session", {"signup_id": client.signup_id}, "status"
			),
			session.READY,
		)

	def test_yes_raises_no_conflict_and_renames_nothing(self):
		first = self.existing_account()
		before = frappe.db.get_value("Contact", first["contact"], "first_name")

		client, _resolved, _decided = self.come_back(first, accept=True)
		with signup_enabled():
			client.call(
				signup_api.complete, password="An0ther-Passw0rd!q4", confirm_password="An0ther-Passw0rd!q4"
			)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.resolution, linking.RECOVER_EXISTING)
		self.assertFalse(
			frappe.db.exists(
				"Webshop Identity Conflict",
				{"signup_session": doc.name, "status": ["in", ("Open", "In Review")]},
			),
			"recovering your own account is not a conflict",
		)
		self.assertEqual(frappe.db.get_value("Contact", first["contact"], "first_name"), before)

	def test_no_lets_them_carry_on_rather_than_stopping_them(self):
		""""That is not me" almost always means "that name is not mine".

		The email and the number are both theirs - that is how they got
		here. Blocking them over the name left the one person who could
		clear it up staring at a dead end, so they carry on, set their own
		password, and get in.
		"""
		from frappe.utils.password import check_password

		first = self.existing_account()
		chosen = "An0ther-Passw0rd!q4"

		client, _resolved, decided = self.come_back(first, accept=False)
		self.assertEqual(decided["state"], session.READY)
		self.assertEqual(decided["data"]["recovering"], "disputed")

		with signup_enabled():
			done = client.call(signup_api.complete, password=chosen, confirm_password=chosen)

		self.assertEqual(done["state"], session.COMPLETED)
		self.assertEqual(frappe.db.count("User", {"email": first["email"]}), 1)
		# The password they just chose is theirs from now on.
		check_password(first["email"], chosen)

	def test_no_asks_staff_about_the_name_and_changes_nothing_itself(self):
		first = self.existing_account()
		before = frappe.db.get_value("Contact", first["contact"], "full_name")
		chosen = "An0ther-Passw0rd!q4"

		client, _resolved, _decided = self.come_back(first, accept=False)
		with signup_enabled():
			client.call(signup_api.complete, password=chosen, confirm_password=chosen)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PROFILE_DISCREPANCY", signup_session=doc.name),
			["status", "submitted_name", "created_user", "created_customer"],
			as_dict=True,
		)
		self.assertEqual(conflict.status, "Open")
		self.assertEqual(conflict.created_user, first["email"])
		self.assertEqual(conflict.created_customer, first["customer"])
		self.assertTrue(conflict.submitted_name.startswith("Mohamed"))

		# A name typed into a form is a claim, not a correction.
		self.assertEqual(frappe.db.get_value("Contact", first["contact"], "full_name"), before)
		self.assertEqual(
			frappe.db.get_value("Customer", first["customer"], "customer_name"), before
		)

	def test_the_card_shows_the_whole_name(self):
		first = self.existing_account()
		_client, resolved, _decided = self.come_back(first, accept=True)

		self.assertEqual(resolved["data"]["recognition"]["name"], first["name"])

	def test_one_channel_alone_is_still_not_ownership(self):
		"""A recycled phone number must not open somebody else's account."""
		first = self.existing_account()

		with signup_enabled():
			_client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=first["phone"], email=unique_email()
			)

		self.assertEqual(resolved["state"], session.BLOCKED)
		self.assertNotIn("decide", resolved["allowed_actions"])

	def test_an_email_on_one_account_and_a_phone_on_another_still_blocks(self):
		first = self.existing_account()
		second = self.existing_account()

		with signup_enabled():
			_client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=first["phone"], email=second["email"]
			)

		self.assertEqual(resolved["state"], session.BLOCKED)

	def test_a_disabled_account_is_not_offered_back(self):
		first = self.existing_account()
		frappe.db.set_value("User", first["email"], "enabled", 0, update_modified=False)

		with signup_enabled():
			_client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=first["phone"], email=first["email"]
			)

		self.assertEqual(resolved["state"], session.BLOCKED)


class TestTheAccountAndItsContactPointAtEachOther(SignupFlowTestCase):
	"""A link only one way round is not a link.

	`Contact.user` was set and nothing else, so the Desk's own User form
	showed an empty "User Primary Contact" - the field contact_enhancements
	reads to keep the two in step, and the one its `link_user_contact`
	hook turns into the Dynamic Link on the Contact. Neither existed.
	"""

	def test_a_new_signup_links_both_ways(self):
		email, phone = unique_email(), unique_phone()
		with signup_enabled():
			client, _resolved = self.run_to_ready(email=email, phone=phone)
			self.complete(client)

		contact = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, "contact"
		)
		self.assertTrue(contact)
		self.assertEqual(frappe.db.get_value("Contact", contact, "user"), email)

		if frappe.get_meta("User").has_field("user_primary_contact"):
			self.assertEqual(
				frappe.db.get_value("User", email, "user_primary_contact"),
				contact,
				"the account does not point back at its contact",
			)
			self.assertTrue(
				frappe.db.exists(
					"Dynamic Link",
					{
						"parenttype": "Contact",
						"parent": contact,
						"link_doctype": "User",
						"link_name": email,
					},
				),
				"contact_enhancements' own link between the two was never built",
			)


class TestWhoseNameEndsUpWhere(SignupFlowTestCase):
	"""The account may be renamed. The business records may not.

	A name typed into a signup form is a claim. The account is the
	person's own, so it follows them immediately. The Contact and the
	Customer carry order history and belong to the business, so they wait
	for somebody in the Desk to agree.

	The trap this is really guarding: renaming a User the ordinary way
	fires `on_update`, which enqueues Frappe's `create_contact`, which
	assigns `first_name`/`last_name`/`gender` onto the Contact holding
	that email - and contact_enhancements then propagates it to the
	Customer. Renaming the account "properly" renames everything with it.
	"""

	def own_account(self):
		"""One finished signup, so a real account exists to come back to."""
		phone, email, name = unique_phone(), unique_email(), unique_name("Ahmed")
		with signup_enabled():
			client, _r = self.run_to_ready(full_name=name, phone=phone, email=email)
			self.complete(client)

		identity = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, ["customer", "contact"], as_dict=True
		)
		return {
			"phone": phone,
			"email": email,
			"stored": name,
			"customer": identity.customer,
			"contact": identity.contact,
		}

	def come_back(self, first, claimed, accept, use_submitted=None):
		"""Sign up again under a different name and answer the cards."""
		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=claimed, phone=first["phone"], email=first["email"]
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			decided = client.call(signup_api.decide, accept=accept)
			if use_submitted is not None:
				self.assertIn(
					"name_choice", decided["data"], "the second card was never offered"
				)
				decided = client.call(signup_api.choose_name, use_submitted=use_submitted)
			self.complete(client, password="Qamar7Nile")
		return client, decided

	def assert_records_untouched(self, first):
		self.assertEqual(
			frappe.db.get_value("Contact", first["contact"], "full_name"), first["stored"]
		)
		self.assertEqual(
			frappe.db.get_value("Customer", first["customer"], "customer_name"), first["stored"]
		)

	def test_this_is_not_my_data_renames_the_account_and_nothing_else(self):
		first = self.own_account()
		claimed = unique_name("Mohamed")

		self.come_back(first, claimed, accept=False)

		self.assertEqual(frappe.db.get_value("User", first["email"], "first_name"), claimed)
		self.assertEqual(frappe.db.get_value("User", first["email"], "full_name"), claimed)
		self.assert_records_untouched(first)

	def test_this_is_not_my_data_queues_the_rest_for_staff(self):
		first = self.own_account()
		claimed = unique_name("Mohamed")

		client, _d = self.come_back(first, claimed, accept=False)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PROFILE_DISCREPANCY", signup_session=doc.name),
			["status", "submitted_name"],
			as_dict=True,
		)
		self.assertEqual(conflict.status, "Open")
		self.assertEqual(conflict.submitted_name, claimed)

	def test_yes_asks_which_name_before_assuming_one(self):
		first = self.own_account()
		claimed = unique_name("Mohamed")

		with signup_enabled():
			client, _r = self.run_to_ready(
				full_name=claimed, phone=first["phone"], email=first["email"]
			)
			decided = client.call(signup_api.decide, accept=True)

		choice = decided["data"]["name_choice"]
		self.assertEqual(decided["state"], session.MATCH_REVIEW)
		self.assertEqual(choice["stored"], first["stored"])
		self.assertEqual(choice["submitted"], claimed)
		self.assertTrue(choice["own_account"])

	def test_yes_then_keep_changes_nothing_at_all(self):
		first = self.own_account()
		claimed = unique_name("Mohamed")

		client, decided = self.come_back(first, claimed, accept=True, use_submitted=False)

		self.assertEqual(decided["state"], session.READY)
		self.assertEqual(frappe.db.get_value("User", first["email"], "first_name"), first["stored"])
		self.assert_records_untouched(first)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertFalse(
			conflict_with("PROFILE_DISCREPANCY", signup_session=doc.name) is not None,
			"keeping the stored name is not a dispute",
		)

	def test_yes_then_use_mine_renames_the_account_and_nothing_else(self):
		first = self.own_account()
		claimed = unique_name("Mohamed")

		client, _d = self.come_back(first, claimed, accept=True, use_submitted=True)

		self.assertEqual(frappe.db.get_value("User", first["email"], "first_name"), claimed)
		self.assert_records_untouched(first)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertTrue(
			conflict_with("PROFILE_DISCREPANCY", signup_session=doc.name) is not None
		)

	def test_no_second_card_when_the_names_already_agree(self):
		first = self.own_account()

		with signup_enabled():
			client, _r = self.run_to_ready(
				full_name=first["stored"], phone=first["phone"], email=first["email"]
			)
			decided = client.call(signup_api.decide, accept=True)

		self.assertEqual(decided["state"], session.READY)
		self.assertNotIn("name_choice", decided["data"])

	def test_a_new_account_linked_to_a_record_follows_the_same_rule(self):
		"""Not only the own-account path: A4 offers the choice too."""
		phone, email = unique_phone(), unique_email()
		stored = unique_name("Ahmed")
		customer, contact = make_customer_with_contact(
			customer_name=stored, phone=phone, email=email
		)
		claimed = unique_name("Mohamed")

		with signup_enabled():
			client, resolved = self.run_to_ready(full_name=claimed, phone=phone, email=email)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			decided = client.call(signup_api.decide, accept=True)
			self.assertIn("name_choice", decided["data"])
			client.call(signup_api.choose_name, use_submitted=True)
			self.complete(client)

		self.assertEqual(frappe.db.get_value("User", email, "first_name"), claimed)
		self.assertEqual(frappe.db.get_value("Contact", contact.name, "full_name"), stored)
		self.assertEqual(
			frappe.db.get_value("Customer", customer.name, "customer_name"), stored
		)

	def test_the_staff_button_is_what_moves_it_to_the_records(self):
		"""End to end: the account is renamed, then a person agrees."""
		from custom_webshop.api import conflicts as conflicts_api

		first = self.own_account()
		claimed = unique_name("Mohamed")
		client, _d = self.come_back(first, claimed, accept=False)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PROFILE_DISCREPANCY", signup_session=doc.name),
			"name",
		)
		conflicts_api.resolve_conflict(conflict, "apply_name")

		self.assertEqual(frappe.db.get_value("Contact", first["contact"], "full_name"), claimed)
		self.assertEqual(
			frappe.db.get_value("Customer", first["customer"], "customer_name"), claimed
		)


class TestSayingNoAlwaysWorks(SignupFlowTestCase):
	"""The rejection path, which used to end in nothing at all.

	contact_enhancements allows one Contact to hold a given mobile number
	and no more - a validate hook and a unique index on a generated
	column, enforced across the whole table rather than within one record.
	So the Contact created for somebody who says "no, that is not me"
	cannot carry the number that surfaced the match: it is on the record
	they just declined.

	Appending it anyway threw, and because Frappe rolls the whole request
	back on an unhandled exception, a person who had proved both channels
	and answered honestly got no account, no conflict, and no explanation.
	These tests hold the shape that replaced it - the number is left off,
	recorded where staff can see it, and the account is finished.
	"""

	def reject_a_match(self, phone=None, name=None):
		"""Run a signup to a recognition card and answer no.

		Returns:
			An (email, existing_customer, existing_contact) tuple.
		"""
		phone = phone or unique_phone()
		name = name or unique_name("Ahmed")
		existing, contact = make_customer_with_contact(customer_name=name, phone=phone)
		email = unique_email()

		with signup_enabled():
			client, resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=False)
			self.complete(client)

		return email, existing, contact

	def test_the_account_is_created(self):
		email, existing, _contact = self.reject_a_match()

		self.assertTrue(frappe.db.exists("User", email), "saying no produced no account")
		identity = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, ["customer", "phone_e164"], as_dict=True
		)
		self.assertNotEqual(identity.customer, existing.name)
		# The number is still recorded against the account that proved it.
		self.assertTrue(identity.phone_e164)

	def test_the_number_stays_on_exactly_one_contact(self):
		phone = unique_phone()
		email, _existing, contact = self.reject_a_match(phone=phone)

		holders = frappe.get_all(
			"Contact Phone",
			filters={"parenttype": "Contact", "phone": to_e164(phone)},
			pluck="parent",
		)
		self.assertEqual(holders, [contact.name])

		new_contact = frappe.db.get_value("Contact", {"user": email}, "name")
		self.assertTrue(new_contact)
		self.assertNotEqual(new_contact, contact.name)
		self.assertEqual(
			frappe.db.count("Contact Phone", {"parenttype": "Contact", "parent": new_contact}),
			0,
			"the declined number was written onto the new contact after all",
		)

	def test_the_withheld_number_is_recorded_where_staff_can_see_it(self):
		phone = unique_phone()
		email, _existing, _contact = self.reject_a_match(phone=phone)

		new_contact = frappe.db.get_value("Contact", {"user": email}, "name")
		self.assertEqual(
			frappe.db.get_value("Contact", new_contact, "custom_pending_phone_e164"),
			to_e164(phone),
		)

	def test_the_account_carries_no_mobile_number_either(self):
		"""Frappe would put it straight back.

		`User.on_update` calls `create_contact`, which finds the Contact
		by the account's email and calls `add_phone` with `mobile_no` on
		it - appending, from inside somebody else's hook, the row that was
		just withheld.
		"""
		email, _existing, _contact = self.reject_a_match()
		self.assertFalse(frappe.db.get_value("User", email, "mobile_no"))

	def test_both_contacts_are_named_in_a_conflict(self):
		phone = unique_phone()
		email, _existing, contact = self.reject_a_match(phone=phone)
		new_contact = frappe.db.get_value("Contact", {"user": email}, "name")

		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("PHONE_ALREADY_ASSOCIATED", phone_e164=to_e164(phone)),
			["status", "created_user", "resolution_notes"],
			as_dict=True,
		)
		self.assertEqual(conflict.status, "Open")
		self.assertEqual(conflict.created_user, email)
		self.assertIn(contact.name, conflict.resolution_notes)
		self.assertIn(new_contact, conflict.resolution_notes)

	def test_the_rejection_conflict_is_raised_as_well(self):
		# Two problems, two records: why the account exists on its own
		# Customer, and which number it cannot hold.
		phone = unique_phone()
		email, _existing, _contact = self.reject_a_match(phone=phone)

		for conflict_type in ("USER_REJECTED_MATCH", "PHONE_ALREADY_ASSOCIATED"):
			with self.subTest(conflict_type=conflict_type):
				self.assertTrue(
					conflict_with(conflict_type, phone_e164=to_e164(phone), created_user=email) is not None
				)

	def test_the_unique_index_is_the_real_guarantee_not_the_check(self):
		"""The check is a read; the insert is a write; a race fits between.

		Simulated by making the check lie - exactly what a concurrent
		signup claiming the number between the two would produce. The
		insert must then fail, be rolled back to its own savepoint, and be
		made again with the number withheld, reaching the same outcome the
		check would have produced had it seen the row.
		"""
		from unittest.mock import patch

		phone = unique_phone()
		name = unique_name("Ahmed")
		_existing, contact = make_customer_with_contact(customer_name=name, phone=phone)
		email = unique_email()

		with signup_enabled(), patch.object(linking, "_phone_held_elsewhere", return_value=False):
			client, resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			client.call(signup_api.decide, accept=False)
			self.complete(client)

		self.assertTrue(frappe.db.exists("User", email), "the race lost the account")
		self.assertEqual(
			frappe.get_all(
				"Contact Phone",
				filters={"parenttype": "Contact", "phone": to_e164(phone)},
				pluck="parent",
			),
			[contact.name],
		)
		new_contact = frappe.db.get_value("Contact", {"user": email}, "name")
		self.assertEqual(
			frappe.db.get_value("Contact", new_contact, "custom_pending_phone_e164"),
			to_e164(phone),
		)


class TestExistingAccountBlocks(SignupFlowTestCase):
	def test_scenario_8_email_already_has_an_account(self):
		email = unique_email()
		make_website_user(email)

		with signup_enabled():
			client, resolved = self.run_to_ready(email=email)

		self.assertEqual(resolved["state"], session.BLOCKED)
		self.assertIn("sign in", resolved["message"].lower())

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.match_result, matching.EMAIL_ACCOUNT_EXISTS)

	def test_verifying_the_email_does_not_reveal_that_it_is_registered(self):
		# The verdict waits for the phone. Verifying a registered address
		# and an unregistered one are indistinguishable, so the email step
		# cannot be used on its own to test whether an address has an
		# account - which is the whole reason the check moved to resolve.
		known = unique_email()
		make_website_user(known)

		with signup_enabled():
			c1, _s1 = start_signup(email=known)
			taken = c1.call(signup_api.verify_email, code=c1.codes["email"])
			c2, _s2 = start_signup(email=unique_email())
			free = c2.call(signup_api.verify_email, code=c2.codes["email"])

		self.assertEqual(taken["state"], session.EMAIL_VERIFIED)
		self.assertEqual(taken["state"], free["state"])
		self.assertEqual(taken["message"], free["message"])
		self.assertEqual(taken["allowed_actions"], free["allowed_actions"])

	def test_start_does_not_reveal_that_an_email_is_registered(self):
		# Both a known and an unknown address must produce the same shape.
		known = unique_email()
		make_website_user(known)

		with signup_enabled():
			_c1, taken = start_signup(email=known)
			_c2, free = start_signup(email=unique_email())

		self.assertEqual(taken["state"], free["state"])
		self.assertEqual(taken["allowed_actions"], free["allowed_actions"])
		self.assertEqual(taken["message"].replace(taken["email"], ""), free["message"].replace(free["email"], ""))

	def test_scenario_9_phone_already_has_an_account(self):
		phone = unique_phone()
		customer, _c = make_customer_with_contact()
		other_user = make_website_user(unique_email())
		make_identity(other_user.name, customer.name, to_e164(phone), other_user.name)

		email = unique_email()
		with signup_enabled():
			_client, result = self.run_to_ready(email=email, phone=phone)

		self.assertEqual(result["state"], session.BLOCKED)
		self.assertFalse(frappe.db.exists("User", email))
		# matching.PHONE_ACCOUNT_EXISTS is still the classification that
		# raised this block; the queue itself files it under the merged
		# type ACCOUNT_ALREADY_EXISTS (see conflicts._RESULT_TO_CONFLICT_TYPE).
		self.assertTrue(
			conflict_with("ACCOUNT_ALREADY_EXISTS", phone_e164=to_e164(phone)) is not None
		)


class TestChangingDetails(SignupFlowTestCase):
	def test_scenario_10_change_email(self):
		original, replacement = unique_email(), unique_email()

		with signup_enabled():
			client, _started = start_signup(email=original)
			first_code = client.codes["email"]

			result = client.call(signup_api.change_email, email=replacement)
			self.assertEqual(result["state"], session.EMAIL_PENDING)
			self.assertEqual(result["email"], replacement)

			# The code sent to the old address is dead.
			self.assertRaises(
				otp.OTPInvalid, client.call, signup_api.verify_email, code=first_code
			)
			client.call(signup_api.verify_email, code=client.codes["email"])

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.email_normalized, replacement)
		self.assertTrue(doc.email_verified)

	def test_change_email_after_verifying_revokes_verification(self):
		with signup_enabled():
			client, _started = start_signup()
			client.call(signup_api.verify_email, code=client.codes["email"])

			doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
			self.assertTrue(doc.email_verified)

			client.call(signup_api.change_email, email=unique_email())

		doc.reload()
		self.assertFalse(doc.email_verified, "the old address still counted as verified")
		self.assertEqual(doc.status, session.EMAIL_PENDING)

	def test_scenario_11_change_phone(self):
		original, replacement = unique_phone(), unique_phone()

		with signup_enabled():
			client, _started = start_signup(phone=original)
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)
			first_code = client.codes["phone"]

			result = client.call(signup_api.change_phone, phone=replacement)
			self.assertEqual(result["state"], session.PHONE_PENDING)

			self.assertRaises(
				otp.OTPInvalid, client.call, signup_api.verify_phone, code=first_code
			)
			client.call(signup_api.verify_phone, code=client.codes["phone"])

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_e164, to_e164(replacement))
		self.assertTrue(doc.phone_verified)

	def test_change_phone_after_verifying_revokes_verification(self):
		with signup_enabled():
			client, _started = start_signup()
			verify_both_channels(client)
			client.call(signup_api.change_phone, phone=unique_phone())

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertFalse(doc.phone_verified)
		self.assertEqual(doc.status, session.PHONE_PENDING)

	def test_changing_to_the_same_address_is_rejected(self):
		email = unique_email()
		with signup_enabled():
			client, _started = start_signup(email=email)
			self.assertRaises(
				frappe.ValidationError, client.call, signup_api.change_email, email=email
			)


class TestPasscodeHandling(SignupFlowTestCase):
	def test_scenario_12_wrong_otp(self):
		with signup_enabled():
			client, _started = start_signup()
			self.assertRaises(
				otp.OTPInvalid, client.call, signup_api.verify_email, code="000000"
			)
			result = client.call(signup_api.get_state)

		self.assertEqual(result["state"], session.EMAIL_PENDING)
		self.assertFalse(result["email_verified"])

	def test_scenario_13_expired_otp(self):
		with signup_enabled():
			client, _started = start_signup()
			frappe.db.set_value(
				"Webshop Signup Session",
				{"signup_id": client.signup_id},
				"email_otp_expires_at",
				add_to_date(now_datetime(), seconds=-1),
				update_modified=False,
			)
			self.assertRaises(
				otp.OTPInvalid, client.call, signup_api.verify_email, code=client.codes["email"]
			)

	def test_scenario_14_too_many_attempts(self):
		with signup_enabled(), signup_settings_as(otp_max_attempts=3):
			client, _started = start_signup()
			for _ in range(3):
				self.assertRaises(
					otp.OTPInvalid, client.call, signup_api.verify_email, code="000000"
				)
			# The real code no longer works either - it was destroyed.
			self.assertRaises(
				otp.OTPAttemptsExhausted,
				client.call,
				signup_api.verify_email,
				code=client.codes["email"],
			)

	def test_scenario_15_resend_otp(self):
		with signup_enabled():
			client, _started = start_signup()
			first = client.codes["email"]
			result = client.call(signup_api.send_email_otp)
			second = client.codes["email"]

			self.assertNotEqual(first, second)
			self.assertEqual(result["data"]["sends_remaining"], 3)
			self.assertRaises(otp.OTPInvalid, client.call, signup_api.verify_email, code=first)
			client.call(signup_api.verify_email, code=second)

	def test_resend_cooldown_is_enforced(self):
		with signup_enabled(), signup_settings_as(otp_resend_cooldown_seconds=60):
			client, _started = start_signup()
			self.assertRaises(otp.OTPCooldown, client.call, signup_api.send_email_otp)


class TestLifecycle(SignupFlowTestCase):
	def test_scenario_16_abandoned_signup_creates_nothing(self):
		email = unique_email()

		with signup_enabled():
			client, _started = start_signup(email=email)
			verify_both_channels(client)

			frappe.db.set_value(
				"Webshop Signup Session",
				{"signup_id": client.signup_id},
				"expires_at",
				add_to_date(now_datetime(), minutes=-1),
				update_modified=False,
			)
			self.assertRaises(session.SignupExpired, client.call, signup_api.resolve)

		self.assertFalse(frappe.db.exists("User", email))
		self.assertFalse(frappe.db.exists("Webshop Account Identity", {"email_normalized": email}))
		self.assertEqual(
			frappe.db.get_value(
				"Webshop Signup Session", {"signup_id": client.signup_id}, "status"
			),
			session.EXPIRED,
		)

	def test_scenario_18_duplicate_submission_is_idempotent(self):
		email = unique_email()

		with signup_enabled():
			client, _resolved = self.run_to_ready(email=email)
			first = self.complete(client)
			second = self.complete(client)

		self.assertEqual(first["state"], session.COMPLETED)
		self.assertEqual(second["state"], session.COMPLETED)
		self.assertTrue(second["data"]["already_completed"])
		self.assertEqual(frappe.db.count("Webshop Account Identity", {"user": email}), 1)
		self.assertEqual(frappe.db.count("User", {"email": email}), 1)

	def test_cancelling_a_signup_creates_nothing(self):
		email = unique_email()
		with signup_enabled():
			client, _started = start_signup(email=email)
			result = client.call(signup_api.cancel)

		self.assertEqual(result["state"], session.CANCELLED)
		self.assertFalse(frappe.db.exists("User", email))

	def test_get_state_resumes_a_reloaded_browser(self):
		with signup_enabled():
			client, _started = start_signup()
			result = client.call(signup_api.get_state)

		self.assertEqual(result["state"], session.EMAIL_PENDING)
		self.assertEqual(result["data"]["channel"], "email")
		self.assertIn("verify_email", result["allowed_actions"])

	def test_signup_is_refused_when_the_feature_is_off(self):
		# The site-wide switch is lifted, so this isolates the app's own
		# feature flag as the thing doing the refusing.
		from custom_webshop.tests.utils import signup_allowed

		with signup_allowed(), signup_settings_as(signup_enabled=0):
			self.assertRaises(frappe.ValidationError, start_signup)

	def test_signup_is_refused_when_a_channel_cannot_deliver(self):
		# Fails closed: the phone is the primary identity signal, so a
		# site that cannot send SMS must not run identity resolution.
		with signup_enabled(), signup_settings_as(
			phone_otp_enabled=0, email_otp_dev_mode=0, phone_otp_dev_mode=0
		):
			self.assertRaises(frappe.ValidationError, start_signup)


class TestValidationAtStart(SignupFlowTestCase):
	def test_rejects_a_two_part_name(self):
		with signup_enabled():
			self.assertRaises(frappe.ValidationError, start_signup, full_name="Ahmed Amin")

	def test_rejects_an_invalid_email(self):
		with signup_enabled():
			self.assertRaises(frappe.ValidationError, start_signup, email="userexample.com")

	def test_rejects_an_invalid_phone(self):
		with signup_enabled():
			self.assertRaises(frappe.ValidationError, start_signup, phone="01312345678")

	def test_rejects_an_unknown_account_type(self):
		with signup_enabled():
			self.assertRaises(frappe.ValidationError, start_signup, account_type="Robot")

	def test_company_signup_requires_a_company_name(self):
		with signup_enabled():
			self.assertRaises(
				frappe.ValidationError, start_signup, account_type="Company", company_name=""
			)

	def test_an_irregular_name_is_repaired_not_rejected(self):
		"""Signup corrects a name's spelling instead of turning the person away."""
		email = unique_email()
		with signup_enabled():
			client, started = start_signup(full_name="أحمد مُحمَّد الجويلي", email=email)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.full_name, "احمد محمد الجويلى")
		self.assertEqual(started["data"]["name_adjusted"], "احمد محمد الجويلى")

	def test_the_repaired_name_reaches_the_customer_and_contact(self):
		email = unique_email()
		with signup_enabled():
			client, _resolved = self.run_to_ready(full_name="أحمد مُحمَّد الجويلي", email=email)
			self.complete(client)

		identity = frappe.db.get_value(
			"Webshop Account Identity", {"user": email}, ["customer", "contact"], as_dict=True
		)
		self.assertEqual(
			frappe.db.get_value("Customer", identity.customer, "customer_name"),
			"احمد محمد الجويلى",
		)
		self.assertEqual(
			frappe.db.get_value("Contact", identity.contact, "first_name"), "احمد محمد الجويلى"
		)
		self.assertEqual(frappe.db.get_value("User", email, "first_name"), "احمد محمد الجويلى")

	def test_a_name_needing_no_repair_reports_no_adjustment(self):
		with signup_enabled():
			_client, started = start_signup(full_name="Ahmed Amin Algewily")
		self.assertNotIn("name_adjusted", started["data"])

	def test_digits_and_symbols_are_stripped_from_the_name(self):
		email = unique_email()
		with signup_enabled():
			client, _started = start_signup(full_name="Ahmed & Sons Ltd 2026", email=email)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.full_name, "Ahmed Sons Ltd")

	def test_a_repaired_name_can_still_be_too_short(self):
		# "Ahmed 1 Amin" is three tokens as typed but only two names.
		with signup_enabled():
			self.assertRaises(frappe.ValidationError, start_signup, full_name="Ahmed 1 Amin")

	def test_the_chosen_country_decides_the_rules(self):
		"""A Canadian number is accepted when Canada is picked."""
		email = unique_email()
		with signup_enabled():
			client, _started = start_signup(
				email=email, phone="506 234 5678", phone_country="CA"
			)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_e164, "+15062345678")
		self.assertEqual(doc.phone_country, "CA")

	def test_the_same_digits_are_refused_under_another_country(self):
		# 01012345678 is a valid Egyptian mobile and not a Canadian one.
		with signup_enabled():
			start_signup(phone="01012345678", phone_country="EG")
			self.assertRaises(
				frappe.ValidationError, start_signup, phone="01012345678", phone_country="CA"
			)

	def test_an_unknown_country_falls_back_to_the_default(self):
		# Never "no rules at all" - a bogus region uses the configured default.
		with signup_enabled():
			client, _started = start_signup(phone="01012345678", phone_country="ZZ")

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_country, "EG")
		self.assertEqual(doc.phone_e164, "+201012345678")

	def test_no_country_at_all_still_works(self):
		# An old client that does not send one must keep working.
		with signup_enabled():
			client, _started = start_signup(phone="01012345678")

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_country, "EG")

	def test_the_envelope_carries_the_country_back(self):
		# So a browser resuming after a refresh can restore the picker.
		with signup_enabled():
			client, started = start_signup(phone="506 234 5678", phone_country="CA")
		self.assertEqual(started["phone_country"], "CA")

	def test_changing_the_phone_can_change_the_country(self):
		with signup_enabled():
			client, _started = start_signup(phone="01012345678", phone_country="EG")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)
			client.call(
				signup_api.change_phone, phone="506 234 5678", phone_country="CA"
			)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_e164, "+15062345678")
		self.assertEqual(doc.phone_country, "CA")

	def test_changing_only_the_digits_keeps_the_country(self):
		with signup_enabled():
			client, _started = start_signup(phone="506 234 5678", phone_country="CA")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)
			client.call(signup_api.change_phone, phone="416 234 5678")

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_country, "CA")
		self.assertEqual(doc.phone_e164, "+14162345678")

	def test_a_full_international_number_overrides_the_picker(self):
		with signup_enabled():
			client, _started = start_signup(phone="+201012345678", phone_country="CA")

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_e164, "+201012345678")

	def test_phone_is_canonicalised_at_start(self):
		with signup_enabled():
			client, _started = start_signup(phone="+20 101 234 5678")

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_e164, "+201012345678")

	def test_email_is_canonicalised_at_start(self):
		with signup_enabled():
			client, _started = start_signup(email="  MixedCase@Example.COM ")

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.email_normalized, "mixedcase@example.com")


class TestPasswordHandling(SignupFlowTestCase):
	def test_mismatched_passwords_are_rejected(self):
		with signup_enabled():
			client, _resolved = self.run_to_ready()
			self.assertRaises(
				frappe.ValidationError,
				client.call,
				signup_api.complete,
				password=PASSWORD,
				confirm_password="something-else",
			)

	def test_missing_password_is_rejected(self):
		with signup_enabled():
			client, _resolved = self.run_to_ready()
			self.assertRaises(
				frappe.ValidationError,
				client.call,
				signup_api.complete,
				password="",
				confirm_password="",
			)

	def test_password_is_never_stored_on_the_session(self):
		email = unique_email()
		with signup_enabled():
			client, _resolved = self.run_to_ready(email=email)
			self.complete(client)

		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertNotIn(PASSWORD, frappe.as_json(doc.as_dict()))

	def test_the_chosen_password_actually_works(self):
		from frappe.utils.password import check_password

		email = unique_email()
		with signup_enabled():
			client, _resolved = self.run_to_ready(email=email)
			self.complete(client)

		self.assertEqual(check_password(email, PASSWORD), email)


def tearDownModule():
	"""Remove sessions the deliberate commits in this app left behind."""
	from custom_webshop.tests.utils import purge_test_accounts, purge_test_sessions

	purge_test_sessions()
	purge_test_accounts()


class TestTakingAnAnswerBack(SignupFlowTestCase):
	"""The codes are proof and stay proven. The card's answer is not.

	Everything before the recognition card is verification, and nothing
	here reaches back into it. What the back button undoes is the answer:
	a yes or no about a record, and the spelling chosen after it.
	"""

	def test_it_is_only_offered_once_there_is_an_answer_to_undo(self):
		name, phone = unique_name("Ahmed"), unique_phone()
		make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=name, phone=phone, email=unique_email()
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			# Looking at the card is not answering it.
			self.assertNotIn("go_back", resolved["allowed_actions"])

			answered = client.call(signup_api.decide, accept=True)
			self.assertIn("go_back", answered["allowed_actions"])

	def test_a_signup_that_was_never_asked_is_not_offered_a_way_back(self):
		# Nobody matched, so no card was shown and there is no answer to
		# take back. Offering "back" here would suggest the verified email
		# and phone could be changed, which they cannot.
		with signup_enabled():
			_client, resolved = self.run_to_ready(
				full_name=unique_name(), phone=unique_phone(), email=unique_email()
			)

		self.assertEqual(resolved["state"], session.READY)
		self.assertNotIn("go_back", resolved["allowed_actions"])

	def test_going_back_shows_the_same_record_again(self):
		name, phone = unique_name("Ahmed"), unique_phone()
		make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=name, phone=phone, email=unique_email()
			)
			card = resolved["data"]["recognition"]
			client.call(signup_api.decide, accept=False)

			back = client.call(signup_api.go_back)

		self.assertEqual(back["state"], session.MATCH_REVIEW)
		self.assertEqual(back["data"]["recognition"], card)
		# And the answer really is gone, not merely re-displayed.
		self.assertNotIn("go_back", back["allowed_actions"])

	def test_taking_back_a_no_takes_back_the_conflict_it_raised(self):
		# A "no" queues USER_REJECTED_MATCH the moment it is given. If a
		# mis-click could not be undone, staff would be handed a decision
		# nobody made.
		name, phone = unique_name("Ahmed"), unique_phone()
		make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			client, _resolved = self.run_to_ready(
				full_name=name, phone=phone, email=unique_email()
			)
			client.call(signup_api.decide, accept=False)
			session_name = frappe.db.get_value(
				"Webshop Signup Session", {"signup_id": client.signup_id}, "name"
			)
			self.assertTrue(
				conflict_with("USER_REJECTED_MATCH", signup_session=session_name) is not None
			)

			client.call(signup_api.go_back)

		self.assertFalse(
			conflict_with("USER_REJECTED_MATCH", signup_session=session_name) is not None
		)

	def test_the_verified_channels_survive_going_back(self):
		name, phone = unique_name("Ahmed"), unique_phone()
		make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			client, _resolved = self.run_to_ready(
				full_name=name, phone=phone, email=unique_email()
			)
			client.call(signup_api.decide, accept=True)
			back = client.call(signup_api.go_back)

		self.assertTrue(back["email_verified"])
		self.assertTrue(back["phone_verified"])

	def test_you_can_answer_differently_and_finish(self):
		# The point of the button: the second answer is the one that counts.
		name, phone = unique_name("Ahmed"), unique_phone()
		existing, _contact = make_customer_with_contact(customer_name=name, phone=phone)
		email = unique_email()

		with signup_enabled():
			client, _resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			client.call(signup_api.decide, accept=False)
			client.call(signup_api.go_back)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		self.assertEqual(
			frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer"),
			existing.name,
		)


class TestADisabledRecordAlwaysReachesSomebody(SignupFlowTestCase):
	"""A flag the shopper cannot see must not decide things silently.

	`matching.classify` refuses to link a disabled Customer
	automatically and says staff review is required. That verdict used to
	reach the person as a question and then be forgotten: answering "yes"
	linked the account and queued nothing, so a shopper ended up owning
	an account against a record the business had switched off, with
	nobody told and no order possible.
	"""

	def _disabled_customer_matching_both_channels(self):
		name, phone, email = unique_name("Ahmed"), unique_phone(), unique_email()
		customer, contact = make_customer_with_contact(customer_name=name, phone=phone)
		contact.append("email_ids", {"email_id": email, "is_primary": 1})
		contact.save(ignore_permissions=True)
		frappe.db.set_value("Customer", customer.name, "disabled", 1)
		return customer, name, phone, email

	def test_the_link_is_queued_for_somebody_to_look_at(self):
		customer, name, phone, email = self._disabled_customer_matching_both_channels()

		with signup_enabled():
			client, resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		session_name = frappe.db.get_value(
			"Webshop Signup Session", {"email_normalized": email}, "name"
		)
		self.assertTrue(
			conflict_with("MATCHED_CUSTOMER_DISABLED", signup_session=session_name) is not None,
			"a disabled record was linked with nothing queued",
		)

	def test_it_is_not_quietly_re_enabled(self):
		# Re-opening it is the decision the conflict exists to have made.
		customer, name, phone, email = self._disabled_customer_matching_both_channels()

		with signup_enabled():
			client, _resolved = self.run_to_ready(full_name=name, phone=phone, email=email)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		self.assertEqual(frappe.db.get_value("Customer", customer.name, "disabled"), 1)


class TestTheDecisionThatPermitsALinkIsAlwaysRecorded(SignupFlowTestCase):
	"""The "yes" is the only thing authorising a link to somebody's record.

	It used to go unlogged on exactly the signups that went furthest:
	`decide` wrote the event after the state transition, and a signup
	offered the second "which name?" card returned before reaching it. So
	the consent behind every renamed account was missing from the trail,
	while rejections were recorded in full.
	"""

	def events_for(self, session_id, log):
		return [e for e in log if e.get("signup_id") == session_id]

	def test_it_is_logged_even_when_a_name_card_follows(self):
		name, phone = unique_name("Ahmed"), unique_phone()
		make_customer_with_contact(customer_name=name, phone=phone)
		logged = []

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=phone, email=unique_email()
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)

			with patch("custom_webshop.api.signup.log_event") as spy:
				answered = client.call(signup_api.decide, accept=True)
				logged = [call.args[0] for call in spy.call_args_list]

		# The second card really did follow - otherwise this proves nothing.
		self.assertIn("name_choice", answered["data"])
		self.assertIn("match_decision", logged)

	def test_a_rejection_is_still_logged(self):
		name, phone = unique_name("Ahmed"), unique_phone()
		make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			client, _resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=phone, email=unique_email()
			)
			with patch("custom_webshop.api.signup.log_event") as spy:
				client.call(signup_api.decide, accept=False)
				logged = [call.args[0] for call in spy.call_args_list]

		self.assertIn("match_decision", logged)


class TestWhatTheQueueIsToldAboutACompanyRecord(SignupFlowTestCase):
	"""An individual signing into a company's record is not an error.

	A real person can be the contact on a company account, so refusing
	would strand a genuine owner over a field they cannot see. What must
	not happen is nobody being told: the link puts a company's order
	history behind a personal login, and on a phone-only match that rests
	on a number that may have changed hands.
	"""

	def test_the_conflict_says_it_is_a_company(self):
		arabic = "الارف"
		phone = unique_phone()
		customer, _contact = make_customer_with_contact(customer_name=arabic, phone=phone)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=phone, email=unique_email()
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		notes = frappe.db.get_value(
			"Webshop Identity Conflict",
			conflict_with("ACCOUNT_TYPE_MISMATCH", created_customer=customer.name),
			"resolution_notes",
		)
		self.assertTrue(notes, "an individual signup on a company record raised nothing")
		self.assertIn("individual", notes.lower())
		self.assertIn("company", notes.lower())

	def test_an_individual_record_says_nothing_extra(self):
		# The line is for the surprising case only; adding it everywhere
		# would make it invisible.
		name, phone = unique_name("Ahmed"), unique_phone()
		customer, _contact = make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			client, _resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=phone, email=unique_email()
			)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		self.assertFalse(
			conflict_with("ACCOUNT_TYPE_MISMATCH", created_customer=customer.name) is not None,
			"types that agree should raise nothing",
		)


class TestWhatMatchedIsRememberedNotRederived(SignupFlowTestCase):
	"""Which channels matched is a fact about the past, not the present.

	Linking writes the signup's email onto the matched Contact - by
	design, since production records carry a phone and no email - and
	`Customer.email_id` follows by native fetch_from. So a record matched
	on the phone alone is reachable by both channels afterwards, and
	anything that asks the live database reports "both matched" for every
	linked signup. The queue reads this to tell staff how strong the
	match was, so it has to be the recorded answer.
	"""

	def test_the_recorded_answer_survives_the_link_that_would_change_it(self):
		arabic = "عمر احمد صبرى"
		phone = unique_phone()
		customer, _contact = make_customer_with_contact(customer_name=arabic, phone=phone)

		email = unique_email()

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=phone, email=email
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			answer_name_card(client, client.call(signup_api.decide, accept=True))
			self.complete(client)

		doc = frappe.get_doc("Webshop Signup Session", {"email_normalized": email})
		# The email is on the record now, so the live query would say both.
		self.assertIn(
			customer.name, matching.find_customers_by_email(doc.email_normalized)
		)
		self.assertEqual(
			matching.matched_channels(doc, customer.name),
			["phone"],
			"the link's own side effect was mistaken for what matched",
		)


class TestTheNameCardOffersTwoPeople(SignupFlowTestCase):
	"""The choice is between the person on the record and the person typing.

	A company's name is never a candidate. This card used to read
	`Customer.customer_name` whatever the Customer was, so on a company
	record it offered to name somebody's personal account after the
	business - while the identity card they had just answered showed the
	person's name correctly. Both now ask
	`matching.recognition_identity`, because it is the same question one
	step later.
	"""

	def offer_for(self, *, customer_type):
		company, person = unique_name("Acme"), unique_name("Ahmed")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(
			customer_name=company, contact_name=person, phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", customer_type)

		mine = unique_name("Mohamed")
		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=mine, phone=phone, email=unique_email()
			)
			self.assertEqual(resolved["state"], session.MATCH_REVIEW)
			answered = client.call(signup_api.decide, accept=True)

		return answered["data"].get("name_choice"), {
			"company": company, "person": person, "mine": mine
		}

	def test_a_company_record_offers_its_contact_not_the_business(self):
		choice, names = self.offer_for(customer_type="Company")

		self.assertIsNotNone(choice, "no name choice was offered")
		self.assertEqual(choice["stored"], names["person"])
		self.assertEqual(choice["submitted"], names["mine"])
		self.assertNotEqual(
			choice["stored"],
			names["company"],
			"the card offered to name a personal account after the business",
		)

	def test_the_card_agrees_with_the_one_before_it(self):
		company, person = unique_name("Acme"), unique_name("Ahmed")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(
			customer_name=company, contact_name=person, phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		with signup_enabled():
			client, resolved = self.run_to_ready(
				full_name=unique_name("Mohamed"), phone=phone, email=unique_email()
			)
			shown = resolved["data"]["recognition"]["name"]
			answered = client.call(signup_api.decide, accept=True)

		# What the second card calls "the stored name" must be what the
		# first card showed as the name.
		self.assertEqual(answered["data"]["name_choice"]["stored"], shown)

	def test_an_individual_record_offers_its_own_name(self):
		# On an individual the Customer's own name *is* a person's name,
		# so that is what the choice is against - unchanged by any of
		# this, and the case the old code happened to get right.
		person = unique_name("Ahmed")
		phone = unique_phone()
		make_customer_with_contact(customer_name=person, contact_name=person, phone=phone)

		mine = unique_name("Mohamed")
		with signup_enabled():
			client, _resolved = self.run_to_ready(
				full_name=mine, phone=phone, email=unique_email()
			)
			answered = client.call(signup_api.decide, accept=True)

		choice = answered["data"].get("name_choice")
		self.assertIsNotNone(choice, "no name choice was offered")
		self.assertEqual(choice["stored"], person)
		self.assertEqual(choice["submitted"], mine)


class TestAnAccountIsNeverNamedAfterABusiness(SignupFlowTestCase):
	"""A User is a person. A company name belongs on the Customer.

	`submitted_party_name` returns the business for a company signup, and
	it was feeding the account rename and the "which name?" card - so
	somebody signing up for "Beta Works" was offered, and given, a login
	called Beta Works.
	"""

	def company_signup_against(self, record_name, *, customer_type):
		company, person = unique_name("Beta"), unique_name("Kareem")
		phone, email = unique_phone(), unique_email()
		customer, contact = make_customer_with_contact(
			customer_name=record_name, contact_name=unique_name("Omar"), phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", customer_type)

		with signup_enabled():
			client, _started = start_signup(
				full_name=person, phone=phone, email=email,
				account_type="Company", company_name=company,
			)
			verify_both_channels(client)
			client.call(signup_api.resolve)
			answered = client.call(signup_api.decide, accept=True)
			if "name_choice" in answered["data"]:
				client.call(signup_api.choose_name, use_submitted=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		return {"email": email, "person": person, "company": company,
		        "customer": customer.name, "contact": contact.name}

	def test_the_card_never_offers_the_business_name(self):
		company, person = unique_name("Beta"), unique_name("Kareem")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(
			customer_name=unique_name("Acme"), contact_name=unique_name("Omar"), phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		with signup_enabled():
			client, _r = start_signup(
				full_name=person, phone=phone, email=unique_email(),
				account_type="Company", company_name=company,
			)
			verify_both_channels(client)
			client.call(signup_api.resolve)
			answered = client.call(signup_api.decide, accept=True)

		choice = answered["data"].get("name_choice")
		self.assertIsNotNone(choice, "no name choice was offered")
		self.assertEqual(choice["submitted"], person)
		self.assertNotEqual(choice["submitted"], company)

	def test_taking_your_name_renames_the_login_to_the_person(self):
		state = self.company_signup_against(unique_name("Acme"), customer_type="Company")

		self.assertEqual(
			frappe.db.get_value("User", state["email"], "full_name"), state["person"]
		)
		self.assertNotEqual(
			frappe.db.get_value("User", state["email"], "full_name"), state["company"]
		)

	def test_a_new_customer_still_takes_the_business_name(self):
		# The other half of the rule: the Customer is where a business
		# name belongs, and that path is unchanged.
		company, person = unique_name("Beta"), unique_name("Kareem")
		email = unique_email()
		with signup_enabled():
			client, _r = start_signup(
				full_name=person, phone=unique_phone(), email=email,
				account_type="Company", company_name=company,
			)
			verify_both_channels(client)
			client.call(signup_api.resolve)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		customer = frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer")
		self.assertEqual(
			frappe.db.get_value("Customer", customer, "customer_name"), company
		)
		self.assertEqual(frappe.db.get_value("User", email, "full_name"), person)
