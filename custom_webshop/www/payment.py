# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from frappe import _
from frappe.utils import flt

from custom_webshop.signup.resolution import owns_customer


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.title = _("Payment")
	context.parents = [{"route": "me", "title": _("My Account")}]

	order_id = frappe.form_dict.get("order_id")
	context.order_id = order_id

	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/payment?order_id=" + order_id if order_id else "/login"
		raise frappe.Redirect

	if not order_id:
		context.invalid = True
		context.error = _("No order specified.")
		return context

	# Ownership is checked against the verified identity record, not the
	# Portal User table: this page loads a Sales Order by an id straight
	# out of the query string, so the check standing between one customer
	# and another's order has to be the authoritative one.
	sales_order = frappe.get_doc("Sales Order", order_id)
	if not sales_order or not owns_customer(sales_order.customer):
		context.invalid = True
		context.error = _("Order not found.")
		return context

	if sales_order.docstatus != 0:
		context.invalid = True
		context.error = _("This order does not require payment.")
		return context

	context.sales_order = sales_order
	context.grand_total_formatted = frappe.format_value(
		sales_order.grand_total,
		{"fieldtype": "Currency", "options": sales_order.currency}
	)

	# Shipping details — show raw total weight in its original UOM
	context.total_weight = flt(sales_order.total_net_weight)

	# Determine weight UOM from items (same logic as shipping_api)
	weight_uom = None
	if sales_order.get("weight_uom"):
		weight_uom = sales_order.weight_uom
	else:
		for item in sales_order.get("items", []):
			if item.get("weight_uom"):
				weight_uom = item.weight_uom
				break
	context.weight_uom = weight_uom or ""

	# Get shipping destination name
	if sales_order.get("shipping_destination"):
		context.shipping_destination = frappe.db.get_value(
			"Governorate", sales_order.shipping_destination, "governorate_name"
		) or sales_order.shipping_destination
	else:
		context.shipping_destination = None

	# Find shipping tax amount from taxes
	context.shipping_amount = 0
	for tax in sales_order.get("taxes", []):
		# Shipping rules typically add tax rows with description containing shipping
		if "shipping" in (tax.get("description") or "").lower():
			context.shipping_amount += flt(tax.tax_amount)

	context.shipping_amount_formatted = frappe.format_value(
		context.shipping_amount,
		{"fieldtype": "Currency", "options": sales_order.currency}
	)

	# Payment options
	settings = frappe.get_cached_doc("Webshop Settings")
	context.payment_options = [
		{
			"key": "instapay",
			"label": _("InstaPay"),
			"number": settings.get("custom_instapay_number") or "",
			"icon": "icon-instapay",
		},
		{
			"key": "vodafone_cash",
			"label": _("Vodafone Cash"),
			"number": settings.get("custom_vodafone_cash_number") or "",
			"icon": "icon-vodafone-cash",
		},
		{
			"key": "etisalat_cash",
			"label": _("Etisalat Cash"),
			"number": settings.get("custom_etisalat_cash_number") or "",
			"icon": "icon-etisalat-cash",
		},
	]

	return context
