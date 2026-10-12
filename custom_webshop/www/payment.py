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

	# Retrieve document (supports Quotation first, then fallback to Sales Order)
	doc = None
	doctype = None
	if frappe.db.exists("Quotation", order_id):
		doc = frappe.get_doc("Quotation", order_id)
		doctype = "Quotation"
	elif frappe.db.exists("Sales Order", order_id):
		doc = frappe.get_doc("Sales Order", order_id)
		doctype = "Sales Order"

	if not doc:
		context.invalid = True
		context.error = _("Order not found.")
		return context

	customer_name = doc.customer if doctype == "Sales Order" else (doc.party_name if doc.quotation_to == "Customer" else None)
	if not customer_name or not owns_customer(customer_name):
		context.invalid = True
		context.error = _("Order not found.")
		return context

	if doc.status == "Cancelled":
		context.invalid = True
		context.is_expired = True
		context.error_title = _("Order Cancelled")
		context.error = _("This order or quotation has been cancelled. Please place a new order.")
		context.action_url = "/shop"
		context.action_text = _("Return to Shop")
		return context

	# For orders > 10,000 EGP, payment proof is not uploaded online
	if flt(doc.grand_total) > 10000.0:
		context.invalid = True
		context.error_title = _("Order Confirmation")
		context.error = _("Because your order exceeds 10,000 EGP, our customer support agents will contact you directly to confirm the order and arrange payment.")
		context.action_url = "/orders"
		context.action_text = _("View Orders")
		return context

	# If payment proof has already been uploaded on Quotation
	if doc.get("custom_payment_receipt"):
		context.invalid = True
		context.error_title = _("Payment Proof Received")
		context.error = _("Payment proof has already been uploaded for this order. Our customer support agents will review it and contact you.")
		context.action_url = "/orders"
		context.action_text = _("View Orders")
		return context

	sales_order = doc
	context.sales_order = doc
	context.doc = doc
	context.grand_total_formatted = frappe.format_value(
		doc.grand_total,
		{"fieldtype": "Currency", "options": doc.currency}
	)

	# Shipping details — show raw total weight in its original UOM
	context.total_weight = flt(doc.get("total_net_weight") or 0)

	# Determine weight UOM from items (same logic as shipping_api)
	weight_uom = doc.get("weight_uom") or None
	if not weight_uom:
		for item in doc.get("items", []):
			if item.get("weight_uom"):
				weight_uom = item.weight_uom
				break
	context.weight_uom = weight_uom or ""

	# Get shipping destination name
	if doc.get("shipping_destination"):
		context.shipping_destination = frappe.db.get_value(
			"Governorate", doc.shipping_destination, "governorate_name"
		) or doc.shipping_destination
	else:
		context.shipping_destination = None

	# Find shipping tax amount from taxes
	context.shipping_amount = 0
	for tax in doc.get("taxes", []):
		# Shipping rules typically add tax rows with description containing shipping
		if "shipping" in (tax.get("description") or "").lower():
			context.shipping_amount += flt(tax.tax_amount)

	context.shipping_amount_formatted = frappe.format_value(
		context.shipping_amount,
		{"fieldtype": "Currency", "options": doc.currency}
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
