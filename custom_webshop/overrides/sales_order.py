import frappe
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder


class CustomSalesOrder(SalesOrder):
	def has_website_permission(self, ptype, user, verbose=False):
		"""
		Override website permission check at the document level.
		Called BEFORE hooks, so it bypasses ERPNext's role-based check.
		Allows access if the Sales Order's customer is linked to the user
		via the Portal User child table.
		"""
		if not self.customer:
			return False
		customers = frappe.get_all(
			"Portal User",
			filters={"user": user, "parenttype": "Customer"},
			pluck="parent"
		)
		return self.customer in customers
