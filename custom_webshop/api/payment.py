import base64
import io
import os
import re
from PIL import Image

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import flt
from frappe.utils.file_manager import save_file

from custom_webshop.shopping_cart.cart_override import _send_order_email
from custom_webshop.signup.resolution import owns_customer

VALID_PAYMENT_METHODS = {
	"instapay": "InstaPay",
	"vodafone_cash": "Vodafone Cash",
	"etisalat_cash": "Etisalat Cash",
}

MAX_BASE64_SIZE = 7 * 1024 * 1024  # 7 MB base64 payload limit
MIN_FILE_SIZE = 100                 # 100 bytes minimum
MAX_FILE_SIZE = 5 * 1024 * 1024    # 5 MB decoded raw image size limit
MAX_IMAGE_DIMENSION = 4096         # 4096 x 4096 maximum width/height
MAX_IMAGE_PIXELS = 10_000_000      # 10 MP decompression bomb protection
MAX_QUOTATION_AMOUNT = 10000.0     # 10,000 EGP assisted-sales ceiling


def _detect_and_validate_signature(data: bytes) -> str:
	"""
	Verify magic bytes for allowed image types (JPEG, PNG, WebP).
	Rejects SVG, HTML, PDF, executable, and unknown file signatures.
	Returns normalized format string ('JPEG', 'PNG', 'WEBP').
	"""
	if len(data) < 12:
		frappe.throw(_("File content is too small to be a valid image."), frappe.ValidationError)

	# JPEG starts with \xFF\xD8\xFF
	if data.startswith(b"\xff\xd8\xff"):
		return "JPEG"

	# PNG starts with \x89PNG\r\n\x1a\n
	if data.startswith(b"\x89PNG\r\n\x1a\n"):
		return "PNG"

	# WebP: 'RIFF' .... 'WEBP'
	if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
		return "WEBP"

	frappe.throw(
		_("Unsupported file type. Only JPEG, PNG, and WebP images are allowed."),
		frappe.ValidationError,
	)


def _validate_and_sanitize_image(data: bytes, detected_format: str) -> tuple[bytes, str]:
	"""
	Decodes the image using Pillow, validates integrity and dimensions,
	and re-encodes into a clean raster format to strip metadata (EXIF/GPS)
	and discard any trailing or embedded non-image payloads.

	Returns:
		tuple of (sanitized_bytes, file_extension)
	"""
	Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

	try:
		# Step 1: Verify structure integrity
		with Image.open(io.BytesIO(data)) as img:
			actual_format = (img.format or "").upper()
			if actual_format not in ("JPEG", "PNG", "WEBP"):
				frappe.throw(_("Invalid image format detected."), frappe.ValidationError)
			img.verify()
	except Exception:
		frappe.throw(_("Invalid or corrupted image file."), frappe.ValidationError)

	try:
		# Step 2: Open fresh image stream for pixel inspection & re-encoding
		with Image.open(io.BytesIO(data)) as img:
			width, height = img.size
			if width <= 0 or height <= 0:
				frappe.throw(_("Invalid image dimensions."), frappe.ValidationError)

			if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
				frappe.throw(
					_("Image dimensions exceed the allowed limit ({0}x{0}).").format(MAX_IMAGE_DIMENSION),
					frappe.ValidationError,
				)

			if (width * height) > MAX_IMAGE_PIXELS:
				frappe.throw(
					_("Image resolution exceeds maximum allowed limit."),
					frappe.ValidationError,
				)

			# Re-encode to clean raster format (strips EXIF, comments, trailing data)
			output_io = io.BytesIO()
			if actual_format == "PNG":
				img.save(output_io, format="PNG", optimize=True)
				safe_ext = ".png"
			elif actual_format == "WEBP":
				img.save(output_io, format="WEBP", quality=90)
				safe_ext = ".webp"
			else:
				# JPEG: convert RGBA/palette modes to RGB
				if img.mode in ("RGBA", "LA", "P"):
					img = img.convert("RGB")
				img.save(output_io, format="JPEG", quality=90, optimize=True)
				safe_ext = ".jpg"

			sanitized_bytes = output_io.getvalue()
			return sanitized_bytes, safe_ext

	except frappe.ValidationError:
		raise
	except Exception:
		frappe.throw(_("Failed to process image file."), frappe.ValidationError)


