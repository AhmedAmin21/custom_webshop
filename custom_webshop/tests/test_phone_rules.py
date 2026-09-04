# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Per-country phone rules, and the single stored format.

Two rules are asserted here, and they are separate on purpose:

* **What is written** is E.164, everywhere, whatever country it came
  from. Before this, an Egyptian number was stored as `01012345678` and
  a Saudi one as `+966512345678`, so the same column meant two things.
* **What is read** still accepts every form, because rows written by
  contact_enhancements and by this app's own earlier signups hold the
  local one. Canonical on write, forgiving on read.

The per-country length rules come from `phonenumbers`' metadata rather
than a table maintained here, so the tests check the wiring and the
edges - an unknown region, a national prefix, a region with no mobile
metadata - not the digit counts themselves, which are that library's to
get right.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.api import signup as signup_api
from custom_webshop.signup import countries, matching
from custom_webshop.signup.identity import (
	example_national_number,
	example_significant_number,
	national_number_lengths,
	national_trunk_prefix,
	to_e164,
)
from custom_webshop.tests.utils import (
	make_contact,
	make_customer_with_contact,
	signup_enabled,
	start_signup,
	unique_email,
	unique_name,
	unique_phone,
	verify_both_channels,
)

PASSWORD = "Str0ng-Passw0rd!x7"


class TestNationalNumberLengths(FrappeTestCase):
	def test_egypt_is_ten_digits_without_its_trunk_zero(self):
		# The leading zero people write locally is a trunk prefix, not part
		# of the number: `+20 10 01234567` is the whole of it. The field
		# holds the significant number because the dial code sits beside
		# it, so ten is the count it enforces.
		self.assertEqual(national_number_lengths("EG"), (10,))

	def test_a_region_with_a_different_length_reports_its_own(self):
		self.assertEqual(national_number_lengths("SA"), (9,))

	def test_a_region_with_several_lengths_reports_them_all(self):
		self.assertEqual(national_number_lengths("DE"), (10, 11))

	def test_an_unknown_region_imposes_no_rule(self):
		# An empty tuple means "no rule", not "reject everything" - the
		# UI reads it that way and the server still validates.
		self.assertEqual(national_number_lengths("ZZ"), ())
		self.assertEqual(national_number_lengths(""), ())
		self.assertEqual(national_number_lengths(None), ())

	def test_the_region_code_is_case_insensitive(self):
		self.assertEqual(national_number_lengths("eg"), national_number_lengths("EG"))

	def test_every_number_the_server_accepts_is_an_offered_length(self):
		"""The rule must never be stricter than the validator.

		If it were, the form would refuse a number the backend would have
		accepted, and nobody could get past the field. Written trunk-free,
		which is the shape the field settles on.
		"""
		samples = {
			"EG": ["1012345678", "1112223344"],
			"SA": ["512345678"],
			"GB": ["7400123456"],
			"DE": ["15123456789"],
			"CA": ["5062345678"],
		}
		for region, numbers in samples.items():
			lengths = national_number_lengths(region)
			for raw in numbers:
				with self.subTest(region=region, raw=raw):
					to_e164(raw, region=region)  # must not throw
					self.assertIn(len(raw), lengths)

	def test_the_rule_is_necessary_but_not_sufficient(self):
		"""A right-length number can still be a fake one.

		This is why the length check is only ever feedback: `1312345678`
		is exactly the length Egypt uses and 13 is not an issued mobile
		prefix, and only `to_e164` can tell.
		"""
		self.assertIn(10, national_number_lengths("EG"))
		with self.assertRaises(frappe.ValidationError):
			to_e164("1312345678", region="EG")


