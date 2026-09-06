# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""HTTP client for sending WhatsApp text messages through Evolution API.

Kept separate from `notifications.py` so that adjusting to the exact
contract of a deployed Evolution API instance - the endpoint path, the
payload shape, the auth header - is a one-file change, isolated from the
OTP delivery/fail-closed logic that wraps it.

Contract assumed here - this is Evolution API's commonly documented
send-text shape, but forks and versions have varied it (some wrap the text
under `textMessage.text`, or expect the number without its leading `+`),
so this MUST be verified against the actual deployed instance (its own
Swagger/API docs) before depending on this in production:

    POST {base_url}/message/sendText/{instance}
    Headers: apikey: <api key>
    Body:    {"number": "<digits, no leading +>", "text": "<message>"}

If the deployed instance differs, `_build_request` is the only place that
needs to change.
"""


class WhatsAppSendError(Exception):
	"""Raised when Evolution API could not be reached or refused the send."""


def _build_request(base_url, instance, api_key, phone_e164, message):
	"""Build the URL, headers and payload for a send-text call.

	Args:
		base_url: Evolution API server base URL, with or without a
			trailing slash.
		instance: the Evolution API instance name.
		api_key: the instance's API key.
		phone_e164: destination number, E.164 format (leading +).
		message: the message body.

	Returns:
		A (url, headers, payload) tuple.
	"""
	from urllib.parse import quote

	# Instance names can contain spaces or other characters that are not
	# valid unescaped in a URL path segment (e.g. "ahmed amin1") - left as
	# plain f-string interpolation, a space here produces a malformed
	# request that Evolution API can't route, and the send never lands
	# with no error raised on this side to say so.
	url = f"{base_url.rstrip('/')}/message/sendText/{quote(str(instance), safe='')}"
	headers = {"apikey": api_key, "Content-Type": "application/json"}
	# Evolution API's documented send-text contract takes the destination
	# without the leading '+' - phone_e164 always carries one (identity.to_e164
	# guarantees this), so it is stripped here rather than upstream, keeping
	# the canonical E.164 form intact everywhere else in the signup flow.
	payload = {"number": phone_e164.lstrip("+"), "text": message}
	return url, headers, payload


def send_text(base_url, instance, api_key, phone_e164, message, timeout):
	"""Send a WhatsApp text message through Evolution API.

	No retry: a failed send is reported to the caller, which decides what
	to do (the signup OTP flow fails closed, same as SMS).

	Args:
		base_url: Evolution API server base URL.
		instance: the Evolution API instance name.
		api_key: the instance's API key.
		phone_e164: destination number, E.164 format.
		message: the message body.
		timeout: request timeout in seconds.

	Raises:
		WhatsAppSendError: on any network failure, timeout, or a
			non-2xx/error response.
	"""
	import requests

	url, headers, payload = _build_request(base_url, instance, api_key, phone_e164, message)

	try:
		response = requests.post(url, json=payload, headers=headers, timeout=timeout)
		response.raise_for_status()
	except requests.RequestException as exc:
		raise WhatsAppSendError(str(exc)) from exc
