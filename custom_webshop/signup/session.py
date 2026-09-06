# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""The signup state machine.

Every rule about what a signup may do next lives in this one module, in
`ALLOWED_TRANSITIONS`, rather than being spread across endpoint bodies -
so "can a signup jump straight from STARTED to COMPLETED?" is answered by
reading one table instead of auditing nine functions.

Browser binding
---------------
A signup is addressed by an opaque `signup_id`, but possessing that id is
deliberately *not* sufficient to drive the flow. On `start` the server
mints a second secret, hands it to the browser in an httpOnly cookie, and
stores only its SHA-256. Every later call must present the cookie.

The obvious alternative - binding to `frappe.session.sid` - does nothing
here: `Session.start_as_guest` documents that "all guests share the same
'Guest' session", so every anonymous visitor on the site carries the
identical sid. Verified by reading frappe/sessions.py:251-258.
"""

import hashlib
import hmac
import json

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime

from custom_webshop.signup import settings

SIGNUP_COOKIE = "webshop_signup"

STARTED = "STARTED"
EMAIL_PENDING = "EMAIL_PENDING"
EMAIL_VERIFIED = "EMAIL_VERIFIED"
PHONE_PENDING = "PHONE_PENDING"
PHONE_VERIFIED = "PHONE_VERIFIED"
MATCH_REVIEW = "MATCH_REVIEW"
READY = "READY"
COMPLETED = "COMPLETED"
BLOCKED = "BLOCKED"
EXPIRED = "EXPIRED"
CANCELLED = "CANCELLED"

TERMINAL_STATES = frozenset({COMPLETED, BLOCKED, EXPIRED, CANCELLED})

# How the phone OTP is delivered for a signup. Chosen once (at `start`, or
# by `switch_phone_otp_channel` mid-flow) and persisted on the row, so it
# survives resend and a page reload the same way `phone`/`phone_country` do.
PHONE_OTP_SMS = "SMS"
PHONE_OTP_WHATSAPP = "WhatsApp"
PHONE_OTP_CHANNELS = (PHONE_OTP_SMS, PHONE_OTP_WHATSAPP)

# Every state a signup may move to from a given state. A state absent from
# a row's value is an invalid transition and raises. Terminal states have
# no outgoing edges at all, which is what makes "STARTED -> COMPLETED"
# structurally impossible rather than merely unlikely.
#
# EMAIL_PENDING appears in most rows because "change email" is offered at
# every later step and always sends the signup back to re-verify. Same for
# PHONE_PENDING and "change phone".
#
# BLOCKED is reachable from exactly two states, and that is the point.
# Every "you already have an account" verdict is reached at PHONE_VERIFIED
# (by `resolve`) or at READY (by the re-check inside `finalize`), never
# while a channel is still unproven - so the answer is only ever given to
# somebody who has proved control of *both* the address and the number,
# and there is no earlier step whose response could be diffed to learn it.
# A signup cannot be blocked before it is fully verified; the table is
# what enforces that, not the endpoints' good behaviour.
ALLOWED_TRANSITIONS = {
	STARTED: {EMAIL_PENDING, CANCELLED, EXPIRED},
	EMAIL_PENDING: {EMAIL_PENDING, EMAIL_VERIFIED, CANCELLED, EXPIRED},
	EMAIL_VERIFIED: {EMAIL_PENDING, PHONE_PENDING, CANCELLED, EXPIRED},
	PHONE_PENDING: {EMAIL_PENDING, PHONE_PENDING, PHONE_VERIFIED, CANCELLED, EXPIRED},
	PHONE_VERIFIED: {
		EMAIL_PENDING,
		PHONE_PENDING,
		MATCH_REVIEW,
		READY,
		BLOCKED,
		CANCELLED,
		EXPIRED,
	},
	MATCH_REVIEW: {MATCH_REVIEW, READY, CANCELLED, EXPIRED},
	READY: {MATCH_REVIEW, READY, COMPLETED, BLOCKED, CANCELLED, EXPIRED},
	COMPLETED: set(),
	BLOCKED: set(),
	EXPIRED: set(),
	CANCELLED: set(),
}

# What the browser is allowed to do next. The frontend renders from this
# rather than deciding for itself, so the backend stays the authority on
# the shape of the flow.
#: The two values of `user_decision` that mean somebody actually
#: answered the card. The field starts at "Pending".
ANSWERED = ("Accepted", "Rejected")

ALLOWED_ACTIONS = {
	STARTED: [],
	EMAIL_PENDING: ["verify_email", "resend_email_otp", "change_email", "cancel"],
	EMAIL_VERIFIED: ["send_phone_otp", "change_email", "switch_phone_otp_channel", "cancel"],
	PHONE_PENDING: [
		"verify_phone",
		"resend_phone_otp",
		"change_phone",
		"switch_phone_otp_channel",
		"cancel",
	],
	PHONE_VERIFIED: ["resolve", "change_phone", "cancel"],
	MATCH_REVIEW: ["decide", "cancel"],
	READY: ["complete", "cancel"],
	COMPLETED: [],
	BLOCKED: ["restart"],
	EXPIRED: ["restart"],
	CANCELLED: ["restart"],
}


class InvalidSignupState(frappe.ValidationError):
	http_status_code = 409


class SignupNotFound(frappe.ValidationError):
	http_status_code = 404


class SignupExpired(frappe.ValidationError):
	http_status_code = 410


# ──────────────────────────────────────────────────────────────────────────
# Browser binding
# ──────────────────────────────────────────────────────────────────────────


def _hash_secret(secret):
	"""Return the stored form of a binding secret.

	Args:
		secret: the raw secret from the browser cookie.

	Returns:
		Its hex SHA-256, or "" for a blank secret.
	"""
	if not secret:
		return ""
	return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _issue_binding_secret():
	"""Mint a binding secret, hand it to the browser, and return its hash.

	The raw secret is written to an httpOnly cookie, so page JavaScript
	cannot read it back out - an XSS that steals the `signup_id` from
	sessionStorage still cannot drive the signup without it.

	Returns:
		The SHA-256 of the issued secret, to store on the session row.
	"""
	secret = frappe.generate_hash()

	cookie_manager = getattr(frappe.local, "cookie_manager", None)
	if cookie_manager:
		cookie_manager.set_cookie(
			SIGNUP_COOKIE,
			secret,
			httponly=True,
			samesite="Lax",
			max_age=settings.get_int("session_ttl_minutes") * 60,
		)

	# Also stashed on the request-local flags so the value is readable
	# within this same request (a cookie only comes back on the *next*
	# one) and so tests and CLI callers have a seam to drive.
	frappe.local.flags.webshop_signup_secret = secret
	return _hash_secret(secret)


def _presented_secret():
	"""Return the binding secret this caller presented, if any.

	Returns:
		The raw secret string, or None.
	"""
	if getattr(frappe.local, "request", None):
		from_cookie = frappe.request.cookies.get(SIGNUP_COOKIE)
		if from_cookie:
			return from_cookie

	return frappe.local.flags.get("webshop_signup_secret")


def _clear_binding_cookie():
	"""Drop the signup cookie once the flow has reached a terminal state."""
	cookie_manager = getattr(frappe.local, "cookie_manager", None)
	if cookie_manager:
		cookie_manager.delete_cookie(SIGNUP_COOKIE)
	frappe.local.flags.webshop_signup_secret = None


# ──────────────────────────────────────────────────────────────────────────
# Lifecycle
# ──────────────────────────────────────────────────────────────────────────


def create(
	account_type,
	full_name,
	company_name,
	email,
	email_normalized,
	phone_raw,
	phone_e164,
	phone_country=None,
	phone_otp_channel=None,
):
	"""Insert a new signup session in STARTED.

	Creates no ERPNext record of any kind - a signup abandoned from here
	leaves nothing behind but this row, which the daily purge removes.

	Args:
		account_type: "Individual" or "Company".
		full_name: the validated full name.
		company_name: the company name, for a Company signup.
		email: the address as typed, kept for display.
		email_normalized: its canonical form.
		phone_raw: the number as typed, kept for display.
		phone_e164: its canonical form.
		phone_otp_channel: "SMS" or "WhatsApp", the phone OTP delivery
			channel to use for the whole flow. Never trusted blindly from
			the client - anything other than a recognised value falls back
			to "SMS", the same way an unrecognised `phone_country` falls
			back to the configured default region.

	Returns:
		The inserted Webshop Signup Session document.
	"""
	if phone_otp_channel not in PHONE_OTP_CHANNELS:
		phone_otp_channel = PHONE_OTP_SMS

	doc = frappe.new_doc("Webshop Signup Session")
	doc.update(
		{
			"signup_id": frappe.generate_hash(),
			"status": STARTED,
			"account_type": account_type,
			"full_name": full_name,
			"company_name": company_name,
			"email": email,
			"email_normalized": email_normalized,
			"phone_raw": phone_raw,
			"phone_country": phone_country,
			"phone_e164": phone_e164,
			"phone_otp_channel": phone_otp_channel,
			"binding_hash": _issue_binding_secret(),
			"expires_at": _new_expiry(),
			"ip_address": getattr(frappe.local, "request_ip", None),
			"user_agent": _user_agent(),
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc


def _user_agent():
	"""Return a truncated User-Agent string for the audit trail."""
	request = getattr(frappe.local, "request", None)
	if not request:
		return None
	return (request.headers.get("User-Agent") or "")[:500]


def _new_expiry():
	"""Return the expiry timestamp for a step that just succeeded."""
	return add_to_date(now_datetime(), minutes=settings.get_int("session_ttl_minutes"))


def load(signup_id, expected_states=None, for_update=False):
	"""Fetch a signup session, authorise the caller, and enforce expiry.

	Args:
		signup_id: the opaque handle from the request.
		expected_states: an iterable of states this endpoint accepts; None
			to accept any non-terminal state.
		for_update: take a row lock, for the finalise path.

	Returns:
		The Webshop Signup Session document.

	Raises:
		SignupNotFound: no such signup, or the wrong browser.
		SignupExpired: past its expiry.
		InvalidSignupState: not in a state this endpoint accepts.
	"""
	if not signup_id or not isinstance(signup_id, str):
		frappe.throw(_("This signup could not be found. Please start again."), exc=SignupNotFound)

	name = frappe.db.get_value(
		"Webshop Signup Session", {"signup_id": signup_id}, "name", for_update=for_update
	)
	if not name:
		frappe.throw(_("This signup could not be found. Please start again."), exc=SignupNotFound)

	doc = frappe.get_doc("Webshop Signup Session", name)

	# Constant-time comparison, and a deliberately identical error to the
	# not-found case: an attacker holding a guessed signup_id must not be
	# able to tell "no such signup" from "right signup, wrong browser".
	if not hmac.compare_digest(doc.binding_hash or "", _hash_secret(_presented_secret())):
		frappe.throw(_("This signup could not be found. Please start again."), exc=SignupNotFound)

	if doc.status not in TERMINAL_STATES and _is_expired(doc):
		_mark_expired(doc)
		frappe.throw(_("This signup has expired. Please start again."), exc=SignupExpired)

	if expected_states is not None and doc.status not in expected_states:
		frappe.throw(
			_("This step is not available right now. Please continue where you left off."),
			exc=InvalidSignupState,
		)

	return doc


def _is_expired(doc):
	"""Return True when the session's expiry has passed."""
	return bool(doc.expires_at) and doc.expires_at < now_datetime()


