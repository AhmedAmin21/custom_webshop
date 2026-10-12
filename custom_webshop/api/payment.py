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

	from custom_webshop.signup.resolution import owns_customer

	# Fetch and validate Document (Quotation first, fallback to Sales Order)
	doc = None
	doctype = None
	if frappe.db.exists("Quotation", order_id):
		doc = frappe.get_doc("Quotation", order_id)
		doctype = "Quotation"
	elif frappe.db.exists("Sales Order", order_id):
		doc = frappe.get_doc("Sales Order", order_id)
		doctype = "Sales Order"

	if not doc:
		frappe.throw(_("Order not found."), frappe.DoesNotExistError)

	customer_name = doc.customer if doctype == "Sales Order" else (doc.party_name if doc.quotation_to == "Customer" else None)
	if not customer_name or not owns_customer(customer_name):
		frappe.throw(_("Order not found."), frappe.DoesNotExistError)

	if doc.status == "Cancelled":
		frappe.throw(
			_("This order or quotation has been cancelled. Please place a new order."),
			frappe.ValidationError,
		)

	# Validate file type and size
	import os
	ext = os.path.splitext(filename)[1].lower()
	if ext not in [".png", ".jpg", ".jpeg", ".pdf", ".webp"]:
		frappe.throw(_("Only images or PDF files are allowed."), frappe.ValidationError)

	if len(file_content) > 10 * 1024 * 1024:
		frappe.throw(_("File size exceeds 7MB limit."), frappe.ValidationError)

	# Decode file content
	try:
		decoded_content = base64.b64decode(file_content)
	except Exception:
		frappe.throw(_("Invalid file content."), frappe.ValidationError)

	if not decoded_content:
		frappe.throw(_("Empty file content."), frappe.ValidationError)

	# Save file attached to Document using Frappe's standard file manager
	file_doc = save_file(
		fname=filename,
		content=decoded_content,
		dt=doctype,
		dn=doc.name,
		folder=None,
		decode=False,
		is_private=0,
	)

	method_label = {
		"instapay": "InstaPay",
		"vodafone_cash": "Vodafone Cash",
		"etisalat_cash": "Etisalat Cash",
	}.get(payment_method)

	if doctype == "Quotation":
		doc.db_set("custom_payment_method", method_label)
		doc.db_set("custom_payment_receipt", file_doc.file_url)
		doc.db_set("custom_agent_contact_status", "Pending Agent Contact")
		try:
			frappe.flags.ignore_permissions = True
			doc.add_comment(
				"Comment",
				text=f"Payment proof uploaded ({method_label}): {file_doc.file_url}"
			)
		finally:
			frappe.flags.ignore_permissions = False
		_send_order_email(doc, "order_payment_confirmed")
		return {
			"success": True,
			"message": _("Payment proof received. Customer support agents will review it and contact you to confirm the order.")
		}
	else:
		doc.custom_payment_method = method_label
		doc.save(ignore_permissions=True)
		try:
			frappe.flags.ignore_permissions = True
			doc.submit()
		finally:
			frappe.flags.ignore_permissions = False

		_send_order_email(doc, "order_payment_confirmed")
		return {"success": True, "message": _("Payment confirmed and order submitted.")}


@frappe.whitelist()
def reject_payment_proof(order_id):
	"""
	Admin handler to reject a manual payment proof.
	Releases the SREs associated with the Draft Sales Order without cancelling the order itself.
	This is idempotent: calling it twice on an already released order does nothing.
	"""
	sales_order = frappe.get_doc("Sales Order", order_id)
	
	# Verify the user has write access to the order
	sales_order.check_permission("write")

	if sales_order.docstatus != 0:
		frappe.throw(_("Can only reject payment proof for draft orders."), frappe.ValidationError)

	from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import cancel_stock_reservation_entries

	has_sre = frappe.db.exists(
		"Stock Reservation Entry",
		{
			"voucher_type": "Sales Order",
			"voucher_no": sales_order.name,
			"docstatus": 1,
			"status": ["not in", ["Delivered", "Cancelled"]]
		}
	)
	
	if has_sre:
		cancel_stock_reservation_entries(
			voucher_type="Sales Order",
			voucher_no=sales_order.name,
			notify=False
		)
		
	return {"success": True, "message": _("Payment proof rejected and stock reservation released.")}
