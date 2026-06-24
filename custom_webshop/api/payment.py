import base64

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils.file_manager import save_file

from custom_webshop.services.checkout import create_draft_sales_order_from_cart
from custom_webshop.services.customer_identity import verify_sales_order_belongs_to_user
from custom_webshop.services.payment_upload import validate_payment_proof
from custom_webshop.shopping_cart.cart_override import _send_order_email


METHOD_LABELS = {
	"instapay": "InstaPay",
	"vodafone_cash": "Vodafone Cash",
	"etisalat_cash": "Etisalat Cash",
}


@frappe.whitelist()
@rate_limit(key="custom_webshop_confirm_payment", limit=10, seconds=60 * 60)
def confirm_payment(payment_method, filename, file_content, order_id=None):
	"""
	Upload payment proof and create a draft Sales Order for admin review.

	If order_id is supplied (resubmission), attach proof to the existing draft order.
	Otherwise create a new draft Sales Order from the current cart quotation.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	if payment_method not in METHOD_LABELS:
		frappe.throw(_("Invalid payment method."), frappe.ValidationError)

	try:
		decoded_content = base64.b64decode(file_content)
	except Exception:
		frappe.throw(_("Invalid file content."), frappe.ValidationError)

	safe_filename, decoded_content = validate_payment_proof(filename, decoded_content)
	method_label = METHOD_LABELS[payment_method]

	if order_id:
		sales_order = frappe.get_doc("Sales Order", order_id)
		verify_sales_order_belongs_to_user(sales_order)
		if sales_order.docstatus != 0:
			frappe.throw(_("This order does not require payment."), frappe.ValidationError)
		if frappe.db.has_column("Sales Order", "custom_payment_review_status"):
			status = sales_order.get("custom_payment_review_status")
			if status and status not in ("Pending Review", "Rejected"):
				frappe.throw(_("This order is not awaiting payment proof."), frappe.ValidationError)
	else:
		sales_order = create_draft_sales_order_from_cart(method_label)

	save_file(
		fname=safe_filename,
		content=decoded_content,
		dt="Sales Order",
		dn=sales_order.name,
		folder=None,
		decode=False,
		is_private=1,
	)

	sales_order.custom_payment_method = method_label
	if frappe.db.has_column("Sales Order", "custom_payment_review_status"):
		sales_order.custom_payment_review_status = "Pending Review"
		sales_order.custom_rejection_reason = None
	sales_order.flags.ignore_permissions = True
	sales_order.save()

	_send_order_email(sales_order, "order_created")

	return {
		"success": True,
		"order_id": sales_order.name,
		"message": _("Payment proof submitted. Your order is pending review."),
	}
