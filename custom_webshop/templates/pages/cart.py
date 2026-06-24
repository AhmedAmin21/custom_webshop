# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from webshop.webshop.shopping_cart.cart import get_cart_quotation, get_party
from custom_webshop.shopping_cart.shipping_api import _get_cart_weight_info


def get_context(context):
	context.body_class = "product-page"

	context.update(get_cart_quotation())

	cart_weight = _get_cart_weight_info()
	context.update(cart_weight)

	for addr in context.get("shipping_addresses", []):
		full_addr = frappe.get_doc("Address", addr["name"]).as_dict()
		addr.update(full_addr)

	for addr in context.get("billing_addresses", []):
		full_addr = frappe.get_doc("Address", addr["name"]).as_dict()
		addr.update(full_addr)

	context.user_fullname = (
		frappe.session.user_fullname
		or frappe.db.get_value("User", frappe.session.user, "full_name")
		or frappe.session.user
	)

	party = get_party()
	if party:
		contact = frappe.db.sql(
			"""
			SELECT c.name, c.first_name, c.mobile_no
			FROM `tabContact` c
			JOIN `tabDynamic Link` dl ON dl.parent = c.name
			WHERE dl.link_doctype = 'Customer'
			AND dl.link_name = %s
			AND c.is_primary_contact = 1
			LIMIT 1
			""",
			party.name,
			as_dict=True,
		)
		if not contact:
			contact = frappe.db.sql(
				"""
				SELECT c.name, c.first_name, c.mobile_no
				FROM `tabContact` c
				JOIN `tabDynamic Link` dl ON dl.parent = c.name
				WHERE dl.link_doctype = 'Customer'
				AND dl.link_name = %s
				LIMIT 1
				""",
				party.name,
				as_dict=True,
			)
		if contact:
			context.primary_contact = contact[0]
