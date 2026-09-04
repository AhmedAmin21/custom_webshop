# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Desk endpoints for the identity review queue.

Staff-only, unlike everything in `api.signup`: no `allow_guest`, and
every call re-checks write permission on the conflict rather than relying
on the form having been rendered. The form is a convenience; the
permission check is the control.

The work itself lives in `custom_webshop.signup.merge`. This layer does
three things and no more - authorise, validate the arguments against the
conflict as it exists right now, and keep the whole decision inside one
savepoint so a merge that fails halfway leaves nothing behind.
"""

import frappe
from frappe import _

from custom_webshop.signup import conflicts, merge

CLOSED_STATUSES = ("Resolved", "Dismissed")


def _load(conflict):
	"""Fetch a conflict the caller is allowed to act on."""
	doc = frappe.get_doc("Webshop Identity Conflict", conflict)
	doc.check_permission("write")
	return doc


@frappe.whitelist()
def get_resolution_options(conflict):
	"""Everything the resolve dialog needs to show a choice.

	Read-only. Deliberately computed fresh on every open rather than
	stored on the conflict: the queue is worked days after the rows land,
	and a footprint captured at signup time would be telling staff about
	a customer that has since placed orders.

	Args:
		conflict: the Webshop Identity Conflict's name.

	Returns:
		A dict with the parties, the suggested survivor and the reason
		for suggesting it, and whether the conflict is already closed.
	"""
	doc = _load(conflict)
	parties = merge.conflict_parties(doc)
	survivor, reason = merge.suggest_survivor(parties)
	headline, happened, todo = conflicts.describe(doc.conflict_type)

	return {
		"conflict": doc.name,
		"conflict_type": doc.conflict_type,
		"headline": headline,
		"what_happened": happened,
		"what_to_do": todo,
		"opened_on": doc.opened_on,
		"resolution_notes": doc.resolution_notes,
		"account_type": doc.account_type,
		"status": doc.status,
		"is_closed": doc.status in CLOSED_STATUSES,
		"submitted_name": doc.submitted_name,
		"phone_e164": doc.phone_e164,
		"email_normalized": doc.email_normalized,
		"parties": parties,
		"suggested_survivor": survivor,
		"suggestion_reason": reason,
		"mergeable": len(parties) > 1,
		# A name dispute has no two records to choose between - it has one
		# record and two names - so the dialog offers a different verb.
		# One person, two scripts - an Arabic record and a Latin or
		# Chinese signup. Not a conflict at all, so it gets its own verb.
		"foreign_name": merge.foreign_name_offer(doc),
		# Which verified channels reach the record, so the form can say so
		# before somebody files one name onto another. A phone-only match
		# is the weaker one: the stored name was withheld from the shopper
		# precisely because a number may have changed hands.
		"foreign_name_channels": merge.channels_reaching(doc),
		# One direction of a person/business disagreement is fixable in a
		# click; the other needs nothing done. Only the fixable one is
		# offered a button.
		"company_conversion": merge.company_conversion_offer(doc),
		"claimed_company_name": doc.claimed_company_name,
		"nameable": (
			bool(doc.submitted_name)
			and bool(doc.created_customer or doc.created_user)
			and doc.submitted_name != _stored_name(doc)
		),
		"stored_name": _stored_name(doc),
		"problems": _problems(doc),
	}


def _outstanding(doc, answers):
	"""Whether any problem this action answers is still open.

	A conflict with no problems at all is an older row from before the
	queue held one case per signup; those are let through, because
	refusing every action on them would strand them.

	Args:
		doc: the Webshop Identity Conflict document.
		answers: the problem types the action settles.

	Returns:
		True when there is something for it to do.
	"""
	rows = doc.get("problems") or []
	if not rows:
		return True

	return any(row.problem_type in answers and not row.resolved for row in rows)


def _problems(doc):
	"""Everything wrong with this signup, in the order it was found.

	One conflict is opened per signup and each problem is a row on it, so
	the form can ask each question in its own section with its own
	buttons - rather than the queue holding the same case several times,
	each row offering actions belonging to a problem it did not describe.

	Args:
		doc: the Webshop Identity Conflict document.

	Returns:
		A list of dicts, each with the problem's type, its explanation,
		whether it is settled, and what was recorded when it was found.
	"""
	out = []
	for row in doc.get("problems") or []:
		headline, happened, todo = conflicts.describe(row.problem_type)
		out.append(
			{
				"problem_type": row.problem_type,
				"headline": headline,
				"what_happened": happened,
				"what_to_do": todo,
				"detail": row.detail,
				"resolved": bool(row.resolved),
			}
		)

	return out


def _stored_name(doc):
	"""The name a conflict's records currently carry, for comparison."""
	contact = None
	if doc.created_customer:
		contact = frappe.db.get_value("Customer", doc.created_customer, "customer_primary_contact")
	if not contact and doc.created_user:
		contact = frappe.db.get_value(
			"Webshop Account Identity", {"user": doc.created_user}, "contact"
		)

	return (
		(contact and frappe.db.get_value("Contact", contact, "full_name"))
		or (doc.created_customer and frappe.db.get_value("Customer", doc.created_customer, "customer_name"))
		or (doc.created_user and frappe.db.get_value("User", doc.created_user, "full_name"))
	)


