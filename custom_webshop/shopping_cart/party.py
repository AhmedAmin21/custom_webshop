# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Safe party resolution for the webshop.

Eliminates the auto-creation of Customer documents for System Users (employees,
administrators) visiting webshop pages, while preserving manual Customer creation
and linking in ERPNext Desk.
"""

import sys
import frappe

_original_get_party = None


def safe_get_party(user=None):
	"""Return the Customer doc for a user without auto-creating Customers for System Users.

	Behavior:
	1. If the user already has a Customer linked (via Webshop Account Identity,
	   Portal User child table, or Contact dynamic links), that Customer is returned.
	   This ensures manual linking of Customers to System Users works seamlessly.
	2. If the user is a 'System User' or 'Administrator' and has NO Customer linked,
	   returns None. Crucially, this suppresses stock webshop's automatic
	   customer insertion.
	3. If the user is a 'Website User' without a Customer, delegates to the original
	   webshop get_party logic.

	Args:
		user: The User name (email); defaults to frappe.session.user.

	Returns:
		A Customer document, or None.
	"""
	if not user:
		user = frappe.session.user

	if not user or user == "Guest":
		return None

	# 1. Authoritative Webshop Account Identity (highest priority)
	identity_customer = frappe.db.get_value("Webshop Account Identity", {"user": user}, "customer")
	if identity_customer and frappe.db.exists("Customer", identity_customer):
		return frappe.get_doc("Customer", identity_customer)

	# 2. Manual link via Portal User child table on Customer
	portal_customer = frappe.db.get_value(
		"Portal User",
		{"user": user, "parenttype": "Customer"},
		"parent",
		order_by="creation desc",
	)
	if portal_customer and frappe.db.exists("Customer", portal_customer):
		return frappe.get_doc("Customer", portal_customer)

	# 3. Dynamic Link on user's primary Contact to a Customer
	try:
		from frappe.contacts.doctype.contact.contact import get_contact_name

		contact_name = get_contact_name(user)
		if contact_name:
			contact = frappe.get_doc("Contact", contact_name)
			for link in (contact.links or []):
				if link.link_doctype == "Customer" and frappe.db.exists("Customer", link.link_name):
					return frappe.get_doc("Customer", link.link_name)
	except Exception:
		pass

	# 4. Check user_type: System Users must NEVER be auto-created as Customers
	user_type = frappe.db.get_value("User", user, "user_type")
	if user_type == "System User" or user == "Administrator":
		return None

	# 5. Website Users fallback to original webshop get_party
	global _original_get_party
	if _original_get_party:
		return _original_get_party(user)

	return None


def safe_set_price_list(cart_settings, quotation=None):
	"""Set price list based on customer or shopping cart default.

	Safe against get_party() returning None for System Users without a customer.
	"""
	from erpnext.accounts.party import get_default_price_list

	party_name = quotation.get("party_name") if quotation else None
	if not party_name:
		party = safe_get_party()
		if party:
			party_name = party.get("name")

	selling_price_list = None

	# check if default customer price list exists
	if party_name and frappe.db.exists("Customer", party_name):
		selling_price_list = get_default_price_list(
			frappe.get_doc("Customer", party_name)
		)

	# check default price list in shopping cart
	if not selling_price_list:
		selling_price_list = cart_settings.price_list

	if quotation:
		quotation.selling_price_list = selling_price_list

	return selling_price_list


def patch_webshop_get_party():
	"""Monkey-patch webshop get_party and _set_price_list across modules."""
	global _original_get_party

	try:
		import webshop.webshop.shopping_cart.cart as webshop_cart

		if webshop_cart.get_party is not safe_get_party:
			_original_get_party = webshop_cart.get_party
			webshop_cart.get_party = safe_get_party

		webshop_cart._set_price_list = safe_set_price_list

		# Patch other modules that imported get_party or _set_price_list directly
		import webshop.webshop.doctype.website_item.website_item as web_item_mod
		web_item_mod.get_party = safe_get_party
		web_item_mod._set_price_list = safe_set_price_list

		import webshop.webshop.shopping_cart.product_info as prod_info_mod
		prod_info_mod.get_party = safe_get_party
		prod_info_mod._set_price_list = safe_set_price_list

		modules_to_patch = [
			"webshop.templates.pages.wishlist",
			"custom_webshop.shopping_cart.cart_override",
			"custom_webshop.shopping_cart.shipping_api",
			"custom_webshop.www.checkout.index",
		]

		for mod_name in modules_to_patch:
			mod = sys.modules.get(mod_name)
			if mod and hasattr(mod, "get_party"):
				setattr(mod, "get_party", safe_get_party)
			if mod and hasattr(mod, "_set_price_list"):
				setattr(mod, "_set_price_list", safe_set_price_list)
	except Exception as e:
		frappe.logger("custom_webshop").warning(f"Failed to patch webshop get_party: {e}")