class TestTrunkPrefix(FrappeTestCase):
	"""What the field strips off the front as you type."""

	def test_the_common_case_is_a_leading_zero(self):
		for region in ("EG", "SA", "GB", "DE", "AE"):
			with self.subTest(region=region):
				self.assertEqual(national_trunk_prefix(region), "0")

	def test_north_america_uses_one(self):
		self.assertEqual(national_trunk_prefix("CA"), "1")
		self.assertEqual(national_trunk_prefix("US"), "1")

	def test_a_region_that_keeps_its_leading_zero_reports_none(self):
		# Italian numbers really do begin with the digit they begin with;
		# stripping it would break them.
		self.assertEqual(national_trunk_prefix("IT"), "")

	def test_an_unknown_region_reports_none(self):
		self.assertEqual(national_trunk_prefix("ZZ"), "")
		self.assertEqual(national_trunk_prefix(None), "")

	def test_the_server_still_accepts_the_trunk_form(self):
		"""Stripping is a display rule, not a validation one.

		Anything pasted or typed with the zero still resolves, so the
		field being forgiving never depends on the client behaving.
		"""
		for raw in ("1012345678", "01012345678", "+201012345678", "00201012345678"):
			with self.subTest(raw=raw):
				self.assertEqual(to_e164(raw, region="EG"), "+201012345678")


class TestTheExampleShownInTheField(FrappeTestCase):
	def test_it_carries_no_trunk_prefix(self):
		# The placeholder has to show the shape the field will hold, or it
		# teaches people to type something the field then rewrites.
		self.assertEqual(example_significant_number("EG"), "10 01234567")
		self.assertEqual(example_significant_number("SA"), "51 234 5678")

	def test_it_keeps_the_grouping_that_country_uses(self):
		self.assertEqual(example_significant_number("CA"), "506-234-5678")

	def test_a_region_that_has_no_trunk_prefix_is_unchanged(self):
		self.assertEqual(example_significant_number("IT"), example_national_number("IT"))

	def test_an_unknown_region_has_no_example(self):
		self.assertEqual(example_significant_number("ZZ"), "")

	def test_the_example_is_itself_a_valid_number(self):
		for region in ("EG", "SA", "GB", "DE", "CA", "IT"):
			with self.subTest(region=region):
				digits = example_significant_number(region).replace(" ", "").replace("-", "")
				to_e164(digits, region=region)  # must not throw


class TestCountryPayloadCarriesTheRules(FrappeTestCase):
	def setUp(self):
		countries.clear_cache()
		self.addCleanup(countries.clear_cache)

	def test_every_country_offers_lengths_and_a_maximum(self):
		listed = countries.build()
		self.assertTrue(listed)
		for country in listed:
			with self.subTest(country=country["code"]):
				self.assertIsInstance(country["lengths"], list)
				if country["lengths"]:
					self.assertEqual(country["max_len"], max(country["lengths"]))
				else:
					self.assertEqual(country["max_len"], 0)

	def test_egypt_carries_the_lengths_the_field_will_enforce(self):
		egypt = next(c for c in countries.build() if c["code"] == "EG")
		self.assertEqual(egypt["lengths"], [10])
		self.assertEqual(egypt["max_len"], 10)

	def test_every_country_carries_its_trunk_prefix(self):
		listed = {c["code"]: c for c in countries.build()}
		self.assertEqual(listed["EG"]["trunk"], "0")
		self.assertEqual(listed["CA"]["trunk"], "1")
		self.assertEqual(listed["IT"]["trunk"], "")

	def test_the_example_shown_is_the_trunk_free_one(self):
		listed = {c["code"]: c for c in countries.build()}
		self.assertEqual(listed["EG"]["example"], "10 01234567")

	def test_the_endpoint_the_form_calls_serves_them(self):
		payload = countries.for_signup(lang="en")
		egypt = next(c for c in payload["countries"] if c["code"] == "EG")
		self.assertEqual(egypt["lengths"], [10])
		self.assertEqual(egypt["max_len"], 10)
		self.assertEqual(egypt["trunk"], "0")


class StorageTestCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def complete_signup(self, **kwargs):
		"""Run one signup to COMPLETED and return its session document."""
		with signup_enabled():
			client, _started = start_signup(**kwargs)
			verify_both_channels(client)
			client.call(signup_api.resolve)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		return frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})


