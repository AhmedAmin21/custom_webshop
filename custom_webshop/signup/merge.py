# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Resolving an identity conflict once a person has looked at it.

The signup flow never merges anything. When it cannot tell two records
apart it creates a new Customer, queues a conflict, and lets the person
get on with their order - a tracked duplicate is cheap and reversible,
and attaching the wrong person to a real customer's order history is
neither.

This is the other half: what staff do with the queue afterwards. It
gathers the records a conflict is actually about, shows what each of them
is worth in submitted documents, and - once somebody has chosen - carries
out the merge or records that the two are genuinely different people.

Two rules hold throughout:

* **The survivor is always a human choice.** `frappe.rename_doc(...,
  merge=True)` is one-way; there is no undo short of restoring a backup.
  A default is suggested, and the reasoning for it is shown, but nothing
  here decides on its own.
* **The invariant is checked afterwards, not assumed.** A website account
  is one User, one Contact and one Customer that all agree with each
  other. `assert_account_is_consistent` re-reads the database and says so
  out loud, so a merge that half-worked is caught here rather than
  discovered by a customer who cannot see their own orders.
"""

import json
import re

import frappe
from frappe import _
from frappe.utils import now_datetime

from custom_webshop.signup import conflicts
from custom_webshop.signup.telemetry import log_event

#: Submitted documents that make a Customer "the one with the history".
#: Deliberately the ones a person would recognise as their own dealings
#: with the shop, rather than every doctype that happens to link here.
FINANCIAL_DOCTYPES = (
	("Sales Order", "customer"),
	("Sales Invoice", "customer"),
	("Delivery Note", "customer"),
	("Payment Entry", None),
)

MERGE = "merge"
KEEP_SEPARATE = "keep_separate"
DISMISS = "dismiss"
APPLY_NAME = "apply_name"
ADD_FOREIGN_NAME = "add_foreign_name"
MAKE_COMPANY = "make_company"
KEEP_TYPE = "keep_type"
#: "Looked at this one, nothing to change." Every question needs an
#: answer or the case cannot close, and some questions have no button of
#: their own: a dispute about an address rather than a name has no name
#: to apply, and a record that was already the right kind has nothing to
#: convert. Without this the section sat there with no way to answer it.
SETTLE_ONE = "settle_one"
ACTIONS = (MERGE, KEEP_SEPARATE, DISMISS, APPLY_NAME, ADD_FOREIGN_NAME,
           MAKE_COMPANY, KEEP_TYPE, SETTLE_ONE)

#: Arabic letters, including the presentation forms text sometimes
#: arrives in.
_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

#: Any letter at all, so a string of digits is not mistaken for a name.
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


# ──────────────────────────────────────────────────────────────────────────
# What a conflict is about
# ──────────────────────────────────────────────────────────────────────────


def financial_footprint(customer):
	"""Count the submitted documents that make a Customer worth keeping.

	Only `docstatus = 1`. A draft is not history - it is somebody's
	half-finished form, and merging it away costs nothing.

	Args:
		customer: a Customer name.

	Returns:
		A dict of doctype -> count, plus `total`.
	"""
	counts = {}
	for doctype, field in FINANCIAL_DOCTYPES:
		if not frappe.db.table_exists(doctype):
			continue
		filters = (
			{"party_type": "Customer", "party": customer, "docstatus": 1}
			if field is None
			else {field: customer, "docstatus": 1}
		)
		counts[doctype] = frappe.db.count(doctype, filters)

	counts["total"] = sum(counts.values())
	return counts


def conflict_parties(conflict):
	"""Every Customer this conflict is actually about.

	Assembled from three places, because a conflict type does not always
	say which records collided: the Customer the signup created, the
	candidates the matching engine considered and recorded, and - for a
	withheld phone - whoever currently holds the number on their Contact.

	Args:
		conflict: the Webshop Identity Conflict document.

	Returns:
		A list of dicts, one per Customer, newest last. Each carries the
		Customer's name, its primary Contact, whether it holds the
		verified number, its website account if it has one, and its
		financial footprint.
	"""
	names = []

	def remember(name):
		if name and name not in names and frappe.db.exists("Customer", name):
			names.append(name)

	for entry in _recorded_candidates(conflict):
		remember(entry.get("customer"))

	for name in _customers_holding(conflict.phone_e164):
		remember(name)

	remember(conflict.created_customer)

	return [_describe(name, conflict) for name in names]


def _recorded_candidates(conflict):
	"""Parse the candidate audit list stored on a conflict.

	Never raises: this is a Small Text field written by an older version
	of this app, and a queue that will not open because one row's JSON is
	malformed is worse than a queue missing one row's history.
	"""
	try:
		parsed = json.loads(conflict.candidate_customers or "[]")
	except (ValueError, TypeError):
		return []

	return [entry for entry in parsed if isinstance(entry, dict)]


def _customers_holding(phone_e164):
	"""Customers reachable from whoever currently holds a number."""
	if not phone_e164:
		return []

	from custom_webshop.signup.matching import find_customers_by_phone

	return sorted(find_customers_by_phone(phone_e164))


def _describe(customer, conflict):
	"""Build one side of the comparison staff are shown."""
	row = (
		frappe.db.get_value(
			"Customer",
			customer,
			["customer_name", "customer_type", "disabled", "customer_primary_contact", "creation"],
			as_dict=True,
		)
		or {}
	)
	contact = row.get("customer_primary_contact")

	return {
		"customer": customer,
		"customer_name": row.get("customer_name"),
		"customer_type": row.get("customer_type"),
		"disabled": bool(row.get("disabled")),
		"created_on": row.get("creation"),
		"contact": contact,
		"contact_name": frappe.db.get_value("Contact", contact, "full_name") if contact else None,
		"user": frappe.db.get_value("Contact", contact, "user") if contact else None,
		"holds_verified_phone": _holds_phone(contact, conflict.phone_e164),
		"pending_phone": (
			frappe.db.get_value("Contact", contact, "custom_pending_phone_e164")
			if contact
			else None
		),
		"is_signup_customer": customer == conflict.created_customer,
		"footprint": financial_footprint(customer),
	}


def _holds_phone(contact, phone_e164):
	if not contact or not phone_e164:
		return False

	return bool(
		frappe.db.exists(
			"Contact Phone", {"parenttype": "Contact", "parent": contact, "phone": phone_e164}
		)
	)


def suggest_survivor(parties):
	"""Which record to pre-select, and why.

	The record with submitted documents wins: merging it away is the one
	move that destroys something. When both have history, or neither does,
	there is nothing to choose on those grounds and the older record is
	suggested instead - it is the one other people's references are more
	likely to point at.

	This is a suggestion shown with its reason attached, never a decision.
	On this site today every Customer has zero submitted documents, so the
	answer will usually be "neither has any history" - which is worth
	saying plainly rather than presenting an arbitrary pick as if it were
	reasoned.

	Args:
		parties: the list from `conflict_parties`.

	Returns:
		A (customer_name, reason) tuple, or (None, reason) when there is
		nothing to suggest.
	"""
	if len(parties) < 2:
		return None, _("Only one customer record is involved; there is nothing to merge.")

	with_history = [p for p in parties if p["footprint"]["total"]]

	if len(with_history) == 1:
		return with_history[0]["customer"], _(
			"Only this record has submitted documents ({0}). Merging it away would move real history."
		).format(with_history[0]["footprint"]["total"])

	if len(with_history) > 1:
		richest = max(with_history, key=lambda p: p["footprint"]["total"])
		return richest["customer"], _(
			"Both records have submitted documents. This one has the most ({0}); check the other "
			"before merging - whichever you keep, the other's history moves onto it."
		).format(richest["footprint"]["total"])

	oldest = min(parties, key=lambda p: p["created_on"] or now_datetime())
	return oldest["customer"], _(
		"Neither record has any submitted documents, so there is no history to weigh. "
		"The older one is suggested because other records are more likely to point at it."
	)


# ──────────────────────────────────────────────────────────────────────────
# Carrying out the decision
# ──────────────────────────────────────────────────────────────────────────


def merge_customers(conflict, survivor, loser):
	"""Merge two Customers and everything that hangs off them.

	Contacts first, then Customers. Merging the Contacts while both
	Customers still exist lets Frappe re-point the losing Customer's
	`customer_primary_contact` as part of the rename, so the second merge
	meets a consistent pair rather than a dangling link.

	`rename_doc(..., merge=True)` re-points Link fields and Dynamic Links,
	which covers `Webshop Account Identity.customer` and `.contact` on its
	own - but it does *not* merge child tables, so the losing Customer's
	Portal User rows go with it. The account's portal access is re-granted
	explicitly afterwards, and the whole thing is checked rather than
	trusted.

	ERPNext refuses a merge across two party currencies
	(`validate_party_currency_before_merging`, called from
	`Customer.before_rename`). That error is allowed through as itself: it
	means the two records are not interchangeable, which is exactly what
	staff need to be told.

	Args:
		conflict: the Webshop Identity Conflict document.
		survivor: the Customer to keep.
		loser: the Customer to merge into it.

	Returns:
		A dict describing what was done.
	"""
	survivor_contact = frappe.db.get_value("Customer", survivor, "customer_primary_contact")
	loser_contact = frappe.db.get_value("Customer", loser, "customer_primary_contact")

	steps = []
	merged_contact = _merge_contacts(conflict, survivor_contact, loser_contact, steps)

	frappe.rename_doc("Customer", loser, survivor, merge=True)
	steps.append(_("Merged customer {0} into {1}.").format(loser, survivor))

	_restore_portal_access(survivor, steps)
	_clear_pending_phone(merged_contact or survivor_contact, conflict.phone_e164, steps)

	return {"survivor": survivor, "loser": loser, "contact": merged_contact, "steps": steps}


def _merge_contacts(conflict, survivor_contact, loser_contact, steps):
	"""Reduce the two Contacts to one, by whichever route applies.

	When both genuinely hold the number - which only legacy rows can now,
	since contact_enhancements' unique index went live - this hands the
	job to that app's own `merge_duplicate_mobile_contacts`. It is their
	invariant, their query, and their sanctioned path; re-implementing it
	here would be a second thing to keep right.

	The case this app actually produces is the other one: the number is on
	one Contact and merely *recorded* on the other, in
	`custom_pending_phone_e164`, because the index would not let it be
	written twice. Their helper refuses that outright - it looks for
	Contacts sharing the number and finds one - so the merge goes through
	`rename_doc` directly, which is the same mechanism their helper wraps.

	Args:
		conflict: the Webshop Identity Conflict document.
		survivor_contact: the Contact to keep, or None.
		loser_contact: the Contact to merge in, or None.
		steps: a list to append a human-readable account to.

	Returns:
		The surviving Contact's name, or None if there was nothing to do.
	"""
	if not survivor_contact or not loser_contact or survivor_contact == loser_contact:
		return survivor_contact or loser_contact

	shared = _customers_share_the_number(conflict.phone_e164, survivor_contact, loser_contact)
	if shared:
		result = _merge_through_contact_enhancements(conflict.phone_e164, survivor_contact)
		if result is not None:
			steps.append(
				_("Merged contacts {0} into {1} via contact_enhancements.").format(
					", ".join(result.get("merged") or []) or _("none"), survivor_contact
				)
			)
			for failure in result.get("failed") or []:
				steps.append(
					_("Could not merge contact {0}: {1}").format(
						failure.get("name"), failure.get("error")
					)
				)
			return survivor_contact

	# The losing Contact's own child rows are deleted with it, so anything
	# worth keeping is copied across first. The account link matters most:
	# a Contact with no `user` is a Contact the website cannot find.
	_carry_over_account_details(survivor_contact, loser_contact, steps)

	frappe.rename_doc("Contact", loser_contact, survivor_contact, merge=True)
	steps.append(_("Merged contact {0} into {1}.").format(loser_contact, survivor_contact))
	return survivor_contact


def _customers_share_the_number(phone_e164, *contacts):
	"""True when more than one of these Contacts holds the number itself."""
	return sum(1 for contact in contacts if _holds_phone(contact, phone_e164)) > 1


def _merge_through_contact_enhancements(phone_e164, survivor_contact):
	"""Call that app's merge, or return None when it is not installed."""
	try:
		from contact_enhancements.api.contact_dedupe import merge_duplicate_mobile_contacts
	except ImportError:
		return None

	return merge_duplicate_mobile_contacts(phone_e164, survivor_contact)


