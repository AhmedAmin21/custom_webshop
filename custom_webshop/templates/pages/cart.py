# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from webshop.webshop.shopping_cart.cart import get_cart_quotation, get_party, _get_cart_quotation as _fetch_cart_quotation
from custom_webshop.shopping_cart.shipping_api import _get_cart_weight_info, apply_cart_settings_for_webshop


def get_context(context):
	context.body_class = "product-page"

	# --- Fix: clear any non-Governorate shipping rule saved in the DB ---
	quotation = _fetch_cart_quotation()
	if quotation and quotation.get("shipping_rule"):
		is_governorate = frappe.db.get_value(
			"Shipping Rule", quotation.shipping_rule, "calculate_based_on"
		) == "Governorate"
		if not is_governorate:
			quotation.shipping_rule = None
			quotation.shipping_destination = None
			quotation.set("taxes", [t for t in quotation.get("taxes", []) if "shipping" not in (t.description or "").lower()])
			quotation.flags.ignore_permissions = True
			quotation.save()
	# ------------------------------------------------------------------

	context.update(get_cart_quotation())

	# Inject raw weight info so the payment summary can render it server-side
	cart_weight = _get_cart_weight_info()
	context.update(cart_weight)

	# Enrich shipping and billing addresses with full Address document fields
	# so the address_card template can access address_line1, city, country, etc.
	for addr in context.get("shipping_addresses", []):
		full_addr = frappe.get_doc("Address", addr["name"]).as_dict()
		addr.update(full_addr)

	for addr in context.get("billing_addresses", []):
		full_addr = frappe.get_doc("Address", addr["name"]).as_dict()
		addr.update(full_addr)

	# Get user full name for dialogs - fallback chain: session -> User doc -> username
	context.user_fullname = (
		frappe.session.user_fullname
		or frappe.db.get_value("User", frappe.session.user, "full_name")
		or frappe.session.user
	)

	# Fetch primary contact for customer to display phone in address cards
	party = get_party()
	if party:
		# FIX: Ensure contact is properly linked to customer
		# This prevents "Contact Person does not belong to Customer" errors
		user_email = frappe.session.user
		contact_name = frappe.db.get_value("Contact", {"email_id": user_email})
		
		if contact_name:
			# Check if contact has Dynamic Link to this customer
			has_link = frappe.db.exists("Dynamic Link", {
				"parenttype": "Contact",
				"parent": contact_name,
				"link_doctype": "Customer",
				"link_name": party.name
			})
			
			if not has_link:
				# Add missing customer link to contact
				contact_doc = frappe.get_doc("Contact", contact_name)
				contact_doc.append("links", {
					"link_doctype": "Customer",
					"link_name": party.name
				})
				if not contact_doc.is_primary_contact:
					contact_doc.is_primary_contact = 1
				contact_doc.save(ignore_permissions=True)
			
			# Update current quotation to use this contact
			quotation = frappe.db.get_value("Quotation", {
				"party_name": party.name,
				"contact_email": user_email,
				"order_type": "Shopping Cart",
				"docstatus": 0
			})
			if quotation:
				frappe.db.set_value("Quotation", quotation, "contact_person", contact_name)
				frappe.db.commit()
		
		# Now fetch for display
		contact = frappe.db.sql("""
			SELECT c.name, c.first_name, c.mobile_no
			FROM `tabContact` c
			JOIN `tabDynamic Link` dl ON dl.parent = c.name
			WHERE dl.link_doctype = 'Customer'
			AND dl.link_name = %s
			AND c.is_primary_contact = 1
			LIMIT 1
		""", party.name, as_dict=True)

		if contact:
			context.primary_contact = contact[0]
		else:
			# Try without is_primary_contact filter
			contact = frappe.db.sql("""
				SELECT c.name, c.first_name, c.mobile_no
				FROM `tabContact` c
				JOIN `tabDynamic Link` dl ON dl.parent = c.name
				WHERE dl.link_doctype = 'Customer'
				AND dl.link_name = %s
				LIMIT 1
			""", party.name, as_dict=True)
			if contact:
				context.primary_contact = contact[0]
