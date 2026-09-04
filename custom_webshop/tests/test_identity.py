# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for custom_webshop.signup.identity - the phone/email/name
normalization and validation primitives the whole signup flow is built on.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.signup.identity import (
	InvalidEmail,
	InvalidFullName,
	InvalidPhoneNumber,
	clean_name,
	mask_email,
	mask_phone,
	name_tokens,
	names_match,
	normalize_email,
	normalize_name,
	repair_name,
	to_e164,
	to_local,
	try_to_e164,
	validate_full_name,
)

# The four mobile prefixes actually issued in Egypt, per
# contact_enhancements.api.lead_lookup.EGYPT_MOBILE_PATTERN.
EGYPT_PREFIXES = ("010", "011", "012", "015")


class TestPhoneNormalization(FrappeTestCase):
	def test_all_egyptian_prefixes_are_accepted(self):
		for prefix in EGYPT_PREFIXES:
			with self.subTest(prefix=prefix):
				self.assertEqual(try_to_e164(f"{prefix}12345678"), f"+20{prefix[1:]}12345678")

	def test_every_input_format_resolves_to_one_identity(self):
		# Acceptance criterion 7: these must all be the same phone identity.
		for raw in (
			"01012345678",
			"+201012345678",
			"00201012345678",
			"201012345678",
			"+20 101 234 5678",
			"0101-234-5678",
			"(010) 1234 5678",
			"  01012345678  ",
			"010.1234.5678",
		):
			with self.subTest(raw=raw):
				self.assertEqual(try_to_e164(raw), "+201012345678")

	def test_rejects_the_garbage_number_present_in_live_data(self):
		# tabCustomer "OMAR SABRY" carries this 18-digit value today.
		self.assertIsNone(try_to_e164("011011012121212121"))

	def test_rejects_invalid_numbers(self):
		for raw in ("", None, "   ", "abc", "0121234567", "01312345678", "123", "0000000000"):
			with self.subTest(raw=raw):
				self.assertIsNone(try_to_e164(raw))

	def test_bare_local_number_starting_with_20_is_not_mangled(self):
		# "201012345678" is only accepted because prepending "+" yields a
		# genuinely valid number; a short local string starting with 20
		# must not be silently reinterpreted as a country code.
		self.assertIsNone(try_to_e164("2012345"))

	def test_supports_international_numbers_for_future_expansion(self):
		self.assertEqual(try_to_e164("+14155552671"), "+14155552671")

	def test_try_to_e164_never_raises(self):
		for raw in (None, "", "!!!", 12345, "01012345678"):
			with self.subTest(raw=raw):
				try_to_e164(raw)

	def test_to_e164_throws_on_invalid(self):
		self.assertRaises(InvalidPhoneNumber, to_e164, "01312345678")
		self.assertRaises(InvalidPhoneNumber, to_e164, "")

	def test_to_e164_returns_canonical_form(self):
		self.assertEqual(to_e164("01012345678"), "+201012345678")

	def test_to_local_renders_egyptian_numbers_with_leading_zero(self):
		# This is the form written into Contact Phone.phone, matching both
		# existing data and contact_enhancements.
		self.assertEqual(to_local("+201012345678"), "01012345678")
		self.assertEqual(to_local("+201512345678"), "01512345678")

	def test_to_local_leaves_non_egyptian_numbers_in_e164(self):
		self.assertEqual(to_local("+14155552671"), "+14155552671")

	def test_to_local_handles_blank(self):
		self.assertEqual(to_local(""), "")
		self.assertEqual(to_local(None), "")

	def test_round_trip_local_to_e164(self):
		for prefix in EGYPT_PREFIXES:
			with self.subTest(prefix=prefix):
				e164 = to_e164(f"{prefix}12345678")
				self.assertEqual(to_e164(to_local(e164)), e164)

	def test_mask_phone_hides_the_middle(self):
		masked = mask_phone("+201012345678")
		self.assertTrue(masked.startswith("+20 101 "))
		self.assertTrue(masked.endswith("78"))
		self.assertNotIn("2345", masked)

	def test_mask_phone_handles_blank(self):
		self.assertEqual(mask_phone(None), "")
		self.assertEqual(mask_phone(""), "")


