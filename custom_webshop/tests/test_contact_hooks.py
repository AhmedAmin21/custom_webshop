# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for custom_webshop.contact_hooks - the Contact validate hook.

One job: maintain the canonical E.164 column identity matching queries,
without ever touching the number itself.

Most tests here call `sync_phone_e164` directly on an unsaved document
rather than inserting one, for two reasons. Some exercise numbers
contact_enhancements' validator now refuses outright, which could not be
inserted at all - though rows in exactly that shape already exist in this
database and this hook still has to survive them. The rest would need the
same number more than once, and that app's unique index on
`Contact Phone.phone` makes a second Contact holding it impossible. An
unsaved document reaches the hook exactly as a saved one does and touches
no index, so it tests the thing under test and nothing else.
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.contact_hooks import sync_phone_e164
from custom_webshop.signup.identity import to_e164
from custom_webshop.tests.utils import make_contact, unique_email, unique_phone

# contact_enhancements keeps the numbering plan on each phone row, not
# on the Contact. It is that app's field, so the tests that lean on it
# skip themselves on a site where it is not installed.
HAS_COUNTRY = frappe.get_meta("Contact Phone").has_field("country")


def unsaved_contact(*phones, country=None):
	"""Build an in-memory Contact with the given phone rows.

	`country` is set on every row, which is where contact_enhancements
	keeps it - one plan per number, since a person can carry a local
	mobile and a foreign one side by side.
	"""
	doc = frappe.new_doc("Contact")
	doc.first_name = "Legacy Shape Contact"
	for phone in phones:
		row = doc.append("phone_nos", {"phone": phone})
		if country and HAS_COUNTRY:
			row.country = country
	return doc