def _carry_over_account_details(survivor_contact, loser_contact, steps):
	"""Move the website account and its email onto the surviving Contact.

	Written field by field rather than by saving the Contact, because a
	full save re-runs every validate hook in the chain - including the
	phone rules that are the reason this merge exists - on a document that
	is halfway through being merged.
	"""
	loser = frappe.get_doc("Contact", loser_contact)
	survivor = frappe.get_doc("Contact", survivor_contact)

	if loser.user and not survivor.user:
		frappe.db.set_value("Contact", survivor_contact, "user", loser.user, update_modified=False)
		steps.append(_("Moved website account {0} onto {1}.").format(loser.user, survivor_contact))

	held = {row.email_id for row in survivor.get("email_ids", [])}
	for row in loser.get("email_ids", []):
		if row.email_id in held:
			continue
		frappe.get_doc(
			{
				"doctype": "Contact Email",
				"parenttype": "Contact",
				"parentfield": "email_ids",
				"parent": survivor_contact,
				"email_id": row.email_id,
				"is_primary": 0,
			}
		).insert(ignore_permissions=True)
		steps.append(_("Copied email {0} onto {1}.").format(row.email_id, survivor_contact))


def _restore_portal_access(customer, steps):
	"""Re-grant portal access the Customer merge dropped.

	`rename_doc` moves Link fields, not child rows, so every Portal User
	row on the losing Customer is deleted with it. Without this a person
	whose account was merged keeps their login and loses their orders.
	"""
	from custom_webshop.signup.linking import _ensure_portal_user

	users = frappe.get_all(
		"Webshop Account Identity", filters={"customer": customer}, pluck="user"
	)
	for user in users:
		if not user or not frappe.db.exists("User", user):
			continue
		_ensure_portal_user(customer, frappe.get_doc("User", user))
		steps.append(_("Confirmed portal access for {0}.").format(user))


