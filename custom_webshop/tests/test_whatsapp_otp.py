# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for the WhatsApp OTP delivery channel (Evolution API).

Mirrors the shape of test_signup_flow.py: each test asserts resulting
state, not just the response. The SMS path itself is not re-tested here -
test_signup_flow.py/test_signup_security.py already cover it exhaustively,
and nothing in notifications.send_phone_otp or otp.py was touched to add
WhatsApp - these tests exist to prove the new channel selection, dispatch,
and switch-mid-flow behaviour, and that choosing WhatsApp never disturbs
SMS's own code path.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from custom_webshop.api import signup as signup_api
from custom_webshop.signup import notifications, otp, session, whatsapp
from custom_webshop.tests.utils import (
	signup_enabled,
	signup_settings_as,
	start_signup,
	unique_email,
	unique_name,
	unique_phone,
	verify_both_channels,
)

PASSWORD = "Str0ng-Passw0rd!x7"


class WhatsAppOTPTestCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)


class TestChannelSelection(WhatsAppOTPTestCase):
	def test_start_with_whatsapp_channel_is_recorded_and_reported(self):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, envelope = start_signup(phone_otp_channel="WhatsApp")

		self.assertEqual(envelope["phone_otp_channel"], "WhatsApp")
		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_otp_channel, "WhatsApp")

	def test_omitted_channel_defaults_to_sms(self):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, envelope = start_signup()

		self.assertEqual(envelope["phone_otp_channel"], "SMS")
		doc = frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})
		self.assertEqual(doc.phone_otp_channel, "SMS")

	def test_whatsapp_requested_but_disabled_site_wide_falls_back_to_sms(self):
		"""A raw API call cannot request a channel the site never offered.

		Defense in depth: the frontend only renders the WhatsApp option
		when `whatsapp_otp_enabled` is on, but `start` must not trust that
		client-side gate either.
		"""
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=0):
			client, envelope = start_signup(phone_otp_channel="WhatsApp")

		self.assertEqual(envelope["phone_otp_channel"], "SMS")


class TestWhatsAppDispatch(WhatsAppOTPTestCase):
	def test_phone_otp_is_delivered_over_whatsapp_not_sms(self):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, _ = start_signup(phone_otp_channel="WhatsApp")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)

		self.assertIn("whatsapp", client.codes)
		self.assertNotIn("phone", client.codes)

	def test_resend_keeps_the_same_channel(self):
		"""Ordinary resend must never silently switch channel."""
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, _ = start_signup(phone_otp_channel="WhatsApp")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)
			first_code = client.codes["whatsapp"]

			envelope = client.call(signup_api.send_phone_otp)
			second_code = client.codes["whatsapp"]

		self.assertEqual(envelope["phone_otp_channel"], "WhatsApp")
		self.assertNotEqual(first_code, second_code, "resend must issue a fresh code")

	def test_full_signup_completes_over_whatsapp(self):
		"""Same OTP verification and account-creation path as SMS."""
		name, email, phone = unique_name(), unique_email(), unique_phone()

		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, envelope = start_signup(
				full_name=name, email=email, phone=phone, phone_otp_channel="WhatsApp"
			)
			verify_both_channels(client)
			resolved = client.call(signup_api.resolve)
			self.assertEqual(resolved["state"], session.READY)
			result = client.call(
				signup_api.complete, password=PASSWORD, confirm_password=PASSWORD
			)

		self.assertEqual(result["state"], session.COMPLETED)
		self.assertTrue(frappe.db.exists("User", email))