class TestSyncPhoneE164(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_populates_e164_on_insert(self):
		phone = unique_phone()
		contact = make_contact(phone=phone)
		self.assertEqual(contact.phone_nos[0].custom_phone_e164, to_e164(phone))

	def test_normalizes_every_input_format_to_one_value(self):
		# One number written five ways must derive one canonical value.
		# Not inserted: they are the *same* number, and only one Contact
		# in the database may hold it.
		digits = unique_phone().lstrip("0")
		for raw in (f"0{digits}", f"+20{digits}", f"0020{digits}", f"20{digits}", f"0{digits[:3]} {digits[3:6]} {digits[6:]}"):
			with self.subTest(raw=raw):
				doc = unsaved_contact(raw)
				sync_phone_e164(doc)
				self.assertEqual(doc.phone_nos[0].custom_phone_e164, f"+20{digits}")

	def test_updates_when_the_phone_changes(self):
		contact = make_contact(phone=unique_phone())
		replacement = unique_phone()
		contact.phone_nos[0].phone = replacement
		contact.save()
		self.assertEqual(contact.phone_nos[0].custom_phone_e164, to_e164(replacement))

	def test_unparseable_number_leaves_the_column_empty_without_failing(self):
		# This hook runs on every Contact save in the system, so a number
		# it cannot parse must never block one. The value below is real
		# live data from this site.
		doc = unsaved_contact("011011012121212121")
		sync_phone_e164(doc)
		self.assertEqual(doc.phone_nos[0].custom_phone_e164, "")
		self.assertEqual(doc.phone_nos[0].phone, "011011012121212121")

	def test_handles_multiple_phone_rows(self):
		# The third passes Frappe's own loose PHONE_NUMBER_PATTERN but is
		# not a real number, so phonenumbers declines to canonicalise it.
		doc = unsaved_contact("01012345678", "+201112223344", "12345")
		sync_phone_e164(doc)
		self.assertEqual(doc.phone_nos[0].custom_phone_e164, "+201012345678")
		self.assertEqual(doc.phone_nos[1].custom_phone_e164, "+201112223344")
		self.assertEqual(doc.phone_nos[2].custom_phone_e164, "")

	def test_contact_without_phones_saves_normally(self):
		contact = make_contact()
		self.assertEqual(contact.phone_nos, [])

	def test_e164_column_is_queryable(self):
		phone = unique_phone()
		contact = make_contact(phone=phone)
		found = frappe.get_all(
			"Contact Phone",
			filters={"custom_phone_e164": contact.phone_nos[0].custom_phone_e164},
			pluck="parent",
		)
		self.assertIn(contact.name, found)


class TestTheRegionALocalNumberIsReadUnder(FrappeTestCase):
	"""A local number means nothing without a numbering plan to read it under."""

	def test_the_default_region_is_used_when_the_contact_has_no_country(self):
		doc = unsaved_contact("01012345678")
		sync_phone_e164(doc)
		self.assertEqual(doc.phone_nos[0].custom_phone_e164, "+201012345678")

	@unittest.skipUnless(
		HAS_COUNTRY, "contact_enhancements' Contact Phone.country is not installed"
	)
	def test_a_foreign_rows_local_number_is_read_under_its_own_plan(self):
		"""`0512345678` is a valid Saudi mobile and not a valid Egyptian one.

		Read under the default region it canonicalises to nothing at all,
		which would leave every foreign number invisible to phone
		matching.
		"""
		doc = unsaved_contact("0512345678", country="Saudi Arabia")
		sync_phone_e164(doc)
		self.assertEqual(doc.phone_nos[0].custom_phone_e164, "+966512345678")

	@unittest.skipUnless(
		HAS_COUNTRY, "contact_enhancements' Contact Phone.country is not installed"
	)
	def test_each_row_is_read_under_its_own_country(self):
		"""One person, a local mobile and a foreign one, one Contact."""
		doc = frappe.new_doc("Contact")
		doc.first_name = "Two Plans Contact"
		local = doc.append("phone_nos", {"phone": "01012345678"})
		local.country = "Egypt"
		foreign = doc.append("phone_nos", {"phone": "0512345678"})
		foreign.country = "Saudi Arabia"

		sync_phone_e164(doc)

		self.assertEqual(doc.phone_nos[0].custom_phone_e164, "+201012345678")
		self.assertEqual(doc.phone_nos[1].custom_phone_e164, "+966512345678")


class TestTheHookNeverRewritesTheNumber(FrappeTestCase):
	"""The column is ours. `Contact Phone.phone` is not.

	This app is registered after contact_enhancements, so its hook runs
	last and could overwrite anything that one wrote. It used to: while
	that app stored the local national form, a number this app had just
	verified in international form did not survive its own signup, and
	the hook put it back for exactly the rows an identity record vouched
	for.

	That app now stores E.164 itself, so there is nothing left to put
	back and the code that did it is gone. These tests hold the boundary
	the retirement leaves behind - not "the number ends up canonical",
	which is now that app's doing and its business, but that this hook
	writes to `custom_phone_e164` and to nothing else.
	"""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_the_phone_value_is_left_exactly_as_found(self):
		for raw in ("01012345678", "+201012345678", "0020 101 234 5678", "not a number"):
			with self.subTest(raw=raw):
				doc = unsaved_contact(raw)
				sync_phone_e164(doc)
				self.assertEqual(doc.phone_nos[0].phone, raw)

	def test_an_identity_record_does_not_make_it_rewrite_anything(self):
		"""A verified number is no longer a reason to touch the row.

		This is the retired behaviour stated as its inverse, so that
		bringing the old code back would fail here rather than pass
		quietly.
		"""
		from custom_webshop.tests.test_matching import make_identity, make_website_user
		from custom_webshop.tests.utils import make_customer_with_contact

		phone = unique_phone()
		canonical = to_e164(phone)
		customer, _contact = make_customer_with_contact()
		user = make_website_user(unique_email())
		make_identity(user.name, customer.name, canonical, user.name)

		doc = unsaved_contact(phone)
		sync_phone_e164(doc)

		self.assertEqual(doc.phone_nos[0].phone, phone)
		self.assertEqual(doc.phone_nos[0].custom_phone_e164, canonical)

	def test_a_saved_contact_ends_up_canonical_anyway(self):
		"""Not this hook's doing, but worth pinning.

		contact_enhancements normalises the row on the same save, so on a
		site with both apps installed the stored number is international
		either way. If that ever stops being true, phone matching still
		works - `custom_phone_e164` is what it queries - but a good deal
		of this app's reasoning about stored formats would need revisiting,
		and this is where it would show.
		"""
		phone = unique_phone()
		contact = make_contact(phone=phone)
		self.assertEqual(contact.phone_nos[0].custom_phone_e164, to_e164(phone))
