import frappe
from frappe.utils import now_datetime, add_to_date
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import cancel_stock_reservation_entries

TTL_MINUTES = 60

def expire_unpaid_webshop_reservations():
	"""
	Scheduled task to cancel Stock Reservation Entries for abandoned 
	Shopping Cart Draft Sales Orders that exceed the TTL.
	"""
	expiration_threshold = add_to_date(now_datetime(), minutes=-TTL_MINUTES)
	
	# Find Draft Sales Orders created by the webshop that are older than TTL
	# and have not yet been submitted or cancelled.
	abandoned_orders = frappe.get_all(
		"Sales Order",
		filters={
			"order_type": "Shopping Cart",
			"docstatus": 0,  # Draft
			"creation": ["<", expiration_threshold],
			"status": ["not in", ["Closed", "Cancelled", "Completed"]]
		},
		fields=["name", "status"]
	)
	
	for so in abandoned_orders:
		# Check if the order has any active Stock Reservation Entries
		has_sre = frappe.db.exists(
			"Stock Reservation Entry",
			{
				"voucher_type": "Sales Order",
				"voucher_no": so.name,
				"docstatus": 1,
				"status": ["not in", ["Delivered", "Cancelled"]]
			}
		)
		
		if has_sre:
			# Verify no active Payment Entry or Invoice exists against this draft SO
			# Draft SOs technically shouldn't have linked submitted invoices/payments 
			# but we check to be safe before expiring.
			linked_payments = frappe.db.exists("Payment Entry Reference", {"reference_name": so.name, "docstatus": ["<", 2]})
			
			if not linked_payments:
				# Cancel the SREs, releasing the reserved_stock
				try:
					frappe.db.set_value("Sales Order", so.name, "status", "Cancelled")
					cancel_stock_reservation_entries(
						voucher_type="Sales Order",
						voucher_no=so.name,
						notify=False
					)
				except Exception:
					frappe.log_error(f"Failed to cancel reservations for abandoned order {so.name}", "expire_unpaid_webshop_reservations")
