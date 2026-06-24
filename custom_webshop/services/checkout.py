"""Checkout validation and draft Sales Order creation."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.selling.doctype.quotation.quotation import _make_sales_order
from webshop.webshop.shopping_cart.cart import _get_cart_quotation
from webshop.webshop.utils.product import get_web_item_qty_in_stock

from custom_webshop.services.customer_identity import get_customer_for_user, get_party_for_user
from custom_webshop.shopping_cart.shipping_api import apply_cart_settings_for_webshop


def validate_cart_for_checkout(quotation=None):
	"""Ensure cart quotation is ready to proceed to payment."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	if not quotation:
		quotation = _get_cart_quotation()

	if not quotation or not quotation.get("items"):
		frappe.throw(_("Your cart is empty."))

	if not (quotation.shipping_address_name or quotation.customer_address):
		frappe.throw(_("Set Shipping Address or Billing Address"))

	if not quotation.shipping_rule or not quotation.get("shipping_destination"):
		frappe.throw(_("Select shipping company and governorate."))

	apply_cart_settings_for_webshop(quotation=quotation)
	quotation.flags.ignore_permissions = True
	quotation.save()

	cart_settings = frappe.get_cached_doc("Webshop Settings")
	if not cint(cart_settings.allow_items_not_in_stock):
		for row in quotation.get("items") or []:
			is_stock_item = frappe.db.get_value("Item", row.item_code, "is_stock_item")
			if not is_stock_item:
				continue
			item_stock = get_web_item_qty_in_stock(row.item_code, "website_warehouse")
			if not cint(item_stock.in_stock):
				frappe.throw(_("{0} Not in Stock").format(row.item_code))
			if flt(row.qty) > flt(item_stock.stock_qty):
				frappe.throw(
					_("Only {0} in Stock for item {1}").format(item_stock.stock_qty, row.item_code)
				)

	return quotation


def build_payment_preview(quotation):
	shipping_amount = 0
	for tax in quotation.get("taxes") or []:
		if "shipping" in (tax.get("description") or "").lower():
			shipping_amount += flt(tax.get("tax_amount"))

	return {
		"order_id": None,
		"quotation_name": quotation.name,
		"grand_total": flt(quotation.grand_total),
		"grand_total_formatted": frappe.format_value(
			quotation.grand_total,
			{"fieldtype": "Currency", "options": quotation.currency},
		),
		"currency": quotation.currency,
		"shipping": shipping_amount,
		"items": [
			{
				"productId": row.item_code,
				"qty": row.qty,
				"price": flt(row.rate),
				"name": row.item_name,
			}
			for row in quotation.get("items") or []
		],
	}


def create_draft_sales_order_from_cart(payment_method_label):
	"""Submit quotation, create draft Sales Order, keep cart cleared after success."""
	quotation = validate_cart_for_checkout()
	cart_settings = frappe.get_cached_doc("Webshop Settings")
	quotation.company = cart_settings.company
	quotation.flags.ignore_permissions = True

	if quotation.docstatus == 0:
		quotation.submit()

	party = get_party_for_user()
	if quotation.quotation_to == "Lead" and quotation.party_name:
		frappe.defaults.set_user_default("company", quotation.company)

	sales_order = frappe.get_doc(_make_sales_order(quotation.name, ignore_permissions=True))
	sales_order.payment_schedule = []

	for field in ("shipping_rule", "shipping_destination", "custom_manual_shipping_amount"):
		if quotation.get(field):
			sales_order.set(field, quotation.get(field))

	sales_order.reserve_stock = 1
	sales_order.custom_payment_method = payment_method_label
	if frappe.db.has_column("Sales Order", "custom_payment_review_status"):
		sales_order.custom_payment_review_status = "Pending Review"

	if party:
		contact = frappe.db.sql(
			"""
			SELECT c.name, c.first_name, c.last_name, c.mobile_no
			FROM `tabContact` c
			JOIN `tabDynamic Link` dl ON dl.parent = c.name
			WHERE dl.link_doctype = 'Customer'
			AND dl.link_name = %s
			ORDER BY c.is_primary_contact DESC
			LIMIT 1
			""",
			party.name,
			as_dict=True,
		)
		if contact:
			contact_doc = contact[0]
			sales_order.contact_person = contact_doc.name
			sales_order.contact_mobile = contact_doc.mobile_no
			sales_order.contact_email = frappe.session.user
			sales_order.contact_display = (
				f"{contact_doc.first_name or ''} {contact_doc.last_name or ''}".strip()
			)

	if not cint(cart_settings.allow_items_not_in_stock):
		for item in sales_order.get("items"):
			item.warehouse = frappe.db.get_value(
				"Website Item", {"item_code": item.item_code}, "website_warehouse"
			)
			is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
			if is_stock_item:
				item_stock = get_web_item_qty_in_stock(item.item_code, "website_warehouse")
				if not cint(item_stock.in_stock):
					frappe.throw(_("{0} Not in Stock").format(item.item_code))
				if item.qty > item_stock.stock_qty:
					frappe.throw(
						_("Only {0} in Stock for item {1}").format(item_stock.stock_qty, item.item_code)
					)

	sales_order.flags.ignore_permissions = True
	sales_order.insert()

	if hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.delete_cookie("cart_count")

	return sales_order