def _mark_expired(doc):
	"""Record the expiry so it survives the exception that follows it.

	The obvious version of this - transition to EXPIRED, then throw - does
	not work. Frappe rolls the whole request transaction back on an
	unhandled exception, so the status write is discarded and the session
	is found in its old state again on the next request, forever. Only the
	daily purge would ever correct it.

	Committing here is safe specifically because `load` is the first thing
	every endpoint does: nothing else has been written yet, so this commits
	the expiry and nothing besides. It is written with `db.set_value`
	rather than a document save to keep it to exactly that one column.

	Args:
		doc: the Webshop Signup Session document.
	"""
	frappe.db.set_value(
		"Webshop Signup Session", doc.name, "status", EXPIRED, update_modified=False
	)
	frappe.db.commit()
	doc.status = EXPIRED


def transition(doc, to_state, save=False):
	"""Move a session to a new state, or refuse.

	Args:
		doc: the Webshop Signup Session document.
		to_state: the target state.
		save: persist immediately (callers batching several field changes
			pass False and save once).

	Raises:
		InvalidSignupState: if the move is not in ALLOWED_TRANSITIONS.
	"""
	allowed = ALLOWED_TRANSITIONS.get(doc.status, set())
	if to_state not in allowed:
		frappe.throw(
			_("Cannot move a signup from {0} to {1}.").format(doc.status, to_state),
			exc=InvalidSignupState,
			title=_("Invalid Signup State"),
		)

	doc.status = to_state

	# The binding cookie is dropped where the person is expected to start
	# over, but deliberately *kept* on COMPLETED. `complete` has to stay
	# idempotent - a double-clicked button or a retried request must get
	# the original outcome back, not an error - and it cannot re-read the
	# session without the cookie that authorises it. Keeping it costs
	# nothing: every endpoint refuses a COMPLETED session except
	# `complete` and `get_state`, which only return what the caller has
	# already been told.
	if to_state in (CANCELLED, EXPIRED):
		_clear_binding_cookie()
	elif to_state not in TERMINAL_STATES:
		doc.expires_at = _new_expiry()

	if save:
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)


