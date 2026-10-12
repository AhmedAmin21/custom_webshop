import frappe
from frappe import _
from custom_webshop.signup.resolution import get_customer_names


@frappe.whitelist()
def get_order_items(order_name):
	"""
	Fetch items and grand_total for a Quotation or Sales Order owned by the current customer.
	Safely bypasses desk permissions while strictly verifying customer ownership.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	customers = get_customer_names()
	if not customers:
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)

	# 1. Try Quotation
	order = frappe.db.get_value(
		"Quotation",
		{"name": order_name, "party_name": ["in", customers]},
		["name", "grand_total", "currency"],
		as_dict=True,
	)
	child_doctype = "Quotation Item"

	# 2. Fallback to Sales Order
	if not order:
		order = frappe.db.get_value(
			"Sales Order",
			{"name": order_name, "customer": ["in", customers]},
			["name", "grand_total", "currency"],
			as_dict=True,
		)
		child_doctype = "Sales Order Item"

	if not order:
		frappe.throw(_("Order not found."), frappe.DoesNotExistError)

	items = frappe.get_all(
		child_doctype,
		filters={"parent": order_name},
		fields=["item_code", "item_name", "qty", "rate", "amount"],
		order_by="idx asc",
		ignore_permissions=True,
	)

	return {
		"name": order.name,
		"grand_total": order.grand_total,
		"currency": order.currency or "EGP",
		"items": items,
	}
