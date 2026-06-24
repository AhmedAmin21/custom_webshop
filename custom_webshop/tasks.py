"""Scheduled maintenance for abandoned checkout states."""

import frappe
from frappe.utils import add_days, now_datetime


def cancel_stale_draft_webshop_orders():
	"""Cancel draft Sales Orders awaiting review for more than 7 days."""
	if not frappe.db.has_column("Sales Order", "custom_payment_review_status"):
		return

	cutoff = add_days(now_datetime(), -7)
	orders = frappe.get_all(
		"Sales Order",
		filters={
			"docstatus": 0,
			"custom_payment_review_status": "Pending Review",
			"creation": ["<", cutoff],
		},
		pluck="name",
		limit=100,
	)
	for name in orders:
		try:
			doc = frappe.get_doc("Sales Order", name)
			doc.cancel()
		except Exception:
			frappe.log_error(title=f"Failed to cancel stale draft order {name}")
