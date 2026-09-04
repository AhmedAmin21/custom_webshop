# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Security tests for the signup flow.

Each of these describes an attack rather than a feature. The one that
matters most is the last group: a person who controls a phone number and
an email address must not be able to talk the backend into linking their
new account to somebody else's Customer.
"""

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from custom_webshop.api import signup as signup_api
from custom_webshop.signup import linking, matching, otp, session, telemetry
from custom_webshop.signup.identity import to_e164
from custom_webshop.tests.test_matching import make_identity, make_website_user
from custom_webshop.tests.utils import (
	SignupClient,
	make_customer_with_contact,
	signup_enabled,
	signup_settings_as,
	start_signup,
	unique_email,
	unique_name,
	unique_phone,
	verify_both_channels,
)

PASSWORD = "Str0ng-Passw0rd!x7"


class TestOTPBruteForce(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_guessing_is_capped_well_below_the_keyspace(self):
		with signup_enabled(), signup_settings_as(otp_max_attempts=5, otp_max_sends_per_channel=5):
			client, _started = start_signup()
			guesses = 0
			for _ in range(5):  # every send this session is allowed
				for _ in range(5):  # every attempt on that code
					try:
						client.call(signup_api.verify_email, code="000000")
						guesses += 1
					except (otp.OTPInvalid, otp.OTPAttemptsExhausted):
						guesses += 1
				try:
					client.call(signup_api.send_email_otp)
				except otp.OTPSendLimitReached:
					break

			# 25 guesses against a 10^6 keyspace, then the session is spent.
			self.assertLessEqual(guesses, 25)
			self.assertRaises(
				otp.OTPSendLimitReached, client.call, signup_api.send_email_otp
			)

	def test_the_attempt_counter_survives_a_rollback(self):
		"""The cap has to hold across requests, not just within one.

		`verify` reports a wrong code by raising, and Frappe rolls the
		request transaction back on an unhandled exception. Until this was
		fixed the incremented counter went with it, so every guess reached
		a session showing zero attempts and a live code - the five-guess
		cap did nothing over HTTP, which is the only place it matters.
		"""
		from custom_webshop.signup import otp as otp_module
		from custom_webshop.tests.test_signup_session import make_session

		self.addCleanup(frappe.db.rollback)
		doc = make_session()

		with signup_settings_as(otp_resend_cooldown_seconds=0):
			otp_module.issue(doc, otp_module.EMAIL)
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			frappe.db.commit()

			self.assertRaises(otp_module.OTPInvalid, otp_module.verify, doc, otp_module.EMAIL, "000000")

		# Simulate what the framework does after the endpoint raises.
		frappe.db.rollback()

		self.assertEqual(
			frappe.db.get_value("Webshop Signup Session", doc.name, "email_otp_attempts"),
			1,
			"the failed attempt was rolled back - brute force is unbounded",
		)

	def test_the_cap_destroys_the_code_durably(self):
		from custom_webshop.signup import otp as otp_module
		from custom_webshop.tests.test_signup_session import make_session

		self.addCleanup(frappe.db.rollback)
		doc = make_session()

		with signup_settings_as(otp_max_attempts=3, otp_resend_cooldown_seconds=0):
			otp_module.issue(doc, otp_module.EMAIL)
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			frappe.db.commit()

			for _ in range(3):
				self.assertRaises(
					otp_module.OTPInvalid, otp_module.verify, doc, otp_module.EMAIL, "000000"
				)
				frappe.db.rollback()
				doc.reload()

		self.assertEqual(
			frappe.db.get_value("Webshop Signup Session", doc.name, "email_otp_attempts"), 3
		)
		self.assertIsNone(
			frappe.db.get_value("Webshop Signup Session", doc.name, "email_otp_hash"),
			"the spent code must be destroyed durably",
		)

	def test_a_spent_session_cannot_be_revived(self):
		with signup_enabled(), signup_settings_as(otp_max_attempts=2, otp_max_sends_per_channel=1):
			client, _started = start_signup()
			for _ in range(2):
				self.assertRaises(
					otp.OTPInvalid, client.call, signup_api.verify_email, code="000000"
				)
			self.assertRaises(
				otp.OTPSendLimitReached, client.call, signup_api.send_email_otp
			)


class TestOTPReplayAndOracles(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_a_used_code_cannot_be_replayed(self):
		with signup_enabled():
			client, _started = start_signup()
			code = client.codes["email"]
			client.call(signup_api.verify_email, code=code)
			client.call(signup_api.change_email, email=unique_email())
			self.assertRaises(otp.OTPInvalid, client.call, signup_api.verify_email, code=code)

	def test_wrong_and_expired_codes_are_indistinguishable(self):
		with signup_enabled():
			wrong_client, _a = start_signup()
			with self.assertRaises(otp.OTPInvalid) as wrong:
				wrong_client.call(signup_api.verify_email, code="000000")

			expired_client, _b = start_signup()
			frappe.db.set_value(
				"Webshop Signup Session",
				{"signup_id": expired_client.signup_id},
				"email_otp_expires_at",
				add_to_date(now_datetime(), seconds=-1),
				update_modified=False,
			)
			with self.assertRaises(otp.OTPInvalid) as expired:
				expired_client.call(
					signup_api.verify_email, code=expired_client.codes["email"]
				)

		self.assertEqual(str(wrong.exception), str(expired.exception))
		self.assertEqual(type(wrong.exception), type(expired.exception))

	def test_a_code_is_never_returned_to_the_browser(self):
		with signup_enabled():
			client, started = start_signup()
			state = client.call(signup_api.get_state)

		for payload in (started, state):
			self.assertNotIn(client.codes["email"], frappe.as_json(payload))

	def test_the_otp_hash_is_never_returned_to_the_browser(self):
		with signup_enabled():
			client, started = start_signup()

		stored = frappe.db.get_value(
			"Webshop Signup Session", {"signup_id": client.signup_id}, "email_otp_hash"
		)
		self.assertTrue(stored)
		self.assertNotIn(stored, frappe.as_json(started))


class TestSessionIsolation(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_a_signup_id_alone_does_not_grant_control(self):
		"""Possessing the handle is not enough without the browser cookie."""
		with signup_enabled():
			victim, _started = start_signup()

			attacker = SignupClient()
			attacker.signup_id = victim.signup_id
			attacker.secret = "attackers-own-secret"

			self.assertRaises(
				session.SignupNotFound, attacker.call, signup_api.get_state
			)
			self.assertRaises(
				session.SignupNotFound, attacker.call, signup_api.verify_email, code="000000"
			)

	def test_a_missing_binding_secret_is_rejected(self):
		with signup_enabled():
			victim, _started = start_signup()
			attacker = SignupClient()
			attacker.signup_id = victim.signup_id
			attacker.secret = None
			self.assertRaises(session.SignupNotFound, attacker.call, signup_api.get_state)

	def test_one_browser_cannot_complete_anothers_signup(self):
		with signup_enabled():
			victim, _started = start_signup()
			verify_both_channels(victim)
			victim.call(signup_api.resolve)

			attacker = SignupClient()
			attacker.signup_id = victim.signup_id
			attacker.secret = "wrong"
			self.assertRaises(
				session.SignupNotFound,
				attacker.call,
				signup_api.complete,
				password=PASSWORD,
				confirm_password=PASSWORD,
			)


class TestFrontendCannotChooseACustomer(FrappeTestCase):
	"""The central guarantee: identity resolution is not client-influenced."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_no_endpoint_accepts_a_customer_identifier(self):
		# Structural: nothing in the public surface takes a Customer.
		suspicious = {"customer", "candidate", "candidate_customer", "party", "party_name", "link_to"}
		for name, func in inspect.getmembers(signup_api, inspect.isfunction):
			if not getattr(func, "__wrapped__", None) and not hasattr(func, "is_whitelisted"):
				continue
			params = set(inspect.signature(func).parameters)
			with self.subTest(endpoint=name):
				self.assertEqual(params & suspicious, set(), f"{name} accepts a customer identifier")

	def test_extra_customer_arguments_are_rejected(self):
		victim, _c = make_customer_with_contact(customer_name=unique_name("Victim"))

		with signup_enabled():
			client, _resolved = start_signup()
			verify_both_channels(client)
			with self.assertRaises(TypeError):
				client.call(signup_api.resolve, candidate_customer=victim.name)

	def test_decide_cannot_redirect_the_link_to_another_customer(self):
		"""Answering "yes" only ever confirms the server-held candidate."""
		name, phone = unique_name("Ahmed"), unique_phone()
		intended, _a = make_customer_with_contact(customer_name=name, phone=phone)
		victim, _b = make_customer_with_contact(customer_name=unique_name("Victim"))
		email = unique_email()

		with signup_enabled():
			client, resolved = start_signup(full_name=name, phone=phone, email=email)
			verify_both_channels(client)
			client.call(signup_api.resolve)

			# Nothing the caller can send changes which record is linked.
			client.call(signup_api.decide, accept=True)
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		linked = frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer")
		self.assertEqual(linked, intended.name)
		self.assertNotEqual(linked, victim.name)

	def test_tampering_with_the_stored_candidate_is_caught_at_finalise(self):
		"""Rule 13: the decision is re-derived immediately before writing.

		Even a candidate written straight into the session row - which no
		HTTP request can do, but a compromised process could - is
		discarded, because finalise re-runs matching and only honours a
		link the fresh result still agrees with.
		"""
		victim, _v = make_customer_with_contact(customer_name=unique_name("Victim"))
		email = unique_email()

		with signup_enabled():
			client, _resolved = start_signup(email=email)
			verify_both_channels(client)
			client.call(signup_api.resolve)  # NO_MATCH -> READY

			frappe.db.set_value(
				"Webshop Signup Session",
				{"signup_id": client.signup_id},
				{"candidate_customer": victim.name, "resolution": linking.LINK_EXISTING},
				update_modified=False,
			)

			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)

		linked = frappe.db.get_value("Webshop Account Identity", {"user": email}, "customer")
		self.assertNotEqual(linked, victim.name, "a forged candidate was honoured")
		self.assertFalse(
			frappe.db.exists(
				"Portal User", {"parent": victim.name, "user": email, "parenttype": "Customer"}
			)
		)

	def test_a_forged_ready_state_without_verification_cannot_complete(self):
		"""The state field alone is not proof; finalise re-asserts the flags."""
		email = unique_email()
		with signup_enabled():
			client, _started = start_signup(email=email)
			frappe.db.set_value(
				"Webshop Signup Session",
				{"signup_id": client.signup_id},
				{"status": session.READY, "resolution": linking.CREATE_NEW},
				update_modified=False,
			)
			self.assertRaises(
				session.InvalidSignupState,
				client.call,
				signup_api.complete,
				password=PASSWORD,
				confirm_password=PASSWORD,
			)

		self.assertFalse(frappe.db.exists("User", email))


