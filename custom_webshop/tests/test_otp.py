# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for custom_webshop.signup.otp - passcode issue, verify and throttle."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from custom_webshop.signup import otp
from custom_webshop.tests.test_signup_session import make_session
from custom_webshop.tests.utils import signup_settings_as


class TestGenerateCode(FrappeTestCase):
	def test_default_length(self):
		self.assertEqual(len(otp.generate_code()), 6)

	def test_explicit_length(self):
		self.assertEqual(len(otp.generate_code(8)), 8)

	def test_is_all_digits_and_zero_padded(self):
		for _ in range(200):
			code = otp.generate_code()
			self.assertTrue(code.isdigit())
			self.assertEqual(len(code), 6)

	def test_codes_vary(self):
		codes = {otp.generate_code() for _ in range(50)}
		self.assertGreater(len(codes), 40, "generated codes are not sufficiently random")


class TestIssueAndVerify(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.doc = make_session()

	def test_issue_stores_a_hash_not_the_code(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)

		stored = self.doc.email_otp_hash
		self.assertTrue(stored)
		self.assertNotIn(code, stored)
		self.assertEqual(len(stored), 64, "expected a hex sha256 digest")

	def test_correct_code_verifies_and_marks_the_channel(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)
			otp.verify(self.doc, otp.EMAIL, code)

		self.assertEqual(self.doc.email_verified, 1)
		self.assertIsNone(self.doc.email_otp_hash)

	def test_wrong_code_is_rejected_and_counts_an_attempt(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			otp.issue(self.doc, otp.EMAIL)
			self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, "000000")

		self.assertEqual(self.doc.email_otp_attempts, 1)
		self.assertFalse(self.doc.email_verified)

	def test_code_cannot_be_replayed(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)
			otp.verify(self.doc, otp.EMAIL, code)
			self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, code)

	def test_expired_code_is_rejected(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)
			self.doc.email_otp_expires_at = add_to_date(now_datetime(), seconds=-1)
			self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, code)

	def test_wrong_and_expired_produce_the_same_message(self):
		# An attacker must not be able to tell a live wrong guess from a
		# dead one.
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)
			with self.assertRaises(otp.OTPInvalid) as wrong:
				otp.verify(self.doc, otp.EMAIL, "000000")

			other = make_session()
			code = otp.issue(other, otp.EMAIL)
			other.email_otp_expires_at = add_to_date(now_datetime(), seconds=-1)
			with self.assertRaises(otp.OTPInvalid) as expired:
				otp.verify(other, otp.EMAIL, code)

		self.assertEqual(str(wrong.exception), str(expired.exception))

	def test_attempts_are_capped_and_the_code_is_destroyed(self):
		with signup_settings_as(otp_max_attempts=3, otp_resend_cooldown_seconds=0):
			otp.issue(self.doc, otp.EMAIL)
			for _ in range(3):
				self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, "000000")

			self.assertIsNone(self.doc.email_otp_hash, "spent code should be destroyed")
			self.assertRaises(
				otp.OTPAttemptsExhausted, otp.verify, self.doc, otp.EMAIL, "000000"
			)

	def test_the_correct_code_fails_once_attempts_are_spent(self):
		with signup_settings_as(otp_max_attempts=2, otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)
			for _ in range(2):
				self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, "000000")
			self.assertRaises(otp.OTPAttemptsExhausted, otp.verify, self.doc, otp.EMAIL, code)

	def test_issuing_a_new_code_invalidates_the_old_one(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			first = otp.issue(self.doc, otp.EMAIL)
			second = otp.issue(self.doc, otp.EMAIL)
			self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, first)

		self.assertNotEqual(first, second)

	def test_a_new_code_restores_the_attempt_budget(self):
		with signup_settings_as(otp_max_attempts=2, otp_resend_cooldown_seconds=0):
			otp.issue(self.doc, otp.EMAIL)
			for _ in range(2):
				self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, "000000")

			code = otp.issue(self.doc, otp.EMAIL)
			otp.verify(self.doc, otp.EMAIL, code)

		self.assertEqual(self.doc.email_verified, 1)

	def test_email_code_cannot_be_used_for_the_phone_channel(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			email_code = otp.issue(self.doc, otp.EMAIL)
			otp.issue(self.doc, otp.PHONE)
			self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.PHONE, email_code)

	def test_a_code_from_one_signup_does_not_work_on_another(self):
		other = make_session()
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)
			otp.issue(other, otp.EMAIL)
			self.assertRaises(otp.OTPInvalid, otp.verify, other, otp.EMAIL, code)

	def test_verifying_with_no_outstanding_code_is_rejected(self):
		self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, "123456")

	def test_blank_submission_is_rejected(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			otp.issue(self.doc, otp.EMAIL)
			self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, "")
			self.assertRaises(otp.OTPInvalid, otp.verify, self.doc, otp.EMAIL, None)

	def test_unknown_channel_is_a_programming_error(self):
		self.assertRaises(ValueError, otp.issue, self.doc, "carrier_pigeon")