class TestEmailNormalization(FrappeTestCase):
	def test_valid_address_is_casefolded(self):
		self.assertEqual(normalize_email("User@Example.COM"), "user@example.com")

	def test_whitespace_is_stripped(self):
		self.assertEqual(normalize_email("  user@example.com  "), "user@example.com")

	def test_display_name_form_is_reduced_to_the_address(self):
		self.assertEqual(normalize_email("Jane Doe <jane@example.com>"), "jane@example.com")

	def test_rejects_address_without_at_sign(self):
		self.assertRaises(InvalidEmail, normalize_email, "userexample.com")

	def test_rejects_blank(self):
		self.assertRaises(InvalidEmail, normalize_email, "")
		self.assertRaises(InvalidEmail, normalize_email, None)

	def test_rejects_multiple_addresses(self):
		self.assertRaises(InvalidEmail, normalize_email, "a@example.com,b@example.com")
		self.assertRaises(InvalidEmail, normalize_email, "a@example.com;b@example.com")

	def test_plus_tags_and_dots_are_preserved(self):
		# Deliberate: merging a+tag@ with a@ would merge two identities.
		self.assertEqual(normalize_email("a.b+shop@example.com"), "a.b+shop@example.com")

	def test_mask_email(self):
		self.assertEqual(mask_email("ahmed@example.com"), "a****@example.com")
		self.assertEqual(mask_email("a@example.com"), "*@example.com")
		self.assertEqual(mask_email(""), "")
		self.assertEqual(mask_email(None), "")


class TestNameNormalization(FrappeTestCase):
	def test_collapses_whitespace(self):
		self.assertEqual(clean_name("  Ahmed   Amin  Algewily "), "Ahmed Amin Algewily")

	def test_clean_name_does_not_escape_html(self):
		# Regression: the previous signup ran escape_html before storing,
		# corrupting the value and then failing the "no symbols" rule.
		self.assertEqual(clean_name("Ahmed & Sons"), "Ahmed & Sons")
		self.assertEqual(clean_name("O'Brien Smith Jones"), "O'Brien Smith Jones")

	def test_normalize_strips_diacritics_and_tatweel(self):
		self.assertEqual(normalize_name("مُحمد"), normalize_name("محمد"))
		self.assertEqual(normalize_name("محمــد"), normalize_name("محمد"))

	def test_normalize_folds_arabic_orthography_variants(self):
		self.assertEqual(normalize_name("أحمد"), normalize_name("احمد"))
		self.assertEqual(normalize_name("إبراهيم"), normalize_name("ابراهيم"))
		self.assertEqual(normalize_name("فاطمة"), normalize_name("فاطمه"))
		self.assertEqual(normalize_name("الجويلى"), normalize_name("الجويلي"))

	def test_normalize_casefolds_latin(self):
		self.assertEqual(normalize_name("AHMED amin"), normalize_name("Ahmed Amin"))

	def test_name_tokens(self):
		self.assertEqual(name_tokens("Ahmed Amin Algewily"), ["ahmed", "amin", "algewily"])
		self.assertEqual(name_tokens(""), [])
		self.assertEqual(name_tokens(None), [])


