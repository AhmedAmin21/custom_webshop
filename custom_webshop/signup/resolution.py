# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Resolving a logged-in website user to their ERPNext Customer.

The single entry point every page and endpoint in this app should use.
Before this existed the site answered the question three different ways
and they disagreed with each other:

* `webshop.shopping_cart.cart.get_party` walked
  `Contact Email -> Contact -> contact.links[0]` and took whatever the
  *first* Dynamic Link happened to be - which is a Lead as often as a
  Customer - then silently granted portal access to whatever it landed on.
* `erpnext.portal.utils.party_exists` read the flat `Contact.email_id`
  field instead of the child table, so it disagreed with the above and
  created a second Customer when they diverged.
* This app's own pages read the `Portal User` child table.

`Webshop Account Identity` is now the authority: one verified row per
account, written inside the signup transaction. Portal User rows are still
maintained, because ERPNext's own portal permission checks
(erpnext/controllers/website_list_for_contact.py) read them - but they are
a derived artefact, and the fallback below exists only for accounts that
predate the identity table.
"""

import frappe


def get_customer_name(user=None):
	"""Return the Customer this website user belongs to.

	Args:
		user: the User to resolve; defaults to the session user.

	Returns:
		A Customer name, or None.
	"""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return None

	customer = frappe.db.get_value("Webshop Account Identity", {"user": user}, "customer")
	if customer:
		return customer

	# Legacy fallback for accounts created before the identity table. A
	# user with several Portal User rows is deliberately resolved to the
	# oldest rather than an arbitrary one, so the answer is at least
	# stable between requests; the migration backfill turns these into
	# real identity rows, and flags the ambiguous ones for staff.
	rows = frappe.get_all(
		"Portal User",
		filters={"user": user, "parenttype": "Customer"},
		fields=["parent"],
		order_by="creation asc",
		limit=1,
	)
	return rows[0].parent if rows else None


def get_customer_names(user=None):
	"""Return every Customer this user can legitimately see.

	Normally exactly one. More than one is only possible for a legacy
	account carrying several Portal User rows, and those are precisely the
	rows the migration audit surfaces for review.

	Args:
		user: the User to resolve; defaults to the session user.

	Returns:
		A list of Customer names, possibly empty.
	"""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return []

	customer = frappe.db.get_value("Webshop Account Identity", {"user": user}, "customer")
	if customer:
		return [customer]

	return frappe.get_all(
		"Portal User", filters={"user": user, "parenttype": "Customer"}, pluck="parent"
	)


def get_customer(user=None):
	"""Return the Customer document for this website user.

	Args:
		user: the User to resolve; defaults to the session user.

	Returns:
		The Customer document, or None.
	"""
	name = get_customer_name(user)
	return frappe.get_doc("Customer", name) if name else None


def owns_customer(customer, user=None):
	"""Return True when this user is entitled to act for a Customer.

	The check every page guarding a Customer-scoped record should make,
	instead of trusting a Portal User row on its own.

	Args:
		customer: the Customer name in question.
		user: the User to check; defaults to the session user.

	Returns:
		True when the user may see this Customer's records.
	"""
	return bool(customer) and customer in get_customer_names(user)
