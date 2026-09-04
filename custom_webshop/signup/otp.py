# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""One-time passcodes for signup email and phone verification.

Storage
-------
Only a keyed HMAC of the code is ever written down, on the signup session
row itself. The plaintext exists in memory long enough to be handed to a
sender and is never logged, never returned to the browser, and never put
in Redis.

The HMAC is keyed with the site's own `encryption_key`, which lives in
site_config.json and not in the database - so a database dump alone does
not let an attacker pre-compute the 10^6 possible six-digit hashes.

Why the session row and not Redis
---------------------------------
`frappe.cache` swallows a Redis `ConnectionError` and silently returns
None (frappe/utils/redis_wrapper.py). An OTP store that can quietly fail
open is the wrong shape for the one thing standing between a stranger and
somebody's order history: with the state on the row, issuing and verifying
share the request transaction and either both happen or neither does.
Redis is still used for rate limiting, where degrading open is acceptable.
"""

import hmac
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime

from custom_webshop.signup import settings

EMAIL = "email"
PHONE = "phone"
CHANNELS = (EMAIL, PHONE)


class OTPInvalid(frappe.ValidationError):
	pass


class OTPAttemptsExhausted(frappe.ValidationError):
	pass


class OTPCooldown(frappe.ValidationError):
	pass


class OTPSendLimitReached(frappe.ValidationError):
	pass


def _field(channel, suffix):
	"""Return the session fieldname holding `suffix` for a channel.

	Args:
		channel: "email" or "phone".
		suffix: the field suffix, e.g. "otp_hash".

	Returns:
		The fieldname string.
	"""
	if channel not in CHANNELS:
		raise ValueError(f"unknown OTP channel: {channel}")
	return f"{channel}_{suffix}"


def _digest(code, doc, channel):
	"""Return the stored form of a code.

	Bound to both the signup id and the channel, so a code issued for the
	email step cannot be replayed against the phone step of the same
	signup, and a hash lifted from one row is meaningless against another.

	Args:
		code: the plaintext code.
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".

	Returns:
		A hex HMAC-SHA256 digest.
	"""
	from frappe.utils.password import get_encryption_key

	message = f"{doc.signup_id}:{channel}:{code}".encode()
	return hmac.new(get_encryption_key().encode(), message, "sha256").hexdigest()


def generate_code(length=None):
	"""Return a fresh numeric passcode.

	Uses `secrets` rather than pyotp: an HOTP code would need its own
	per-session secret and counter persisted on the row anyway, and buys
	nothing over a random number whose hash we already store. Six digits
	against five attempts and a five-send cap gives an attacker at most 25
	guesses in 10^6, and a code that is destroyed the moment it is used.

	Args:
		length: number of digits; falls back to the configured OTP length.

	Returns:
		The code, zero-padded to `length`.
	"""
	length = cint(length or settings.get_int("otp_length"))
	return str(secrets.randbelow(10**length)).zfill(length)


def issue(doc, channel):
	"""Mint a code for a channel and record it on the session.

	Enforces the resend cooldown and the per-channel send cap before
	issuing. Issuing overwrites any previous hash, which is what makes an
	older code stop working the instant a newer one is sent.

	The caller is responsible for saving the document and for delivering
	the returned code.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".

	Returns:
		The plaintext code, for the sender only.

	Raises:
		OTPCooldown: a code was sent too recently.
		OTPSendLimitReached: the per-channel cap is spent.
	"""
	now = now_datetime()
	last_sent = doc.get(_field(channel, "otp_last_sent_at"))
	cooldown = settings.get_int("otp_resend_cooldown_seconds")

	if last_sent and cooldown:
		elapsed = (now - last_sent).total_seconds()
		if elapsed < cooldown:
			frappe.throw(
				_("Please wait {0} seconds before requesting another code.").format(
					int(cooldown - elapsed) + 1
				),
				exc=OTPCooldown,
				title=_("Please Wait"),
			)

	sends = cint(doc.get(_field(channel, "otp_sends")))
	if sends >= settings.get_int("otp_max_sends_per_channel"):
		frappe.throw(
			_("Too many codes have been sent. Please start again."),
			exc=OTPSendLimitReached,
			title=_("Limit Reached"),
		)

	code = generate_code()

	doc.set(_field(channel, "otp_hash"), _digest(code, doc, channel))
	doc.set(
		_field(channel, "otp_expires_at"),
		add_to_date(now, seconds=settings.get_int("otp_ttl_seconds")),
	)
	# A fresh code gets a fresh attempt budget; without this reset an
	# attacker could exhaust the budget once and lock the real owner out
	# of every subsequent code too.
	doc.set(_field(channel, "otp_attempts"), 0)
	doc.set(_field(channel, "otp_sends"), sends + 1)
	doc.set(_field(channel, "otp_last_sent_at"), now)

	return code


def verify(doc, channel, code):
	"""Check a submitted code and mark the channel verified on success.

	A wrong code and an expired code produce the identical error, so the
	endpoint cannot be used to learn whether a code is still live. A
	successful check clears the hash, so the same code cannot be replayed.

	The caller is responsible for saving the document.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".
		code: the submitted code.

	Raises:
		OTPAttemptsExhausted: the attempt budget for this code is spent.
		OTPInvalid: wrong, expired, or no code outstanding.
	"""
	stored = doc.get(_field(channel, "otp_hash"))
	expires_at = doc.get(_field(channel, "otp_expires_at"))
	attempts = cint(doc.get(_field(channel, "otp_attempts")))
	max_attempts = settings.get_int("otp_max_attempts")

	if attempts >= max_attempts:
		frappe.throw(
			_("Too many incorrect attempts. Please request a new code."),
			exc=OTPAttemptsExhausted,
			title=_("Too Many Attempts"),
		)

	# Count the attempt before deciding anything, so a caller that dies
	# mid-verify cannot be used to get free guesses.
	doc.set(_field(channel, "otp_attempts"), attempts + 1)

	submitted = (code or "").strip()
	expired = not expires_at or expires_at < now_datetime()

	# Always run the comparison, even when there is nothing to compare
	# against or the code has expired, so the work done is the same in
	# every failing branch.
	candidate = _digest(submitted, doc, channel) if submitted else ""
	matched = bool(stored) and bool(candidate) and hmac.compare_digest(stored, candidate)

	if not matched or expired:
		if attempts + 1 >= max_attempts:
			# Budget spent: destroy the code outright rather than leaving
			# a dead hash around for the next request to grind against.
			doc.set(_field(channel, "otp_hash"), None)
			doc.set(_field(channel, "otp_expires_at"), None)

		_persist_failed_attempt(doc, channel)
		frappe.throw(
			_("That code is not correct. Please check it and try again."),
			exc=OTPInvalid,
			title=_("Incorrect Code"),
		)

	doc.set(_field(channel, "otp_hash"), None)
	doc.set(_field(channel, "otp_expires_at"), None)
	doc.set(_field(channel, "otp_attempts"), 0)
	doc.set(f"{channel}_verified", 1)


def _persist_failed_attempt(doc, channel):
	"""Write a spent attempt so the exception that follows cannot undo it.

	This is load-bearing, not defensive. `verify` reports a wrong code by
	raising, and Frappe rolls the whole request transaction back on an
	unhandled exception - so the attempt counter incremented moments
	earlier was discarded along with it, and every guess arrived at a
	session that still showed zero attempts and a live code. The five-guess
	cap existed only inside a single request and did nothing at all across
	HTTP, which is the only way an attacker would ever use it.

	Committing here is safe: by this point a verify request has written
	nothing else, so this commits the counter and nothing besides. The
	columns are written directly rather than through a document save so
	that exactly these three change, and `update_modified=False` keeps the
	caller's own `doc.save()` from tripping a timestamp mismatch.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".
	"""
	frappe.db.set_value(
		"Webshop Signup Session",
		doc.name,
		{
			_field(channel, "otp_attempts"): doc.get(_field(channel, "otp_attempts")),
			_field(channel, "otp_hash"): doc.get(_field(channel, "otp_hash")),
			_field(channel, "otp_expires_at"): doc.get(_field(channel, "otp_expires_at")),
		},
		update_modified=False,
	)
	frappe.db.commit()


def reset(doc, channel):
	"""Invalidate a channel's code and its verified flag.

	Called when the user changes the address or number behind a channel:
	the old value stops counting as verified immediately, and its
	outstanding code stops working.

	The send counter is deliberately *not* reset - otherwise changing the
	email back and forth would be an unlimited supply of messages to any
	address an attacker chose.

	The cooldown *is* cleared, though. It exists to stop one address being
	mail-bombed, and this is a different address: somebody who mistyped
	their email should not be told to wait a minute before they may
	correct it. The per-session send cap, which is not reset, remains the
	control that actually bounds how many messages a signup can generate.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".
	"""
	doc.set(_field(channel, "otp_hash"), None)
	doc.set(_field(channel, "otp_expires_at"), None)
	doc.set(_field(channel, "otp_attempts"), 0)
	doc.set(_field(channel, "otp_last_sent_at"), None)
	doc.set(f"{channel}_verified", 0)


def seconds_until_resend(doc, channel):
	"""Return how long the browser should keep the resend button disabled.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".

	Returns:
		Whole seconds remaining, or 0.
	"""
	last_sent = doc.get(_field(channel, "otp_last_sent_at"))
	cooldown = settings.get_int("otp_resend_cooldown_seconds")
	if not last_sent or not cooldown:
		return 0

	remaining = cooldown - (now_datetime() - last_sent).total_seconds()
	return max(0, int(remaining) + 1) if remaining > 0 else 0


def sends_remaining(doc, channel):
	"""Return how many more codes may be sent on this channel.

	Args:
		doc: the Webshop Signup Session document.
		channel: "email" or "phone".

	Returns:
		A non-negative count.
	"""
	used = cint(doc.get(_field(channel, "otp_sends")))
	return max(0, settings.get_int("otp_max_sends_per_channel") - used)
