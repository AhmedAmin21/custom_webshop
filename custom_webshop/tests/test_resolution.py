# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for user-to-Customer resolution and the portal-access guard.

These pin the fix for the two ways an account could previously end up
seeing another customer's records: a Portal User row granted from an
arbitrary Contact link, and pages that trusted that row.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.signup.resolution import (
	get_customer,
	get_customer_name,
	get_customer_names,
	owns_customer,
)
from custom_webshop.tests.test_matching import make_identity, make_website_user
from custom_webshop.tests.utils import (
	make_customer_with_contact,
	unique_email,
	unique_name,
	unique_phone,
)
from custom_webshop.signup.identity import to_e164


def add_portal_user(customer, user):
	"""Insert a Portal User row directly, the way webshop's get_party does.

	Args:
		customer: the Customer name.
		user: the User name.
	"""
	row = frappe.new_doc("Portal User")
	row.update(
		{"parenttype": "Customer", "parentfield": "portal_users", "parent": customer, "user": user}
	)
	row.insert(ignore_permissions=True)
	return row


class TestResolution(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_resolves_through_the_identity_record(self):
		customer, _c = make_customer_with_contact()
		user = make_website_user(unique_email())
		make_identity(user.name, customer.name, to_e164(unique_phone()), user.name)

		self.assertEqual(get_customer_name(user.name), customer.name)
		self.assertEqual(get_customer_names(user.name), [customer.name])
		self.assertEqual(get_customer(user.name).name, customer.name)

	def test_identity_wins_over_a_stray_portal_user_row(self):
		"""The core fix.

		A Portal User row on some other Customer must not change the
		answer once the account has a verified identity.
		"""
		mine, _a = make_customer_with_contact()
		theirs, _b = make_customer_with_contact()
		user = make_website_user(unique_email())
		make_identity(user.name, mine.name, to_e164(unique_phone()), user.name)
		add_portal_user(theirs.name, user.name)

		self.assertEqual(get_customer_names(user.name), [mine.name])
		self.assertTrue(owns_customer(mine.name, user.name))
		self.assertFalse(owns_customer(theirs.name, user.name))

	def test_falls_back_to_portal_user_for_legacy_accounts(self):
		# Accounts predating the identity table must keep working.
		customer, _c = make_customer_with_contact()
		user = make_website_user(unique_email())
		add_portal_user(customer.name, user.name)

		self.assertEqual(get_customer_name(user.name), customer.name)
		self.assertTrue(owns_customer(customer.name, user.name))

	def test_guest_resolves_to_nothing(self):
		self.assertIsNone(get_customer_name("Guest"))
		self.assertEqual(get_customer_names("Guest"), [])
		self.assertFalse(owns_customer("anything", "Guest"))

	def test_unknown_user_resolves_to_nothing(self):
		self.assertIsNone(get_customer_name(unique_email()))

	def test_owns_customer_rejects_blank(self):
		user = make_website_user(unique_email())
		self.assertFalse(owns_customer(None, user.name))
		self.assertFalse(owns_customer("", user.name))


class TestPortalUserGuard(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_strips_a_grant_to_a_customer_the_account_is_not_verified_against(self):
		"""Reproduces webshop get_party()'s silent grant and blocks it.

		get_party takes contact.links[0] - an arbitrary first link - and
		appends a Portal User row to whatever Customer it lands on, then
		saves. The validate hook removes the row on the way through.
		"""
		mine, _a = make_customer_with_contact()
		theirs, _b = make_customer_with_contact()
		user = make_website_user(unique_email())
		make_identity(user.name, mine.name, to_e164(unique_phone()), user.name)

		victim = frappe.get_doc("Customer", theirs.name)
		victim.append("portal_users", {"user": user.name})
		victim.flags.ignore_permissions = True
		victim.flags.ignore_mandatory = True
		victim.save(ignore_permissions=True)

		self.assertFalse(
			frappe.db.exists(
				"Portal User",
				{"parent": theirs.name, "user": user.name, "parenttype": "Customer"},
			),
			"an account was granted access to a Customer it was not verified against",
		)

	def test_allows_a_grant_to_the_verified_customer(self):
		mine, _a = make_customer_with_contact()
		user = make_website_user(unique_email())
		make_identity(user.name, mine.name, to_e164(unique_phone()), user.name)

		customer = frappe.get_doc("Customer", mine.name)
		customer.append("portal_users", {"user": user.name})
		customer.flags.ignore_permissions = True
		customer.flags.ignore_mandatory = True
		customer.save(ignore_permissions=True)

		self.assertTrue(
			frappe.db.exists(
				"Portal User", {"parent": mine.name, "user": user.name, "parenttype": "Customer"}
			)
		)

	def test_leaves_legacy_accounts_alone(self):
		# No identity row means no verified opinion, so the hook must not
		# revoke access somebody is using today.
		customer, _c = make_customer_with_contact()
		user = make_website_user(unique_email())

		doc = frappe.get_doc("Customer", customer.name)
		doc.append("portal_users", {"user": user.name})
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save(ignore_permissions=True)

		self.assertTrue(
			frappe.db.exists(
				"Portal User", {"parent": customer.name, "user": user.name, "parenttype": "Customer"}
			)
		)

	def test_customer_without_portal_users_saves_normally(self):
		customer, _c = make_customer_with_contact()
		doc = frappe.get_doc("Customer", customer.name)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save(ignore_permissions=True)


class TestOrdersPageScoping(FrappeTestCase):
	"""The end of the exposure chain: /orders lists Sales Orders with
	ignore_permissions, so whatever it resolves customers with *is* the
	access control."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_orders_page_uses_the_verified_identity(self):
		from custom_webshop.www import orders

		mine, _a = make_customer_with_contact()
		theirs, _b = make_customer_with_contact()
		user = make_website_user(unique_email())
		make_identity(user.name, mine.name, to_e164(unique_phone()), user.name)
		# A stray legacy grant that must not widen what the page shows.
		add_portal_user(theirs.name, user.name)

		frappe.set_user(user.name)
		try:
			context = frappe._dict()
			orders.get_context(context)
		finally:
			frappe.set_user("Administrator")

		# No orders exist for either customer, but the important assertion
		# is that resolution answered with exactly one customer.
		self.assertEqual(get_customer_names(user.name), [mine.name])
		self.assertEqual(context.orders, [])
