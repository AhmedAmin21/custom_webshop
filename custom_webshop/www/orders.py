# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from frappe import _
from frappe.utils import flt

from custom_webshop.signup.resolution import get_customer_names


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = True
	context.title = _("Orders & Quotations")
	context.parents = [{"route": "me", "title": _("My Account")}]

	customers = get_customer_names()

	quotation_filters = {
		"docstatus": ["<", 2],
	}
	if customers:
		quotation_filters["party_name"] = ["in", customers]
	else:
		quotation_filters["contact_email"] = frappe.session.user

	# Fetch Quotations for customer
	quotations = frappe.get_all(
		"Quotation",
		filters=quotation_filters,
		fields=[
			"name",
			"transaction_date",
			"status",
			"docstatus",
			"grand_total",
			"currency",
			"custom_payment_method",
			"custom_payment_receipt",
			"custom_agent_contact_status",
		],
		order_by="transaction_date desc, creation desc",
		ignore_permissions=True,
	)

	quotation_names = [q.name for q in quotations]
	items_by_quotation = {}
	if quotation_names:
		items = frappe.get_all(
			"Quotation Item",
			filters={"parent": ["in", quotation_names]},
			fields=["parent", "item_code", "item_name", "qty", "rate", "amount"],
			order_by="idx asc",
			ignore_permissions=True,
		)
		for item in items:
			items_by_quotation.setdefault(item.parent, []).append({
				"item_code": item.item_code,
				"item_name": item.item_name,
				"qty": item.qty,
				"rate": item.rate,
				"amount": item.amount,
			})

	for q in quotations:
		q.items = items_by_quotation.get(q.name, [])
		q.grand_total_formatted = frappe.format_value(
			q.grand_total, {"fieldtype": "Currency", "options": q.currency}
		)
		q.requires_payment = flt(q.grand_total) <= 10000.0
		q.has_payment_receipt = bool(q.custom_payment_receipt)
		if q.transaction_date:
			q.transaction_date = str(q.transaction_date)

	context.orders = quotations
	return context
