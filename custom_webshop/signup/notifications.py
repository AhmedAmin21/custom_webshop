# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Delivery of signup passcodes over email, SMS and WhatsApp.

Every sender here fails *closed*: if a code cannot be delivered, the
caller is told so and the surrounding transaction rolls back, rather than
leaving a signup stuck waiting for a message that will never arrive.

Dev mode is the exception and the reason it exists: on a site with no
outgoing Email Account and no SMS/WhatsApp gateway - which is the state of
this bench today - `email_otp_dev_mode`/`phone_otp_dev_mode`/
`whatsapp_otp_dev_mode` write the code to the site log instead of sending
it, so the whole flow is exercisable end to end before any of that
infrastructure is configured. The flags are independent, so one channel
can go live in production while another stays in dev mode until its own
infrastructure is ready.

Phone OTPs are sent by SMS (`send_phone_otp`) or WhatsApp
(`send_whatsapp_otp`) depending on the signup session's
`phone_otp_channel` - the choice of which function to call lives in
`custom_webshop.api.signup`, not here; both functions are self-contained
and neither knows the other exists.
"""

import frappe
from frappe import _

from custom_webshop.signup import settings, whatsapp
from custom_webshop.signup.telemetry import log_dev_otp

EMAIL_TEMPLATE = "custom_webshop/templates/emails/signup_otp.html"
WELCOME_EMAIL_TEMPLATE = "custom_webshop/templates/emails/custom_welcome_email.html"


class OTPDeliveryFailed(frappe.ValidationError):
	pass


def _site_name():
	"""Return a human-facing name for this shop, for message copy."""
	return (
		frappe.db.get_default("site_name")
		or frappe.get_conf().get("site_name")
		or frappe.db.get_default("company")
		or "CNCLeaders"
	)


def _deliver_in_dev_mode(channel, destination, code):
	"""Write a passcode to the site log instead of sending it.

	This is the one place a plaintext code is ever written down, and it is
	gated on an explicit setting whose description says never to enable it
	in production. The destination is masked even here.

	Args:
		channel: "email" or "phone".
		destination: the address or number, for masked display.
		code: the plaintext passcode.
	"""
	log_dev_otp(channel, destination, code)


def send_email_otp(doc, code):
	"""Email a passcode to the address on a signup session.

	Args:
		doc: the Webshop Signup Session document.
		code: the plaintext passcode.

	Raises:
		OTPDeliveryFailed: if the site cannot send mail.
	"""
	if settings.is_enabled("email_otp_dev_mode"):
		_deliver_in_dev_mode("email", doc.email, code)
		return

	context = {
		"full_name": doc.full_name,
		"code": code,
		"site_name": _site_name(),
		"validity_minutes": max(1, settings.get_int("otp_ttl_seconds") // 60),
	}

	try:
		frappe.sendmail(
			recipients=[doc.email],
			subject=_("{0} is your verification code").format(code),
			message=frappe.render_template(EMAIL_TEMPLATE, context),
			# Immediate and undelayed: a passcode that sits in the Email
			# Queue until the next scheduler tick has already expired by
			# the time it arrives.
			now=True,
			delayed=False,
			retry=1,
		)
	except Exception:
		frappe.log_error("custom_webshop: signup email OTP delivery failed")
		frappe.throw(
			_("We could not send the verification email. Please try again shortly."),
			exc=OTPDeliveryFailed,
			title=_("Email Not Sent"),
		)


def send_welcome_email(user_email, full_name):
	"""Email a welcome message to a newly created account.

	Best-effort, like `_send_order_email` in cart_override.py: a missed
	welcome email must never undo or block account creation, so a failure
	here is logged and swallowed rather than raised.

	Args:
		user_email: the new account's email address.
		full_name: the person's full name, for greeting and salutation.
	"""
	first_name = (full_name or "").split(" ")[0] or full_name
	context = {
		"full_name": full_name,
		"first_name": first_name,
		"site_name": _site_name(),
		"site_url": frappe.utils.get_url(),
	}

	try:
		frappe.sendmail(
			recipients=[user_email],
			subject=_("Welcome to {0}!").format(_site_name()),
			message=frappe.render_template(WELCOME_EMAIL_TEMPLATE, context),
			now=True,
		)
	except Exception:
		frappe.log_error("custom_webshop: welcome email delivery failed")


def send_phone_otp(doc, code):
	"""Send a passcode by SMS to the number on a signup session.

	Delivery goes through `sms_sender_method` when one is configured - a
	dotted path called as `sender(phone_e164, message)`, which is the seam
	for a provider SDK - and otherwise through Frappe's own SMS Settings
	gateway, which needs no code at all for any HTTP-based provider.

	Args:
		doc: the Webshop Signup Session document.
		code: the plaintext passcode.

	Raises:
		OTPDeliveryFailed: if no gateway is configured or the send fails.
	"""
	if settings.is_enabled("phone_otp_dev_mode"):
		_deliver_in_dev_mode("phone", doc.phone_e164, code)
		return

	message = _("{0} is your {1} verification code.").format(code, _site_name())

	custom_sender = settings.get("sms_sender_method")
	if custom_sender:
		try:
			frappe.get_attr(custom_sender)(doc.phone_e164, message)
			return
		except Exception:
			frappe.log_error("custom_webshop: custom SMS sender failed")
			frappe.throw(
				_("We could not send the verification SMS. Please try again shortly."),
				exc=OTPDeliveryFailed,
				title=_("SMS Not Sent"),
			)

	_send_via_sms_settings(doc.phone_e164, message)


def _send_via_sms_settings(phone_e164, message):
	"""Send one SMS through the gateway configured in SMS Settings.

	Calls `send_request` directly rather than the whitelisted `send_sms`:
	that helper msgprints "Please Update SMS Settings" and returns
	successfully when no gateway is configured, which would leave a signup
	believing a code was on its way. Here an unconfigured gateway is an
	error. This mirrors how frappe/twofactor.py's own
	`send_token_via_sms` uses the same low-level function.

	Args:
		phone_e164: the destination number.
		message: the message body.

	Raises:
		OTPDeliveryFailed: if unconfigured, or the gateway call fails.
	"""
	from frappe.core.doctype.sms_settings.sms_settings import send_request

	sms_settings = frappe.get_doc("SMS Settings")
	if not sms_settings.sms_gateway_url or not sms_settings.receiver_parameter:
		frappe.throw(
			_("SMS verification is not available right now. Please try again later."),
			exc=OTPDeliveryFailed,
			title=_("SMS Not Configured"),
		)

	args = {sms_settings.message_parameter: message, sms_settings.receiver_parameter: phone_e164}
	for parameter in sms_settings.get("parameters") or []:
		if not parameter.header:
			args[parameter.parameter] = parameter.value

	headers = {
		parameter.parameter: parameter.value
		for parameter in (sms_settings.get("parameters") or [])
		if parameter.header
	}

	try:
		send_request(
			sms_settings.sms_gateway_url, args, headers=headers or None, use_post=sms_settings.use_post
		)
	except Exception:
		frappe.log_error("custom_webshop: signup SMS OTP delivery failed")
		frappe.throw(
			_("We could not send the verification SMS. Please try again shortly."),
			exc=OTPDeliveryFailed,
			title=_("SMS Not Sent"),
		)


def send_whatsapp_otp(doc, code):
	"""Send a passcode over WhatsApp, through Evolution API.

	Mirrors `send_phone_otp` exactly in shape and failure behaviour - dev
	mode short-circuits to the site log, everything else fails closed
	through the same `OTPDeliveryFailed`, so callers treat a WhatsApp
	failure identically to an SMS one. `send_phone_otp` itself is untouched
	by this function's existence.

	Args:
		doc: the Webshop Signup Session document.
		code: the plaintext passcode.

	Raises:
		OTPDeliveryFailed: if Evolution API is not configured, or the send
			fails.
	"""
	if settings.is_enabled("whatsapp_otp_dev_mode"):
		_deliver_in_dev_mode("phone", doc.phone_e164, code)
		return

	message = _("{0} is your {1} verification code.").format(code, _site_name())

	base_url = settings.get("evolution_api_base_url")
	instance = settings.get("evolution_instance_name")
	api_key = settings.get_evolution_api_key()
	if not base_url or not instance or not api_key:
		frappe.throw(
			_("WhatsApp verification is not available right now. Please try again later."),
			exc=OTPDeliveryFailed,
			title=_("WhatsApp Not Configured"),
		)

	try:
		whatsapp.send_text(
			base_url,
			instance,
			api_key,
			doc.phone_e164,
			message,
			timeout=settings.get_int("evolution_api_timeout_seconds"),
		)
	except Exception:
		frappe.log_error("custom_webshop: signup WhatsApp OTP delivery failed")
		frappe.throw(
			_("We could not send the verification WhatsApp message. Please try again shortly."),
			exc=OTPDeliveryFailed,
			title=_("WhatsApp Not Sent"),
		)
