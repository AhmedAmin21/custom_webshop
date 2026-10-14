# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Revoke Customer role read permission on Item DocType.

Prevents exposure of valuation_rate, standard_rate, and costing details to portal customers.
Cart quotation operations safely read items via cart_override.shopping_as_customer().
"""

import frappe


def execute():
	"""Remove Custom DocPerm granting Customer read on Item."""
	for name in frappe.get_all(
		"Custom DocPerm",
		filters={"parent": "Item", "role": "Customer"},
		pluck="name",
	):
		frappe.delete_doc("Custom DocPerm", name, force=True, ignore_permissions=True)

	frappe.clear_cache()