class TestEverythingIsStoredInInternationalForm(StorageTestCase):
	def test_an_egyptian_signup_stores_e164_in_every_column(self):
		phone = unique_phone()
		email = unique_email()
		session = self.complete_signup(phone=phone, email=email)
		expected = to_e164(phone)

		self.assertTrue(expected.startswith("+20"))
		self.assertEqual(session.phone_e164, expected)

		contact = frappe.get_doc("Contact", session.created_contact)
		self.assertEqual(contact.phone_nos[0].phone, expected)
		self.assertEqual(contact.phone_nos[0].custom_phone_e164, expected)

		self.assertEqual(frappe.db.get_value("User", email, "mobile_no"), expected)
		self.assertEqual(
			frappe.db.get_value("Webshop Account Identity", {"user": email}, "phone_e164"),
			expected,
		)

	def test_a_foreign_signup_is_stored_the_same_way(self):
		"""The point of the rule: one convention, not one per country."""
		session = self.complete_signup(phone="512345678", phone_country="SA")
		self.assertEqual(session.phone_e164, "+966512345678")

		contact = frappe.get_doc("Contact", session.created_contact)
		self.assertEqual(contact.phone_nos[0].phone, "+966512345678")

	def test_the_stored_phone_never_keeps_the_local_form(self):
		session = self.complete_signup(phone="01012349999")
		contact = frappe.get_doc("Contact", session.created_contact)
		stored = contact.phone_nos[0].phone
		self.assertFalse(stored.startswith("0"), f"{stored} is still in local form")
		self.assertTrue(stored.startswith("+"))


class TestReadingStaysForgiving(StorageTestCase):
	def test_a_contact_holding_the_local_form_is_still_matched(self):
		"""contact_enhancements still writes `01...` on its own paths.

		If canonicalising what we write had also narrowed what we look
		for, every Customer created before this change - and every one
		that app creates from a Lead - would become invisible to
		matching, which is the precise failure this flow exists to
		prevent.
		"""
		phone = unique_phone()
		customer, _contact = make_customer_with_contact(phone=phone)
		self.assertIn(customer.name, matching.find_customers_by_phone(to_e164(phone)))

	def test_the_local_form_is_among_the_forms_searched_for(self):
		self.assertIn("01012345678", matching.phone_variants("+201012345678"))
		self.assertIn("+201012345678", matching.phone_variants("+201012345678"))


class TestExtendingAContactThatHoldsTheLocalForm(StorageTestCase):
	def test_the_same_number_is_not_appended_twice(self):
		"""One person, one phone, one row.

		Two different string comparisons can duplicate the row here, and
		this has caught both:

		* ours, in `_add_verified_details` - the Contact holds `01...`
		  and the signup is about to write `+20...`, so comparing the raw
		  strings misses the match;
		* Frappe's own, in `Contact.add_phone`, called from
		  `create_contact` inside `User.on_update`. It checks for the
		  number with an exact match too, so a Contact momentarily left
		  in local form while `User.mobile_no` holds E.164 reads as a
		  different number and gets a second row appended - and a third,
		  because granting a role fires `on_update` again.
		"""
		phone = unique_phone()
		name = unique_name("Linkable")
		customer, contact = make_customer_with_contact(customer_name=name, phone=phone)
		# Stored international, because contact_enhancements normalises it
		# on the way in. What this test is about is how many rows there
		# are, not which format they are written in.
		self.assertEqual(contact.phone_nos[0].phone, to_e164(phone))

		with signup_enabled():
			client, _started = start_signup(full_name=name, phone=phone)
			verify_both_channels(client)
			client.call(signup_api.resolve)
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		contact.reload()
		canonical = to_e164(phone)
		rows = [row for row in contact.phone_nos if to_e164(row.phone) == canonical]
		self.assertEqual(len(rows), 1, "the same number was stored twice, in two formats")
		self.assertEqual(len(contact.phone_nos), 1, "the Contact gained a phone row")
		self.assertEqual(contact.phone_nos[0].phone, canonical)