def _clear_pending_phone(contact, phone_e164, steps):
	"""Drop the withheld-number marker once the records are one.

	The field exists to say "this account proved a number its Contact
	could not hold". After a merge that is no longer true - there is one
	Contact now - so leaving it set would keep the account looking
	unresolved forever.
	"""
	if not contact or not phone_e164:
		return

	if frappe.db.get_value("Contact", contact, "custom_pending_phone_e164") != phone_e164:
		return

	frappe.db.set_value("Contact", contact, "custom_pending_phone_e164", None, update_modified=False)
	steps.append(_("Cleared the pending-number marker on {0}.").format(contact))


# ──────────────────────────────────────────────────────────────────────────
# The invariant
# ──────────────────────────────────────────────────────────────────────────


def assert_account_is_consistent(customer):
	"""Check that every website account on a Customer still hangs together.

	One User, one Contact, one Customer, all agreeing. Read back from the
	database rather than inferred from what the merge believed it did, so
	a step that silently failed is caught here.

	Args:
		customer: the surviving Customer's name.

	Raises:
		frappe.ValidationError: listing every account that does not.
	"""
	problems = []

	for identity in frappe.get_all(
		"Webshop Account Identity",
		filters={"customer": customer},
		fields=["name", "user", "contact"],
	):
		if not frappe.db.exists("User", identity.user):
			problems.append(_("{0}: its user no longer exists.").format(identity.name))
			continue

		if identity.contact and not frappe.db.exists("Contact", identity.contact):
			problems.append(_("{0}: its contact no longer exists.").format(identity.name))
			continue

		if identity.contact:
			owner = frappe.db.get_value("Contact", identity.contact, "user")
			if owner and owner != identity.user:
				problems.append(
					_("{0}: contact {1} belongs to {2}, not {3}.").format(
						identity.name, identity.contact, owner, identity.user
					)
				)

		if not frappe.db.exists(
			"Portal User", {"parenttype": "Customer", "parent": customer, "user": identity.user}
		):
			problems.append(
				_("{0}: {1} has no portal access to {2}.").format(
					identity.name, identity.user, customer
				)
			)

	if problems:
		frappe.throw(
			_("The merge left these accounts inconsistent:")
			+ "\n"
			+ "\n".join(problems),
			title=_("Merge Incomplete"),
		)


