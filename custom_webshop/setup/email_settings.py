# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Site-wide outgoing email presentation settings this app owns.

Every email this site sends is one of custom_webshop's own branded
customer communications (signup OTP, order status, welcome) - never an
ERPNext-authored notification - so ERPNext's own promotional
"Sent via ERPNext" footer (contributed by erpnext.hooks.default_mail_footer,
appended by frappe.email.email_body.get_footer) has no place on outgoing
mail from this site.
"""

import frappe


def disable_standard_email_footer():
	"""Turn off Frappe's standard mail footer for the whole site.

	`System Settings.disable_standard_email_footer` is the only lever
	Frappe exposes for this: `get_footer()` (frappe/email/email_body.py)
	appends the `default_mail_footer` hook (ERPNext's "Sent via ERPNext"
	line) to every outgoing email unless this is set, and that hook is
	contributed by erpnext's own hooks.py - nothing in this app's
	templates can suppress it on a per-email basis.

	`get_footer()` reads the setting via `frappe.db.get_default(...)`, a
	separate cache (`tabDefaultValue`) from the System Settings document
	field itself. That cache is normally kept in sync by
	`System Settings.on_update()`'s own `set_defaults()` - but only for
	fields where `has_value_changed()` is true, comparing against the
	value already in the database. Confirmed the hard way, in two steps:
	first a raw `frappe.db.set_single_value()` write left the field
	looking enabled while the cache stayed stale (that call bypasses
	`on_update()` entirely); then, with the field already sitting at `1`
	from that mistake, going through a normal `frappe.get_doc(...).save()`
	*still* didn't sync the cache, because saving `1` over an
	already-`1` field trips no change and `set_defaults()` skips it.
	Writing both places directly, unconditionally, is what actually
	works regardless of whatever state either one is already in.

	Idempotent: safe to call on every install and migrate.
	"""
	frappe.db.set_single_value("System Settings", "disable_standard_email_footer", 1)
	frappe.db.set_default("disable_standard_email_footer", 1)
