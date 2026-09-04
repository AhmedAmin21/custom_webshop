# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""The verified signup API.

Every endpoint follows the same shape: authorise the caller against the
signup session, validate the input, delegate to a module in
`custom_webshop.signup`, and return `session.envelope(doc)` - the state
the flow is now in and the actions permitted from it. The browser renders
that; it decides nothing itself.

Two rules hold across the whole surface:

* No endpoint accepts a Customer identifier, and none returns one. The
  candidate under consideration lives on the server; the browser can only
  say yes or no to it.
* Nothing in ERPNext is created until `complete`. A signup abandoned at
  any earlier point leaves one expired row and nothing else.
"""

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint

from custom_webshop.signup import (
	conflicts,
	linking,
	matching,
	notifications,
	otp,
	passwords,
	session,
	settings,
)
from custom_webshop.signup.identity import (
	names_match,
	normalize_email,
	normalize_region,
	to_e164,
	validate_full_name,
)
from custom_webshop.signup.telemetry import log_event

ACCOUNT_TYPES = ("Individual", "Company")

# Deliberately identical wording for "this email has an account" and "this
# phone has an account". Both are only ever shown to somebody who has just
# proved they control the channel in question, but keeping the copy
# uniform means the responses cannot be diffed for information either.
ACCOUNT_EXISTS_MESSAGE = "An account already exists for these details. Please sign in, or reset your password."

# Which detail was already taken. Named to the person, because by the time
# any of these is decided they have verified *both* the email and the
# phone in this session - so every one of them is about something they
# have just proved they control, and there is nothing here they could not
# already find out by trying to sign in.
#
# The reason it is safe now and was not before: this verdict used to be
# reached at `verify_email`, where a caller who controlled only an address
# could learn whether some *other* channel was registered. It is reached
# at `resolve` now, after both.
BLOCK_REASONS = {
	"EMAIL_ACCOUNT_EXISTS": "email",
	"PHONE_ACCOUNT_EXISTS": "phone",
	"CUSTOMER_ALREADY_LINKED": "customer",
}


# ──────────────────────────────────────────────────────────────────────────
# Guards
# ──────────────────────────────────────────────────────────────────────────


def is_available():
	"""Return whether a signup can be started and finished right now.

	Three switches, all of which must be on: Website Settings' site-wide
	`disable_signup` must be clear, this app's own `signup_enabled` must
	be set, and both verification channels must be usable.

	Fails closed on the last one. The phone number is this flow's primary
	identity signal, so a site that cannot send an SMS cannot safely run
	identity resolution at all - better to decline at the first step than
	to walk somebody through half a signup and strand them, or to quietly
	resolve customers against an unproven number.

	`otp_dev_mode` is *not* an exception to that and never checked here.
	It changes only how a code is delivered - written to the site log
	instead of sent - so the flow stays exercisable before an Email
	Account or an SMS gateway exists while still requiring both codes to
	be typed. A switch that skipped verification outright would mean a
	site could resolve identities against an unproven number, which is
	the one thing this whole module exists to prevent.

	The login page renders its "Create one" link from this same function,
	so the link appears if and only if the endpoint behind it will work -
	the two cannot drift into offering a signup that then refuses.

	Returns:
		True when signup is fully available.
	"""
	from frappe.website.utils import is_signup_disabled

	if is_signup_disabled() or not settings.is_enabled("signup_enabled"):
		return False

	return settings.is_enabled("email_otp_enabled") and settings.is_enabled("phone_otp_enabled")


def _assert_signup_available():
	"""Refuse to start - or continue - a signup the site cannot finish.

	Called at every flow-advancing step, not only at `start`. A session
	begun while both channels were on must not be finishable after an
	admin turns one off, or the switch would only bind new visitors and
	leave whoever was mid-flow able to complete with less proof than the
	site now requires. Reading state and cancelling stay available, so
	nobody is stranded holding a session they cannot even abandon.

	Raises:
		frappe.ValidationError: when signup is unavailable. The message is
			deliberately the same whichever switch is off - which of them
			is is not a visitor's business.
	"""
	if not is_available():
		frappe.throw(_("Sign up is currently unavailable."), title=_("Not Available"))


def _as_bool(value):
	"""Interpret a truthy value arriving over HTTP.

	A JSON body delivers a real bool, a form post delivers "1"/"true"/"on"
	as a string, and both reach the same parameter. Anything unrecognised
	is False, so a malformed answer to the recognition card can only ever
	fail safe - towards a new Customer, never towards a link.

	Args:
		value: whatever the request carried.

	Returns:
		True or False.
	"""
	if isinstance(value, bool):
		return value
	return str(value).strip().lower() in ("1", "true", "yes", "on")


# ──────────────────────────────────────────────────────────────────────────
# Start
# ──────────────────────────────────────────────────────────────────────────


def _signup_start_limit():
	"""How many signups one IP may begin per hour.

	Read through a callable so it can be tuned without a deploy - and a
	callable is what `frappe.rate_limiter.rate_limit` accepts for exactly
	this.

	The default is deliberately generous. This limit is per *IP*, and
	Egyptian mobile carriers route large numbers of subscribers through a
	single public address, so a tight value here turns away real customers
	long before it inconveniences anyone abusing the endpoint. The controls
	that actually bound abuse are per-session and much tighter: five codes
	per channel, five verify attempts per code, and a resend cooldown.

	Returns:
		The configured hourly limit.
	"""
	return settings.get_int("signup_starts_per_hour_per_ip")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=_signup_start_limit, seconds=60 * 60, methods=["POST"])
def start(account_type, full_name, email, phone, company_name=None, phone_country=None):
	"""Begin a signup and send the first email passcode.

	Deliberately does not check whether the email or phone already has an
	account. Answering that here would turn this endpoint into an oracle
	anybody could use to test addresses against the customer base; the
	check runs after the relevant channel is verified, so the answer only
	ever reaches someone who controls it.

	Args:
		account_type: "Individual" or "Company".
		full_name: the person's full name, at least three parts.
		email: the account email.
		phone: the mobile number, in that country's local format or full
			international form.
		company_name: required when account_type is "Company".
		phone_country: ISO region the number was entered under, from the
			country picker. Decides which rules the number is judged by;
			falls back to the configured default if missing or unknown.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()

	if account_type not in ACCOUNT_TYPES:
		frappe.throw(_("Please choose whether this is a personal or a company account."))

	submitted_name = (full_name or "").strip()
	full_name = validate_full_name(full_name, min_parts=settings.get_int("require_name_parts"))

	company_name = (company_name or "").strip()
	if account_type == "Company" and not company_name:
		frappe.throw(_("Please enter your company name."), title=_("Missing Company Name"))

	# Names are corrected rather than refused, so the person has to be told
	# what was actually stored - finding a silently different spelling on an
	# invoice later is worse than being asked to fix it up front.
	name_adjusted = full_name if full_name != submitted_name else None

	email_normalized = normalize_email(email)
	region = normalize_region(phone_country, settings.get_phone_region())
	phone_e164 = to_e164(phone, region=region)

	doc = session.create(
		account_type=account_type,
		full_name=full_name,
		company_name=company_name or None,
		email=email_normalized,
		email_normalized=email_normalized,
		phone_raw=(phone or "").strip(),
		phone_e164=phone_e164,
		phone_country=region,
	)
	log_event("signup_started", doc, name_adjusted=bool(name_adjusted))

	return _begin_email_verification(doc, name_adjusted=name_adjusted)


