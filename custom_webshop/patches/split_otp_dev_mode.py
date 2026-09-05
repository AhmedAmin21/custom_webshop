# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Split the single `otp_dev_mode` flag into per-channel settings.

`Webshop Signup Settings.otp_dev_mode` used to gate both send_email_otp
and send_phone_otp together - there was no way to run one channel live
while keeping the other in dev mode. It is now two independent fields,
`email_otp_dev_mode` and `phone_otp_dev_mode` (see
custom_webshop.signup.notifications).

This preserves the value a site already had: whatever `otp_dev_mode` was
set to becomes the starting value for *both* new fields, so a site
currently running with it on (or off) sees no behavior change until
someone deliberately splits them apart in Webshop Signup Settings.

Being a Single, the old field's row in `tabSingles` survives the DocType
JSON no longer declaring it - the row is not touched by any ALTER TABLE,
since Singles have no real columns to drop. It is read directly through
the query builder rather than `frappe.db.get_single_value`, which looks
the fieldname up in the *current* doctype meta first and throws
`Field otp_dev_mode does not exist` - confirmed the hard way, since meta
already reflects this app's own edited DocType JSON (declaring the two
new fields, not the old one) by the time any patch runs, in either
patches.txt section; only the raw table still remembers the old value.
The row is deleted at the end so the settings doctype does not carry a
dead, undeclared key forever.

Idempotent: does nothing once the old field's row is gone.
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Webshop Signup Settings"):
		return

	row = frappe.qb.get_query(
		table="Singles",
		filters={"doctype": "Webshop Signup Settings", "field": "otp_dev_mode"},
		fields="value",
	).run()
	if not row:
		return
	old_value = row[0][0]

	frappe.db.set_single_value(
		"Webshop Signup Settings",
		{"email_otp_dev_mode": old_value, "phone_otp_dev_mode": old_value},
	)
	frappe.db.delete("Singles", {"doctype": "Webshop Signup Settings", "field": "otp_dev_mode"})
	frappe.db.commit()
	print(f"custom_webshop: split otp_dev_mode ({old_value}) into email/phone dev-mode settings.")
