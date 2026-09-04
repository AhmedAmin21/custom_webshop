# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WebshopAccountIdentity(Document):
	"""The authoritative verified User <-> Customer link.

	This is the record the rest of custom_webshop resolves identity
	through, replacing three mutually-inconsistent lookups that existed
	before it: webshop's `contact.links[0]` guess, erpnext's
	`Contact.email_id` check, and the Portal User child table. Portal User
	rows are still written, because ERPNext's own portal permissions
	(erpnext/controllers/website_list_for_contact.py) read them - but they
	are a derived artefact of this table now, not a source of truth.

	The three unique constraints are load-bearing: they are the last line
	of defence against two concurrent signups producing two accounts for
	one person, and they fire inside the finalise transaction so the loser
	rolls back cleanly instead of writing a duplicate.
	"""

	pass