# ──────────────────────────────────────────────────────────────────────────
# Closing the conflict
# ──────────────────────────────────────────────────────────────────────────


def apply_submitted_name(conflict):
	"""Put the name somebody gave at signup onto the records it disagrees with.

	Raised when a person verified both channels of an account, was shown
	it, and said the name on it is not theirs. The signup deliberately
	changed nothing at the time - a name typed into a form is a claim, and
	the record it disagrees with may be a company account, a relative's,
	or simply right. This is the click that decides it was the person's
	own name after all.

	Written through the Contact and then, for an individual, the Customer.
	The Contact first because contact_enhancements propagates a Contact's
	name onto the records linked to it, so doing them the other way round
	would have its hook overwrite the Customer straight back. The Customer
	is still set explicitly rather than left to that propagation: this app
	does not depend on it, and an outcome that only happens when another
	app is installed is not an outcome.

	A company's `customer_name` is its trading name and is left alone -
	the person signing up is a contact there, not the company.

	Args:
		conflict: the Webshop Identity Conflict document.

	Returns:
		A list of what was changed, in words.

	Raises:
		frappe.ValidationError: when there is no name, or nothing to put it on.
	"""
	name = (conflict.submitted_name or "").strip()
	if not name:
		frappe.throw(_("This conflict carries no submitted name to apply."))

	customer = conflict.created_customer
	contact = frappe.db.get_value("Customer", customer, "customer_primary_contact") if customer else None
	if not contact and conflict.created_user:
		contact = frappe.db.get_value(
			"Webshop Account Identity", {"user": conflict.created_user}, "contact"
		)

	if not contact and not customer:
		frappe.throw(_("This conflict names no contact or customer to apply it to."))

	steps = []
	# Read before the Contact is touched: contact_enhancements propagates a
	# Contact's name onto the records linked to it the moment it is saved,
	# so the Customer's own values have to be captured first to report what
	# actually changed.
	before = (
		frappe.db.get_value(
			"Customer", customer, ["customer_name", "customer_type"], as_dict=True
		)
		if customer
		else None
	)

	if contact:
		doc = frappe.get_doc("Contact", contact)
		if doc.full_name != name:
			previous = doc.full_name
			# Stored whole in `first_name`, which is where this app puts a
			# submitted name and where `full_name` is derived from.
			doc.first_name = name
			doc.last_name = None
			doc.flags.ignore_permissions = True
			doc.save()
			steps.append(_("Contact {0}: {1} → {2}").format(contact, previous, name))

	if before:
		# A company's `customer_name` is its trading name and belongs to the
		# company, not to whoever happens to be its contact. Only an
		# individual takes the person's name.
		#
		# This used to write the company name back afterwards, because the
		# propagation above overwrote it regardless of type. That app gates
		# the name sync on `customer_type` now, so skipping is enough.
		if before.customer_type == "Individual":
			if before.customer_name != name:
				frappe.db.set_value("Customer", customer, "customer_name", name)
				steps.append(
					_("Customer {0}: {1} → {2}").format(customer, before.customer_name, name)
				)
		else:
			steps.append(
				_("Customer {0} kept as {1} - a company's name is not a person's.").format(
					customer, before.customer_name
				)
			)

	if conflict.created_user:
		first = frappe.db.get_value("User", conflict.created_user, "first_name")
		if first != name:
			frappe.db.set_value("User", conflict.created_user, "first_name", name)
			frappe.db.set_value("User", conflict.created_user, "last_name", None)
			steps.append(_("Account {0}: {1} → {2}").format(conflict.created_user, first, name))

	return steps or [_("Every record already carried that name.")]


