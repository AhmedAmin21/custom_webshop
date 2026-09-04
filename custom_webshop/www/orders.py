# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from frappe import _

from custom_webshop.signup.resolution import get_customer_names


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.title = _("Orders")
	context.parents = [{"route": "me", "title": _("My Account")}]

	# Resolve through the verified identity record rather than reading
	# Portal User directly: a Portal User row only says some code path
	# once linked this account to that Customer, and webshop's get_party()
	# adds them from an arbitrary contact link. This list drives an
	# ignore_permissions query below, so it has to be the authoritative
	# answer.
	customers = get_customer_names()
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
			"docstatus",
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
		# Serialize date for Jinja tojson in orders.html
		if order.transaction_date:
			order.transaction_date = str(order.transaction_date)

	context.orders = orders
	return context
