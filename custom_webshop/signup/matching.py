# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Deciding whether a verified signup is an existing ERPNext Customer.

This module is read-only. It looks at a verified phone number and email
address, gathers every Customer they could plausibly belong to, and
classifies the situation. It never writes, never links, and never picks a
winner when there is more than one candidate.

Deliberately rule-based, not a similarity score. A probabilistic threshold
over business records is precisely how the wrong person ends up holding
somebody else's invoices, and there is no threshold at which that becomes
an acceptable outcome. Every classification below is reproducible from the
data by hand.

The name is never, on its own, permission to link anything. It only ever
*downgrades* a phone match into a conflict - two unrelated people really
do share names, and one person really does write their own name several
ways.
"""

import json

import frappe

from custom_webshop.signup.identity import names_match

#: The two things a signup can prove, and the only values a candidate's
#: `matched_on` may carry.
CHANNELS = ("email", "phone")

NO_MATCH = "NO_MATCH"
STRONG_MATCH = "STRONG_MATCH"
PHONE_NAME_MISMATCH = "PHONE_NAME_MISMATCH"
EMAIL_MATCH = "EMAIL_MATCH"
EMAIL_NAME_MISMATCH = "EMAIL_NAME_MISMATCH"
MULTIPLE_MATCH = "MULTIPLE_MATCH"
EMAIL_ACCOUNT_EXISTS = "EMAIL_ACCOUNT_EXISTS"
PHONE_ACCOUNT_EXISTS = "PHONE_ACCOUNT_EXISTS"
CUSTOMER_ALREADY_LINKED = "CUSTOMER_ALREADY_LINKED"
OWN_ACCOUNT = "OWN_ACCOUNT"

# Results the person is shown a card for and asked about. A verified
# phone against a record in a different name used to skip this and go
# straight to a new Customer plus a staff conflict, on the reasoning that
# the answer would not change the outcome. It does change it: "yes, that
# is me, the name on it is old" is a link, and only the person can say so.
# What their answer never becomes is proof - `finalize` re-derives the
# match against the database regardless, and a "yes" only permits a link
# the engine independently reaches.
CONFIRMABLE_RESULTS = frozenset({STRONG_MATCH, EMAIL_MATCH, PHONE_NAME_MISMATCH, OWN_ACCOUNT})

# The results whose stored name goes on the card.
#
# STRONG_MATCH and EMAIL_MATCH echo back a name that already agrees with
# what was typed, so they disclose nothing the person did not supply.
# OWN_ACCOUNT is there for a different reason: reaching it means proving
# control of both the email *and* the phone of that very account, which is
# more than a password reset asks for, so withholding their own name from
# them would be theatre.
#
# PHONE_NAME_MISMATCH is here by a business decision, not by that logic. A
# verified Egyptian mobile is treated as trustworthy enough to identify
# its holder, so the name is shown and the person is asked which spelling
# their account should carry. The cost is accepted deliberately: a number
# that has been reassigned shows the previous holder's name to whoever
# holds it now. What that person can do with it is bounded - the name
# choice renames their own login and nothing else, and the Contact and
# the Customer wait for staff either way.
NAME_DISCLOSABLE_RESULTS = frozenset(
	{STRONG_MATCH, EMAIL_MATCH, OWN_ACCOUNT, PHONE_NAME_MISMATCH}
)

# Recorded for staff without asking. MULTIPLE_MATCH cannot be asked about
# - there is no one record to show - and an email match whose name
# disagrees is too weak a signal to put a stranger's record in front of
# somebody on the strength of.
CONFLICT_RESULTS = frozenset({EMAIL_NAME_MISMATCH, MULTIPLE_MATCH})

# Results that stop the signup outright.
BLOCKING_RESULTS = frozenset({EMAIL_ACCOUNT_EXISTS, PHONE_ACCOUNT_EXISTS, CUSTOMER_ALREADY_LINKED})


# ──────────────────────────────────────────────────────────────────────────
# Candidate gathering
# ──────────────────────────────────────────────────────────────────────────


def find_customers_by_phone(phone_e164):
	"""Return every Customer reachable from a verified phone number.

	Two routes, because phone data lives in two places. The Contact route
	is the real one: `Contact Phone.custom_phone_e164` is the canonical
	column this app maintains, joined to Customer through the Dynamic Link
	table. The Customer route is a backstop for legacy rows whose
	`mobile_no` was written directly with `db_set`, bypassing the
	read-only `fetch_from` that normally mirrors it from the primary
	Contact - the live database has exactly such rows.

	Args:
		phone_e164: the verified number in canonical form.

	Returns:
		A set of Customer names.
	"""
	if not phone_e164:
		return set()

	via_contact = frappe.db.sql(
		"""
		SELECT DISTINCT dl.link_name
		FROM `tabContact Phone` cp
		JOIN `tabDynamic Link` dl
		  ON dl.parent = cp.parent AND dl.parenttype = 'Contact'
		WHERE cp.parenttype = 'Contact'
		  AND cp.custom_phone_e164 = %(phone)s
		  AND dl.link_doctype = 'Customer'
		""",
		{"phone": phone_e164},
		pluck=True,
	)

	# Customer.mobile_no is stored in whatever format it was written in,
	# so it is compared against the small, enumerable set of shapes an
	# Egyptian number takes rather than normalised in SQL - a LOWER()- or
	# REPLACE()-style expression would defeat the index outright.
	via_customer = frappe.db.sql(
		"""
		SELECT name FROM `tabCustomer`
		WHERE IFNULL(mobile_no, '') != '' AND mobile_no IN %(variants)s
		""",
		{"variants": tuple(phone_variants(phone_e164))},
		pluck=True,
	)

	return {name for name in (via_contact + via_customer) if name}


def phone_variants(phone_e164):
	"""Return the written forms a canonical number may appear as.

	Args:
		phone_e164: the number in canonical form.

	Returns:
		A list of candidate strings for an exact-match query.
	"""
	from custom_webshop.signup.identity import to_local

	digits = phone_e164.lstrip("+")
	return list({phone_e164, digits, "00" + digits, to_local(phone_e164)})


def find_customers_by_email(email_normalized):
	"""Return every Customer reachable from a verified email address.

	Both queries compare with `=` rather than `LOWER(...)`: these columns
	collate `utf8mb4_unicode_ci`, so the comparison is already
	case-insensitive and still uses the index (`Contact Email.email_id` is
	indexed by this app's own setup step).

	Args:
		email_normalized: the verified address in canonical form.

	Returns:
		A set of Customer names.
	"""
	if not email_normalized:
		return set()

	via_contact = frappe.db.sql(
		"""
		SELECT DISTINCT dl.link_name
		FROM `tabContact Email` ce
		JOIN `tabDynamic Link` dl
		  ON dl.parent = ce.parent AND dl.parenttype = 'Contact'
		WHERE ce.parenttype = 'Contact'
		  AND ce.email_id = %(email)s
		  AND dl.link_doctype = 'Customer'
		""",
		{"email": email_normalized},
		pluck=True,
	)

	via_customer = frappe.db.get_all(
		"Customer", filters={"email_id": email_normalized}, pluck="name"
	)

	return {name for name in (via_contact + via_customer) if name}


# ──────────────────────────────────────────────────────────────────────────
# Existing-account checks
# ──────────────────────────────────────────────────────────────────────────


def account_for_email(email_normalized):
	"""Return the website account using this email, if there is one.

	Args:
		email_normalized: the verified address.

	Returns:
		A User name, or None.
	"""
	if not email_normalized:
		return None

	return frappe.db.get_value("User", email_normalized, "name")


def email_has_account(email_normalized):
	"""Return True when a website account already uses this email."""
	return bool(account_for_email(email_normalized))


def account_for_phone(phone_e164):
	"""Return the website account holding this number, if there is one.

	Two sources, because two things enforce it. The identity table is this
	app's own record of a verified phone. `tabUser.mobile_no` carries a
	*unique index* of Frappe's own - so a legacy account created before
	this flow existed will refuse a second User with the same number at
	insert time whether or not it has an identity row. Checking only the
	identity table would let such a signup run all the way to the final
	step and then die on a database constraint, instead of being told
	plainly after phone verification.

	Args:
		phone_e164: the verified number in canonical form.

	Returns:
		The User name of the holder, or None.
	"""
	if not phone_e164:
		return None

	identity_user = frappe.db.get_value(
		"Webshop Account Identity", {"phone_e164": phone_e164}, "user"
	)
	if identity_user:
		return identity_user

	return frappe.db.get_value(
		"User", {"mobile_no": ["in", phone_variants(phone_e164)], "enabled": 1}, "name"
	)


def phone_has_account(phone_e164):
	"""Return True when a website account already holds this number."""
	return bool(account_for_phone(phone_e164))


def customer_has_account(customer):
	"""Return the Webshop Account Identity linked to a Customer, if any.

	Args:
		customer: a Customer name.

	Returns:
		The identity record's name, or None.
	"""
	if not customer:
		return None
	return frappe.db.get_value("Webshop Account Identity", {"customer": customer}, "name")


# ──────────────────────────────────────────────────────────────────────────
# Classification
# ──────────────────────────────────────────────────────────────────────────


def submitted_party_name(doc):
	"""Return the name a Customer record would carry for this signup.

	Args:
		doc: the Webshop Signup Session document.

	Returns:
		The company name for a Company signup, otherwise the full name.
	"""
	if doc.account_type == "Company" and doc.company_name:
		return doc.company_name
	return doc.full_name


def candidate_names(customer):
	"""The names a Customer may be recognised by, split by what kind of
	name each one is.

	A person's name and a business's name are different things and must
	not be compared with each other. Somebody signing up as Ahmed is not
	claiming to be "Acme Trading" because the phone happens to reach it,
	and treating those as a name mismatch - or worse, as a match - asks
	the wrong question of everybody downstream.

	So the two are kept apart:

	* **person** - the primary Contact's name always, because a Contact
	  is a human whatever the Customer is; plus the Customer's own name
	  when the Customer *is* an individual.
	* **business** - the Customer's own name when it is a company or a
	  partnership, and nothing otherwise.

	Args:
		customer: a Customer name.

	Returns:
		A dict with "person" and "business" lists.
	"""
	row = frappe.db.get_value(
		"Customer",
		customer,
		["customer_name", "customer_type", "customer_primary_contact"],
		as_dict=True,
	)
	if not row:
		return {"person": [], "business": []}

	person = []
	if row.customer_primary_contact:
		person.append(
			frappe.db.get_value("Contact", row.customer_primary_contact, "full_name")
		)

	business = []
	if row.customer_type == "Individual":
		person.append(row.customer_name)
	else:
		business.append(row.customer_name)

	return {
		"person": [name for name in person if name],
		"business": [name for name in business if name],
	}


def _names_agree(doc, customer):
	"""Return True when the submitted name does not contradict a candidate.

	Like is compared with like: the person's own name against the names
	of people on the record, and a business name - only ever supplied by
	a company signup - against the record's business name.

	Args:
		doc: the Webshop Signup Session document.
		customer: a Customer name.
	"""
	names = candidate_names(customer)

	if doc.full_name and any(names_match(doc.full_name, theirs) for theirs in names["person"]):
		return True

	if doc.account_type == "Company" and doc.company_name:
		return any(names_match(doc.company_name, theirs) for theirs in names["business"])

	return False


def describe_candidate(customer, matched_on):
	"""Build the audit-trail record of one considered candidate.

	Staff-facing only. This is what lands in the signup session's and the
	conflict's `candidate_customers` JSON; it is never sent to a browser.

	Args:
		customer: a Customer name.
		matched_on: list of signals that surfaced it, e.g. ["phone"].

	Returns:
		A plain dict.
	"""
	row = (
		frappe.db.get_value(
			"Customer",
			customer,
			["customer_name", "customer_type", "disabled", "customer_primary_contact"],
			as_dict=True,
		)
		or {}
	)
	return {
		"customer": customer,
		"customer_name": row.get("customer_name"),
		"customer_type": row.get("customer_type"),
		"disabled": bool(row.get("disabled")),
		"primary_contact": row.get("customer_primary_contact"),
		"matched_on": matched_on,
	}


def _customer_for_account(user):
	"""The Customer a website account belongs to, if it has one.

	Read from this app's own identity row rather than by searching, since
	that row is the record of which Customer the account was resolved to.
	A legacy account created before this flow existed has none, and that
	is not an error - the recognition card simply has less to show.

	Args:
		user: a User name.

	Returns:
		A Customer name, or None.
	"""
	return frappe.db.get_value("Webshop Account Identity", {"user": user}, "customer")


def classify(doc):
	"""Decide what a verified signup means, without changing anything.

	Args:
		doc: the Webshop Signup Session document, with both channels
			verified.

	Returns:
		A dict with:
			result: one of the module-level result constants.
			candidate: the single Customer under consideration, or None.
			candidates: the full audit list of everything considered.
			reason: a short staff-facing explanation.
	"""
	phone_candidates = find_customers_by_phone(doc.phone_e164)
	email_candidates = find_customers_by_email(doc.email_normalized)
	all_candidates = phone_candidates | email_candidates

	audit = [
		describe_candidate(
			customer,
			[
				signal
				for signal, group in (("phone", phone_candidates), ("email", email_candidates))
				if customer in group
			],
		)
		for customer in sorted(all_candidates)
	]

	def outcome(result, candidate=None, reason=""):
		return {"result": result, "candidate": candidate, "candidates": audit, "reason": reason}

	# ── Their own account, coming back ──────────────────────────────────
	# Both verified channels resolving to one account is not a collision,
	# it is the owner. Proving control of an account's email *and* its
	# phone is strictly more than Frappe's own password reset asks for -
	# that needs the mailbox alone - so there is nothing to protect them
	# from here, and telling somebody "an account already exists" when the
	# account is theirs is a dead end they cannot get out of.
	#
	# Only when it is the *same* account. An email on one account and a
	# phone on another is the ambiguous case and still blocks: neither
	# channel on its own is proof of owning the other's account, and a
	# recycled phone number must never be a way into somebody else's.
	email_account = account_for_email(doc.email_normalized)
	phone_account = account_for_phone(doc.phone_e164)

	if email_account and email_account == phone_account:
		if frappe.db.get_value("User", email_account, "enabled"):
			return outcome(
				OWN_ACCOUNT,
				_customer_for_account(email_account),
				reason="Both verified channels belong to the existing account {0}.".format(
					email_account
				),
			)
		# A disabled account is not offered back. Whatever it was disabled
		# for, re-opening it is a decision for staff.
		return outcome(
			EMAIL_ACCOUNT_EXISTS,
			reason="Account {0} owns both channels but is disabled.".format(email_account),
		)

	# ── Blocking pre-checks ─────────────────────────────────────────────
	if email_account:
		return outcome(EMAIL_ACCOUNT_EXISTS, reason="A website account already uses this email.")

	if phone_account:
		return outcome(
			PHONE_ACCOUNT_EXISTS, reason="A website account already uses this phone number."
		)

	linked = [c for c in sorted(all_candidates) if customer_has_account(c)]
	if linked:
		return outcome(
			CUSTOMER_ALREADY_LINKED,
			reason="Candidate customer {0} already has a website account.".format(linked[0]),
		)

	# ── Classification ──────────────────────────────────────────────────
	if not all_candidates:
		return outcome(NO_MATCH, reason="No existing customer matched the verified phone or email.")

	if len(all_candidates) > 1:
		return outcome(
			MULTIPLE_MATCH,
			reason="{0} customers matched; the engine must not choose between them.".format(
				len(all_candidates)
			),
		)

	candidate = next(iter(all_candidates))
	matched_by_phone = candidate in phone_candidates
	agrees = _names_agree(doc, candidate)

	# A disabled Customer is never linked to automatically. Whatever the
	# reason it was disabled, re-attaching a live website account to it is
	# a decision for staff, not for a matching rule.
	if frappe.db.get_value("Customer", candidate, "disabled"):
		return outcome(
			PHONE_NAME_MISMATCH if matched_by_phone else EMAIL_NAME_MISMATCH,
			candidate,
			reason="Matched customer {0} is disabled; staff review required.".format(candidate),
		)

	if matched_by_phone:
		if agrees:
			return outcome(STRONG_MATCH, candidate, reason="Verified phone and name both match.")
		return outcome(
			PHONE_NAME_MISMATCH,
			candidate,
			reason="Verified phone matches {0}, but the name does not.".format(candidate),
		)

	if agrees:
		return outcome(EMAIL_MATCH, candidate, reason="Verified email and name both match.")

	return outcome(
		EMAIL_NAME_MISMATCH,
		candidate,
		reason="Verified email matches {0}, but the name does not.".format(candidate),
	)


# ──────────────────────────────────────────────────────────────────────────
# What the browser is allowed to see
# ──────────────────────────────────────────────────────────────────────────


#: What a redacted value is replaced with, one glyph per character.
BLOCK = "\u2593"


def recognition_payload(doc, result, customer):
	"""Build the "is this you?" card, disclosing as little as possible.

	The person on the other end has proved control of a phone number and
	an email address. That is not proof they are the person in an existing
	Customer record, so this returns only enough for a genuine owner to
	recognise their own record:

	* Never a Customer identifier - the browser has nothing to tamper with
	  and nothing to send back but yes or no.
	* The street in the clear, the governorate and country hidden. That is
	  the opposite of the instinctive choice and it is deliberate: the
	  card's only job is recognition, and a governorate shared by millions
	  helps nobody recognise their own record while a street does it
	  instantly. The cost is real and worth stating plainly - somebody who
	  proves a matching phone or email *and* types an agreeing name is
	  shown a third party's street. That is a narrow gate, but it is not
	  nothing. Nothing else in this design depends on which half is
	  hidden, so inverting the two is a one-line change if the trade ever
	  stops looking right.
	* Never the building, apartment, or delivery notes.
	* The existing name in full, but only when it already agrees with the
	  name the person typed, or when the record is their own account. A
	  half-shown name is worse than none: recognising your own record is
	  the entire job of this card, and "Ahmed ▓▓▓▓ ▓▓▓▓" asks somebody to
	  recognise themselves from a first name a great many people share.
	  Where a name would be a disclosure - a stranger's record reached by
	  a phone number, with a name that does not agree - none is sent at
	  all, which is the distinction that actually protects anybody.

	Redaction happens here, not in the browser. What is hidden is replaced
	with block glyphs before the response is built, so the blur applied on
	the card is presentation and the hidden characters are simply not in
	the page to be read out of it.

	Args:
		doc: the Webshop Signup Session document.
		result: the classification result.
		customer: the candidate Customer name.

	Returns:
		A dict safe to serialise to a guest. Each redacted key has a
		matching entry in `blurred`, so the card can render it as hidden
		rather than as a literal row of blocks.
	"""
	from custom_webshop.signup.identity import mask_phone

	payload = {
		# Two different questions share this card, and the browser has to
		# know which one it is asking. "We think this record may be yours,
		# is it?" and "this is your own account, shall we sign you in?"
		# want different words and different buttons; everything else
		# about them - what is shown, what is hidden, that the answer is
		# yes or no and nothing else - is identical.
		"kind": "own_account" if result == OWN_ACCOUNT else "match",
		"phone": mask_phone(doc.phone_e164),
		"name": None,
		# The business the record belongs to, when it belongs to one. Kept
		# apart from `name` for the same reason the comparison keeps them
		# apart: a company's name is not the name of whoever answers its
		# phone, and showing one in the other's place is what made this
		# card tell an individual their name was "الارف".
		"company": None,
		# True when a business holds this number and the person signing up
		# said they were an individual. They are not being told it is
		# theirs - they are being told what is there, which is the fact
		# they need to decide whether they recognise it.
		"company_on_record": False,
		"address": None,
		"governorate": None,
		"country": None,
		"blurred": ["governorate", "country"],
	}

	if name_is_disclosable(doc, customer, result):
		person, business = recognition_identity(doc, customer, result)
		payload["name"] = person
		payload["company"] = business
		payload["company_on_record"] = bool(business) and doc.account_type != "Company"

	address = _recognition_address(customer) if customer else None
	if address:
		payload["address"] = address.get("address_line1")
		payload["governorate"] = _redact(address.get("state") or address.get("city"))
		payload["country"] = _redact(address.get("country"))

	return payload


def _redact(value):
	"""Replace a value with one block glyph per character.

	Length is preserved because the card has to occupy the space it would
	have occupied - a hidden field that collapses to nothing reads as an
	empty field. Length is also all it leaks, which is nothing worth
	having about a governorate or a country.

	Args:
		value: the string to hide, or None.

	Returns:
		The blocked string, or None if there was nothing there.
	"""
	if not value:
		return None
	return BLOCK * len(str(value).strip())


def name_is_disclosable(doc, customer, result):
	"""Whether the record's own name may go on the card.

	Two ways to earn it, and they are the same reason twice: there is
	nobody left to protect.

	The first is a name that already agrees with the one just typed, or an
	account both verified channels reach - `NAME_DISCLOSABLE_RESULTS`.

	The second is a record that both verified channels reach even though
	no website account exists for it yet: a Customer and Contact staff
	created, or a previous order left behind. Proving the email *and* the
	phone on one record is the same proof of ownership as proving them on
	an account, and it does not become weaker because nobody has signed up
	against it yet. The name on such a record is shown even when it
	disagrees with what was typed - a disagreement is exactly what the
	person needs to see to answer the question.

	What stays hidden is the case this distinction exists for: a record
	reached by the phone alone, carrying somebody else's name. Whoever
	holds a number today is not necessarily who held it when that record
	was written.

	Args:
		doc: the Webshop Signup Session document.
		customer: the candidate Customer name, or None.
		result: the classification result.

	Returns:
		True when the name may be disclosed.
	"""
	if result in NAME_DISCLOSABLE_RESULTS:
		return True

	if not customer:
		return False

	return set(matched_channels(doc, customer)) == {"email", "phone"}


def matched_channels(doc, customer):
	"""Which verified channels reached this record when it was matched.

	Answered from the audit `classify` wrote, not from the record as it
	stands. Linking a signup to a record puts the signup's email onto its
	Contact - and `Customer.email_id` follows by native fetch_from - so
	asking the database afterwards reports both channels for every linked
	signup, including the phone-only ones. Those are precisely the ones
	whose name was withheld, so the live answer flips exactly where it
	must not: a card rebuilt after the fact would disclose a name the
	person was never shown.

	Safe on the live path: `resolve` calls `set_candidates` and saves the
	session before it builds the recognition card, so the audit is already
	there the first time this is asked.

	Falls back to querying when no audit survives - an older row, or a
	conflict raised outside a signup.

	Args:
		doc: the Webshop Signup Session document, or a Webshop Identity
			Conflict - anything carrying `phone_e164` and
			`email_normalized`.
		customer: the Customer being asked about.

	Returns:
		A sorted list of "email" and/or "phone"; empty when neither did.
	"""
	if not customer:
		return []

	for entry in recorded_candidates(doc):
		if entry.get("customer") == customer:
			return sorted({c for c in (entry.get("matched_on") or []) if c in CHANNELS})

	reaching = set()
	if customer in find_customers_by_phone(doc.phone_e164):
		reaching.add("phone")
	if customer in find_customers_by_email(doc.email_normalized):
		reaching.add("email")

	return sorted(reaching)


def recorded_candidates(doc):
	"""Parse a stored candidate audit list, never raising.

	A queue that will not open because one row's JSON is malformed is
	worse than a queue missing one row's history, so a bad value reads as
	"no audit" and the caller falls back.

	Args:
		doc: anything with a `candidate_customers` field.

	Returns:
		A list of dicts, possibly empty.
	"""
	try:
		parsed = json.loads(doc.get("candidate_customers") or "[]")
	except (ValueError, TypeError):
		return []

	return [entry for entry in parsed if isinstance(entry, dict)]


def recognition_identity(doc, customer, result):
	"""The person and the business to put on the card, kept apart.

	What a Customer's own name means depends on what the Customer is. On
	an individual it is a person's name; on a company it is the business,
	and the person is its primary Contact. Reading it as "the name" either
	way is what put a company's name in front of somebody as though it
	were their own.

	Args:
		doc: the Webshop Signup Session document.
		customer: the candidate Customer name.
		result: the classification result.

	Returns:
		A (person_name, business_name) tuple; either may be None.
	"""
	if customer:
		row = frappe.db.get_value(
			"Customer",
			customer,
			["customer_name", "customer_type", "customer_primary_contact"],
			as_dict=True,
		)
		if row:
			if row.customer_type == "Individual":
				return row.customer_name, None

			contact = (
				frappe.db.get_value("Contact", row.customer_primary_contact, "full_name")
				if row.customer_primary_contact
				else None
			)
			return contact, row.customer_name

	if result != OWN_ACCOUNT:
		return None, None

	user = account_for_email(doc.email_normalized)
	return (user and frappe.db.get_value("User", user, "full_name")), None


def _recognition_address(customer):
	"""Return the address fields the recognition card may consider.

	`state` is the governorate on a properly filled Address, but it is
	empty on every one of this site's records, where the governorate was
	typed into `city` instead - so the card falls back to it. Both are
	redacted before they leave `recognition_payload`; this returns them
	raw because it is also the only place that knows which of the two the
	value came from.

	Args:
		customer: a Customer name.

	Returns:
		A dict of address fields, or None when there is no address.
	"""
	fields = ["address_line1", "city", "state", "country"]

	primary = frappe.db.get_value("Customer", customer, "customer_primary_address")
	if primary:
		return frappe.db.get_value("Address", primary, fields, as_dict=True)

	linked = frappe.db.sql(
		"""
		SELECT a.address_line1, a.city, a.state, a.country
		FROM `tabAddress` a
		JOIN `tabDynamic Link` dl ON dl.parent = a.name AND dl.parenttype = 'Address'
		WHERE dl.link_doctype = 'Customer' AND dl.link_name = %(customer)s
		ORDER BY a.creation ASC
		LIMIT 1
		""",
		{"customer": customer},
		as_dict=True,
	)
	return linked[0] if linked else None