@frappe.whitelist()
def resolve_conflict(conflict, action, survivor=None, note=None, problem=None):
	"""Carry out a decision somebody has made about a conflict.

	Three outcomes, and the destructive one is the only one that needs an
	argument:

	* `make_company` - the record is an individual but the person signed
	  up as a business and gave its name. Converts the Customer's type and
	  name together, leaving them as its contact. The only place this app
	  writes `customer_type`.
	* `add_foreign_name` - one person, two scripts. The record is Arabic
	  and they signed up in Latin or Chinese letters, so both spellings
	  are kept: the Arabic stays where it is and theirs is filed in the
	  contact's Foreign Name. Nothing is overwritten and nothing is
	  duplicated.
	* `apply_name` - the person's own name was right and the record's was
	  not. Puts the submitted name on the Contact, on the Customer when it
	  is an individual, and on the account. Raised by somebody who proved
	  both channels of an account and said the name on it is not theirs;
	  the signup deliberately changed nothing at the time.
	* `merge` - the same person twice. Requires `survivor`, which must be
	  one of the Customers this conflict is about; there is no default
	  applied here, because `rename_doc(..., merge=True)` cannot be
	  undone and a merge that happened because a field was left blank is
	  exactly the accident this refuses to have.
	* `keep_separate` - two different people who share a number. Nothing
	  is changed; the conflict is closed so the pair stops resurfacing.
	* `dismiss` - not a real problem, or already handled elsewhere.

	The whole thing runs inside one savepoint. A merge touches Contacts,
	Customers, portal access and the identity rows in sequence, and half
	of that is worse than none of it - so a failure at any step rolls the
	lot back and the conflict stays open for somebody to look at again.

	Args:
		conflict: the Webshop Identity Conflict's name.
		action: one of "merge", "keep_separate", "dismiss".
		survivor: for a merge, the Customer to keep.
		note: optional free text from the person deciding.
		problem: for `settle_one`, which question is being answered.

	Returns:
		A dict describing what was done.

	Raises:
		frappe.ValidationError: on an unknown action, a survivor that is
			not part of this conflict, a merge with nothing to merge, or
			an invariant left broken afterwards.
	"""
	doc = _load(conflict)

	if action not in merge.ACTIONS:
		frappe.throw(_("Unknown action {0}.").format(action))

	if doc.status in CLOSED_STATUSES:
		frappe.throw(
			_("This conflict was already {0} by {1}.").format(
				doc.status.lower(), doc.resolved_by or _("someone")
			)
		)

	# A case stays open while other questions are outstanding, so being
	# open is no longer proof this particular question is. Refusing here
	# is what stops a second merge, or a name applied twice, on a case
	# somebody is still working through.
	answers = () if action == merge.SETTLE_ONE else merge.SETTLES.get(action, ())
	if answers and not _outstanding(doc, answers):
		frappe.throw(
			_("That part of this conflict has already been settled."),
			exc=frappe.ValidationError,
		)

	if action == merge.DISMISS:
		# The one action that closes the case outright: "none of this was
		# a real problem" answers every question on it at once.
		for row in doc.get("problems") or []:
			row.resolved = 1
		merge.close(doc, "Dismissed", note or _("Dismissed without changes."))
		return {"action": action, "conflict": doc.name}

	if action == merge.SETTLE_ONE:
		if not problem:
			frappe.throw(_("Say which part of this conflict is being settled."))

		closed = merge.settle(
			doc, action, note or _("Looked at; nothing to change."), problem=problem
		)
		return {"action": action, "conflict": doc.name, "closed": closed}

	if action == merge.MAKE_COMPANY:
		savepoint = "custom_webshop_make_company"
		frappe.db.savepoint(savepoint)
		try:
			steps = merge.make_company(doc)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			raise

		closed = merge.settle(
			doc,
			action,
			"\n".join(
				[_("Converted {0} to a company.").format(doc.created_customer)]
				+ steps
				+ ([note] if note else [])
			),
		)
		return {"action": action, "conflict": doc.name, "steps": steps, "closed": closed}

	if action == merge.ADD_FOREIGN_NAME:
		savepoint = "custom_webshop_foreign_name"
		frappe.db.savepoint(savepoint)
		try:
			steps = merge.add_foreign_name(doc)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			raise

		closed = merge.settle(
			doc,
			action,
			"\n".join(
				[_("Filed {0!r} as the contact's foreign name.").format(doc.submitted_name)]
				+ steps
				+ ([note] if note else [])
			),
		)
		return {"action": action, "conflict": doc.name, "steps": steps, "closed": closed}

	if action == merge.APPLY_NAME:
		savepoint = "custom_webshop_apply_name"
		frappe.db.savepoint(savepoint)
		try:
			steps = merge.apply_submitted_name(doc)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			raise

		account = _("Applied the submitted name {0!r}.").format(doc.submitted_name)
		closed = merge.settle(
			doc, action, "\n".join([account] + steps + ([note] if note else []))
		)
		return {"action": action, "conflict": doc.name, "steps": steps, "closed": closed}

	if action == merge.KEEP_TYPE:
		closed = merge.settle(
			doc,
			action,
			note
			or _(
				"Reviewed and left as it is: the record is the right kind. A person being "
				"the contact on a company account is the ordinary shape of one."
			),
		)
		return {"action": action, "conflict": doc.name, "closed": closed}

	if action == merge.KEEP_SEPARATE:
		closed = merge.settle(
			doc,
			action,
			note
			or _(
				"Reviewed and kept separate: these are different people. The number stays on "
				"the record that holds it, and the other account keeps it recorded as pending."
			),
		)
		return {"action": action, "conflict": doc.name, "closed": closed}

	return _merge(doc, survivor, note)