class TestNamesMatch(FrappeTestCase):
	def test_identical_names_match(self):
		self.assertTrue(names_match("Ahmed Amin Algewily", "Ahmed Amin Algewily"))

	def test_reordered_names_match(self):
		self.assertTrue(names_match("Ahmed Amin Algewily", "Algewily Ahmed Amin"))

	def test_case_and_spacing_differences_match(self):
		self.assertTrue(names_match("  AHMED   amin ALGEWILY ", "Ahmed Amin Algewily"))

	def test_arabic_orthography_variants_match(self):
		self.assertTrue(names_match("أحمد امين الجويلى", "احمد امين الجويلي"))

	def test_longer_form_of_the_same_name_matches(self):
		self.assertTrue(names_match("Ahmed Amin Algewily", "Ahmed Amin Mohamed Algewily"))

	def test_different_people_do_not_match(self):
		self.assertFalse(names_match("Ahmed Amin Algewily", "Mohamed Hassan Ali"))

	def test_same_first_name_only_does_not_match(self):
		# One shared token is not enough - this is the case that must stay
		# a PHONE_NAME_MISMATCH rather than a STRONG_MATCH.
		self.assertFalse(names_match("Ahmed Amin Algewily", "Ahmed Hassan Mahmoud"))

	def test_different_first_name_does_not_match(self):
		self.assertFalse(names_match("Ahmed Amin Algewily", "Mohamed Amin Algewily"))

	def test_blank_never_matches(self):
		self.assertFalse(names_match("", "Ahmed Amin Algewily"))
		self.assertFalse(names_match("Ahmed Amin Algewily", None))
		self.assertFalse(names_match(None, None))


