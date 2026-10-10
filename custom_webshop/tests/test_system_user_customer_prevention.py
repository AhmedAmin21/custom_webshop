# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests that System Users (employees) are never auto-created as Customers merely
from visiting webshop pages, while preserving manual Customer creation and linking.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.shopping_cart.party import safe_get_party, patch_webshop_get_party
from webshop.webshop.shopping_cart.cart import get_party as webshop_get_party
from custom_webshop.tests.utils import unique_email, unique_name, make_customer


class TestSystemUserCustomerPrevention(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		patch_webshop_get_party()

	def _create_system_user(self, first_name="Employee", role="Employee"):
		email = unique_email("sysuser")
		user = frappe.new_doc("User")
		user.update(
			{
				"email": email,
				"first_name": first_name,
				"send_welcome_email": 0,
			}
		)
		user.flags.ignore_permissions = True
		user.insert(ignore_permissions=True)
		user.add_roles(role)
		user.reload()
		return user

	def test_system_user_without_customer_returns_none_and_creates_no_records(self):
		"""A System User (employee/admin) visiting webshop pages must NEVER
		have a Customer or Portal User record auto-created."""
		user = self._create_system_user(first_name="StoreManager")

		# Record counts before
		customers_before = frappe.db.count("Customer")
		portal_users_before = frappe.db.count("Portal User")

		# Simulate browsing website / resolving party
		party = safe_get_party(user.name)

		self.assertIsNone(party)
		self.assertEqual(frappe.db.count("Customer"), customers_before)
		self.assertEqual(frappe.db.count("Portal User"), portal_users_before)
		self.assertFalse(frappe.db.exists("Portal User", {"user": user.name}))
		self.assertFalse(frappe.db.exists("Customer", {"customer_name": "StoreManager"}))

	def test_monkey_patched_webshop_get_party_protects_system_user(self):
		"""Calling webshop's get_party directly must invoke the safe guard."""
		user = self._create_system_user(first_name="WarehouseStaff")

		party = webshop_get_party(user.name)

		self.assertIsNone(party)
		self.assertFalse(frappe.db.exists("Portal User", {"user": user.name}))
		self.assertFalse(frappe.db.exists("Customer", {"customer_name": "WarehouseStaff"}))

	def test_manually_linked_customer_is_properly_recognized(self):
		"""When an administrator manually creates and links a Customer to a System User,
		safe_get_party must recognize and return that Customer."""
		user = self._create_system_user(first_name="SalesDirector")

		# Manually create Customer and link user in portal_users
		customer = make_customer(customer_name=unique_name("EmpCust"))
		customer.append("portal_users", {"user": user.name})
		customer.flags.ignore_permissions = True
		customer.flags.ignore_mandatory = True
		customer.save(ignore_permissions=True)

		party = safe_get_party(user.name)

		self.assertIsNotNone(party)
		self.assertEqual(party.name, customer.name)

	def test_guest_returns_none(self):
		"""Guest users should resolve to None without creating any records."""
		party = safe_get_party("Guest")
		self.assertIsNone(party)

	def test_product_page_price_list_does_not_crash_for_system_user(self):
		"""When a System User views a product page without having a Customer,
		_set_price_list must safely resolve the default price list without throwing AttributeError."""
		user = self._create_system_user(first_name="PriceInspector")
		frappe.session.user = user.name

		import webshop.webshop.doctype.website_item.website_item as web_item_mod
		cart_settings = frappe.get_cached_doc("Webshop Settings")

		# Must not throw AttributeError: 'NoneType' object has no attribute 'get'
		price_list = web_item_mod._set_price_list(cart_settings, None)
		self.assertEqual(price_list, cart_settings.price_list)
		self.assertFalse(frappe.db.exists("Customer", {"customer_name": "PriceInspector"}))

