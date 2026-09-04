# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for the login page's signup entry point.

The point of these is that the "Create one" button and the endpoint behind
it are driven by the same decision. A page that offers a signup the API
then refuses is worse than one that offers nothing.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.api.signup import is_available
from custom_webshop.tests.utils import (
	signup_allowed,
	signup_blocked_site_wide,
	signup_settings_as,
)
from custom_webshop.www.login import index as login_page


def build_context():
	"""Render the login page context as a guest.

	Returns:
		The populated context dict.
	"""
	context = frappe._dict()
	login_page.get_context(context)
	return context


class TestSignupAvailability(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_available_when_every_switch_is_on(self):
		with signup_allowed(), signup_settings_as(
			signup_enabled=1, email_otp_enabled=1, phone_otp_enabled=1, otp_dev_mode=0
		):
			self.assertTrue(is_available())

	def test_unavailable_when_the_site_wide_switch_is_set(self):
		# The outermost kill switch wins over every app-level flag.
		with signup_blocked_site_wide(), signup_settings_as(
			signup_enabled=1, email_otp_enabled=1, phone_otp_enabled=1, otp_dev_mode=1
		):
			self.assertFalse(is_available())

	def test_unavailable_when_the_app_switch_is_off(self):
		with signup_allowed(), signup_settings_as(signup_enabled=0):
			self.assertFalse(is_available())

	def test_unavailable_when_a_channel_cannot_deliver(self):
		with signup_allowed(), signup_settings_as(
			signup_enabled=1, email_otp_enabled=1, phone_otp_enabled=0, otp_dev_mode=0
		):
			self.assertFalse(is_available())

	def test_dev_mode_does_not_excuse_a_channel_being_off(self):
		# Dev mode changes how a code is delivered, never whether one is
		# required. A site with phone verification switched off cannot run
		# identity resolution safely, and saying "but it is only dev" does
		# not change that - so the signup is unavailable either way.
		with signup_allowed(), signup_settings_as(
			signup_enabled=1, email_otp_enabled=1, phone_otp_enabled=0, otp_dev_mode=1
		):
			self.assertFalse(is_available())

	def test_dev_mode_is_available_with_both_channels_on(self):
		# The case dev mode does exist for: no Email Account, no SMS
		# gateway, both channels required, codes go to the site log.
		with signup_allowed(), signup_settings_as(
			signup_enabled=1, email_otp_enabled=1, phone_otp_enabled=1, otp_dev_mode=1
		):
			self.assertTrue(is_available())


class TestSettingsCannotBeZeroed(FrappeTestCase):
	"""A newly-added Int setting arrives as 0 on an existing Single.

	Frappe only applies a DocType default when a document is inserted, and
	these settings were inserted long ago - so every new numeric field
	lands as 0 on a site that has already saved them. A 0 rate limit
	refuses every request, which would have taken signup down site-wide on
	the next migrate.
	"""

	def test_zero_falls_back_to_the_default(self):
		from custom_webshop.signup import settings as signup_settings

		for fieldname in signup_settings.MUST_BE_POSITIVE:
			with self.subTest(fieldname=fieldname):
				with signup_settings_as(**{fieldname: 0}):
					self.assertEqual(
						signup_settings.get_int(fieldname),
						signup_settings.DEFAULTS[fieldname],
						f"a zero {fieldname} must not be taken as configuration",
					)

	def test_a_real_value_is_still_honoured(self):
		from custom_webshop.signup import settings as signup_settings

		with signup_settings_as(otp_max_attempts=7):
			self.assertEqual(signup_settings.get_int("otp_max_attempts"), 7)

	def test_zero_is_still_legal_where_it_means_something(self):
		from custom_webshop.signup import settings as signup_settings

		# "no cooldown" and "flag off" are real settings, not broken ones.
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			self.assertEqual(signup_settings.get_int("otp_resend_cooldown_seconds"), 0)
		with signup_settings_as(signup_enabled=0):
			self.assertFalse(signup_settings.is_enabled("signup_enabled"))

	def test_the_signup_rate_limit_can_never_be_zero(self):
		from custom_webshop.api.signup import _signup_start_limit

		with signup_settings_as(signup_starts_per_hour_per_ip=0):
			self.assertGreater(_signup_start_limit(), 0, "a zero limit blocks every signup")


class TestLoginPageContext(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_offers_signup_exactly_when_the_api_would_accept_it(self):
		with signup_allowed(), signup_settings_as(
			signup_enabled=1, email_otp_enabled=1, phone_otp_enabled=1, otp_dev_mode=0
		):
			context = build_context()
			self.assertTrue(context.signup_available)
			self.assertEqual(context.signup_available, is_available())

	def test_hides_signup_when_the_api_would_refuse(self):
		with signup_allowed(), signup_settings_as(signup_enabled=0):
			context = build_context()
			self.assertFalse(context.signup_available)
			self.assertEqual(context.signup_available, is_available())

	def test_hides_signup_when_a_channel_cannot_deliver(self):
		# The regression this guards: the page used to read only
		# Website Settings, so it would advertise a signup that the first
		# request then declined.
		with signup_allowed(), signup_settings_as(
			signup_enabled=1, email_otp_enabled=1, phone_otp_enabled=0, otp_dev_mode=0
		):
			context = build_context()
			self.assertFalse(context.signup_available)

	def test_disable_signup_context_mirrors_availability(self):
		# page-login.js reads LOGIN_CONTEXT.disable_signup.
		with signup_allowed(), signup_settings_as(signup_enabled=1, otp_dev_mode=1):
			context = build_context()
			self.assertFalse(context.disable_signup)

	def test_provides_a_csrf_token(self):
		context = build_context()
		self.assertTrue(context.csrf_token)

	def test_logged_in_user_is_redirected_away(self):
		frappe.set_user("Administrator")
		self.assertRaises(frappe.Redirect, build_context)


class TestLoginTemplateMarkup(FrappeTestCase):
	"""The link has to exist in the template, not just in the context."""

	def setUp(self):
		import os

		path = os.path.join(
			frappe.get_app_path("custom_webshop"), "www", "login", "index.html"
		)
		with open(path, encoding="utf-8") as handle:
			self.markup = handle.read()

	def test_signup_entry_point_is_present(self):
		self.assertIn('id="go-to-signup"', self.markup)
		self.assertIn("switchTab('signup')", self.markup)

	def test_entry_point_is_gated_on_availability(self):
		self.assertIn("{% if signup_available %}", self.markup)
		self.assertNotIn("{% if not disable_signup %}", self.markup)

	def test_signup_view_and_wizard_mount_point_exist(self):
		self.assertIn('id="signup-view"', self.markup)
		self.assertIn('id="signup-wizard"', self.markup)

	def test_wizard_script_is_loaded(self):
		self.assertIn("page-signup.js", self.markup)

	def test_signup_view_links_back_to_login(self):
		self.assertIn("switchTab('login')", self.markup)
