# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests that the legacy one-step signup is genuinely closed.

The old endpoint could create a User, Customer, Contact and Portal User
from one unauthenticated POST with nothing verified, and would attach the
new account to any existing Customer whose name string matched. These
assert that none of it can happen any more - including through Frappe's
own built-in `sign_up`, which this app's hook still intercepts.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.api.auth import custom_sign_up
from custom_webshop.tests.utils import (
	make_customer_with_contact,
	signup_allowed,
	unique_email,
	unique_name,
	unique_phone,
)


class TestLegacySignupIsClosed(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_declines_without_creating_an_account(self):
		email = unique_email()
		with signup_allowed():
			status, message = custom_sign_up(
				email=email,
				full_name=unique_name(),
				pwd="Str0ng-Passw0rd!x",
				mobile_no=unique_phone(),
			)

		self.assertEqual(status, 0)
		self.assertIn("sign-up form", message)
		self.assertFalse(frappe.db.exists("User", email))

	def test_creates_no_customer_or_contact(self):
		name = unique_name()
		before_customers = frappe.db.count("Customer")
		before_contacts = frappe.db.count("Contact")

		with signup_allowed():
			custom_sign_up(
				email=unique_email(), full_name=name, pwd="Str0ng-Passw0rd!x", mobile_no=unique_phone()
			)

		self.assertEqual(frappe.db.count("Customer"), before_customers)
		self.assertEqual(frappe.db.count("Contact"), before_contacts)

	def test_cannot_attach_to_an_existing_customer_by_name(self):
		"""The account-takeover regression, permanently.

		The old code matched on `customer_name` and granted a Portal User
		row. Nothing here can grant anything now.
		"""
		shared_name = unique_name("Shared")
		existing, _contact = make_customer_with_contact(customer_name=shared_name)
		email = unique_email()

		with signup_allowed():
			custom_sign_up(
				email=email,
				full_name=shared_name,
				pwd="Str0ng-Passw0rd!x",
				mobile_no=unique_phone(),
			)

		self.assertFalse(
			frappe.db.exists(
				"Portal User", {"parent": existing.name, "user": email, "parenttype": "Customer"}
			)
		)
		self.assertFalse(frappe.db.exists("User", email))

	def test_frappes_own_signup_is_intercepted(self):
		# The hook points frappe.core.doctype.user.user.sign_up here, so
		# the framework's built-in signup cannot be used to bypass
		# verification either.
		hooks = frappe.get_hooks("override_whitelisted_methods")
		self.assertEqual(
			hooks.get("frappe.core.doctype.user.user.sign_up"),
			["custom_webshop.api.auth.custom_sign_up"],
		)

	def test_accepts_any_arguments_without_failing(self):
		# An old cached client must get the message, not a signature error.
		with signup_allowed():
			self.assertEqual(custom_sign_up()[0], 0)
			self.assertEqual(custom_sign_up(email="x@example.com")[0], 0)
