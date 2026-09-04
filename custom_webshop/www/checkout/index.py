import json

import frappe
from frappe.contacts.doctype.contact.contact import get_contact_name
from webshop.webshop.shopping_cart.cart import _get_cart_quotation as _fetch_cart_quotation, get_party

from custom_webshop.shopping_cart.shipping_api import _get_cart_weight_info

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.session_user = frappe.session.user
	context.is_guest = frappe.session.user == "Guest"
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.cart_bootstrap = "null"

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/cart"
		raise frappe.Redirect

	quotation = _fetch_cart_quotation()
	if quotation and quotation.get("shipping_rule"):
		is_governorate = frappe.db.get_value(
			"Shipping Rule", quotation.shipping_rule, "calculate_based_on"
		) == "Governorate"
		if not is_governorate:
			quotation.shipping_rule = None
			quotation.shipping_destination = None
			quotation.set(
				"taxes",
				[
					t
					for t in quotation.get("taxes", [])
					if "shipping" not in (t.description or "").lower()
				],
			)
			quotation.flags.ignore_permissions = True
			quotation.save()

	context.cart_bootstrap = json.dumps(_build_cart_bootstrap(quotation))
	return context


def _build_cart_bootstrap(quotation=None):
	user = frappe.session.user
	user_fullname = (
		frappe.session.user_fullname
		or frappe.db.get_value("User", user, "full_name")
		or frappe.db.get_value("User", user, "first_name")
		or user
	)
	mobile_no = frappe.db.get_value("User", user, "mobile_no") or ""

	contact_name = get_contact_name(user)
	if contact_name:
		# Contact.mobile_no is a read-only virtual field; query the child table directly
		contact_mobile = frappe.db.get_value(
			"Contact Phone",
			{"parent": contact_name, "is_primary_mobile_no": 1},
			"phone",
		)
		if contact_mobile:
			mobile_no = contact_mobile
		elif not mobile_no:
			# fallback: any phone on the contact
			any_phone = frappe.db.get_value("Contact Phone", {"parent": contact_name}, "phone")
			if any_phone:
				mobile_no = any_phone
		if not user_fullname or user_fullname == user:
			first = frappe.db.get_value("Contact", contact_name, "first_name")
			if first:
				user_fullname = first

	address_line1 = ""
	city = ""
	country = frappe.db.get_default("country") or "Egypt"
	address_name = None
	contact_name_for_edit = contact_name

	party = get_party()
	if party:
		addresses = frappe.db.sql(
			"""
			SELECT a.name, a.address_line1, a.city, a.country
			FROM `tabAddress` a
			INNER JOIN `tabDynamic Link` dl ON dl.parent = a.name
			WHERE dl.link_doctype = 'Customer' AND dl.link_name = %s
			ORDER BY a.modified DESC
			LIMIT 1
			""",
			party.name,
			as_dict=True,
		)
		if addresses:
			addr = addresses[0]
			address_name = addr.name
			address_line1 = addr.address_line1 or ""
			city = addr.city or ""
			country = addr.country or country

	weight_info = _get_cart_weight_info(quotation)

	return {
		"user_fullname": user_fullname,
		"mobile_no": mobile_no or "",
		"address_line1": address_line1,
		"city": city,
		"country": country,
		"address_name": address_name,
		"contact_name": contact_name_for_edit,
		# Read with .get: `shipping_destination` is not a Quotation field
		# here. It belongs to custom_shipping_rule, which this site does
		# not have installed, and attribute access on a field a doctype
		# does not carry raises - which took the whole checkout page down
		# with a 500. www/payment.py already reads it this way.
		"shipping_rule": quotation.get("shipping_rule") or "",
		"shipping_destination": quotation.get("shipping_destination") or "",
		"total_weight": weight_info.get("total_weight") or 0,
		"weight_uom": weight_info.get("weight_uom") or "",
	}