def _begin_email_verification(doc, name_adjusted=None):
	"""Move a signup into email verification and send a code.

	Args:
		doc: the Webshop Signup Session document.
		name_adjusted: the corrected name, when it differs from what was
			typed, so the browser can tell the person what was stored.

	Returns:
		The standard signup envelope.
	"""
	session.transition(doc, session.EMAIL_PENDING)

	code = otp.issue(doc, otp.EMAIL)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	notifications.send_email_otp(doc, code)

	log_event("otp_sent", doc, channel="email")
	data = _otp_data(doc, otp.EMAIL)
	if name_adjusted:
		data["name_adjusted"] = name_adjusted
	return session.envelope(
		doc, _("We sent a verification code to {0}.").format(doc.email), data
	)


def _otp_data(doc, channel):
	"""Return the client-side hints for an outstanding passcode.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".

	Returns:
		A dict of non-sensitive display values.
	"""
	return {
		"channel": channel,
		"otp_length": settings.get_int("otp_length"),
		"resend_in": otp.seconds_until_resend(doc, channel),
		"sends_remaining": otp.sends_remaining(doc, channel),
	}


# ──────────────────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=60, seconds=60 * 60, methods=["POST"])
def get_state(signup_id):
	"""Return where a signup currently stands, for a browser that reloaded.

	Args:
		signup_id: the opaque signup handle.

	Returns:
		The standard signup envelope.
	"""
	doc = session.load(signup_id)
	data = {}

	if doc.status == session.EMAIL_PENDING:
		data = _otp_data(doc, otp.EMAIL)
	elif doc.status == session.PHONE_PENDING:
		data = _otp_data(doc, otp.PHONE)
	elif doc.status == session.MATCH_REVIEW:
		data = {
			"recognition": matching.recognition_payload(doc, doc.match_result, doc.candidate_customer)
		}

	return session.envelope(doc, data=data)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=20, seconds=60 * 60, methods=["POST"])
