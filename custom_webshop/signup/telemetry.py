# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Structured logging for the signup flow.

One line per meaningful event, written to `logs/custom_webshop.signup.log`
via Frappe's own site logger. Two rules hold everywhere:

* Secrets never appear. `REDACTED_KEYS` is applied to every field of every
  event, so a caller cannot leak a passcode or password by accident.
* Contact details appear masked. A log that quietly accumulates the email
  and phone of everyone who ever started a signup is its own liability.

`log_dev_otp` is the single sanctioned exception, gated on the
`otp_dev_mode` setting whose own description says never to turn it on in
production.
"""

import logging

import frappe

from custom_webshop.signup.identity import mask_email, mask_phone

LOGGER_NAME = "custom_webshop.signup"

# Anything whose name looks like a secret is replaced before it is
# written, whatever the caller passed.
REDACTED_KEYS = frozenset(
	{
		"otp",
		"code",
		"pwd",
		"password",
		"new_password",
		"confirm_pwd",
		"otp_hash",
		"email_otp_hash",
		"phone_otp_hash",
		"binding_hash",
		"secret",
		"signup_secret",
	}
)


def get_logger():
	"""Return the signup logger, with its level pinned to INFO.

	Frappe's own default is WARNING on a dev server and ERROR anywhere
	else (frappe/utils/logger.py:12), so without this every event below
	would be discarded in production - silently, which is the worst way
	for an audit trail to fail. These events are low-volume and
	security-relevant: one line per state change on a signup, a few dozen
	a day on a shop this size.

	An operator who explicitly raises the level for the whole bench, via
	the `logging` site-config key, still wins - that is a deliberate
	choice, unlike the default.

	Returns:
		A logging.Logger writing to this site's custom_webshop.signup log.
	"""
	logger = frappe.logger(LOGGER_NAME, allow_site=True)
	if frappe.log_level is None:
		logger.setLevel(logging.INFO)
	return logger


def _scrub(fields):
	"""Replace anything secret-shaped in an event payload.

	Args:
		fields: the caller's key/value pairs.

	Returns:
		A safe copy.
	"""
	return {
		key: ("***" if key in REDACTED_KEYS else value) for key, value in (fields or {}).items()
	}


def log_event(event, doc=None, **fields):
	"""Record one signup event.

	Args:
		event: a short stable event name, e.g. "signup_started".
		doc: the Webshop Signup Session document, if there is one.
		**fields: extra context; secret-named keys are redacted.
	"""
	payload = {"event": event}

	if doc is not None:
		payload.update(
			{
				"signup_id": doc.get("signup_id"),
				"state": doc.get("status"),
				"account_type": doc.get("account_type"),
				"email": mask_email(doc.get("email_normalized")),
				"phone": mask_phone(doc.get("phone_e164")),
				"match_result": doc.get("match_result"),
				"resolution": doc.get("resolution"),
			}
		)

	payload.update(_scrub(fields))

	try:
		get_logger().info(payload)
	except Exception:
		# Telemetry must never be the reason a signup fails.
		pass


def log_transition(doc, from_state, to_state, **fields):
	"""Record a state change.

	Args:
		doc: the Webshop Signup Session document.
		from_state: the state being left.
		to_state: the state being entered.
		**fields: extra context.
	"""
	log_event("signup_transition", doc, from_state=from_state, to_state=to_state, **fields)


def log_dev_otp(channel, destination, code):
	"""Write a passcode to the log. Only ever called under otp_dev_mode.

	Args:
		channel: "email" or "phone".
		destination: the raw address or number; masked before writing.
		code: the plaintext passcode.
	"""
	masked = mask_email(destination) if channel == "email" else mask_phone(destination)
	get_logger().warning(
		{
			"event": "otp_dev_mode_not_sent",
			"channel": channel,
			"destination": masked,
			"code": code,
		}
	)
