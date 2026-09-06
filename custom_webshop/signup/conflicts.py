# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""The staff review queue for signups the engine will not resolve alone.

Every ambiguous outcome ends here rather than in a guess. The person
signing up is never left stuck: they get a working account against a new
Customer straight away, and a record lands in this queue so staff can
merge the duplicate in ERPNext when they have looked at it.

That trade is deliberate. A tracked duplicate Customer is cheap and
reversible; attaching the wrong person to a real customer's order history
is neither.
"""

import json

import frappe
from frappe import _
from frappe.utils import now_datetime

from custom_webshop.signup.telemetry import log_event

# Matching results whose name differs from the conflict type that records
# them. Everything not listed here uses its own name verbatim.
#
# EMAIL_ACCOUNT_EXISTS and PHONE_ACCOUNT_EXISTS collapse into one type: both
# are the same blocking outcome ("dismiss, unless the person says they're
# locked out"), differing only in which channel matched - a distinction
# that belongs in the per-conflict reason string, not in the taxonomy.
# PHONE_NAME_MISMATCH and EMAIL_NAME_MISMATCH collapse the same way: same
# staff question, same buttons, differing only by which verified channel
# found the record.
_RESULT_TO_CONFLICT_TYPE = {
	"MULTIPLE_MATCH": "MULTIPLE_PHONE_MATCHES",
	"EMAIL_ACCOUNT_EXISTS": "ACCOUNT_ALREADY_EXISTS",
	"PHONE_ACCOUNT_EXISTS": "ACCOUNT_ALREADY_EXISTS",
	"PHONE_NAME_MISMATCH": "NAME_MISMATCH",
	"EMAIL_NAME_MISMATCH": "NAME_MISMATCH",
}

VALID_CONFLICT_TYPES = frozenset(
	{
		"NAME_MISMATCH",
		"MULTIPLE_PHONE_MATCHES",
		"CUSTOMER_ALREADY_LINKED",
		"ACCOUNT_ALREADY_EXISTS",
		"USER_REJECTED_MATCH",
		# The verified number is on somebody else's Contact, so it was
		# left off this one. Raised whenever a signup ends up with a
		# Contact that cannot carry the number it was verified against.
		"PHONE_ALREADY_ASSOCIATED",
		# Linked to an existing Customer whose stored name, or other
		# identity field, disagrees with what was submitted. The link
		# stands; the existing record is never rewritten to match.
		"PROFILE_DISCREPANCY",
		"ACCOUNT_TYPE_MISMATCH",
		"MATCHED_CUSTOMER_DISABLED",
	}
)


#: What each conflict type means, in words somebody who did not write
#: this app can act on. Staff open the queue to a screaming-snake constant
#: and a JSON blob otherwise, which tells them nothing about what happened
#: or what they are being asked to decide.
#:
#: Each entry is (headline, what happened, what to do about it).
EXPLANATIONS = {
	"NAME_MISMATCH": (
		"Linked on a verified channel, but the name doesn't match",
		"They proved a phone number or email address that already belongs to an existing "
		"customer, but the name on that record disagrees with what they typed - too weak a "
		"signal to put a stranger's record in front of anybody, so a new customer was "
		"created rather than guessing.",
		"Check whether the two are the same person. Egyptian phone numbers get reassigned, "
		"and an email can be shared by a household or an office. If they are the same "
		"person under a different spelling or script, apply the submitted name or file it "
		"as a foreign-script spelling. If they're different people, dismiss this.",
	),
	"MULTIPLE_PHONE_MATCHES": (
		"One number, several customers",
		"More than one customer record carries this number, so the engine refused to "
		"choose between them and made a new one.",
		"Merge the duplicates into whichever record has the history, then merge the new "
		"one into it too.",
	),
	"PHONE_ALREADY_ASSOCIATED": (
		"Two records want the same number",
		"The verified number could not be written onto this signup's contact, because "
		"another contact already holds it - one mobile belongs to one contact. It is "
		"recorded on the new contact as pending instead.",
		"Same person twice? Merge them and the number settles on one record. Genuinely "
		"two people sharing a line? Keep them separate and this stops resurfacing.",
	),
	"USER_REJECTED_MATCH": (
		"They said the record we found was not theirs",
		"We showed them an existing record and they declined it. A new customer was "
		"created and the number stayed where it was.",
		"Usually nothing - they knew better than the engine. Worth a look if the two "
		"records clearly are the same person.",
	),
	"PROFILE_DISCREPANCY": (
		"They say the details on this account are not theirs",
		"They signed in to an existing account after proving both its email and its phone - "
		"so the account is theirs - but said the details stored on it are wrong. Nothing "
		"was changed.",
		"Compare the name they gave with the one on the records below, and check the "
		"address and phone on the customer too. If the name they gave is right, apply it - "
		"that puts it on the contact, on the customer when it is an individual, and on the "
		"account. If the records are right as they stand, dismiss this.",
	),
	"CUSTOMER_ALREADY_LINKED": (
		"That customer already has an account",
		"The record this signup matched already has a website account attached, so the "
		"signup was stopped rather than attaching a second one.",
		"Point the person at sign-in or password reset. Merge only if there really are "
		"two accounts for one person.",
	),
	"ACCOUNT_ALREADY_EXISTS": (
		"Signup stopped: already registered",
		"Both codes were proved, and the email or phone number turned out to belong to an "
		"existing account that the other channel does not reach.",
		"Nothing to fix here unless the person says they cannot get in, or the number was "
		"reassigned and the new holder is locked out. Dismiss.",
	),
	"ACCOUNT_TYPE_MISMATCH": (
		"Signed up as one kind of party, matched another",
		"The signup said one thing about who this is - a person or a business - and "
		"the record it matched says the other. That is not necessarily wrong: a real "
		"person is very often the contact on a company account, and somebody trading "
		"under a business name may have been entered as an individual years ago. So "
		"the account was linked rather than refused. Nothing about the customer was "
		"changed: its type, its name and its history are exactly as they were.",
		"Decide which the record should be. If a person signed in to a company they "
		"work for, there is nothing to do - close this. If somebody trading as a "
		"business is sitting on an individual record, 'Make it a company' converts it "
		"and puts the business name on it; the person stays as its contact.",
	),
	"MATCHED_CUSTOMER_DISABLED": (
		"Linked to a customer that is switched off",
		"They proved both the email and the phone on this customer record, so it is "
		"almost certainly theirs - but somebody had disabled it. The signup asked them "
		"and they confirmed, so the account was linked rather than turned away; a real "
		"owner should not be stranded by a flag they cannot see.",
		"Decide what the disabling was for. If it no longer applies, use 'Re-enable the "
		"customer' - they cannot place an order against a disabled one. If it does still "
		"apply, move the account to a new customer record by hand and leave this one off.",
	),
}


#: The same nine types said in three or four words, for the places a
#: headline does not fit: the chart's axis and the list view's type
#: column. Kept under about 27 characters, which is where frappe-charts
#: starts truncating an axis label into an ellipsis. EXPLANATIONS stays the long form; this is the short one, and
#: both live here so the queue, the chart and the list cannot drift into
#: calling one situation three different things.
SHORT_LABELS = {
	"NAME_MISMATCH": "Linked, name doesn't match",
	"MULTIPLE_PHONE_MATCHES": "One number, many customers",
	"PHONE_ALREADY_ASSOCIATED": "Two records want one number",
	"USER_REJECTED_MATCH": "They declined the match",
	"PROFILE_DISCREPANCY": "Disputes stored details",
	"CUSTOMER_ALREADY_LINKED": "Customer already has an account",
	"ACCOUNT_ALREADY_EXISTS": "Stopped: already registered",
	"MATCHED_CUSTOMER_DISABLED": "Matched record is disabled",
	"ACCOUNT_TYPE_MISMATCH": "Person/business disagree",
}


def short_label(conflict_type):
	"""A few words naming a conflict type, for an axis or a column.

	Falls back to the constant made readable rather than to the constant
	itself: a type nobody has written a label for is still better shown as
	"Some New Type" than as SOME_NEW_TYPE.

	Args:
		conflict_type: a Webshop Identity Conflict type.

	Returns:
		A short human-readable string.
	"""
	label = SHORT_LABELS.get(conflict_type)
	return _(label) if label else (conflict_type or "").replace("_", " ").title()


#: Problems that are recorded rather than asked about. Nothing here has an
#: answer a button could give. Empty now: the three types that used to live
#: here (a customer with no address, a lead's prefill diverging, a stale
#: re-check with nowhere else to go) were removed from the taxonomy outright
#: rather than kept as unactionable rows - see `type_for_result` for the
#: stale-decision case. Left defined, rather than deleted, so a future
#: type that is genuinely recorded-not-asked-about has somewhere to go
#: without re-deriving this mechanism.
INFORMATIONAL = frozenset()


def describe(conflict_type):
	"""Return (headline, what happened, what to do) for a conflict type.

	Falls back to the raw name rather than an empty panel: a type this
	does not know about is still worth showing somebody.

	Args:
		conflict_type: a Webshop Identity Conflict type.

	Returns:
		A tuple of three strings.
	"""
	# Wrapped here, at return time, rather than on the EXPLANATIONS dict
	# itself. `_()` resolves against the language active *when it runs* -
	# a module-level dict would freeze every string in whatever language
	# happened to be active the moment this file was first imported
	# (usually server start, English), and no Arabic-language staff
	# member would ever see it change. Calling it inside the function
	# means every request re-translates under its own session's language.
	headline, happened, todo = EXPLANATIONS.get(
		conflict_type,
		(
			conflict_type.replace("_", " ").title(),
			"No description has been written for this conflict type yet.",
			"Read the notes below and decide.",
		),
	)
	return _(headline), _(happened), _(todo)


def type_for_result(result):
	"""Map a matching result to the conflict type that records it, if any.

	A result with no conflict of its own - NO_MATCH, STRONG_MATCH, OWN_ACCOUNT -
	can still reach here when a link approved earlier no longer holds up on
	the re-check at finalise: the record was merged, renamed, disabled or
	reassigned between approval and account creation. That situation isn't
	filed as a conflict of its own - there's nothing for staff to do beyond
	what a new Customer already did on its own - so it is logged here and
	`None` is returned, and the caller opens no queue row.

	Args:
		result: a custom_webshop.signup.matching result constant.

	Returns:
		A valid Webshop Identity Conflict type, or None when the result
		doesn't correspond to one.
	"""
	mapped = _RESULT_TO_CONFLICT_TYPE.get(result, result)
	if mapped in VALID_CONFLICT_TYPES:
		return mapped

	log_event("signup_stale_link_decision", None, matching_result=result)
	return None


def open_conflict(doc, conflict_type, reason=None, candidates=None, created_user=None, created_customer=None):
	"""Record a conflict for staff review, without duplicating an open one.

	Re-running resolution on the same signup - which happens whenever a
	person backs up a step, or an endpoint is retried - must not pile up
	identical rows for staff to wade through, so an open conflict of the
	same type on the same session is updated rather than repeated.

	Args:
		doc: the Webshop Signup Session document.
		conflict_type: one of the Webshop Identity Conflict types.
		reason: staff-facing explanation from the matching engine.
		candidates: the audit list of candidates considered.
		created_user: the account this signup ended up with, if any.
		created_customer: the Customer this signup ended up with, if any.

	Returns:
		The Webshop Identity Conflict document.
	"""
	# One conflict per signup, not one per problem. A signup can be wrong
	# in several ways at once, and filing each as its own row meant staff
	# worked one case as several unrelated items - each offering actions
	# belonging to a problem it did not describe. The row is keyed on the
	# session; every problem becomes a line on it.
	existing = frappe.db.get_value(
		"Webshop Identity Conflict",
		{"signup_session": doc.name, "status": ["in", ("Open", "In Review")]},
		"name",
	)

	if existing:
		conflict = frappe.get_doc("Webshop Identity Conflict", existing)
	else:
		conflict = frappe.new_doc("Webshop Identity Conflict")
		conflict.signup_session = doc.name
		conflict.status = "Open"

	if not any(row.problem_type == conflict_type for row in conflict.get("problems") or []):
		conflict.append("problems", {"problem_type": conflict_type, "detail": reason})

	# `conflict_type` is the headline the queue lists the row under, and
	# it is always the first problem found. Taken from the rows rather
	# than set when the field looks empty: the field is `reqd` and its
	# options begin with a real value, so `new_doc` pre-fills it and an
	# "if empty" check never fires - which titled every case
	# PHONE_NAME_MISMATCH whatever was actually wrong with it.
	conflict.conflict_type = conflict.problems[0].problem_type

	conflict.update(
		{
			"submitted_name": doc.full_name,
			# Deliberately not folded into submitted_name. That field is
			# the person's own name and `apply_submitted_name` writes it
			# onto an Individual customer - a business name arriving
			# through it would rename a person to a company.
			"claimed_company_name": (
				doc.company_name if doc.account_type == "Company" else None
			),
			"account_type": doc.account_type,
			"phone_e164": doc.phone_e164,
			"email_normalized": doc.email_normalized,
			"created_user": created_user or conflict.created_user,
			"created_customer": created_customer or conflict.created_customer,
		}
	)

	if candidates is not None:
		conflict.candidate_customers = json.dumps(candidates, ensure_ascii=False, indent=1)[:140000]

	if reason:
		note = f"[{now_datetime()}] {reason}"
		conflict.resolution_notes = (
			f"{conflict.resolution_notes}\n{note}" if conflict.resolution_notes else note
		)

	conflict.flags.ignore_permissions = True
	conflict.save(ignore_permissions=True)

	log_event("signup_conflict_opened", doc, conflict=conflict.name, conflict_type=conflict_type)
	return conflict


def attach_outcome(conflict_name, user, customer):
	"""Record which account and Customer a conflicted signup ended up with.

	Called after the finalise step, once those records exist - the conflict
	itself is raised earlier, while the decision is being made.

	Args:
		conflict_name: the Webshop Identity Conflict name, or None.
		user: the created User's name.
		customer: the created Customer's name.
	"""
	if not conflict_name:
		return

	frappe.db.set_value(
		"Webshop Identity Conflict",
		conflict_name,
		{"created_user": user, "created_customer": customer},
		update_modified=False,
	)