@frappe.whitelist(methods=["POST"])
@rate_limit(key="order_id", limit=5, seconds=60, ip_based=True, methods=["POST"])
def confirm_payment(order_id, payment_method, filename, file_content):
	"""
	Attach payment proof to an eligible customer Quotation for staff review.
	Strictly Quotation-only; never submits Sales Orders or modifies stock.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	# 1. Validate payment method
	if not payment_method or payment_method not in VALID_PAYMENT_METHODS:
		frappe.throw(_("Invalid payment method."), frappe.ValidationError)

	method_label = VALID_PAYMENT_METHODS[payment_method]

	# 2. Validate order_id and fetch target Quotation exclusively
	if not order_id or not isinstance(order_id, str):
		frappe.throw(_("No order specified."), frappe.ValidationError)

	# Strictly Quotation only - reject any other doctype or fallback
	if not frappe.db.exists("Quotation", order_id):
		frappe.throw(_("Quotation not found."), frappe.DoesNotExistError)

	doc = frappe.get_doc("Quotation", order_id)

	# 3. Enforce Customer Ownership
	customer_name = doc.party_name if doc.quotation_to == "Customer" else None
	if not customer_name or not owns_customer(customer_name):
		frappe.throw(
			_("You do not have permission to access this quotation."),
			frappe.PermissionError,
		)

	# 4. Enforce Document State Rules
	if doc.docstatus == 2 or doc.status == "Cancelled":
		frappe.throw(
			_("This quotation has been cancelled. Please place a new order."),
			frappe.ValidationError,
		)

	if doc.status in ("Ordered", "Lost"):
		frappe.throw(
			_("This quotation is already processed and cannot accept new payment proofs."),
			frappe.ValidationError,
		)

	# Enforce order amount threshold (assisted-sales ceiling)
	if flt(doc.grand_total) > MAX_QUOTATION_AMOUNT:
		frappe.throw(
			_("Orders exceeding {0} EGP require customer support agent assistance.").format(
				int(MAX_QUOTATION_AMOUNT)
			),
			frappe.ValidationError,
		)

	# Prevent duplicate or unauthorized replacement of existing payment proof
	if doc.get("custom_payment_receipt"):
		frappe.throw(
			_("Payment proof has already been uploaded for this quotation."),
			frappe.ValidationError,
		)

	# 5. Validate Base64 payload size
	if not file_content or not isinstance(file_content, str):
		frappe.throw(_("Empty or invalid file content."), frappe.ValidationError)

	if len(file_content) > MAX_BASE64_SIZE:
		frappe.throw(_("File size exceeds 5MB limit."), frappe.ValidationError)

	# Strip data URL prefix if present (e.g. data:image/png;base64,...)
	if "," in file_content:
		file_content = file_content.split(",", 1)[1]

	try:
		decoded_content = base64.b64decode(file_content, validate=True)
	except Exception:
		frappe.throw(_("Invalid base64 file content."), frappe.ValidationError)

	if len(decoded_content) < MIN_FILE_SIZE or len(decoded_content) > MAX_FILE_SIZE:
		frappe.throw(
			_("File size must be between {0} bytes and 5MB.").format(MIN_FILE_SIZE),
			frappe.ValidationError,
		)

	# 6. Validate magic bytes and sanitize image via Pillow
	detected_format = _detect_and_validate_signature(decoded_content)
	sanitized_content, safe_ext = _validate_and_sanitize_image(decoded_content, detected_format)

	# 7. Generate server-controlled safe filename (prevent path traversal)
	safe_token = frappe.generate_hash(length=8)
	safe_filename = f"receipt_{doc.name}_{safe_token}{safe_ext}"

	# 8. Save as PRIVATE file attached to Quotation
	file_doc = save_file(
		fname=safe_filename,
		content=sanitized_content,
		dt="Quotation",
		dn=doc.name,
		folder=None,
		decode=False,
		is_private=1,  # Strictly private file under /private/files/
	)

	# 9. Atomically record payment details and pending review state
	doc.db_set({
		"custom_payment_method": method_label,
		"custom_payment_receipt": file_doc.file_url,
		"custom_agent_contact_status": "Pending Agent Contact",
	})

	try:
		frappe.flags.ignore_permissions = True
		doc.add_comment(
			"Comment",
			text=f"Payment proof uploaded ({method_label}): {file_doc.file_url}",
		)
	finally:
		frappe.flags.ignore_permissions = False

	# 10. Send customer notification email
	_send_order_email(doc, "order_payment_confirmed")

	return {
		"success": True,
		"message": _("Payment proof received. Customer support agents will review it and contact you to confirm the order."),
	}


@frappe.whitelist(methods=["POST"])
def reject_payment_proof(order_id, reason=None):
	"""
	Admin / staff handler to reject a manual payment proof.
	Requires write permission on Quotation or Sales Order.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	if frappe.db.exists("Quotation", order_id):
		quotation = frappe.get_doc("Quotation", order_id)
		quotation.check_permission("write")

		if quotation.status == "Cancelled":
			frappe.throw(_("Cannot reject payment proof for a cancelled quotation."), frappe.ValidationError)

		quotation.db_set({
			"custom_agent_contact_status": "Contacted",
		})
		comment_text = "Payment proof rejected by staff."
		if reason:
			comment_text += f" Reason: {reason}"
		try:
			frappe.flags.ignore_permissions = True
			quotation.add_comment("Comment", text=comment_text)
		finally:
			frappe.flags.ignore_permissions = False

		return {"success": True, "message": _("Payment proof rejected.")}

	elif frappe.db.exists("Sales Order", order_id):
		sales_order = frappe.get_doc("Sales Order", order_id)
		sales_order.check_permission("write")

		if sales_order.docstatus != 0:
			frappe.throw(_("Can only reject payment proof for draft orders."), frappe.ValidationError)

		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			cancel_stock_reservation_entries,
		)

		has_sre = frappe.db.exists(
			"Stock Reservation Entry",
			{
				"voucher_type": "Sales Order",
				"voucher_no": sales_order.name,
				"docstatus": 1,
				"status": ["not in", ["Delivered", "Cancelled"]],
			},
		)

		if has_sre:
			cancel_stock_reservation_entries(
				voucher_type="Sales Order",
				voucher_no=sales_order.name,
				notify=False,
			)

		return {"success": True, "message": _("Payment proof rejected and stock reservation released.")}

	else:
		frappe.throw(_("Order or quotation not found."), frappe.DoesNotExistError)

