# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for custom_webshop.signup.session - the state machine.

The point of these is the *refusals*. A signup reaching COMPLETED without
proving both channels is the failure this whole flow exists to prevent, so
every edge that must not exist is asserted here rather than assumed.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from custom_webshop.signup import session
from custom_webshop.tests.utils import unique_email, unique_name, unique_phone


def make_session(status=session.STARTED, **kwargs):
	"""Insert a signup session directly, bypassing the API.

	Args:
		status: the state to start it in.
		**kwargs: extra fields.

	Returns:
		The inserted document.
	"""
	email = kwargs.pop("email", unique_email())
	doc = session.create(
		account_type=kwargs.pop("account_type", "Individual"),
		full_name=kwargs.pop("full_name", unique_name()),
		company_name=kwargs.pop("company_name", None),
		email=email,
		email_normalized=email,
		phone_raw=kwargs.pop("phone_raw", unique_phone()),
		phone_e164=kwargs.pop("phone_e164", None) or "+20100" + frappe.generate_hash(length=7)[:7],
	)
	if status != session.STARTED or kwargs:
		doc.db_set({"status": status, **kwargs}, update_modified=False)
		doc.reload()
	return doc


class TestTransitionTable(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_every_state_has_a_transition_rule(self):
		states = set(session.ALLOWED_TRANSITIONS)
		self.assertEqual(states, set(session.ALLOWED_ACTIONS))

	def test_terminal_states_have_no_outgoing_edges(self):
		for state in session.TERMINAL_STATES:
			with self.subTest(state=state):
				self.assertEqual(session.ALLOWED_TRANSITIONS[state], set())

	def test_every_target_is_a_known_state(self):
		known = set(session.ALLOWED_TRANSITIONS)
		for state, targets in session.ALLOWED_TRANSITIONS.items():
			for target in targets:
				with self.subTest(state=state, target=target):
					self.assertIn(target, known)


class TestTransitions(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_started_may_begin_email_verification(self):
		doc = make_session()
		session.transition(doc, session.EMAIL_PENDING)
		self.assertEqual(doc.status, session.EMAIL_PENDING)

	def test_started_cannot_jump_to_completed(self):
		doc = make_session()
		self.assertRaises(
			session.InvalidSignupState, session.transition, doc, session.COMPLETED
		)

	def test_email_verified_cannot_jump_to_completed(self):
		doc = make_session(status=session.EMAIL_VERIFIED)
		self.assertRaises(
			session.InvalidSignupState, session.transition, doc, session.COMPLETED
		)

	def test_phone_verified_cannot_jump_to_completed(self):
		# Only READY may complete, and only after resolution has run.
		doc = make_session(status=session.PHONE_VERIFIED)
		self.assertRaises(
			session.InvalidSignupState, session.transition, doc, session.COMPLETED
		)

	def test_started_cannot_skip_to_phone_verification(self):
		doc = make_session()
		self.assertRaises(
			session.InvalidSignupState, session.transition, doc, session.PHONE_PENDING
		)

	def test_ready_may_complete(self):
		doc = make_session(status=session.READY)
		session.transition(doc, session.COMPLETED)
		self.assertEqual(doc.status, session.COMPLETED)

	def test_completed_is_terminal(self):
		doc = make_session(status=session.COMPLETED)
		for target in (session.READY, session.EMAIL_PENDING, session.CANCELLED):
			with self.subTest(target=target):
				self.assertRaises(
					session.InvalidSignupState, session.transition, doc, target
				)

	def test_expired_is_terminal(self):
		doc = make_session(status=session.EXPIRED)
		self.assertRaises(
			session.InvalidSignupState, session.transition, doc, session.EMAIL_PENDING
		)

	def test_blocked_is_terminal(self):
		doc = make_session(status=session.BLOCKED)
		self.assertRaises(
			session.InvalidSignupState, session.transition, doc, session.READY
		)

	def test_change_email_is_reachable_from_later_states(self):
		for state in (session.EMAIL_VERIFIED, session.PHONE_PENDING, session.PHONE_VERIFIED):
			with self.subTest(state=state):
				doc = make_session(status=state)
				session.transition(doc, session.EMAIL_PENDING)
				self.assertEqual(doc.status, session.EMAIL_PENDING)

	def test_a_non_terminal_transition_extends_expiry(self):
		doc = make_session()
		doc.db_set("expires_at", add_to_date(now_datetime(), minutes=1), update_modified=False)
		doc.reload()
		session.transition(doc, session.EMAIL_PENDING)
		self.assertGreater(doc.expires_at, add_to_date(now_datetime(), minutes=5))


class TestLoad(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_loads_a_session_for_the_browser_that_started_it(self):
		doc = make_session()
		loaded = session.load(doc.signup_id)
		self.assertEqual(loaded.name, doc.name)

	def test_rejects_an_unknown_signup_id(self):
		self.assertRaises(session.SignupNotFound, session.load, "nope")
		self.assertRaises(session.SignupNotFound, session.load, "")
		self.assertRaises(session.SignupNotFound, session.load, None)

	def test_rejects_a_signup_id_without_the_binding_secret(self):
		doc = make_session()
		frappe.local.flags.webshop_signup_secret = "some-other-browsers-secret"
		self.assertRaises(session.SignupNotFound, session.load, doc.signup_id)

	def test_wrong_browser_is_indistinguishable_from_unknown_signup(self):
		# Both must raise the same class, so a guessed id cannot be
		# confirmed by the difference in response.
		doc = make_session()
		frappe.local.flags.webshop_signup_secret = "wrong"
		with self.assertRaises(session.SignupNotFound) as wrong_browser:
			session.load(doc.signup_id)
		with self.assertRaises(session.SignupNotFound) as unknown:
			session.load("definitely-not-a-real-signup-id")
		self.assertEqual(str(wrong_browser.exception), str(unknown.exception))

	def test_expired_session_is_marked_and_rejected(self):
		doc = make_session()
		doc.db_set("expires_at", add_to_date(now_datetime(), minutes=-1), update_modified=False)
		self.assertRaises(session.SignupExpired, session.load, doc.signup_id)
		self.assertEqual(
			frappe.db.get_value("Webshop Signup Session", doc.name, "status"), session.EXPIRED
		)

	def test_expiry_survives_the_exception_that_reports_it(self):
		"""The status write must not be rolled back by its own throw.

		`load` marks the session EXPIRED and then raises. Frappe rolls the
		request transaction back on an unhandled exception, so a plain
		document save here was discarded and the session was found in its
		old state again on every later request - forever.
		"""
		doc = make_session(status=session.EMAIL_PENDING)
		doc.db_set("expires_at", add_to_date(now_datetime(), minutes=-1), update_modified=False)

		self.assertRaises(session.SignupExpired, session.load, doc.signup_id)

		# Read it back on a connection that cannot see uncommitted work.
		frappe.db.rollback()
		self.assertEqual(
			frappe.db.get_value("Webshop Signup Session", doc.name, "status"),
			session.EXPIRED,
			"the expiry was rolled back with the exception",
		)

	def test_rejects_a_state_the_endpoint_does_not_accept(self):
		doc = make_session(status=session.READY)
		self.assertRaises(
			session.InvalidSignupState,
			session.load,
			doc.signup_id,
			expected_states=[session.EMAIL_PENDING],
		)


class TestHousekeeping(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_expires_elapsed_sessions(self):
		doc = make_session(status=session.EMAIL_PENDING)
		doc.db_set("expires_at", add_to_date(now_datetime(), minutes=-5), update_modified=False)

		session.expire_stale_sessions()

		self.assertEqual(
			frappe.db.get_value("Webshop Signup Session", doc.name, "status"), session.EXPIRED
		)

	def test_leaves_live_sessions_alone(self):
		doc = make_session(status=session.EMAIL_PENDING)
		session.expire_stale_sessions()
		self.assertEqual(
			frappe.db.get_value("Webshop Signup Session", doc.name, "status"),
			session.EMAIL_PENDING,
		)

	def test_leaves_completed_sessions_alone(self):
		doc = make_session(status=session.COMPLETED)
		doc.db_set("expires_at", add_to_date(now_datetime(), minutes=-5), update_modified=False)
		session.expire_stale_sessions()
		self.assertEqual(
			frappe.db.get_value("Webshop Signup Session", doc.name, "status"), session.COMPLETED
		)


def tearDownModule():
	"""Remove sessions the deliberate commits in this app left behind."""
	from custom_webshop.tests.utils import purge_test_accounts, purge_test_sessions

	purge_test_sessions()
	purge_test_accounts()