class TestCanonicalizationPatch(FrappeTestCase):
	"""The migration that converts what earlier signups already stored."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def make_account(self, phone_local):
		"""Build the shape an older signup left behind: local form stored."""
		from custom_webshop.tests.test_matching import make_identity, make_website_user

		customer, contact = make_customer_with_contact(phone=phone_local)
		user = make_website_user(unique_email())
		make_identity(user.name, customer.name, to_e164(phone_local), user.name)
		frappe.db.set_value("User", user.name, "mobile_no", phone_local, update_modified=False)
		return customer, contact, user

	def run_patch(self):
		"""Run the migration with its commit stubbed out.

		The patch commits, as a migration should - but a commit inside a
		test escapes the rollback that isolates it, and this one walks
		*every* identity on the site, not just the fixtures here. Left
		alone it rewrote live records as a side effect of running the
		suite. Stubbing the commit keeps the work inside the transaction
		while still exercising every line that does it.
		"""
		from unittest.mock import patch

		from custom_webshop.patches import canonicalize_webshop_owned_phones

		with patch.object(frappe.db, "commit"):
			canonicalize_webshop_owned_phones.execute()

	def test_it_converts_the_account_it_owns(self):
		phone = unique_phone()
		customer, contact, user = self.make_account(phone)

		self.run_patch()

		contact.reload()
		expected = to_e164(phone)
		self.assertEqual(contact.phone_nos[0].phone, expected)
		self.assertEqual(frappe.db.get_value("User", user.name, "mobile_no"), expected)

	def test_it_leaves_contacts_it_does_not_own_alone(self):
		"""Staff and contact_enhancements data is not ours to rewrite."""
		phone = unique_phone()
		self.make_account(phone)
		bystander = make_contact(phone=unique_phone())
		untouched = bystander.phone_nos[0].phone

		self.run_patch()

		bystander.reload()
		self.assertEqual(bystander.phone_nos[0].phone, untouched)

	def test_it_never_destroys_a_number_it_cannot_parse(self):
		"""A number we cannot read is still the only way to reach someone.

		Such a row can no longer be *created* - contact_enhancements now
		rejects it on validate - but this site already holds two of them
		(`015545454545` and the 18-digit `011011012121212121`), so the
		migration still has to meet one. Written straight to the column to
		reproduce that legacy shape.

		Not either of those two literals, though: they are live rows, and
		that app's unique index covers this column, so reusing one would
		fail on the duplicate rather than on anything this test is about.
		The shape is what matters - too many digits to be a real number -
		so the value is derived from a fresh one.
		"""
		garbage = unique_phone() + "1234567"
		contact = make_contact(phone=unique_phone())
		row = contact.phone_nos[0].name
		frappe.db.set_value("Contact Phone", row, "phone", garbage, update_modified=False)
		frappe.db.set_value("Contact Phone", row, "custom_phone_e164", "", update_modified=False)

		self.run_patch()

		self.assertEqual(frappe.db.get_value("Contact Phone", row, "phone"), garbage)

	def test_running_it_twice_changes_nothing_the_second_time(self):
		phone = unique_phone()
		_customer, contact, _user = self.make_account(phone)

		self.run_patch()
		contact.reload()
		first = contact.phone_nos[0].phone
		modified_after_first = frappe.db.get_value("Contact", contact.name, "modified")

		self.run_patch()
		contact.reload()

		self.assertEqual(contact.phone_nos[0].phone, first)
		self.assertEqual(
			frappe.db.get_value("Contact", contact.name, "modified"), modified_after_first
		)

	def test_it_does_not_overwrite_a_different_number_set_by_hand(self):
		"""Only the verified number is converted, not whatever else is there."""
		phone = unique_phone()
		_customer, _contact, user = self.make_account(phone)
		other = unique_phone()
		frappe.db.set_value("User", user.name, "mobile_no", other, update_modified=False)

		self.run_patch()

		self.assertEqual(frappe.db.get_value("User", user.name, "mobile_no"), other)


def tearDownModule():
	"""Remove sessions the deliberate commits in this flow left behind."""
	from custom_webshop.tests.utils import purge_test_accounts, purge_test_sessions

	purge_test_sessions()
	purge_test_accounts()