class TestEnumeration(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_start_reveals_nothing_about_a_registered_phone(self):
		phone = unique_phone()
		customer, _c = make_customer_with_contact()
		other = make_website_user(unique_email())
		make_identity(other.name, customer.name, to_e164(phone), other.name)

		with signup_enabled():
			_c1, taken = start_signup(phone=phone)
			_c2, free = start_signup(phone=unique_phone())

		self.assertEqual(taken["state"], free["state"])
		self.assertEqual(taken["allowed_actions"], free["allowed_actions"])

	def test_the_block_message_does_not_say_which_channel_matched(self):
		# One wording for both, so responses cannot be diffed.
		email = unique_email()
		make_website_user(email)
		with signup_enabled():
			client, _s = start_signup(email=email)
			verify_both_channels(client)
			blocked = client.call(signup_api.resolve)

		self.assertEqual(blocked["state"], session.BLOCKED)
		self.assertNotIn("email", blocked["message"].lower().replace("these details", ""))
		self.assertNotIn("phone", blocked["message"].lower())

	def test_a_block_is_only_ever_reached_with_both_channels_proved(self):
		"""The property that actually protects anybody.

		These responses now say *which* detail is taken, because standing
		in front of somebody with "an account already exists for these
		details" when they have proved control of both of them is a dead
		end they cannot reason their way out of.

		That is only safe while this is true: a block cannot be reached
		before both codes are entered. It used to be reachable at
		`verify_email`, where a caller holding one address could learn
		about a channel they did not own - and that, not the wording, was
		the leak. So this asserts the reachability, and the disclosure
		test below asserts that what is named is only ever the person's
		own details.
		"""
		taken_email = unique_email()
		make_website_user(taken_email)

		with signup_enabled():
			client, _s = start_signup(email=taken_email)
			after_email = client.call(signup_api.verify_email, code=client.codes["email"])
			self.assertEqual(after_email["state"], session.EMAIL_VERIFIED)
			self.assertNotIn("blocked_on", after_email["data"])

			client.call(signup_api.send_phone_otp)
			after_phone = client.call(signup_api.verify_phone, code=client.codes["phone"])
			self.assertEqual(after_phone["state"], session.PHONE_VERIFIED)
			self.assertNotIn("blocked_on", after_phone["data"])

			blocked = client.call(signup_api.resolve)

		self.assertEqual(blocked["state"], session.BLOCKED)
		self.assertEqual(blocked["data"]["blocked_on"], "email")

	def test_a_block_names_only_details_the_person_proved(self):
		"""It may say "your number is taken". Never whose account it is."""
		taken_phone = unique_phone()
		customer, _c = make_customer_with_contact(customer_name=unique_name("Mohamed"))
		other = make_website_user(unique_email())
		make_identity(other.name, customer.name, to_e164(taken_phone), other.name)

		with signup_enabled():
			client, _s = start_signup(phone=taken_phone, email=unique_email())
			verify_both_channels(client)
			blocked = client.call(signup_api.resolve)

		self.assertEqual(blocked["data"]["blocked_on"], "phone")
		payload = frappe.as_json(blocked)
		# Nothing about the account that holds it.
		self.assertNotIn(other.name, payload)
		self.assertNotIn(customer.name, payload)
		self.assertNotIn(customer.customer_name, payload)

	def test_the_two_blocks_still_share_one_shape(self):
		"""Same keys, same wording - only the named detail differs.

		The payloads must not drift apart in any *other* way, or the
		difference stops being the one deliberate disclosure and becomes
		an accident again.
		"""
		taken_email = unique_email()
		make_website_user(taken_email)

		taken_phone = unique_phone()
		customer, _c = make_customer_with_contact()
		other = make_website_user(unique_email())
		make_identity(other.name, customer.name, to_e164(taken_phone), other.name)

		with signup_enabled():
			c1, _s1 = start_signup(email=taken_email)
			verify_both_channels(c1)
			by_email = c1.call(signup_api.resolve)

			c2, _s2 = start_signup(phone=taken_phone)
			verify_both_channels(c2)
			by_phone = c2.call(signup_api.resolve)

		self.assertEqual(by_email["state"], session.BLOCKED)
		self.assertEqual(by_phone["state"], session.BLOCKED)
		self.assertEqual(by_email["message"], by_phone["message"])
		self.assertEqual(by_email["allowed_actions"], by_phone["allowed_actions"])
		self.assertEqual(sorted(by_email), sorted(by_phone))
		self.assertEqual(sorted(by_email["data"]), sorted(by_phone["data"]))
		self.assertEqual(by_email["data"]["recovery_email"], by_email["email"])
		self.assertEqual(by_phone["data"]["recovery_email"], by_phone["email"])
		# The one deliberate difference.
		self.assertEqual(by_email["data"]["blocked_on"], "email")
		self.assertEqual(by_phone["data"]["blocked_on"], "phone")


class TestDeskMessagesStayInTheDesk(FrappeTestCase):
	"""A shopper is shown what this flow says, and nothing else.

	Creating an account saves Contacts and Customers, and every app with a
	hook on those gets to `frappe.msgprint` while it happens. Frappe hands
	the whole message log back to whoever made the request - so without
	this, a customer finishing a signup was shown
	contact_enhancements' "check before saving a duplicate", twice: an
	internal note about records they cannot see and cannot act on.
	"""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_another_apps_warning_never_reaches_the_customer(self):
		# An email already on another Contact, so that app's duplicate
		# check fires while this signup writes its own records.
		email = unique_email()
		make_customer_with_contact(
			customer_name=unique_name("Ahmed"), phone=unique_phone(), email=email
		)

		with signup_enabled():
			client, _s = start_signup(full_name=unique_name("Mohamed"), phone=unique_phone(), email=email)
			verify_both_channels(client)
			resolved = client.call(signup_api.resolve)
			if resolved["state"] == session.MATCH_REVIEW:
				decided = client.call(signup_api.decide, accept=True)
				if (decided.get("data") or {}).get("name_choice"):
					client.call(signup_api.choose_name, use_submitted=False)

			frappe.local.message_log = []
			client.call(signup_api.complete, password=PASSWORD, confirm_password=PASSWORD)
			leaked = list(frappe.local.message_log or [])

		self.assertEqual(
			leaked, [], "another app's Desk message was handed to the shopper"
		)

	def test_muting_does_not_swallow_a_real_error(self):
		"""`throw` raises before Frappe checks the mute flag."""
		from custom_webshop.signup import linking

		with linking._desk_messages_kept_off_the_shopfront():
			frappe.msgprint("this must not survive")
			self.assertEqual(frappe.local.message_log or [], [])
			with self.assertRaises(frappe.ValidationError):
				frappe.throw("this must still stop the request")

	def test_the_flag_is_put_back(self):
		from custom_webshop.signup import linking

		before = frappe.flags.mute_messages
		try:
			with linking._desk_messages_kept_off_the_shopfront():
				raise RuntimeError("boom")
		except RuntimeError:
			pass
		self.assertEqual(frappe.flags.mute_messages, before)


class TestSecretsAreNotLogged(FrappeTestCase):
	def test_secret_shaped_fields_are_redacted(self):
		from custom_webshop.signup.telemetry import _scrub

		scrubbed = _scrub(
			{
				"otp": "123456",
				"code": "123456",
				"password": "hunter2",
				"pwd": "hunter2",
				"new_password": "hunter2",
				"binding_hash": "deadbeef",
				"email_otp_hash": "deadbeef",
				"secret": "s3cr3t",
				"state": "READY",
			}
		)

		for key in set(scrubbed) - {"state"}:
			self.assertEqual(scrubbed[key], "***", f"{key} was not redacted")
		self.assertEqual(scrubbed["state"], "READY")

	def test_event_payloads_mask_contact_details(self):
		from unittest.mock import patch

		from custom_webshop.tests.test_signup_session import make_session

		self.addCleanup(frappe.db.rollback)
		doc = make_session(email="someone@example.com", phone_e164="+201012345678")

		with patch.object(telemetry, "get_logger") as logger:
			telemetry.log_event("test_event", doc)
			payload = logger.return_value.info.call_args[0][0]

		self.assertNotIn("someone@example.com", frappe.as_json(payload))
		self.assertNotIn("1012345678", frappe.as_json(payload))
		self.assertIn("*", payload["email"])

	def test_the_redaction_list_covers_every_secret_field_name_used(self):
		# Guards against a new secret field being added without being
		# added here too.
		for field in ("email_otp_hash", "phone_otp_hash", "binding_hash"):
			self.assertIn(field, telemetry.REDACTED_KEYS)


class TestBlockedSignupsCreateNothing(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_a_blocked_signup_leaves_no_records(self):
		email = unique_email()
		make_website_user(email)

		with signup_enabled():
			client, _s = start_signup(email=email)
			verify_both_channels(client)
			client.call(signup_api.resolve)

		self.assertEqual(frappe.db.count("User", {"email": email}), 1, "a second User was created")
		self.assertFalse(frappe.db.exists("Webshop Account Identity", {"email_normalized": email}))

	def test_a_blocked_signup_cannot_be_pushed_further(self):
		email = unique_email()
		make_website_user(email)

		with signup_enabled():
			client, _s = start_signup(email=email)
			verify_both_channels(client)
			blocked = client.call(signup_api.resolve)
			self.assertEqual(blocked["state"], session.BLOCKED)

			for endpoint in (signup_api.send_phone_otp, signup_api.resolve):
				with self.subTest(endpoint=endpoint.__name__):
					self.assertRaises(session.InvalidSignupState, client.call, endpoint)

			self.assertRaises(
				session.InvalidSignupState, client.call, signup_api.decide, accept=True
			)
			self.assertRaises(
				session.InvalidSignupState,
				client.call,
				signup_api.complete,
				password=PASSWORD,
				confirm_password=PASSWORD,
			)

		self.assertEqual(frappe.db.count("User", {"email": email}), 1)


def tearDownModule():
	"""Remove sessions the deliberate commits in this app left behind."""
	from custom_webshop.tests.utils import purge_test_accounts, purge_test_sessions

	purge_test_sessions()
	purge_test_accounts()
