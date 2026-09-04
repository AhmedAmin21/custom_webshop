# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Customer doc_events owned by custom_webshop.

One job: stop a website account being granted portal access to a Customer
that is not the one it was verified against.

This is enforced here, on the document, rather than by patching the code
that does it. The known offender is
`webshop.webshop.shopping_cart.cart.get_party`, which - for any logged-in
user whose Contact has a Dynamic Link - takes `contact.links[0]`, the
*arbitrary first* link, and silently appends a Portal User row to whatever
Customer that turns out to be, then saves. But it is not the only way a
row can appear: ERPNext writes them, staff write them by hand, and a data
import writes them in bulk. A validate hook covers every one of those
paths at once, which patching a single function would not.
"""

import frappe

from custom_webshop.signup.telemetry import log_event


def enforce_portal_user_identity(doc, method=None):
	"""Customer validate hook: drop portal access this account never earned.

	A Portal User row is removed when the user it names has a verified
	`Webshop Account Identity` pointing at a *different* Customer. Owning
	a verified identity is the strongest statement the system has about
	who someone is, and it must win over a link that some other code path
	inferred from a Contact.

	Users with no identity row are left alone. Those are accounts that
	predate this flow, and silently revoking their access would break
	people who are legitimately using the site today - the migration
	backfill turns them into real identity rows, and surfaces the
	ambiguous ones for staff instead of guessing.

	Args:
		doc: the Customer document being validated.
		method: unused, present for the doc_events hook signature.
	"""
	rows = doc.get("portal_users") or []
	if not rows:
		return

	kept = []
	for row in rows:
		owner_customer = _identity_customer(row.user)
		if owner_customer and owner_customer != doc.name:
			log_event(
				"portal_user_grant_rejected",
				user=row.user,
				attempted_customer=doc.name,
				verified_customer=owner_customer,
			)
			continue
		kept.append(row)

	if len(kept) != len(rows):
		doc.set("portal_users", kept)


def _identity_customer(user):
	"""Return the Customer a user is verified against, if any.

	Args:
		user: a User name.

	Returns:
		A Customer name, or None when this account predates the identity
		table.
	"""
	if not user:
		return None
	return frappe.db.get_value("Webshop Account Identity", {"user": user}, "customer")