def touch(doc):
	"""Extend a session's expiry without changing its state.

	Args:
		doc: the Webshop Signup Session document.
	"""
	doc.expires_at = _new_expiry()


def block(doc, match_result, reason):
	"""Send a signup to BLOCKED with a recorded reason.

	Args:
		doc: the Webshop Signup Session document.
		match_result: the classification that caused the block.
		reason: staff-facing explanation, stored for the audit trail.
	"""
	doc.match_result = match_result
	doc.block_reason = reason
	transition(doc, BLOCKED, save=True)


# ──────────────────────────────────────────────────────────────────────────
# API envelope
# ──────────────────────────────────────────────────────────────────────────


def actions_for(doc):
	"""What this particular signup may do next.

	`ALLOWED_ACTIONS` answers that for a *state*; two sessions in the same
	state can still differ in one way, so this adds it.

	Going back is only offered to somebody who was actually asked
	something. A signup that matched nobody, or whose result was recorded
	for staff without a question, has no answer to take back - offering
	"back" there would suggest the verified email and phone could be
	changed, which they cannot. Having answered a card is exactly what
	`user_decision` records - which starts at "Pending" rather than
	empty, so it is the two real answers that are looked for.

	Args:
		doc: the Webshop Signup Session document.

	Returns:
		A list of action names.
	"""
	actions = list(ALLOWED_ACTIONS.get(doc.status, []))
	if doc.status in (MATCH_REVIEW, READY) and doc.user_decision in ANSWERED:
		actions.append("go_back")
	return actions