class TestChannelSwitching(WhatsAppOTPTestCase):
	def test_switch_from_sms_to_whatsapp_invalidates_the_old_code(self):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, _ = start_signup(phone_otp_channel="SMS")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)
			old_sms_code = client.codes["phone"]

			envelope = client.call(signup_api.switch_phone_otp_channel, channel="WhatsApp")
			self.assertEqual(envelope["phone_otp_channel"], "WhatsApp")
			self.assertIn("whatsapp", client.codes)
			new_whatsapp_code = client.codes["whatsapp"]

			with self.assertRaises(otp.OTPInvalid):
				client.call(signup_api.verify_phone, code=old_sms_code)

			result = client.call(signup_api.verify_phone, code=new_whatsapp_code)

		self.assertEqual(result["state"], session.PHONE_VERIFIED)

	def test_switch_from_whatsapp_to_sms_invalidates_the_old_code(self):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, _ = start_signup(phone_otp_channel="WhatsApp")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)
			old_whatsapp_code = client.codes["whatsapp"]

			envelope = client.call(signup_api.switch_phone_otp_channel, channel="SMS")
			self.assertEqual(envelope["phone_otp_channel"], "SMS")
			new_sms_code = client.codes["phone"]

			with self.assertRaises(otp.OTPInvalid):
				client.call(signup_api.verify_phone, code=old_whatsapp_code)

			result = client.call(signup_api.verify_phone, code=new_sms_code)

		self.assertEqual(result["state"], session.PHONE_VERIFIED)

	def test_switching_repeatedly_does_not_bypass_the_resend_cooldown(self):
		"""Toggling channels back and forth must share the ordinary cooldown."""
		with signup_enabled(), signup_settings_as(
			whatsapp_otp_enabled=1, otp_resend_cooldown_seconds=120
		):
			client, _ = start_signup(phone_otp_channel="SMS")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)

			with self.assertRaises(otp.OTPCooldown):
				client.call(signup_api.switch_phone_otp_channel, channel="WhatsApp")

	def test_switch_to_an_unknown_channel_is_rejected(self):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, _ = start_signup(phone_otp_channel="SMS")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)

			with self.assertRaises(frappe.ValidationError):
				client.call(signup_api.switch_phone_otp_channel, channel="Carrier Pigeon")

	def test_switch_to_whatsapp_is_rejected_when_disabled_site_wide(self):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=0):
			client, _ = start_signup(phone_otp_channel="SMS")
			client.call(signup_api.verify_email, code=client.codes["email"])
			client.call(signup_api.send_phone_otp)

			with self.assertRaises(frappe.ValidationError):
				client.call(signup_api.switch_phone_otp_channel, channel="WhatsApp")


class TestWhatsAppDeliveryFailure(WhatsAppOTPTestCase):
	def _verified_email_doc(self, channel="WhatsApp"):
		with signup_enabled(), signup_settings_as(whatsapp_otp_enabled=1):
			client, _ = start_signup(phone_otp_channel=channel)
			client.call(signup_api.verify_email, code=client.codes["email"])
		return frappe.get_doc("Webshop Signup Session", {"signup_id": client.signup_id})

	def test_unconfigured_evolution_api_fails_closed(self):
		doc = self._verified_email_doc()

		with signup_settings_as(
			whatsapp_otp_dev_mode=0,
			evolution_api_base_url=None,
			evolution_instance_name=None,
		):
			code = otp.issue(doc, otp.PHONE)
			with self.assertRaises(notifications.OTPDeliveryFailed):
				notifications.send_whatsapp_otp(doc, code)

	def test_dev_mode_delivers_without_a_network_call(self):
		doc = self._verified_email_doc()

		with signup_settings_as(whatsapp_otp_dev_mode=1):
			code = otp.issue(doc, otp.PHONE)
			# Must not raise, and must not attempt any HTTP call.
			notifications.send_whatsapp_otp(doc, code)


class TestRequestBuilding(WhatsAppOTPTestCase):
	"""Regression coverage for a real bug found in the field: an Evolution
	API instance name containing a space produced a malformed, unroutable
	URL because it was interpolated into the path unescaped."""

	def test_instance_name_with_a_space_is_url_encoded(self):
		url, headers, payload = whatsapp._build_request(
			"https://evoapi.example.com/", "ahmed amin1", "secret-key", "+201011112222", "hi"
		)
		self.assertEqual(url, "https://evoapi.example.com/message/sendText/ahmed%20amin1")
		self.assertNotIn(" ", url)

	def test_trailing_slash_on_base_url_does_not_double_up(self):
		url, _, _ = whatsapp._build_request(
			"https://evoapi.example.com/", "shop", "secret-key", "+201011112222", "hi"
		)
		self.assertEqual(url, "https://evoapi.example.com/message/sendText/shop")

	def test_phone_number_loses_its_leading_plus(self):
		_, _, payload = whatsapp._build_request(
			"https://evoapi.example.com", "shop", "secret-key", "+201011112222", "hi"
		)
		self.assertEqual(payload["number"], "201011112222")

	def test_api_key_travels_only_in_the_header(self):
		_, headers, payload = whatsapp._build_request(
			"https://evoapi.example.com", "shop", "top-secret", "+201011112222", "hi"
		)
		self.assertEqual(headers["apikey"], "top-secret")
		self.assertNotIn("top-secret", str(payload))