def cancel(signup_id):
	"""Abandon a signup explicitly.

	Args:
		signup_id: the opaque signup handle.

	Returns:
		The standard signup envelope.
	"""
	doc = session.load(signup_id)
	session.transition(doc, session.CANCELLED, save=True)
	log_event("signup_cancelled", doc)
	return session.envelope(doc, _("This signup has been cancelled."))


# ──────────────────────────────────────────────────────────────────────────
# Email verification
# ──────────────────────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=5, seconds=60 * 60, methods=["POST"])
def send_email_otp(signup_id):
	"""Re-send the email passcode.

	Args:
		signup_id: the opaque signup handle.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(signup_id, expected_states=[session.EMAIL_PENDING])

	code = otp.issue(doc, otp.EMAIL)
	session.touch(doc)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	notifications.send_email_otp(doc, code)

	log_event("otp_resent", doc, channel="email")
	return session.envelope(
		doc, _("We sent a new code to {0}.").format(doc.email), _otp_data(doc, otp.EMAIL)
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=20, seconds=60 * 60, methods=["POST"])
def verify_email(signup_id, code):
	"""Check the email passcode.

	Verifying an address is all this does. Whether that address already
	belongs to an account is decided in `resolve`, once the phone is
	proven too - see the note there.

	Args:
		signup_id: the opaque signup handle.
		code: the submitted passcode.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(signup_id, expected_states=[session.EMAIL_PENDING])

	try:
		otp.verify(doc, otp.EMAIL, code)
	finally:
		# The attempt counter must survive a failed verification, so it is
		# saved whether or not the code was right.
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)

	session.transition(doc, session.EMAIL_VERIFIED, save=True)
	log_event("email_verified", doc)
	return session.envelope(doc, _("Email verified."))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=5, seconds=60 * 60, methods=["POST"])