def is_arabic(name):
	"""Whether a name is written in Arabic script."""
	return bool(name) and bool(_ARABIC.search(name))


def is_foreign_to_arabic(name):
	"""Whether a name is written in letters, but not Arabic ones.

	Latin, Chinese, Cyrillic - the distinction this app needs is only
	"same script as the record" or not, so everything non-Arabic is one
	bucket. A string with no letters in it at all is neither.
	"""
	return bool(name) and bool(_LETTER.search(name)) and not _ARABIC.search(name)


def foreign_name_offer(conflict):
	"""Whether this conflict is really just one person, two scripts.

	The common shape on a shop selling in Egypt: the Contact was entered
	in Arabic and the person signed up in English. Those are not two
	names in conflict, they are one name written twice, and the right
	answer is to keep both rather than to overwrite either.

	Args:
		conflict: the Webshop Identity Conflict document.

	Returns:
		The submitted name when it can be filed as a foreign spelling of
		the stored one, otherwise None.
	"""
	submitted = (conflict.submitted_name or "").strip()
	if not is_foreign_to_arabic(submitted):
		return None

	contact = _contact_for(conflict)
	if not contact:
		return None

	if not frappe.get_meta("Contact").has_field("custom_foreign_name"):
		return None

	stored = frappe.db.get_value("Contact", contact, "full_name")
	if not is_arabic(stored):
		return None

	# Two names are only one person's if something verified connects them
	# to this record. Without that the check is "an Arabic record exists
	# and somebody typed Latin letters", which is true of every stranger.
	if not channels_reaching(conflict):
		return None

	return submitted


