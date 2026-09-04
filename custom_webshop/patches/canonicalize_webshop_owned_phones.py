# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Rewrite the phones this app stored in local form into E.164.

`linking` now writes international form everywhere, but the accounts it
created before that rule still hold the local one (`01101271160` rather
than `+201101271160`), so one column would carry two conventions and a
reader would have to know which signup wrote which row.

Deliberately narrow. It converts only a phone that is *the verified
number of an account this app created* - reached from a Webshop Account
Identity, whose `phone_e164` is the number that account proved it owned.
It does not sweep the Contact Phone table, and that restraint is the
point:

* Most rows on this site belong to Contacts staff and
  contact_enhancements maintain. That app writes the local form on its
  own paths (`api.lead_lookup.normalize_phone_for_country`) and is
  read-only to us, so anything we converted there it would write back in
  local form on the next Lead conversion - churn, not consistency.
* Nothing needs the conversion to read the data. Matching queries every
  written form through `matching.phone_variants`, so a Contact still
  holding `01101271160` is found exactly as before.

Unparseable numbers - this site has two, `015545454545` and the
18-digit `011011012121212121` - are left untouched rather than blanked.
A number we cannot read is still the only record of how to reach that
person, and destroying it to satisfy a format rule would be a worse
outcome than the inconsistency.

Idempotent: a second run finds nothing left to change.
"""

import frappe


def execute():
	"""Canonicalise the stored phone of every account this app created."""
	identities = frappe.get_all(
		"Webshop Account Identity",
		fields=["name", "user", "customer", "phone_e164"],
	)
	if not identities:
		return

	contacts = 0
	users = 0
	customers = 0

	for identity in identities:
		if not identity.phone_e164:
			continue

		contacts += _fix_contact_phones(identity)
		users += _fix_user(identity)
		customers += _fix_customer(identity)

	frappe.db.commit()
	print(
		f"custom_webshop: stored {contacts} contact phone(s), {users} user mobile(s) "
		f"and {customers} customer mobile(s) in international form."
	)


def _fix_contact_phones(identity):
	"""Convert the identity's verified number on its own Customer's Contacts.

	Matched on `custom_phone_e164` rather than on the local string, so it
	finds the row whatever form it was written in, and only ever touches
	the one number that account verified - another phone on the same
	Contact belongs to somebody else's decision and is left alone.

	Args:
		identity: a Webshop Account Identity row with `customer` and
			`phone_e164`.

	Returns:
		The number of rows changed.
	"""
	if not identity.customer:
		return 0

	linked = frappe.get_all(
		"Dynamic Link",
		filters={
			"link_doctype": "Customer",
			"link_name": identity.customer,
			"parenttype": "Contact",
		},
		pluck="parent",
	)
	if not linked:
		return 0

	rows = frappe.get_all(
		"Contact Phone",
		filters={
			"parenttype": "Contact",
			"parent": ["in", linked],
			"custom_phone_e164": identity.phone_e164,
			"phone": ["!=", identity.phone_e164],
		},
		pluck="name",
	)

	for row in rows:
		# update_modified=False: a format migration should not make every
		# Contact it touches look freshly edited by a person.
		frappe.db.set_value(
			"Contact Phone", row, "phone", identity.phone_e164, update_modified=False
		)
	return len(rows)


def _fix_user(identity):
	"""Convert `User.mobile_no` for the account, if it holds that number.

	Args:
		identity: a Webshop Account Identity row.

	Returns:
		1 if the row was changed, 0 otherwise.
	"""
	from custom_webshop.signup.identity import try_to_e164

	if not identity.user:
		return 0

	current = frappe.db.get_value("User", identity.user, "mobile_no")
	if not current or current == identity.phone_e164:
		return 0
	# Only when it is demonstrably the same number written differently -
	# never overwrite a second number somebody set by hand.
	if try_to_e164(current) != identity.phone_e164:
		return 0

	frappe.db.set_value("User", identity.user, "mobile_no", identity.phone_e164, update_modified=False)
	return 1


def _fix_customer(identity):
	"""Convert `Customer.mobile_no`, the read-only mirror of the Contact.

	ERPNext fills this with `fetch_from` on save. Nothing saves the
	Customer here, so the mirror would otherwise keep showing the local
	form the Contact no longer holds.

	Args:
		identity: a Webshop Account Identity row.

	Returns:
		1 if the row was changed, 0 otherwise.
	"""
	from custom_webshop.signup.identity import try_to_e164

	if not identity.customer:
		return 0

	current = frappe.db.get_value("Customer", identity.customer, "mobile_no")
	if not current or current == identity.phone_e164:
		return 0
	if try_to_e164(current) != identity.phone_e164:
		return 0

	frappe.db.set_value(
		"Customer", identity.customer, "mobile_no", identity.phone_e164, update_modified=False
	)
	return 1