def change_email(signup_id, email):
	"""Replace the email on a signup and start verification again.

	The previous address stops counting as verified immediately. The send
	counter is not reset, so this cannot be cycled to send unlimited mail
	to addresses of an attacker's choosing.

	Args:
		signup_id: the opaque signup handle.
		email: the new address.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(
		signup_id,
		expected_states=[session.EMAIL_PENDING, session.EMAIL_VERIFIED, session.PHONE_PENDING],
	)

	email_normalized = normalize_email(email)
	if email_normalized == doc.email_normalized:
		frappe.throw(_("That is already the email address on this signup."))

	otp.reset(doc, otp.EMAIL)
	doc.email = email_normalized
	doc.email_normalized = email_normalized

	if doc.status != session.EMAIL_PENDING:
		session.transition(doc, session.EMAIL_PENDING)

	log_event("email_changed", doc)
	return _resend_after_change(doc, otp.EMAIL)


def _resend_after_change(doc, channel):
	"""Issue and send a fresh code after the address or number changed.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".

	Returns:
		The standard signup envelope.
	"""
	code = otp.issue(doc, channel)
	session.touch(doc)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)

	if channel == otp.EMAIL:
		notifications.send_email_otp(doc, code)
		message = _("We sent a verification code to {0}.").format(doc.email)
	else:
		notifications.send_phone_otp(doc, code)
		message = _("We sent a verification code to {0}.").format(doc.phone_raw)

	return session.envelope(doc, message, _otp_data(doc, channel))


# ──────────────────────────────────────────────────────────────────────────
# Phone verification
# ──────────────────────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=5, seconds=60 * 60, methods=["POST"])
def send_phone_otp(signup_id):
	"""Send, or re-send, the SMS passcode.

	Only reachable once the email is verified - the ordering is enforced
	by the accepted states, not by the browser following instructions.

	Args:
		signup_id: the opaque signup handle.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(
		signup_id, expected_states=[session.EMAIL_VERIFIED, session.PHONE_PENDING]
	)

	code = otp.issue(doc, otp.PHONE)
	if doc.status != session.PHONE_PENDING:
		session.transition(doc, session.PHONE_PENDING)
	session.touch(doc)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	notifications.send_phone_otp(doc, code)

	log_event("otp_sent", doc, channel="phone")
	return session.envelope(
		doc,
		_("We sent a verification code to {0}.").format(doc.phone_raw),
		_otp_data(doc, otp.PHONE),
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=20, seconds=60 * 60, methods=["POST"])
def verify_phone(signup_id, code):
	"""Check the SMS passcode.

	Args:
		signup_id: the opaque signup handle.
		code: the submitted passcode.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(signup_id, expected_states=[session.PHONE_PENDING])

	try:
		otp.verify(doc, otp.PHONE, code)
	finally:
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)

	session.transition(doc, session.PHONE_VERIFIED, save=True)
	log_event("phone_verified", doc)
	return session.envelope(doc, _("Phone verified."))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=5, seconds=60 * 60, methods=["POST"])
def change_phone(signup_id, phone, phone_country=None):
	"""Replace the phone number on a signup and verify it again.

	Args:
		signup_id: the opaque signup handle.
		phone: the new number.
		phone_country: ISO region for the new number. Defaults to the one
			already on the signup, so changing only the digits keeps the
			country the person picked.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(
		signup_id, expected_states=[session.PHONE_PENDING, session.PHONE_VERIFIED]
	)

	region = normalize_region(
		phone_country, doc.phone_country or settings.get_phone_region()
	)
	phone_e164 = to_e164(phone, region=region)
	if phone_e164 == doc.phone_e164:
		frappe.throw(_("That is already the number on this signup."))

	otp.reset(doc, otp.PHONE)
	doc.phone_raw = (phone or "").strip()
	doc.phone_country = region
	doc.phone_e164 = phone_e164

	if doc.status != session.PHONE_PENDING:
		session.transition(doc, session.PHONE_PENDING)

	log_event("phone_changed", doc)
	return _resend_after_change(doc, otp.PHONE)


# ──────────────────────────────────────────────────────────────────────────
# Identity resolution
# ──────────────────────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=10, seconds=60 * 60, methods=["POST"])
def resolve(signup_id):
	"""Work out whether this verified person is an existing Customer.

	Runs only from PHONE_VERIFIED, so both channels are always proven
	before any Customer record is so much as looked up - and so every
	verdict, including "you already have an account", is delivered at one
	point in the flow rather than two. Answering after the email alone
	would let the phone step be skipped to learn whether an address is
	registered, and would make the email branch and the phone branch
	distinguishable however carefully their wording was matched.

	Args:
		signup_id: the opaque signup handle.

	Returns:
		The standard signup envelope. For a confirmable match, `data`
		carries a deliberately sparse recognition card - never a Customer
		identifier.
	"""
	_assert_signup_available()
	doc = session.load(signup_id, expected_states=[session.PHONE_VERIFIED])

	verdict = matching.classify(doc)
	doc.match_result = verdict["result"]
	session.set_candidates(doc, verdict["candidates"])

	if verdict["result"] in matching.BLOCKING_RESULTS:
		# Every blocking result still leaves through this one return, but
		# it now says *which* detail is already taken. Standing in front of
		# somebody with "an account already exists for these details" when
		# they have just proved control of both of them is a dead end they
		# cannot reason their way out of - and there is nothing to protect,
		# because both details are theirs. See BLOCK_REASONS.
		conflicts.open_conflict(
			doc,
			conflicts.type_for_result(verdict["result"]),
			verdict["reason"],
			verdict["candidates"],
		)
		session.block(doc, verdict["result"], verdict["reason"])
		log_event("signup_blocked", doc, reason=verdict["result"])
		return session.envelope(
			doc,
			_(ACCOUNT_EXISTS_MESSAGE),
			{
				"recovery_email": doc.email,
				"blocked_on": BLOCK_REASONS.get(verdict["result"]),
			},
		)

	if verdict["result"] in matching.CONFIRMABLE_RESULTS:
		doc.candidate_customer = verdict["candidate"]
		doc.user_decision = "Pending"
		session.transition(doc, session.MATCH_REVIEW, save=True)
		log_event("match_review", doc)
		return session.envelope(
			doc,
			_("We found an existing customer record that may be yours."),
			{
				"recognition": matching.recognition_payload(
					doc, verdict["result"], verdict["candidate"]
				)
			},
		)

	if verdict["result"] in matching.CONFLICT_RESULTS:
		# No question is asked for what is left here, and for a different
		# reason in each case. MULTIPLE_MATCH has no single record to put
		# in front of anybody. EMAIL_NAME_MISMATCH is too weak a signal to
		# show a stranger's record on: an address can be mistyped into
		# somebody else's, and the name disagreeing is the only other
		# thing there was to go on.
		#
		# A verified *phone* whose name disagrees is now asked about -
		# see matching.CONFIRMABLE_RESULTS. It used to be treated the same
		# way as these two, on the reasoning that the answer would not
		# change the outcome. It does: "yes, that is me, the name on it is
		# old" is a link, and only the person can say so.
		conflicts.open_conflict(
			doc,
			conflicts.type_for_result(verdict["result"]),
			verdict["reason"],
			verdict["candidates"],
		)
		doc.resolution = linking.CREATE_NEW_WITH_CONFLICT
		session.transition(doc, session.READY, save=True)
		log_event("match_conflict", doc, reason=verdict["result"])
		return session.envelope(
			doc,
			_("Almost there — just choose a password."),
			{"notice": _("Our team will review your details to keep your account records tidy.")},
		)

	doc.resolution = linking.CREATE_NEW
	session.transition(doc, session.READY, save=True)
	log_event("match_none", doc)
	return session.envelope(doc, _("Almost there — just choose a password."))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=10, seconds=60 * 60, methods=["POST"])
