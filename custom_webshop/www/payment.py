# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from frappe import _


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

	# Find all customers linked to this user
	customers = frappe.get_all(
		"Portal User",
		filters={"user": frappe.session.user, "parenttype": "Customer"},
		pluck="parent"
	)

	if not order_id:
		context.invalid = True
		context.error = _("No order specified.")
		return context

	# Fetch the order and ensure it belongs to one of the customer's linked customers
	sales_order = frappe.get_doc("Sales Order", order_id)
	if not sales_order or sales_order.customer not in customers:
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
