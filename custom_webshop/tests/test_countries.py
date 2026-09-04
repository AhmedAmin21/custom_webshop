# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for the signup country picker.

The list is assembled from Frappe's own Country doctype plus phonenumbers
rather than hard-coded, so these check the assembly holds together and
that choosing a country genuinely changes which rules a number is judged
by - the whole point of the picker.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.signup import countries
from custom_webshop.signup.identity import (
	InvalidPhoneNumber,
	dial_code,
	example_national_number,
	flag_emoji,
	normalize_region,
	to_e164,
)


class TestRegionHelpers(FrappeTestCase):
	def test_flag_emoji(self):
		self.assertEqual(flag_emoji("EG"), "🇪🇬")
		self.assertEqual(flag_emoji("ca"), "🇨🇦")
		self.assertEqual(flag_emoji("SA"), "🇸🇦")

	def test_flag_emoji_rejects_nonsense(self):
		for value in ("", None, "E", "EGY", "12", "!!"):
			with self.subTest(value=value):
				self.assertEqual(flag_emoji(value), "")

	def test_dial_codes(self):
		self.assertEqual(dial_code("EG"), 20)
		self.assertEqual(dial_code("ca"), 1)
		self.assertEqual(dial_code("SA"), 966)
		self.assertEqual(dial_code("GB"), 44)

	def test_dial_code_of_an_unknown_region(self):
		self.assertIsNone(dial_code("ZZ"))
		self.assertIsNone(dial_code(""))
		self.assertIsNone(dial_code(None))

	def test_example_numbers_are_country_shaped(self):
		# The placeholder should look like a local number, not one global
		# format that is wrong everywhere but home.
		self.assertTrue(example_national_number("EG").startswith("01"))
		self.assertIn("(", example_national_number("CA"))

	def test_example_number_of_an_unknown_region(self):
		self.assertEqual(example_national_number("ZZ"), "")

	def test_normalize_region_accepts_valid_codes(self):
		self.assertEqual(normalize_region("eg"), "EG")
		self.assertEqual(normalize_region("CA"), "CA")

	def test_normalize_region_falls_back(self):
		# An unknown region must never mean "no rules at all".
		self.assertEqual(normalize_region("ZZ", "EG"), "EG")
		self.assertEqual(normalize_region(None, "CA"), "CA")
		self.assertEqual(normalize_region("", "SA"), "SA")


class TestCountryList(FrappeTestCase):
	def setUp(self):
		countries.clear_cache()
		self.addCleanup(countries.clear_cache)

	def test_list_is_substantial(self):
		self.assertGreater(len(countries.build()), 200)

	def test_every_entry_is_complete(self):
		for entry in countries.build():
			with self.subTest(code=entry["code"]):
				self.assertEqual(len(entry["code"]), 2)
				self.assertTrue(entry["name"])
				self.assertTrue(entry["name_en"])
				self.assertGreater(entry["dial"], 0)
				self.assertTrue(entry["flag"])

	def test_entries_carry_an_english_name_for_search(self):
		"""So an Arabic reader can still type "egypt" or "eg" and find مصر."""
		by_code = {c["code"]: c for c in countries.build()}
		self.assertEqual(by_code["EG"]["name_en"], "Egypt")
		self.assertEqual(by_code["SA"]["name_en"], "Saudi Arabia")

	def test_sorted_the_way_a_person_reads_it(self):
		"""Ordered accent-insensitively, as the database collation sorts.

		Python's own `sorted` compares codepoints, which files "Åland
		Islands" after Zimbabwe. MySQL's `utf8mb4_unicode_ci` files it
		under A, which is where a person looking for it would look - so
		the database order is the correct one, and this normalises before
		comparing rather than asserting the naive sort.
		"""
		import unicodedata

		def sort_key(name):
			stripped = unicodedata.normalize("NFKD", name)
			return "".join(c for c in stripped if not unicodedata.combining(c)).casefold()

		names = [c["name"] for c in countries.build()]
		self.assertEqual(names, sorted(names, key=sort_key))

	def test_known_countries_are_present_and_correct(self):
		by_code = {c["code"]: c for c in countries.build()}
		self.assertEqual(by_code["EG"]["dial"], 20)
		self.assertEqual(by_code["EG"]["flag"], "🇪🇬")
		self.assertEqual(by_code["CA"]["dial"], 1)
		self.assertEqual(by_code["SA"]["dial"], 966)

	def test_the_payload_carries_a_default(self):
		payload = countries.for_signup()
		self.assertIn("countries", payload)
		self.assertTrue(payload["default"])
		self.assertIn(payload["default"], {c["code"] for c in payload["countries"]})

	def test_the_list_is_cached_and_invalidated(self):
		first = countries.get_all()
		self.assertEqual(countries.get_all(), first)
		countries.clear_cache()
		self.assertEqual(len(countries.get_all()), len(first))

	def test_endpoint_is_guest_readable(self):
		# It is the public list of countries this shop accepts a number
		# from, and carries nothing about anybody.
		# `frappe.whitelist` records the function in these module-level
		# lists rather than tagging it with an attribute.
		self.assertIn(countries.for_signup, frappe.whitelisted)
		self.assertIn(countries.for_signup, frappe.guest_methods)


class TestTheCountryDecidesTheRules(FrappeTestCase):
	"""The picker's actual purpose: the same digits mean different things."""

	def test_the_same_local_number_resolves_per_country(self):
		# 01012345678 is a valid Egyptian mobile.
		self.assertEqual(to_e164("01012345678", region="EG"), "+201012345678")
		# The same digits are not a valid Canadian number.
		self.assertRaises(InvalidPhoneNumber, to_e164, "01012345678", region="CA")

	def test_a_canadian_number_needs_canada_selected(self):
		self.assertEqual(to_e164("506 234 5678", region="CA"), "+15062345678")
		self.assertRaises(InvalidPhoneNumber, to_e164, "506 234 5678", region="EG")

	def test_a_saudi_number_under_saudi_rules(self):
		self.assertEqual(to_e164("0512345678", region="SA"), "+966512345678")

	def test_the_error_names_the_chosen_country_s_format(self):
		"""Telling a Canadian to type "01012345678" is worse than useless."""
		with self.assertRaises(InvalidPhoneNumber) as ca:
			to_e164("123", region="CA")
		with self.assertRaises(InvalidPhoneNumber) as eg:
			to_e164("123", region="EG")

		self.assertIn("(506)", str(ca.exception))
		self.assertIn("010", str(eg.exception))
		self.assertNotIn("010", str(ca.exception))

	def test_full_international_input_ignores_the_selection(self):
		# Typing the country code explicitly should win over the picker,
		# so a pasted +20 number works whatever is selected.
		self.assertEqual(to_e164("+201012345678", region="CA"), "+201012345678")
		self.assertEqual(to_e164("+15062345678", region="EG"), "+15062345678")
