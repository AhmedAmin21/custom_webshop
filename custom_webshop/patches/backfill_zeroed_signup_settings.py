# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Give the positive-integer signup settings real values.

Frappe creates a newly-declared field on an *existing* Single with a zero
rather than the DocType's declared default - defaults only apply when a
document is inserted, and these settings were inserted long ago. A zero in
one of these is not a configuration, it is a broken one: a zero rate limit
refuses every request, a zero OTP length makes an empty code, a zero
session TTL expires a signup the instant it starts.

`custom_webshop.signup.settings.get_int` already refuses to return a zero
for these fields, so the flow is safe with or without this patch. This
exists so the values a person sees in the Desk match the ones actually in
force, instead of showing a misleading 0.

Idempotent: only fields currently at or below zero are touched.
"""

import frappe

from custom_webshop.signup.settings import DEFAULTS, MUST_BE_POSITIVE


def execute():
	if not frappe.db.exists("DocType", "Webshop Signup Settings"):
		return

	repaired = {}
	for fieldname in sorted(MUST_BE_POSITIVE):
		current = frappe.db.get_single_value("Webshop Signup Settings", fieldname)
		if current is None or int(current) < 1:
			default = DEFAULTS.get(fieldname)
			frappe.db.set_single_value("Webshop Signup Settings", fieldname, default)
			repaired[fieldname] = default

	if repaired:
		frappe.db.commit()
		print(f"custom_webshop: set {len(repaired)} signup setting(s) to their defaults: {repaired}")
