# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Cached accessor for Webshop Signup Settings.

Every signup endpoint reads several of these values on every call, so they
go through `frappe.get_cached_doc`, which Frappe invalidates by itself when
the Single is saved.

Each getter carries its own fallback, so the flow behaves sanely on a site
where the Single has never been opened and saved (all fields NULL) - the
defaults declared in the DocType JSON only materialise once the document is
actually written. Note the fallback for `signup_enabled` is off: a site
that has never configured this must not accidentally be running an open
signup endpoint.
"""

import frappe

DEFAULTS = {
	"signup_enabled": 0,
	"email_otp_enabled": 1,
	"phone_otp_enabled": 1,
	"otp_dev_mode": 0,
	"otp_length": 6,
	"otp_ttl_seconds": 600,
	"otp_max_attempts": 5,
	"otp_resend_cooldown_seconds": 60,
	"otp_max_sends_per_channel": 5,
	"signup_starts_per_hour_per_ip": 30,
	"session_ttl_minutes": 30,
	"session_retention_days": 30,
	"require_name_parts": 3,
	"default_phone_region": "EG",
	"default_customer_group": None,
	"default_territory": None,
	"sms_sender_method": None,
}


def get_settings():
	"""Return the Webshop Signup Settings single document.

	Returns:
		The cached document.
	"""
	return frappe.get_cached_doc("Webshop Signup Settings")


def get(fieldname):
	"""Read one setting, falling back to this module's default.

	Args:
		fieldname: a Webshop Signup Settings fieldname.

	Returns:
		The configured value, or the default when unset.
	"""
	try:
		value = get_settings().get(fieldname)
	except Exception:
		# The DocType may not exist yet during the migrate that creates it.
		return DEFAULTS.get(fieldname)

	if value in (None, ""):
		return DEFAULTS.get(fieldname)
	return value


# Fields where zero is not a meaningful setting but a broken one: a zero
# rate limit blocks every request, a zero OTP length makes an empty code, a
# zero TTL expires everything instantly.
#
# This matters because of how Frappe adds a field to an *existing* Single:
# the column is created and the row keeps a 0, rather than picking up the
# DocType's declared default, which only applies when a document is
# inserted. A new Int setting therefore arrives as 0 on every site that has
# already saved these settings once - and a 0 here would silently disable
# signup site-wide on the next migrate. Falling back to the default for
# these fields makes that impossible.
#
# Deliberately excludes the Check flags and `otp_resend_cooldown_seconds`,
# where 0 is a real, intended value ("off", "no cooldown").
MUST_BE_POSITIVE = frozenset(
	{
		"otp_length",
		"otp_ttl_seconds",
		"otp_max_attempts",
		"otp_max_sends_per_channel",
		"signup_starts_per_hour_per_ip",
		"session_ttl_minutes",
		"session_retention_days",
		"require_name_parts",
	}
)


def get_int(fieldname):
	"""Read one integer setting.

	Args:
		fieldname: a Webshop Signup Settings fieldname.

	Returns:
		The value as an int.
	"""
	from frappe.utils import cint

	value = cint(get(fieldname))
	if value < 1 and fieldname in MUST_BE_POSITIVE:
		return cint(DEFAULTS.get(fieldname))
	return value


def is_enabled(fieldname):
	"""Read one Check setting as a bool.

	Args:
		fieldname: a Webshop Signup Settings fieldname.

	Returns:
		True when the flag is on.
	"""
	return bool(get_int(fieldname))


def get_phone_region():
	"""Return the ISO region used to parse numbers typed without a country code."""
	return get("default_phone_region") or "EG"


def get_customer_group():
	"""Return the Customer Group new Customers are created in.

	Falls back to the site's global default, and then to any leaf group, so
	a site that never configured this still works. The group-node guard
	matters: this site's global default resolves to "All Customer Groups",
	which ERPNext's own validate_customer_group() rejects outright.

	Returns:
		A Customer Group name, or None if the site somehow has none.
	"""
	configured = get("default_customer_group")
	if configured and not frappe.db.get_value("Customer Group", configured, "is_group"):
		return configured

	default = frappe.db.get_default("customer_group")
	if default and not frappe.db.get_value("Customer Group", default, "is_group"):
		return default

	return frappe.db.get_value("Customer Group", {"is_group": 0}, "name")


def get_territory():
	"""Return the Territory new Customers are created in. See get_customer_group.

	Returns:
		A Territory name, or None if the site somehow has none.
	"""
	configured = get("default_territory")
	if configured and not frappe.db.get_value("Territory", configured, "is_group"):
		return configured

	default = frappe.db.get_default("territory")
	if default and not frappe.db.get_value("Territory", default, "is_group"):
		return default

	return frappe.db.get_value("Territory", {"is_group": 0}, "name")
