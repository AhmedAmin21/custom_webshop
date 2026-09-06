# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Consolidate the Webshop Identity Conflict taxonomy from 14 types to 9.

Two straight renames - EMAIL_ACCOUNT_EXISTS and PHONE_ACCOUNT_EXISTS collapse
into ACCOUNT_ALREADY_EXISTS; PHONE_NAME_MISMATCH and EMAIL_NAME_MISMATCH
collapse into NAME_MISMATCH - plus one retirement: INCOMPLETE_PROFILE is
dropped from the taxonomy outright, since a signup collects no address and
the field was informational (`conflicts.INFORMATIONAL`), never holding a
case open. STALE_LINK_DECISION and LEAD_PREFILL_DIVERGENCE are also
retired, but no site has ever recorded either, so there is nothing to
migrate for them. See `custom_webshop.signup.conflicts` for the taxonomy
itself.

Existing rows are migrated rather than left with a retired Select value:
`_validate_selects` (frappe/model/base_document.py) throws on any future
save of a document whose stored value isn't in the field's current
`options`, and this doctype's own desk form disables Save entirely but the
whitelisted resolve actions still call `doc.save()`.

Idempotent: every step only touches rows still carrying a retired value, so
running this again after it has already run finds nothing to do.
"""

import frappe
from frappe.utils import now_datetime

#: Old type -> the merged type it now records under. Applied to both the
#: conflict's own headline field and the per-problem rows.
_RENAMES = {
	"EMAIL_ACCOUNT_EXISTS": "ACCOUNT_ALREADY_EXISTS",
	"PHONE_ACCOUNT_EXISTS": "ACCOUNT_ALREADY_EXISTS",
	"PHONE_NAME_MISMATCH": "NAME_MISMATCH",
	"EMAIL_NAME_MISMATCH": "NAME_MISMATCH",
}


def execute():
	if not frappe.db.exists("DocType", "Webshop Identity Conflict"):
		return

	renamed = 0
	for old, new in _RENAMES.items():
		renamed += frappe.db.count("Webshop Identity Conflict", {"conflict_type": old})
		frappe.db.sql(
			"UPDATE `tabWebshop Identity Conflict` SET conflict_type=%s WHERE conflict_type=%s",
			(new, old),
		)
		frappe.db.sql(
			"UPDATE `tabWebshop Identity Problem` SET problem_type=%s WHERE problem_type=%s",
			(new, old),
		)

	closed = _retire_incomplete_profile()

	frappe.db.commit()
	print(
		f"custom_webshop: renamed {renamed} conflict(s) into the merged taxonomy, "
		f"closed {closed} conflict(s) that existed only for a retired INCOMPLETE_PROFILE."
	)


def _retire_incomplete_profile():
	"""Drop INCOMPLETE_PROFILE from every conflict that carries it.

	Every case seen in practice is standalone - the only problem on its
	conflict - so this closes the case rather than guessing at what should
	headline it instead. Written generically (queried, not assumed) in
	case some other site has one bundled alongside a different problem:
	that conflict keeps its remaining problems and is re-headlined from
	them, exactly as `conflicts.open_conflict` itself derives a headline.

	Returns:
		How many conflicts were closed outright (as opposed to merely
		losing the one problem row and keeping their other problems).
	"""
	parents = frappe.db.sql_list(
		"""
		SELECT DISTINCT parent FROM `tabWebshop Identity Problem`
		WHERE problem_type='INCOMPLETE_PROFILE'
		"""
	)

	closed = 0
	for parent in parents:
		frappe.db.sql(
			"""
			DELETE FROM `tabWebshop Identity Problem`
			WHERE parent=%s AND problem_type='INCOMPLETE_PROFILE'
			""",
			(parent,),
		)

		remaining = frappe.db.sql(
			"""
			SELECT problem_type FROM `tabWebshop Identity Problem`
			WHERE parent=%s ORDER BY idx LIMIT 1
			""",
			(parent,),
		)

		if remaining:
			# Something else was wrong with this signup too; re-headline
			# it from what is left rather than leave a retired constant
			# as the thing the queue lists it under.
			frappe.db.set_value(
				"Webshop Identity Conflict",
				parent,
				"conflict_type",
				remaining[0][0],
				update_modified=False,
			)
			continue

		status = frappe.db.get_value("Webshop Identity Conflict", parent, "status")
		if status in ("Resolved", "Dismissed"):
			continue

		note = (
			"[{0}] Automatically dismissed: INCOMPLETE_PROFILE was retired from the "
			"conflict taxonomy - it fired on every signup-created customer and held "
			"no case open - and this was the only problem on this conflict."
		).format(now_datetime())
		existing_notes = frappe.db.get_value("Webshop Identity Conflict", parent, "resolution_notes")

		frappe.db.set_value(
			"Webshop Identity Conflict",
			parent,
			{
				"status": "Dismissed",
				"resolved_on": now_datetime(),
				"resolved_by": "Administrator",
				"resolution_notes": f"{existing_notes}\n{note}" if existing_notes else note,
			},
			update_modified=False,
		)
		closed += 1

	return closed