def envelope(doc, message=None, data=None):
	"""Build the single response shape every signup endpoint returns.

	Carries the server's view of the flow - current state and the actions
	permitted from it - so the browser renders what it is told rather than
	deciding what is possible.

	Args:
		doc: the Webshop Signup Session document.
		message: a translated, user-safe message.
		data: extra payload; must never contain a Customer identifier.

	Returns:
		A dict safe to serialise to the browser.
	"""
	return {
		"signup_id": doc.signup_id,
		"state": doc.status,
		"allowed_actions": actions_for(doc),
		"account_type": doc.account_type,
		"email": doc.email,
		"phone": doc.phone_raw,
		"phone_country": doc.phone_country,
		"phone_otp_channel": doc.phone_otp_channel or PHONE_OTP_SMS,
		"email_verified": bool(doc.email_verified),
		"phone_verified": bool(doc.phone_verified),
		"message": message or "",
		"data": data or {},
	}


def set_candidates(doc, candidates):
	"""Record the matching engine's candidate list for the audit trail.

	Args:
		doc: the Webshop Signup Session document.
		candidates: a list of plain dicts describing each candidate.
	"""
	doc.candidate_customers = json.dumps(candidates, ensure_ascii=False, indent=1)[:140000]


# ──────────────────────────────────────────────────────────────────────────
# Housekeeping
# ──────────────────────────────────────────────────────────────────────────


def expire_stale_sessions():
	"""Scheduled daily: expire elapsed sessions and purge old dead ones.

	Expiring is a bulk `db.set_value` rather than a document save per row:
	these are dead sessions, nothing observes their transition, and a save
	loop over a large backlog would be pointlessly slow. Conflict records
	are never touched - they are the durable audit trail and outlive the
	sessions that produced them.
	"""
	now = now_datetime()

	frappe.db.sql(
		"""
		UPDATE `tabWebshop Signup Session`
		SET status = %(expired)s, modified = %(now)s
		WHERE status NOT IN %(terminal)s AND expires_at IS NOT NULL AND expires_at < %(now)s
		""",
		{"expired": EXPIRED, "now": now, "terminal": tuple(TERMINAL_STATES)},
	)

	cutoff = add_to_date(now, days=-cint(settings.get_int("session_retention_days")))
	frappe.db.sql(
		"""
		DELETE FROM `tabWebshop Signup Session`
		WHERE status IN (%(expired)s, %(cancelled)s) AND modified < %(cutoff)s
		""",
		{"expired": EXPIRED, "cancelled": CANCELLED, "cutoff": cutoff},
	)
