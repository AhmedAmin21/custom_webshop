"""Payment proof upload validation."""

import os
import re

import frappe
from frappe import _

MAX_PAYMENT_PROOF_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_PREFIXES = ("image/jpeg", "image/png", "image/webp")


def validate_payment_proof(filename, content):
	if not content:
		frappe.throw(_("Empty file content."), frappe.ValidationError)

	if len(content) > MAX_PAYMENT_PROOF_BYTES:
		frappe.throw(_("File exceeds maximum size of 5MB."), frappe.ValidationError)

	safe_name = os.path.basename(filename or "payment-proof.jpg")
	ext = os.path.splitext(safe_name)[1].lower()
	if ext not in ALLOWED_EXTENSIONS:
		frappe.throw(_("Only JPG, PNG, and WEBP images are allowed."), frappe.ValidationError)

	# Basic magic-byte sniffing
	if content.startswith(b"\xff\xd8\xff"):
		mime = "image/jpeg"
	elif content.startswith(b"\x89PNG"):
		mime = "image/png"
	elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
		mime = "image/webp"
	else:
		frappe.throw(_("Invalid image file."), frappe.ValidationError)

	if not any(mime.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
		frappe.throw(_("Invalid image file."), frappe.ValidationError)

	safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", safe_name)
	return safe_name, content