def decide(signup_id, accept):
	"""Record the person's answer to the recognition card.

	The answer is a plain yes or no against a candidate the server is
	already holding. Nothing identifying a Customer crosses the wire in
	either direction, and "yes" is not treated as authentication - it only
	permits a link the backend independently re-verifies at `complete`.

	Saying yes does not always finish the question. When the record's name
	differs from the one just typed, a second card asks which of the two
	the account should carry - see `_offer_name_choice`. Saying yes to a
	record and saying yes to its spelling are different answers, and
	assuming the second from the first is how somebody ends up with a name
	they did not choose.

	Args:
		signup_id: the opaque signup handle.
		accept: truthy for "yes, this is me".

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(signup_id, expected_states=[session.MATCH_REVIEW])
	accepted = _as_bool(accept)

	if doc.match_result == matching.OWN_ACCOUNT:
		return _decide_own_account(doc, accepted)

	if accepted:
		doc.user_decision = "Accepted"
		doc.resolution = linking.LINK_EXISTING
		# Logged here, before the second card can return early. This is
		# the answer that permits the link, and when a name choice
		# followed it the event was never written at all - so the one
		# consent the whole link rests on was missing from the trail for
		# exactly the signups that went furthest.
		log_event("match_decision", doc, accepted=True)
		offer = _offer_name_choice(doc)
		if offer:
			return offer
		message = _("Thanks — we'll connect your account to that record.")
	else:
		doc.user_decision = "Rejected"
		doc.resolution = linking.CREATE_NEW_WITH_CONFLICT
		log_event("match_decision", doc, accepted=False)
		conflicts.open_conflict(
			doc,
			"USER_REJECTED_MATCH",
			"Person declined the match with {0}; a new customer will be created.".format(
				doc.candidate_customer
			),
		)
		message = _("No problem — we'll set up a new account for you.")

	session.transition(doc, session.READY, save=True)
	return session.envelope(doc, message)


def _decide_own_account(doc, accepted):
	"""Answer the card when the record shown is the person's own account.

	A different question from "is this record yours?", so it is not
	squeezed into the branch above - but both answers keep them moving,
	because both are true of somebody who has just verified the email
	*and* the phone of an existing account. They are the owner either way.
	What differs is what they are saying about the details on it.

	**Yes, these are my data.** The record is right. If the name on it
	also matches what they typed there is nothing left to ask, and they go
	to the password step. If it does not, they are asked which of the two
	spellings the account should carry - a second card, not an assumption.

	**This is not my data.** The account is still theirs; something stored
	on it is wrong. Their own account takes the name they just gave, so
	they are not left looking at somebody else's spelling of themselves
	every time they sign in - but the Contact and the Customer are left
	exactly as they are. Those are business records with order history
	behind them, and a name typed at a signup form is a claim, not a
	correction. Staff settle it from the queue.

	Args:
		doc: the Webshop Signup Session document, in MATCH_REVIEW.
		accepted: the person's answer.

	Returns:
		The standard signup envelope.
	"""
	doc.resolution = linking.RECOVER_EXISTING

	if accepted:
		doc.user_decision = "Accepted"
		# Before the second card, for the reason given in `decide`.
		log_event("match_decision", doc, accepted=True, recovery=True)
		offer = _offer_name_choice(doc)
		if offer:
			return offer

		doc.rename_account = 0
		session.transition(doc, session.READY, save=True)
		return session.envelope(
			doc,
			_("Welcome back — set a password and we'll sign you in."),
			{"recovering": "accepted"},
		)

	doc.user_decision = "Rejected"
	doc.rename_account = 1
	session.transition(doc, session.READY, save=True)
	log_event("match_decision", doc, accepted=False, recovery=True)
	return session.envelope(
		doc,
		_("Understood — set a password and we'll get you in."),
		{
			"recovering": "disputed",
			"notice": _(
				"Your account will use the details you just gave. We'll ask our team "
				"to check them against your customer record before changing that."
			),
		},
	)


def _offer_name_choice(doc):
	"""Ask which spelling the account should carry, when the two differ.

	Returns None when there is nothing to ask - the names already agree,
	or one of them is missing - and the caller carries straight on.

	The card stays in MATCH_REVIEW rather than inventing a state of its
	own: it is the second half of the same question, and a person who
	reloads mid-answer should land back on the card rather than on a step
	that assumes an answer they never gave.

	Args:
		doc: the Webshop Signup Session document.

	Returns:
		The standard signup envelope, or None.
	"""
	stored = _stored_display_name(doc)
	# The person's own name, never the business. This card decides what
	# the *account* is called, and `submitted_party_name` returns the
	# company for a company signup - which offered to name a personal
	# login "Beta Works".
	submitted = doc.full_name

	if not stored or not submitted or names_match(stored, submitted):
		return None

	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)
	log_event("name_choice_offered", doc)
	return session.envelope(
		doc,
		_("One last thing."),
		{
			"name_choice": {
				"stored": stored,
				"submitted": submitted,
				"own_account": doc.match_result == matching.OWN_ACCOUNT,
			}
		},
	)


def _stored_display_name(doc):
	"""The *person's* name the matched record currently carries.

	Asked of `matching.recognition_identity`, which is the same function
	the recognition card uses, because this is the same question one step
	later and two lookups are how the two drifted apart. It used to read
	`Customer.customer_name` whatever the Customer was, so on a company
	record this card offered to name somebody's personal account after
	the business - "which name should your account use: Acme Trading, or
	Mohamed?" - while the card they had just answered showed the person's
	name correctly.

	A company's name is never a candidate here. The choice is between the
	person on the record and the person typing.
	"""
	person, _business = matching.recognition_identity(
		doc, doc.candidate_customer, doc.match_result
	)
	if person:
		return person

	user = matching.account_for_email(doc.email_normalized)
	if not user:
		return None

	contact = frappe.db.get_value("Webshop Account Identity", {"user": user}, "contact")
	return (contact and frappe.db.get_value("Contact", contact, "full_name")) or frappe.db.get_value(
		"User", user, "full_name"
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=10, seconds=60 * 60, methods=["POST"])
def choose_name(signup_id, use_submitted):
	"""Answer the second card: which spelling should the account carry?

	Only the *account* is ever renamed by this. The Contact and the
	Customer keep what they have until a person in the Desk decides
	otherwise, because those carry order history and a name typed into a
	signup form is a claim rather than a correction. Choosing "use mine"
	queues that decision; choosing "keep yours" queues nothing, because
	nothing is in dispute.

	Args:
		signup_id: the opaque signup handle.
		use_submitted: truthy to carry the name they typed.

	Returns:
		The standard signup envelope.
	"""
	_assert_signup_available()
	doc = session.load(signup_id, expected_states=[session.MATCH_REVIEW])

	if doc.user_decision != "Accepted":
		frappe.throw(
			_("This signup has not been confirmed yet."), exc=session.InvalidSignupState
		)

	rename = _as_bool(use_submitted)
	doc.rename_account = 1 if rename else 0
	session.transition(doc, session.READY, save=True)
	log_event("name_choice", doc, use_submitted=rename)

	recovering = None
	if doc.resolution == linking.RECOVER_EXISTING:
		recovering = "accepted"

	data = {}
	if recovering:
		data["recovering"] = recovering
	if rename:
		data["notice"] = _(
			"Your account will use the name you just gave. We'll ask our team to "
			"check it against your customer record before changing that."
		)

	return session.envelope(
		doc,
		_("Almost there — just choose a password.") if not recovering
		else _("Welcome back — set a password and we'll sign you in."),
		data,
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=20, seconds=60 * 60, methods=["POST"])
def go_back(signup_id):
	"""Take back the answer given to the recognition card.

	Everything before the card is proof and cannot be undone here - the
	email and the phone stay verified, and this never returns anybody to a
	step where those could be changed. What it undoes is the *answer*: a
	yes or no given to a record, and the spelling chosen afterwards.

	It always lands back on the card itself rather than on the previous
	panel. There is no history to unwind that way, and "back" meaning one
	specific place every time is easier to trust than a stack: whatever
	was answered, the record is put in front of them again and they answer
	it afresh.

	A "no" opens a conflict for staff at the moment it is given, so taking
	the "no" back has to close that too - otherwise a mis-click would
	leave somebody a queue item about a decision that was never made.

	Args:
		signup_id: the opaque signup handle.

	Returns:
		The standard signup envelope, carrying the card again.

	Raises:
		session.InvalidSignupState: when there is no answer to take back.
	"""
	_assert_signup_available()
	doc = session.load(signup_id, expected_states=[session.MATCH_REVIEW, session.READY])

	if doc.user_decision not in session.ANSWERED:
		frappe.throw(
			_("There is nothing to go back to."), exc=session.InvalidSignupState
		)

	_withdraw_rejection(doc)
	doc.user_decision = "Pending"
	doc.resolution = ""
	doc.rename_account = 0
	session.transition(doc, session.MATCH_REVIEW, save=True)
	log_event("match_decision_withdrawn", doc)

	return session.envelope(
		doc,
		_("No problem — here is that record again."),
		{
			"recognition": matching.recognition_payload(
				doc, doc.match_result, doc.candidate_customer
			)
		},
	)


def _withdraw_rejection(doc):
	"""Close the conflict a "no" opened, now that the "no" is withdrawn.

	Deleted rather than marked resolved: it was never a real situation,
	only a click, and leaving a resolved row behind would put a decision
	in the audit trail that nobody made. The rest of the queue - anything
	raised by the matching itself - is untouched, because those describe
	what was found rather than what was answered.

	Args:
		doc: the Webshop Signup Session document.
	"""
	for name in frappe.get_all(
		"Webshop Identity Conflict",
		filters={"signup_session": doc.name, "status": ["in", ("Open", "In Review")]},
		pluck="name",
	):
		conflict = frappe.get_doc("Webshop Identity Conflict", name)
		remaining = [
			row for row in conflict.get("problems") or []
			if row.problem_type != "USER_REJECTED_MATCH"
		]
		if len(remaining) == len(conflict.get("problems") or []):
			continue

		# One conflict per signup now, so the rejection is a line on a
		# case that may be about other things too. Take the line away; the
		# case only goes with it when the rejection was all it held.
		if not remaining:
			frappe.delete_doc(
				"Webshop Identity Conflict", name, force=True, ignore_permissions=True
			)
			continue

		conflict.set("problems", remaining)
		if conflict.conflict_type == "USER_REJECTED_MATCH":
			conflict.conflict_type = remaining[0].problem_type
		conflict.flags.ignore_permissions = True
		conflict.save()


# ──────────────────────────────────────────────────────────────────────────
# Completion
# ──────────────────────────────────────────────────────────────────────────


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(key="signup_id", limit=10, seconds=60 * 60, methods=["POST"])
def complete(signup_id, password, confirm_password, redirect_to=None):
	"""Create the account and everything it needs, then sign the person in.

	Idempotent: calling it again on a finished signup returns the original
	outcome rather than building a second account.

	A password is required on every path, including signing back into an
	account that already has one. The card is shown for records that have
	no website account at all - a Customer and Contact that staff created,
	or that a previous order left behind - and those need one made, which
	needs a password. Where an account does exist, the person is replacing
	a password they could not remember, which is the reason they are here.

	Args:
		signup_id: the opaque signup handle.
		password: the chosen password.
		confirm_password: it again.
		redirect_to: a same-site path to land on.

	Returns:
		The standard signup envelope, with the redirect target.
	"""
	_assert_signup_available()
	doc = session.load(
		signup_id, expected_states=[session.READY, session.COMPLETED], for_update=True
	)

	target = _safe_redirect(redirect_to)

	if doc.status == session.COMPLETED:
		return session.envelope(
			doc, _("Your account is ready."), {"redirect_to": target, "already_completed": True}
		)

	_validate_password(doc, password, confirm_password)

	result = linking.finalize(doc, password)

	if result.get("blocked"):
		# Returned rather than raised so this request still commits the
		# block and its conflict record; see linking.finalize.
		return session.envelope(doc, _(ACCOUNT_EXISTS_MESSAGE))

	if getattr(frappe.local, "login_manager", None):
		frappe.local.login_manager.login_as(result["user"])

	if result.get("recovered"):
		# Not greeted by the name they typed: nothing was created, they
		# were let back into a record that already had a name of its own,
		# and using the typed one here would suggest otherwise.
		return session.envelope(
			doc, _("Welcome back — you're signed in."), {"redirect_to": target}
		)

	return session.envelope(
		doc,
		_("Welcome, {0}! Your account is ready.").format(doc.full_name),
		{"redirect_to": target},
	)


def _validate_password(doc, password, confirm_password):
	"""Check a chosen password before it is used.

	Args:
		doc: the Webshop Signup Session document, for the strength check's
			user context.
		password: the chosen password.
		confirm_password: it again.
	"""
	from frappe.auth import MAX_PASSWORD_SIZE
	from frappe.core.doctype.user.user import test_password_strength

	if not password or not confirm_password:
		frappe.throw(_("Please enter and confirm your password."), title=_("Missing Password"))

	if password != confirm_password:
		frappe.throw(_("The two passwords do not match."), title=_("Passwords Do Not Match"))

	if len(password.encode("utf-8")) > MAX_PASSWORD_SIZE:
		frappe.throw(_("That password is too long."), title=_("Invalid Password"))

	# The four rules the wizard shows beside the field, enforced here so
	# the guide is a preview of what the server does rather than a second
	# opinion. It used to be the latter: the server checked only zxcvbn,
	# so a five-character password passed while the guide said it should
	# not, and switching the site's password policy off left the server
	# enforcing nothing at all behind four green ticks.
	passwords.validate(password, passwords.personal_parts(doc))

	if cint(frappe.get_system_settings("enable_password_policy")):
		result = test_password_strength(
			password, user_data=(doc.full_name, None, None, doc.email_normalized, None)
		)
		feedback = result.get("feedback", {})
		if not feedback.get("password_policy_validation_passed", False):
			# Anything reaching here already satisfies the four rules the
			# guide shows, so repeating them - which this message used to
			# do - tells somebody to fix what they have just fixed. This
			# is the site's strength estimator finding a pattern the four
			# rules cannot describe: a keyboard run, a date, a word with
			# digits tacked on. Say that instead.
			#
			# Frappe's own handler would render zxcvbn's raw feedback as
			# English HTML, which is accurate and not something to put in
			# front of a shopper.
			frappe.throw(
				_(
					"That is still an easy password to guess — it follows a common "
					"pattern, like a run of digits or a word with numbers on the end. "
					"Try adding another word that has nothing to do with the first."
				),
				title=_("Choose a Stronger Password"),
			)


def _safe_redirect(redirect_to):
	"""Return a same-site relative path, defaulting to the shop.

	Args:
		redirect_to: the requested path, from an untrusted source.

	Returns:
		A safe relative path.
	"""
	if not redirect_to or not isinstance(redirect_to, str):
		return "/shop"

	clean = redirect_to.strip()
	if clean.startswith("/") and not clean.startswith("//") and not clean.startswith("/app"):
		return clean

	return "/shop"