def channels_reaching(conflict):
	"""Which verified channels reached this conflict's record.

	The lookup itself lives in `matching.matched_channels`, which the
	signup uses to decide whether a name may be disclosed - the same
	question asked at a different moment, so it must not be a second
	implementation. This adds only what the queue knows and the signup
	does not: which Customer the row is about, and where to find the
	audit when the conflict was raised without a copy of it.

	Args:
		conflict: the Webshop Identity Conflict document.

	Returns:
		A sorted list of "email" and/or "phone"; empty when neither did.
	"""
	from custom_webshop.signup.matching import matched_channels

	customer = conflict.created_customer
	if not customer:
		contact = _contact_for(conflict)
		customer = contact and frappe.db.get_value(
			"Dynamic Link",
			{"parenttype": "Contact", "parent": contact, "link_doctype": "Customer"},
			"link_name",
		)

	if not customer:
		return []

	# `open_conflict` only copies the candidates onto the conflict when a
	# caller passes them, but the session always keeps them - so a row
	# raised without them is not a row with no history.
	source = conflict if _recorded_candidates(conflict) else _signup_session(conflict)
	return matched_channels(source or conflict, customer)


def _signup_session(conflict):
	"""The signup this conflict came out of, for its candidate audit."""
	if not conflict.signup_session:
		return None

	if not frappe.db.exists("Webshop Signup Session", conflict.signup_session):
		return None

	return frappe.get_doc("Webshop Signup Session", conflict.signup_session)


