# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Populate Contact Phone.custom_phone_e164 for rows that predate it.

Safe to ship without sign-off, and deliberately the *only* migration that
is. It writes to one column, created by this app, that nothing else reads
or displays - it never touches `phone`, never touches a Customer, Contact
or Address, and cannot change what any existing record means. A row it
cannot parse is left empty, which is exactly the state it is already in.

Without this, identity matching is blind to every Contact that has not
been re-saved since the column was added - which on an existing site is
all of them. The `contact_phones_missing_canonical_form` check in
custom_webshop.signup.audit reports what is left over afterwards.

The genuinely consequential migrations - deciding which existing account
belongs to which Customer, backfilling identity rows - are deliberately
not here. Those make identity judgements, so they live behind an explicit
command a person has to run.
"""

import frappe

from custom_webshop.setup.custom_fields import create_signup_custom_fields
from custom_webshop.signup.identity import try_to_e164

BATCH_SIZE = 500


def execute():
	"""Fill in the canonical form of every phone that has none yet."""
	# Patches run before both doctype sync and hooks.py's own custom_fields
	# sync in Frappe's migrate order (patches -> sync doctypes -> sync
	# customizations), so a site that has never run after_install/
	# after_migrate reaches this query with the column still missing.
	# create_custom_fields(update=True) is idempotent - safe whether or
	# not the field already exists.
	create_signup_custom_fields()

	rows = frappe.db.sql(
		"""
		SELECT name, phone
		FROM `tabContact Phone`
		WHERE parenttype = 'Contact'
		  AND IFNULL(phone, '') != ''
		  AND IFNULL(custom_phone_e164, '') = ''
		""",
		as_dict=True,
	)

	if not rows:
		return

	updated = skipped = 0
	for index, row in enumerate(rows, start=1):
		e164 = try_to_e164(row.phone)
		if not e164:
			skipped += 1
			continue

		# update_modified=False so a data-quality backfill does not make
		# every Contact in the system look freshly edited.
		frappe.db.set_value(
			"Contact Phone", row.name, "custom_phone_e164", e164, update_modified=False
		)
		updated += 1

		if index % BATCH_SIZE == 0:
			frappe.db.commit()

	frappe.db.commit()
	print(
		f"custom_webshop: canonicalised {updated} phone number(s); "
		f"{skipped} could not be parsed and were left empty."
	)
