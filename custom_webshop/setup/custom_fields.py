# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

SIGNUP_CUSTOM_FIELDS = {
	"Contact Phone": [
		{
			"fieldname": "custom_phone_e164",
			"fieldtype": "Data",
			"label": "Phone (E.164)",
			"insert_after": "phone",
			"read_only": 1,
			"no_copy": 1,
			"search_index": 1,
			"description": (
				"Canonical form of this number, maintained automatically. "
				"Used to match a verified signup against existing records."
			),
		}
	],
	"Contact": [
		{
			"fieldname": "custom_foreign_name",
			"fieldtype": "Data",
			"label": "Foreign Name",
			"insert_after": "full_name",
			"translatable": 0,
			"description": (
				"The same person's name in another script - Latin, Chinese, anything "
				"that is not the Arabic held above. A shopper signing up in English "
				"is not a different customer; both spellings belong on one record."
			),
		},
		{
			"fieldname": "custom_pending_phone_e164",
			"fieldtype": "Data",
			"label": "Verified Phone (Held By Another Contact)",
			"insert_after": "phone_nos",
			"read_only": 1,
			"no_copy": 1,
			"search_index": 1,
			"description": (
				"The number this website account was verified against, when it "
				"could not be stored as a phone row because another contact "
				"already holds it. Staff review decides which record keeps it."
			),
		}
	],
}


def create_signup_custom_fields():
	"""Add the columns this app owns on Contact records.

	`Contact.custom_foreign_name` holds the same person's name in a script
	other than the one `first_name` carries. On a shop selling in Egypt
	the record is usually Arabic and the signup is often English, and
	those are not two people - overwriting one with the other loses a name
	somebody uses, and creating a second Contact loses the connection. The
	identity queue offers to file the incoming spelling here instead.

	The second, `Contact.custom_pending_phone_e164`, exists because
	contact_enhancements allows one Contact to hold a given mobile number
	and no more. When a person is shown a recognition card and says "no,
	that is not me", the Contact created for them cannot carry the number
	they just verified - it is on the record they declined. Withholding
	the row is what lets that answer produce a working account at all; the
	number is written here instead so the signup is not silently missing
	the one thing it proved.

	Below: why the phone columns exist.

	`Contact Phone.phone` is stored in whatever local format the site
	already uses (`01012345678`), which is what `contact_enhancements`
	writes and what every existing row here contains - so it cannot be the
	matching key without either mass-rewriting production data or
	fragmenting on format. This derived column is the matching key
	instead, and it carries `search_index` because `tabContact Phone` has
	no index on any column but `parent`: matching by phone without it is a
	full table scan on every signup.

	`create_custom_fields(update=True)` is idempotent, so this is safe to
	call from both after_install and a patch on every migrate.
	"""
	create_custom_fields(SIGNUP_CUSTOM_FIELDS, update=True)


def create_signup_indexes():
	"""Index the columns identity matching reads that Frappe leaves bare.

	`tabContact Email` has no index on `email_id` (only `tabContact` does),
	so resolving a verified email to its Contacts scans the whole child
	table. `tabCustomer.mobile_no` is likewise unindexed and is read by the
	legacy-row backstop in `matching.find_customers_by_phone`.

	Both are plain secondary indexes on existing ERPNext tables - additive,
	reversible, and unable to fail on existing data the way a unique
	constraint would. `frappe.db.add_index` is a no-op when the index
	already exists, so this is re-runnable on every migrate.
	"""
	frappe.db.add_index("Contact Email", ["email_id"])
	frappe.db.add_index("Customer", ["mobile_no"])