class TestValidateFullName(FrappeTestCase):
	def test_accepts_three_latin_parts(self):
		self.assertEqual(validate_full_name("Ahmed Amin Algewily"), "Ahmed Amin Algewily")

	def test_accepts_four_parts(self):
		self.assertEqual(
			validate_full_name("Ahmed Amin Mohamed Ali"), "Ahmed Amin Mohamed Ali"
		)

	def test_rejects_two_parts(self):
		self.assertRaises(InvalidFullName, validate_full_name, "Ahmed Amin")

	def test_rejects_one_part(self):
		self.assertRaises(InvalidFullName, validate_full_name, "Ahmed")

	def test_rejects_blank(self):
		self.assertRaises(InvalidFullName, validate_full_name, "")
		self.assertRaises(InvalidFullName, validate_full_name, "   ")
		self.assertRaises(InvalidFullName, validate_full_name, None)

	def test_collapses_whitespace_before_counting_parts(self):
		# "Ahmed  Amin" is two parts, not three, despite the double space.
		self.assertRaises(InvalidFullName, validate_full_name, "Ahmed  Amin")

	def test_the_count_is_of_what_was_typed_not_what_survived_repair(self):
		"""A hyphen must not be able to satisfy the rule.

		`repair_name` turns anything that is not a letter into a space, so
		counting the repaired name lets punctuation decide: "Anne-Marie
		Dupont" is two names that become three words once the hyphen goes,
		and it used to pass the rule it should fail. Counting what the
		person supplied fixes it in both directions.
		"""
		# Two components wearing a hyphen - still two.
		self.assertRaises(InvalidFullName, validate_full_name, "Anne-Marie Dupont")
		self.assertRaises(InvalidFullName, validate_full_name, "Jean-Luc Picard")
		# Three components wearing an apostrophe - still three.
		self.assertEqual(
			validate_full_name("O'Brien Sean Murphy"), repair_name("O'Brien Sean Murphy")
		)

	def test_a_token_with_no_letters_is_not_a_name(self):
		# Three names and a typo, not four names.
		self.assertEqual(validate_full_name("Ahmed 1 Ali Hassan"), "Ahmed Ali Hassan")
		# Two names and a stray symbol is still two names.
		self.assertRaises(InvalidFullName, validate_full_name, "Ahmed & Hassan")

	def test_a_two_component_name_is_refused_in_any_script(self):
		"""The rule is about this shop's records, not about language.

		A two-character Chinese name is complete and correct as it stands.
		It still cannot be stored here, because these records are keyed on
		first name, father's name and family name - so it is refused
		cleanly, with its characters intact, rather than being mangled
		into something that passes.
		"""
		for raw in ("李伟", "Ahmed Sabry", "Иван Петров"):
			with self.subTest(raw=raw):
				self.assertRaises(InvalidFullName, validate_full_name, raw)
				# Refused, not corrupted: repair leaves the characters be.
				self.assertEqual(repair_name(raw), raw)

	def test_three_components_are_accepted_in_any_script(self):
		for raw in ("李 伟 明", "Иван Петров Сергеевич", "José María García",
		            "Müller Hans Peter", "احمد سبرى امين"):
			with self.subTest(raw=raw):
				self.assertEqual(validate_full_name(raw), raw)

	def test_the_message_says_what_the_business_needs(self):
		"""Not "your name is wrong" - "here is what we need"."""
		with self.assertRaises(InvalidFullName) as caught:
			validate_full_name("李伟")
		message = str(caught.exception)
		self.assertIn("first name", message)
		self.assertIn("father's name", message)
		self.assertIn("family name", message)

	def test_name_components_counts_what_was_supplied(self):
		from custom_webshop.signup.identity import name_components

		self.assertEqual(name_components("Ahmed Sabry Amin"), 3)
		self.assertEqual(name_components("  Ahmed   Sabry  Amin "), 3)
		self.assertEqual(name_components("Anne-Marie Dupont"), 2)
		self.assertEqual(name_components("Ahmed 1 Ali Hassan"), 3)
		self.assertEqual(name_components("李伟"), 1)
		self.assertEqual(name_components(""), 0)
		self.assertEqual(name_components(None), 0)

	def test_min_parts_is_configurable(self):
		self.assertEqual(validate_full_name("Ahmed Amin", min_parts=2), "Ahmed Amin")

	def test_accepts_valid_arabic_name(self):
		self.assertEqual(validate_full_name("احمد امين الجويله"), "احمد امين الجويله")

	def test_repairs_rather_than_rejects_every_arabic_rule(self):
		"""The five rules contact_enhancements enforces are all repairable.

		Each describes a spelling the business does not want stored - not a
		person it refuses to serve - so signup rewrites the name instead of
		turning them away.
		"""
		cases = [
			# rule 1: word-initial ALEF WITH HAMZA ABOVE
			("أحمد أمين الجويله", "احمد امين الجويله"),
			# rule 2: tashkeel and tatweel
			("مُحمَّد امين الجويله", "محمد امين الجويله"),
			("محمــد امين الجويله", "محمد امين الجويله"),
			# rule 3: repeated spaces
			("احمد   امين   الجويله", "احمد امين الجويله"),
			# rule 4: digits and symbols
			("Ahmed Amin Algewily1", "Ahmed Amin Algewily"),
			("Ahmed & Sons Ltd", "Ahmed Sons Ltd"),
			# rule 5: word-final YEH and TEH MARBUTA
			("احمد امين الجويلي", "احمد امين الجويلى"),
			("احمد امين فاطمة", "احمد امين فاطمه"),
			# all of them at once
			("أحمد مُحمَّد الجويلي", "احمد محمد الجويلى"),
		]
		for raw, expected in cases:
			with self.subTest(raw=raw):
				self.assertEqual(validate_full_name(raw), expected)

	def test_repaired_names_agree_with_the_contact_hook(self):
		"""The stored name and the Contact's name must not drift.

		`contact_enhancements` normalizes `Contact.first_name` on every save.
		If our repair left anything for it to change, the name on the signup
		session and the name on the Contact would differ - so applying its
		normalizer to our output has to be a no-op.
		"""
		try:
			from contact_enhancements.contact_hooks import normalize_arabic_first_name
		except ImportError:
			self.skipTest("contact_enhancements is not installed")

		awkward = [
			"أحمد أمين الجويلي",
			"مُحمَّد عَلي فاطمة",
			"محمــد٥ علي، حسن؟",
			"Ahmed & Sons Ltd 2026",
			"O'Brien Smith-Jones Junior",
			"احمد   امين   الجويلي",
			"Ahmed1Ali Hassan Omar",
		]
		for raw in awkward:
			with self.subTest(raw=raw):
				repaired = repair_name(raw)
				self.assertEqual(normalize_arabic_first_name(repaired), repaired)

	def test_combining_marks_are_deleted_not_spaced(self):
		# Regression: tashkeel are not letters, so a naive "non-letter becomes
		# a space" filter split "مُحمَّد" into three words.
		self.assertEqual(repair_name("مُحمَّد امين الجويله"), "محمد امين الجويله")
		self.assertEqual(len(repair_name("مُحمَّد امين الجويله").split(" ")), 3)

	def test_a_digit_between_letters_splits_the_word(self):
		# Matches contact_enhancements' rule 4 normalization: a disallowed
		# character becomes a space so two words cannot silently merge.
		self.assertEqual(repair_name("Ahmed1Ali Hassan Omar"), "Ahmed Ali Hassan Omar")

	def test_strips_arabic_punctuation_and_digits(self):
		# These live inside the Arabic Unicode block, so a block filter alone
		# would keep them.
		self.assertEqual(repair_name("علي! حسن؟ محمد"), "على حسن محمد")
		self.assertEqual(repair_name("احمد٥ امين الجويله"), "احمد امين الجويله")
		self.assertEqual(repair_name("احمد، امين، الجويله"), "احمد امين الجويله")

	def test_intra_name_punctuation_survives(self):
		# A hyphen or apostrophe belongs *inside* a component, and the
		# Contact hook keeps it. This used to turn into a space here,
		# which stored "O Brien" and "Anne Marie" - a different name from
		# the one the customer typed, and a different one from what the
		# Contact itself would hold.
		self.assertEqual(repair_name("Anne-Marie Dupont Martin"), "Anne-Marie Dupont Martin")
		self.assertEqual(repair_name("O'Brien Sean Murphy"), "O'Brien Sean Murphy")

	def test_anything_that_is_not_part_of_a_name_still_becomes_a_space(self):
		# Keeping punctuation is not the same as keeping everything: a
		# digit or a symbol still separates rather than merges, so
		# "Ahmed1Ali" cannot read as "AhmedAli".
		self.assertEqual(repair_name("Ahmed1Ali Sabry Amin"), "Ahmed Ali Sabry Amin")
		# And punctuation with no letter around it is not a component.
		self.assertEqual(repair_name("Ahmed - Sabry Amin"), "Ahmed Sabry Amin")

	def test_marks_that_carry_vowels_are_not_stripped(self):
		# Devanagari, Tamil, Bengali and Hebrew write their vowels as
		# combining marks. Deleting those left the consonants standing -
		# so nothing errored and the field was not empty, but the name was
		# quietly wrong. Arabic tashkeel is the deliberate exception.
		for name in ("राम कुमार शर्मा", "ராம் குமார் சர்மா", "রাম কুমার শর্মা"):
			self.assertEqual(repair_name(name), name)

	def test_repair_is_idempotent(self):
		for raw in ("أحمد مُحمَّد الجويلي", "Ahmed & Sons Ltd", "احمد امين فاطمة"):
			with self.subTest(raw=raw):
				once = repair_name(raw)
				self.assertEqual(repair_name(once), once)

	def test_repair_leaves_a_clean_name_untouched(self):
		for raw in ("Ahmed Amin Algewily", "احمد امين الجويله", "Mohamed Hassan Ali"):
			with self.subTest(raw=raw):
				self.assertEqual(repair_name(raw), raw)

	def test_repair_handles_blank(self):
		self.assertEqual(repair_name(""), "")
		self.assertEqual(repair_name(None), "")
		self.assertEqual(repair_name("   "), "")

	def test_still_rejects_what_cannot_be_repaired(self):
		# A name cannot be invented, so too few parts is still a refusal -
		# and input that repairs down to nothing has no name in it at all.
		for raw in ("Ahmed Amin", "Ahmed", "123 456 789", "!!! ??? ***", "٥٦٧"):
			with self.subTest(raw=raw):
				self.assertRaises(InvalidFullName, validate_full_name, raw)

	def test_repair_can_reduce_the_part_count(self):
		# "Ahmed 1 Amin" looks like three parts but the middle one is a digit,
		# so after repair only two names remain and it is correctly refused.
		self.assertRaises(InvalidFullName, validate_full_name, "Ahmed 1 Amin")
