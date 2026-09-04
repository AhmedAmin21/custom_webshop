# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Read-only audit of existing identity data.

Run before any migration, and safe to run at any time:

    bench --site <site> execute custom_webshop.signup.audit.report

Nothing here writes, and nothing here decides. It surfaces the records a
migration would have to make a judgement about - duplicate phones, orphan
Contacts, accounts with no verified identity - so a person can make those
judgements before anything is changed. Merging two Customers touches
sales, invoices and accounting history; that is never a decision a script
should take on its own.
"""

import csv
import os

import frappe

from custom_webshop.signup.identity import try_to_e164

CHECKS = (
	"contact_phones_missing_canonical_form",
	"contacts_sharing_a_phone",
	"contacts_sharing_an_email",
	"orphan_contacts",
	"customers_missing_primary_contact",
	"customers_missing_primary_address",
	"website_users_without_a_customer",
	"users_with_multiple_customers",
	"customers_with_multiple_accounts",
	"accounts_without_a_verified_identity",
	"unparseable_customer_mobiles",
)


def contact_phones_missing_canonical_form():
	"""Contact Phone rows with no canonical E.164 value yet.

	Two very different populations, told apart by `would_parse_now`:

	* True  - a perfectly valid number that simply predates this app's
	  derived column. Invisible to phone matching until backfilled; the
	  backfill patch fixes every one of these.
	* False - genuinely not a phone number. These stay invisible to
	  matching no matter what, and are a data-quality problem for staff.
	"""
	rows = frappe.db.sql(
		"""
		SELECT parent AS contact, phone
		FROM `tabContact Phone`
		WHERE parenttype = 'Contact'
		  AND IFNULL(phone, '') != ''
		  AND IFNULL(custom_phone_e164, '') = ''
		ORDER BY parent
		""",
		as_dict=True,
	)
	for row in rows:
		row["would_parse_now"] = bool(try_to_e164(row["phone"]))
	return rows


def contacts_sharing_a_phone():
	"""Canonical numbers appearing on more than one Contact.

	Every one of these makes a signup on that number ambiguous: the
	matching engine will refuse to choose and will raise a conflict.
	"""
	return frappe.db.sql(
		"""
		SELECT custom_phone_e164 AS phone_e164,
		       COUNT(DISTINCT parent) AS contacts,
		       GROUP_CONCAT(DISTINCT parent ORDER BY parent SEPARATOR ' | ') AS contact_names
		FROM `tabContact Phone`
		WHERE parenttype = 'Contact' AND IFNULL(custom_phone_e164, '') != ''
		GROUP BY custom_phone_e164
		HAVING contacts > 1
		ORDER BY contacts DESC
		""",
		as_dict=True,
	)


def contacts_sharing_an_email():
	"""Addresses appearing on more than one Contact."""
	return frappe.db.sql(
		"""
		SELECT email_id,
		       COUNT(DISTINCT parent) AS contacts,
		       GROUP_CONCAT(DISTINCT parent ORDER BY parent SEPARATOR ' | ') AS contact_names
		FROM `tabContact Email`
		WHERE parenttype = 'Contact' AND IFNULL(email_id, '') != ''
		GROUP BY email_id
		HAVING contacts > 1
		ORDER BY contacts DESC
		""",
		as_dict=True,
	)


def orphan_contacts():
	"""Contacts linked to no Customer, Supplier, Lead or anything else.

	Dead weight that still competes for a phone number in a match.
	"""
	return frappe.db.sql(
		"""
		SELECT c.name AS contact, c.first_name, c.email_id, c.mobile_no
		FROM `tabContact` c
		LEFT JOIN `tabDynamic Link` dl
		  ON dl.parent = c.name AND dl.parenttype = 'Contact'
		WHERE dl.name IS NULL
		ORDER BY c.creation DESC
		""",
		as_dict=True,
	)


def customers_missing_primary_contact():
	"""Customers that cannot be saved from the Desk.

	contact_enhancements makes `customer_primary_contact` mandatory, so
	staff opening one of these and pressing save will be blocked.
	"""
	return frappe.db.get_all(
		"Customer",
		filters={"customer_primary_contact": ["in", (None, "")]},
		fields=["name", "customer_name", "customer_type", "disabled"],
		order_by="creation desc",
	)


def customers_missing_primary_address():
	"""Customers with no primary address. Also mandatory, also unsaveable.

	Every Customer the signup flow creates starts in this state - it has
	no address to record until checkout - so this list is expected to grow
	and is not on its own a defect.
	"""
	return frappe.db.get_all(
		"Customer",
		filters={"customer_primary_address": ["in", (None, "")]},
		fields=["name", "customer_name", "disabled"],
		order_by="creation desc",
	)


def website_users_without_a_customer():
	"""Website Users that resolve to no Customer at all.

	They can log in but have no cart, no orders and no identity.
	"""
	return frappe.db.sql(
		"""
		SELECT u.name AS user, u.full_name, u.mobile_no, u.creation
		FROM `tabUser` u
		LEFT JOIN `tabPortal User` pu
		  ON pu.user = u.name AND pu.parenttype = 'Customer'
		LEFT JOIN `tabWebshop Account Identity` wai ON wai.user = u.name
		WHERE u.user_type = 'Website User'
		  AND u.name NOT IN ('Guest', 'Administrator')
		  AND pu.name IS NULL
		  AND wai.name IS NULL
		ORDER BY u.creation DESC
		""",
		as_dict=True,
	)


def users_with_multiple_customers():
	"""Accounts holding portal access to more than one Customer.

	Ambiguous: resolution has to pick one. These need a human decision
	before they can be given a verified identity row.
	"""
	return frappe.db.sql(
		"""
		SELECT user,
		       COUNT(DISTINCT parent) AS customers,
		       GROUP_CONCAT(DISTINCT parent ORDER BY parent SEPARATOR ' | ') AS customer_names
		FROM `tabPortal User`
		WHERE parenttype = 'Customer'
		GROUP BY user
		HAVING customers > 1
		ORDER BY customers DESC
		""",
		as_dict=True,
	)


def customers_with_multiple_accounts():
	"""Customers reachable by more than one website account."""
	return frappe.db.sql(
		"""
		SELECT parent AS customer,
		       COUNT(DISTINCT user) AS accounts,
		       GROUP_CONCAT(DISTINCT user ORDER BY user SEPARATOR ' | ') AS users
		FROM `tabPortal User`
		WHERE parenttype = 'Customer'
		GROUP BY parent
		HAVING accounts > 1
		ORDER BY accounts DESC
		""",
		as_dict=True,
	)


def accounts_without_a_verified_identity():
	"""Portal accounts predating this flow.

	These still resolve through the Portal User fallback, and the
	portal-access guard deliberately leaves them alone because there is no
	verified opinion to enforce. Backfilling the unambiguous ones is what
	closes that gap.
	"""
	return frappe.db.sql(
		"""
		SELECT DISTINCT pu.user, pu.parent AS customer, u.mobile_no, u.enabled
		FROM `tabPortal User` pu
		JOIN `tabUser` u ON u.name = pu.user
		LEFT JOIN `tabWebshop Account Identity` wai ON wai.user = pu.user
		WHERE pu.parenttype = 'Customer' AND wai.name IS NULL
		ORDER BY pu.user
		""",
		as_dict=True,
	)


def unparseable_customer_mobiles():
	"""Customers whose own mobile_no is not a valid number.

	The live data includes an 18-digit value; these are invisible to phone
	matching.
	"""
	rows = frappe.db.get_all(
		"Customer",
		filters={"mobile_no": ["not in", (None, "")]},
		fields=["name", "customer_name", "mobile_no"],
	)
	return [row for row in rows if not try_to_e164(row["mobile_no"])]


def run_checks():
	"""Run every check.

	Returns:
		A dict mapping check name to its list of rows.
	"""
	return {name: globals()[name]() for name in CHECKS}


def report(out_dir=None):
	"""Print a summary of every check and optionally write CSVs.

	Args:
		out_dir: directory to write one CSV per non-empty check into.
			Nothing is written when omitted.

	Returns:
		The dict of results, so this is usable from a console too.
	"""
	results = run_checks()

	print("\nWebshop identity data audit")
	print("=" * 72)

	for name in CHECKS:
		rows = results[name]
		marker = "  " if not rows else "! "
		print(f"{marker}{name:<42} {len(rows):>6}")

	print("=" * 72)
	print("Nothing above has been modified. This report is read-only.\n")

	for name in CHECKS:
		rows = results[name]
		if rows:
			print(f"--- {name} ---")
			for row in rows[:10]:
				print(f"    {row}")
			if len(rows) > 10:
				print(f"    ... and {len(rows) - 10} more")
			print()

	if out_dir:
		written = _write_csvs(results, out_dir)
		print(f"Wrote {len(written)} CSV file(s) to {out_dir}")

	return results


def _write_csvs(results, out_dir):
	"""Write one CSV per non-empty check.

	Args:
		results: the dict from run_checks.
		out_dir: destination directory, created if missing.

	Returns:
		A list of written file paths.
	"""
	os.makedirs(out_dir, exist_ok=True)
	written = []

	for name, rows in results.items():
		if not rows:
			continue
		path = os.path.join(out_dir, f"{name}.csv")
		with open(path, "w", newline="", encoding="utf-8") as handle:
			writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
			writer.writeheader()
			writer.writerows(rows)
		written.append(path)

	return written


def clear_rate_limits():
	"""Drop this app's rate-limit counters. Testing aid, never automatic.

	`frappe.rate_limiter` stores each counter under
	`<site-db>|rl:<method>:<ip>` in Redis with a one-hour TTL, so a tester
	walking the scenario list from one machine runs into the per-IP signup
	cap partway through. Clearing them is the documented way to carry on -
	see TESTING.md.

	Safe by construction: the pattern is anchored on this app's own signup
	methods, so no other endpoint's protection is touched, and the counters
	rebuild from the next request.

	Returns:
		The number of counter keys removed.
	"""
	pattern = "rl:custom_webshop.api.signup"
	keys = list(frappe.cache.get_keys(pattern))
	if not keys:
		return 0

	# Delete by the full, already-prefixed key. Passing these back through
	# `delete_value` would re-apply the site prefix and miss every one.
	frappe.cache.delete(*keys)
	return len(keys)