class TestThrottling(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.doc = make_session()

	def test_resend_cooldown_is_enforced(self):
		with signup_settings_as(otp_resend_cooldown_seconds=60):
			otp.issue(self.doc, otp.EMAIL)
			self.assertRaises(otp.OTPCooldown, otp.issue, self.doc, otp.EMAIL)

	def test_send_cap_is_enforced(self):
		with signup_settings_as(otp_max_sends_per_channel=3, otp_resend_cooldown_seconds=0):
			for _ in range(3):
				otp.issue(self.doc, otp.EMAIL)
			self.assertRaises(otp.OTPSendLimitReached, otp.issue, self.doc, otp.EMAIL)

	def test_channels_have_separate_send_budgets(self):
		with signup_settings_as(otp_max_sends_per_channel=2, otp_resend_cooldown_seconds=0):
			otp.issue(self.doc, otp.EMAIL)
			otp.issue(self.doc, otp.EMAIL)
			otp.issue(self.doc, otp.PHONE)

		self.assertEqual(self.doc.email_otp_sends, 2)
		self.assertEqual(self.doc.phone_otp_sends, 1)

	def test_seconds_until_resend_counts_down(self):
		with signup_settings_as(otp_resend_cooldown_seconds=60):
			otp.issue(self.doc, otp.EMAIL)
			remaining = otp.seconds_until_resend(self.doc, otp.EMAIL)
		self.assertGreater(remaining, 55)
		self.assertLessEqual(remaining, 61)

	def test_sends_remaining_counts_down(self):
		with signup_settings_as(otp_max_sends_per_channel=3, otp_resend_cooldown_seconds=0):
			self.assertEqual(otp.sends_remaining(self.doc, otp.EMAIL), 3)
			otp.issue(self.doc, otp.EMAIL)
			self.assertEqual(otp.sends_remaining(self.doc, otp.EMAIL), 2)


class TestReset(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.doc = make_session()

	def test_reset_clears_verification_and_the_outstanding_code(self):
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			code = otp.issue(self.doc, otp.EMAIL)
			otp.verify(self.doc, otp.EMAIL, code)
			otp.reset(self.doc, otp.EMAIL)

		self.assertFalse(self.doc.email_verified)
		self.assertIsNone(self.doc.email_otp_hash)

	def test_reset_clears_the_cooldown(self):
		"""Changing the address must not be gated by the resend cooldown.

		The cooldown stops one address being mail-bombed; a change targets
		a different address, and somebody who mistyped their email should
		not be told to wait a minute before correcting it. The send cap,
		which reset does not touch, is what bounds the damage.
		"""
		with signup_settings_as(otp_resend_cooldown_seconds=60):
			otp.issue(self.doc, otp.EMAIL)
			self.assertRaises(otp.OTPCooldown, otp.issue, self.doc, otp.EMAIL)

			otp.reset(self.doc, otp.EMAIL)
			self.assertEqual(
				otp.seconds_until_resend(self.doc, otp.EMAIL), 0, "cooldown should be cleared"
			)
			# No longer blocked - this is the fix.
			otp.issue(self.doc, otp.EMAIL)
			# And the fresh send starts its own cooldown again.
			self.assertGreater(otp.seconds_until_resend(self.doc, otp.EMAIL), 0)

	def test_reset_does_not_refill_the_send_budget(self):
		# Otherwise changing the address back and forth would be an
		# unlimited supply of messages to any address of an attacker's
		# choosing.
		with signup_settings_as(otp_resend_cooldown_seconds=0):
			otp.issue(self.doc, otp.EMAIL)
			otp.issue(self.doc, otp.EMAIL)
			otp.reset(self.doc, otp.EMAIL)

		self.assertEqual(self.doc.email_otp_sends, 2)


def tearDownModule():
	"""Remove sessions the deliberate commits in this app left behind."""
	from custom_webshop.tests.utils import purge_test_accounts, purge_test_sessions

	purge_test_sessions()
	purge_test_accounts()
