# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for the password rules.

The bug these exist for: the wizard checked four rules as you typed and
the server checked only zxcvbn, so they could disagree. `Zx9$q` failed the
guide's "8 characters" and the server took it; switching the site's
password policy off left the server enforcing nothing at all behind four
green ticks. A client that validates one thing and a server that
validates another is a bug whichever way round it fails.

So the rules live in `signup.passwords`, the server enforces them, and the
page renders the guide from that module's own list. These tests hold both
halves of that: the rules themselves, and the fact that the page really is
being fed from them.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.api import signup as signup_api
from custom_webshop.signup import passwords
from custom_webshop.tests.utils import (
	signup_enabled,
	signup_settings_as,
	start_signup,
	unique_email,
	unique_phone,
	verify_both_channels,
)


def person(**overrides):
	"""A stand-in for the session document the rules read."""
	base = {
		"full_name": "Ahmed Sabry Amin",
		"company_name": None,
		"email_normalized": "ahmed.sabry@example.com",
		"phone_e164": "+201012345678",
		"phone_raw": "01012345678",
	}
	base.update(overrides)
	return frappe._dict(base)


class TestTheFourRules(FrappeTestCase):
	def parts(self, **overrides):
		return passwords.personal_parts(person(**overrides))

	def test_length(self):
		self.assertFalse(passwords.check("Zx9q4", self.parts())["length"])
		self.assertTrue(passwords.check("Zx9q4abc", self.parts())["length"])

	def test_letters_and_numbers(self):
		self.assertFalse(passwords.check("abcdefghij", self.parts())["mix"])
		self.assertFalse(passwords.check("1234567890", self.parts())["mix"])
		self.assertTrue(passwords.check("abcdefgh1", self.parts())["mix"])

	def test_arabic_counts_as_letters(self):
		# The shop is bilingual; a password typed in Arabic is a password.
		self.assertTrue(passwords.check("كلمةسرقوية9", self.parts())["mix"])

	def test_a_common_password_is_refused_however_it_is_dressed(self):
		for bad in ("password", "PASSWORD", "password12345", "qwerty999"):
			with self.subTest(bad=bad):
				self.assertFalse(passwords.check(bad, self.parts())["common"])
		self.assertTrue(passwords.check("Qamar7Nile", self.parts())["common"])

	def test_each_word_of_the_name_counts_separately(self):
		"""`Ahmed123` used to pass: it compared the whole name as one string."""
		for bad in ("Ahmed12345", "sabry9999", "AMIN2026x"):
			with self.subTest(bad=bad):
				self.assertFalse(passwords.check(bad, self.parts())["personal"])

	def test_the_email_and_its_local_part_count(self):
		self.assertFalse(passwords.check("ahmed.sabry1", self.parts())["personal"])

	def test_the_number_counts_however_it_was_typed(self):
		for bad in ("x1012345678", "x+201012345678", "x0101 234 5678"):
			with self.subTest(bad=bad):
				self.assertFalse(passwords.check(bad, self.parts())["personal"])

	def test_a_short_fragment_is_not_a_personal_detail(self):
		# Two-letter overlaps would fail almost everything.
		parts = self.parts(full_name="Jo Li Xu")
		self.assertTrue(passwords.check("Qamar7Nile", parts)["personal"])

	def test_a_good_password_passes_every_rule(self):
		self.assertTrue(all(passwords.check("Qamar7Nile", self.parts()).values()))

	def test_validate_names_the_rule_that_failed(self):
		cases = [
			("Zx9q4", "at least"),
			("abcdefghij", "letters and numbers"),
			("password123", "commonly used"),
			("Ahmed12345", "your own name"),
		]
		for bad, phrase in cases:
			with self.subTest(bad=bad):
				with self.assertRaises(frappe.ValidationError) as caught:
					passwords.validate(bad, self.parts())
				self.assertIn(phrase, str(caught.exception))


class TestTheServerEnforcesWhatTheGuideShows(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def ready_signup(self):
		with signup_enabled():
			client, _s = start_signup(
				full_name="Ahmed Sabry Amin", email=unique_email(), phone=unique_phone()
			)
			verify_both_channels(client)
			client.call(signup_api.resolve)
		return client

	def refuse(self, client, password):
		with signup_enabled():
			with self.assertRaises(frappe.ValidationError) as caught:
				client.call(
					signup_api.complete, password=password, confirm_password=password
				)
		return str(caught.exception)

	def test_a_short_password_is_refused_by_the_server_too(self):
		"""The gap that started this: five characters, four ticks, accepted."""
		client = self.ready_signup()
		self.assertIn("at least", self.refuse(client, "Zx9q4"))

	def test_letters_only_is_refused_by_the_server_too(self):
		client = self.ready_signup()
		self.assertIn("letters and numbers", self.refuse(client, "abcdefghijk"))

	def test_your_own_name_is_refused_by_the_server_too(self):
		client = self.ready_signup()
		self.assertIn("your own name", self.refuse(client, "Ahmed1234567"))

	def test_the_rules_hold_with_the_site_policy_switched_off(self):
		"""Without this the server enforced nothing at all.

		zxcvbn only runs when `enable_password_policy` is on. These four
		are the floor and do not depend on it.
		"""
		client = self.ready_signup()
		with signup_settings_as(), self.settings_without_policy():
			with signup_enabled():
				with self.assertRaises(frappe.ValidationError):
					client.call(signup_api.complete, password="Zx9q4", confirm_password="Zx9q4")

	def settings_without_policy(self):
		import contextlib

		@contextlib.contextmanager
		def off():
			previous = frappe.db.get_single_value("System Settings", "enable_password_policy")
			frappe.db.set_single_value("System Settings", "enable_password_policy", 0)
			frappe.clear_cache()
			try:
				yield
			finally:
				frappe.db.set_single_value(
					"System Settings", "enable_password_policy", previous
				)
				frappe.clear_cache()

		return off()


class TestThePageIsFedFromTheseRules(FrappeTestCase):
	def test_the_login_context_carries_the_server_list(self):
		"""The guide must not keep a second copy of the word list."""
		from custom_webshop.www.login.index import get_context

		context = frappe._dict()
		frappe.set_user("Guest")
		try:
			get_context(context)
		finally:
			frappe.set_user("Administrator")

		rules = context.get("password_rules") or {}
		self.assertEqual(rules.get("min_length"), passwords.MIN_LENGTH)
		self.assertEqual(rules.get("common"), list(passwords.COMMON))

	def test_the_page_renders_it_into_the_browser_context(self):
		import os

		path = frappe.get_app_path("custom_webshop", "www", "login", "index.html")
		with open(path, encoding="utf-8") as fh:
			html = fh.read()
		self.assertIn("password_rules", html)

		script = frappe.get_app_path("custom_webshop", "public", "js", "page-signup.js")
		with open(script, encoding="utf-8") as fh:
			js = fh.read()
		# The browser reads the injected list rather than hard-coding one.
		self.assertIn("password_rules", js)
		self.assertIn("MIN_PASSWORD_LENGTH", js)
