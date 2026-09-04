# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""The one permission a shopper needs that ERPNext does not grant.

ERPNext resolves item details on every save of a Quotation, and
`erpnext.stock.get_item_details.get_item_details` calls
`item.check_permission()` unconditionally. Nothing in ERPNext gives the
Customer role read access to Item - its own doctype ships permissions for
eight desk roles and none of them is Customer - so a Website User adding
anything to their basket got a bare 403 the moment the quotation was
saved.

On this site that had never been noticed, because the webshop had never
been switched on: `tabQuotation` holds zero Shopping Cart quotations, so
no portal order has ever been placed. The shop looked finished and
nothing could be bought through it.

Granting it here rather than working around it: the alternative was
raising `frappe.flags.ignore_permissions` inside our own cart endpoints,
which does not work - `frappe.permissions.has_permission` does not
consult that flag, only `Document.has_permission` consults the flag on
the document itself - and would in any case have been a broader bypass
than this, since it suppresses every check for the length of the call
rather than granting one named read.

The trade-off is real and worth stating: a portal account can now read
Item through the REST API, including fields the shop does not display.
It is `read` only, at permlevel 0, for one role that only portal users
hold. If that matters more than the shop working, the inverse is a
single deletion - see `revoke`.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

SHOPPING_ROLE = "Customer"

# Read, because `get_item_details` calls `item.check_permission()` and
# nothing narrower will satisfy it.
SHOPPING_READS = ("Item",)

# Select only. ERPNext's own `account_perm_check` asks for "select"
# rather than "read" when select is all the role has
# (erpnext.accounts.party.get_party_account), so the receivable account a
# quotation resolves can be reached without opening the chart of
# accounts to portal users.
SHOPPING_SELECTS = ("Account",)


def grant_portal_shopping_permissions():
	"""Give the Customer role read on the doctypes a cart save touches.

	Idempotent: `add_permission` is a no-op when the rule already exists,
	and the property update simply re-asserts `read`.

	Args:
		None.

	Returns:
		The list of doctypes granted, for the caller to log.
	"""
	if not frappe.db.exists("Role", SHOPPING_ROLE):
		return []

	granted = []
	for doctype in SHOPPING_READS:
		if _apply(doctype, "read"):
			granted.append(f"{doctype} (read)")

	for doctype in SHOPPING_SELECTS:
		if _apply(doctype, "select"):
			granted.append(f"{doctype} (select)")

	frappe.clear_cache()
	return granted


def _apply(doctype, ptype):
	"""Grant one permission type on one doctype, idempotently.

	`add_permission` defaults to creating a `read` rule, so the type is
	passed explicitly - otherwise asking for select would hand out read
	as well, which is the whole thing being avoided here.

	Args:
		doctype: the doctype to grant on.
		ptype: "read" or "select".

	Returns:
		True if the doctype exists and the rule is in place.
	"""
	if not frappe.db.exists("DocType", doctype):
		return False

	add_permission(doctype, SHOPPING_ROLE, 0, ptype)
	update_permission_property(doctype, SHOPPING_ROLE, 0, ptype, 1)
	return True


def revoke():
	"""Remove what `grant_portal_shopping_permissions` added.

	Not wired to anything - it exists so the grant above is reversible by
	one command rather than by hand:

	    bench --site <site> execute \\
	        custom_webshop.setup.portal_permissions.revoke

	Args:
		None.

	Returns:
		None.
	"""
	for doctype in SHOPPING_READS + SHOPPING_SELECTS:
		for name in frappe.get_all(
			"Custom DocPerm", filters={"parent": doctype, "role": SHOPPING_ROLE}, pluck="name"
		):
			frappe.delete_doc("Custom DocPerm", name, force=True, ignore_permissions=True)
	frappe.clear_cache()
