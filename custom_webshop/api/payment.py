import base64

import frappe
from frappe import _
from frappe.utils.file_manager import save_file

from custom_webshop.shopping_cart.cart_override import _send_order_email


@frappe.whitelist()
def confirm_payment(order_id, payment_method, filename, file_content):
	"""
	Attach payment proof to a draft Sales Order and submit it.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	# Validate payment method
	valid_methods = ["instapay", "vodafone_cash", "etisalat_cash"]
	if payment_method not in valid_methods:
		frappe.throw(_("Invalid payment method."), frappe.ValidationError)

	# Find customers linked to this user
	customers = frappe.get_all(
		"Portal User",
		filters={"user": frappe.session.user, "parenttype": "Customer"},
		pluck="parent"
	)
	if not customers:
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)

	# Fetch and validate Sales Order
	sales_order = frappe.get_doc("Sales Order", order_id)
	if sales_order.customer not in customers:
		frappe.throw(_("Order not found."), frappe.DoesNotExistError)

	if sales_order.docstatus != 0:
		frappe.throw(_("This order does not require payment."), frappe.ValidationError)

	# Decode file content
	try:
		decoded_content = base64.b64decode(file_content)
	except Exception:
		frappe.throw(_("Invalid file content."), frappe.ValidationError)

	if not decoded_content:
		frappe.throw(_("Empty file content."), frappe.ValidationError)

	# Save file attached to Sales Order using Frappe's standard file manager
	file_doc = save_file(
		fname=filename,
		content=decoded_content,
		dt="Sales Order",
		dn=sales_order.name,
		folder=None,
		decode=False,
		is_private=1,
	)

	# Update payment method on Sales Order
	method_label = {
		"instapay": "InstaPay",
		"vodafone_cash": "Vodafone Cash",
		"etisalat_cash": "Etisalat Cash",
	}.get(payment_method)

	sales_order.custom_payment_method = method_label
	sales_order.save(ignore_permissions=True)

	# Submit the Sales Order
	sales_order.flags.ignore_permissions = True
	sales_order.submit()

	# Send payment confirmation email
	_send_order_email(sales_order, "order_payment_confirmed")

	return {"success": True, "message": _("Payment confirmed and order submitted.")}
