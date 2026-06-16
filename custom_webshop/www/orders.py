# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from frappe import _


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.title = _("Orders")
	context.parents = [{"route": "me", "title": _("My Account")}]

	# Find ALL customers linked to this user via Portal User
	# (bypasses get_party() which may return a Lead or wrong contact)
	customers = frappe.get_all(
		"Portal User",
		filters={"user": frappe.session.user, "parenttype": "Customer"},
		pluck="parent"
	)
	if not customers:
		context.orders = []
		return context

	# Fetch Sales Orders for ALL linked customers
	orders = frappe.get_all(
		"Sales Order",
		filters={
			"customer": ["in", customers],
			"docstatus": ["<", 2],
		},
		fields=[
			"name",
			"transaction_date",
			"status",
			"grand_total",
			"currency",
			"per_delivered",
			"per_billed",
		],
		order_by="transaction_date desc, creation desc",
		ignore_permissions=True,
	)

	for order in orders:
		order.grand_total_formatted = frappe.format_value(
			order.grand_total, {"fieldtype": "Currency", "options": order.currency}
		)

	context.orders = orders
	return context