def _merge(doc, survivor, note):
	"""The destructive branch, kept apart so it reads on its own."""
	parties = merge.conflict_parties(doc)
	names = [party["customer"] for party in parties]

	if len(names) < 2:
		frappe.throw(
			_("This conflict involves only {0}, so there is nothing to merge.").format(
				names[0] if names else _("no existing customer")
			)
		)

	if not survivor:
		frappe.throw(_("Choose which customer record to keep before merging."))

	if survivor not in names:
		frappe.throw(
			_("{0} is not one of the records this conflict is about ({1}).").format(
				survivor, ", ".join(names)
			)
		)

	losers = [name for name in names if name != survivor]

	savepoint = "custom_webshop_resolve_conflict"
	frappe.db.savepoint(savepoint)
	try:
		steps = []
		for loser in losers:
			steps.extend(merge.merge_customers(doc, survivor, loser)["steps"])

		merge.assert_account_is_consistent(survivor)
	except Exception:
		frappe.db.rollback(save_point=savepoint)
		raise

	account = _("Merged {0} into {1}.").format(", ".join(losers), survivor)
	closed = merge.settle(
		doc, merge.MERGE, "\n".join([account] + steps + ([note] if note else []))
	)

	return {"action": merge.MERGE, "conflict": doc.name, "survivor": survivor,
	        "steps": steps, "closed": closed}