def add_foreign_name(conflict):
	"""File the submitted spelling beside the stored one, keeping both.

	Writes `Contact.custom_foreign_name` and touches nothing else. The
	Arabic name stays where it is - it is the one the business uses on
	paperwork - and the Latin or Chinese spelling stops being a reason to
	create a second record or to argue about which is correct.

	Written with `db.set_value`, not a document save: saving a Contact
	re-runs contact_enhancements' whole validate chain, including the
	unique-phone rule, on a record that is not being changed in any way
	that needs re-validating.

	Args:
		conflict: the Webshop Identity Conflict document.

	Returns:
		A list of what was changed, in words.

	Raises:
		frappe.ValidationError: when this is not that situation.
	"""
	submitted = foreign_name_offer(conflict)
	if not submitted:
		frappe.throw(
			_(
				"This one is not an Arabic record with a foreign spelling that a "
				"verified phone or email reaches - check the two names below "
				"before filing one as the other."
			)
		)

	contact = _contact_for(conflict)
	previous = frappe.db.get_value("Contact", contact, "custom_foreign_name")
	if previous == submitted:
		return [_("Contact {0} already carried that foreign name.").format(contact)]

	frappe.db.set_value("Contact", contact, "custom_foreign_name", submitted)
	stored = frappe.db.get_value("Contact", contact, "full_name")

	# A field that already held something loses it here, so the value that
	# went is named in the account of what happened. `resolve_conflict`
	# folds these lines into resolution_notes, which makes the audit trail
	# the place the old spelling can still be read back from.
	if previous:
		return [
			_("Contact {0}: kept {1}, filed {2} as the foreign name, replacing {3}.").format(
				contact, stored, submitted, previous
			)
		]

	return [
		_("Contact {0}: kept {1}, filed {2} as the foreign name.").format(
			contact, stored, submitted
		)
	]


def company_conversion_offer(conflict):
	"""Whether this conflict is an individual record that claims to be a business.

	The one direction worth offering a button for. A person signing in to
	a company they work for needs nothing done - that is the ordinary
	shape of a company account, and closing the conflict is the whole
	answer. The other way round is a record that is genuinely the wrong
	kind, and fixing it by hand means editing a Customer's type and name
	together and remembering to keep the contact.

	Args:
		conflict: the Webshop Identity Conflict document.

	Returns:
		The business name to convert to, or None when this is not that.
	"""
	claimed = (conflict.claimed_company_name or "").strip()
	if not claimed or conflict.account_type != "Company":
		return None

	customer = conflict.created_customer
	if not customer or not frappe.db.exists("Customer", customer):
		return None

	if frappe.db.get_value("Customer", customer, "customer_type") == "Company":
		return None

	return claimed


def make_company(conflict):
	"""Convert the matched customer into a company, deliberately.

	The only place this app writes `customer_type`. A signup never does:
	the type drives tax templates and party defaults, and
	contact_enhancements can re-derive a customer's fields from a linked
	Lead, so changing it as a side effect of somebody picking a radio
	button on a shop front is not a thing this flow will do.

	The person stays exactly where they are - as the customer's contact,
	which is what a company account looks like. Their own name is not
	touched, and neither is the address or the history.

	Args:
		conflict: the Webshop Identity Conflict document.

	Returns:
		A list of what was changed, in words.

	Raises:
		frappe.ValidationError: when this is not that situation.
	"""
	claimed = company_conversion_offer(conflict)
	if not claimed:
		frappe.throw(
			_(
				"This is not an individual record with a business name to take - "
				"check the customer's type and the name given at signup."
			)
		)

	customer = conflict.created_customer
	before = frappe.db.get_value(
		"Customer", customer, ["customer_name", "customer_type"], as_dict=True
	)
	frappe.db.set_value(
		"Customer", customer, {"customer_type": "Company", "customer_name": claimed}
	)

	steps = [
		_("Customer {0}: {1} → {2}, and {3} → Company.").format(
			customer, before.customer_name, claimed, before.customer_type
		)
	]

	contact = _contact_for(conflict)
	if contact:
		steps.append(
			_("Contact {0} stays as the company's contact; their own name is unchanged.").format(
				contact
			)
		)

	return steps


def _contact_for(conflict):
	"""The Contact a conflict is about, however it is reachable."""
	if conflict.created_customer:
		contact = frappe.db.get_value(
			"Customer", conflict.created_customer, "customer_primary_contact"
		)
		if contact:
			return contact

	if conflict.created_user:
		return frappe.db.get_value(
			"Webshop Account Identity", {"user": conflict.created_user}, "contact"
		)

	return None


#: What each action settles. An action answers one question and leaves
#: the rest of the case alone - applying a name says nothing about
#: whether the customer is a company, and converting a company says
#: nothing about the name.
SETTLES = {
	APPLY_NAME: ("PROFILE_DISCREPANCY", "PHONE_NAME_MISMATCH", "EMAIL_NAME_MISMATCH"),
	ADD_FOREIGN_NAME: ("PROFILE_DISCREPANCY", "PHONE_NAME_MISMATCH", "EMAIL_NAME_MISMATCH"),
	MAKE_COMPANY: ("ACCOUNT_TYPE_MISMATCH",),
	KEEP_TYPE: ("ACCOUNT_TYPE_MISMATCH",),
	# Merging says these are the same person, which is the answer to a
	# rejection as much as to a duplicate: staff decided the "no" was
	# wrong, and there is nothing left to review about it.
	MERGE: ("MULTIPLE_PHONE_MATCHES", "PHONE_ALREADY_ASSOCIATED", "CUSTOMER_ALREADY_LINKED",
	        "USER_REJECTED_MATCH"),
	KEEP_SEPARATE: ("MULTIPLE_PHONE_MATCHES", "PHONE_ALREADY_ASSOCIATED",
	                "USER_REJECTED_MATCH"),
}


def settle(conflict, action, note=None, problem=None):
	"""Mark the problems an action answers, and close only if none are left.

	The queue holds one row per signup, so an action must not close the
	whole case on its own: a name applied leaves the question of what
	kind of record this is exactly where it was. Each action ticks off
	what it actually settled; the conflict closes when nothing is
	outstanding.

	Args:
		conflict: the Webshop Identity Conflict document.
		action: the action just carried out.
		note: what was done, in words a colleague can read later.
		problem: for `SETTLE_ONE`, which question was answered.

	Returns:
		True when the conflict was closed, False when work remains.
	"""
	settled = (problem,) if action == SETTLE_ONE and problem else SETTLES.get(action, ())
	stamped = now_datetime()
	for row in conflict.get("problems") or []:
		if not row.resolved and row.problem_type in settled:
			row.resolved = 1
			row.resolved_on = stamped
			row.resolved_by = frappe.session.user

	outstanding = [
		row
		for row in conflict.get("problems") or []
		if not row.resolved and row.problem_type not in conflicts.INFORMATIONAL
	]
	if outstanding:
		_record(conflict, note)
		conflict.flags.ignore_permissions = True
		conflict.save()
		return False

	close(conflict, "Resolved", note or _("Everything on this signup was settled."))
	return True


def _record(conflict, note):
	"""Append to the account of what happened, without closing anything."""
	if not note:
		return

	stamped = "[{0}] {1}".format(now_datetime(), note)
	conflict.resolution_notes = (
		"{0}\n{1}".format(conflict.resolution_notes, stamped)
		if conflict.resolution_notes
		else stamped
	)


def close(conflict, status, note):
	"""Record what was decided and stamp the conflict closed.

	`resolved_by` and `resolved_on` are filled in by the doctype's own
	`validate`, so this only supplies the account of what happened.

	Args:
		conflict: the Webshop Identity Conflict document.
		status: "Resolved" or "Dismissed".
		note: what was done, in words a colleague can read later.
	"""
	stamped = "[{0}] {1}".format(now_datetime(), note)
	conflict.resolution_notes = (
		"{0}\n{1}".format(conflict.resolution_notes, stamped)
		if conflict.resolution_notes
		else stamped
	)
	conflict.status = status
	conflict.flags.ignore_permissions = True
	conflict.save()

	log_event(
		"identity_conflict_closed",
		None,
		conflict=conflict.name,
		conflict_type=conflict.conflict_type,
		status=status,
	)
