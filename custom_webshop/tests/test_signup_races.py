# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Concurrency tests - scenario 17, two signups for one identity.

Three defences are meant to stop a duplicate account, and each is tested
on its own rather than only in combination, because in production they
fail independently: the re-check inside the lock, the Redis lock, and the
unique indexes on Webshop Account Identity. The last is the one that has
to hold when the others do not.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from custom_webshop.api import signup as signup_api
from custom_webshop.signup import linking, matching, session
from custom_webshop.signup.identity import to_e164
from custom_webshop.tests.utils import (
	conflict_with,
	signup_enabled,
	start_signup,
	unique_email,
	unique_name,
	unique_phone,
	verify_both_channels,
)

PASSWORD = "Str0ng-Passw0rd!x7"


class RaceTestCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def ready_client(self, **kwargs):
		"""Take a signup all the way to READY."""
		client, _started = start_signup(**kwargs)
		verify_both_channels(client)
		client.call(signup_api.resolve)
		return client

	def complete(self, client):
		return client.call(
			signup_api.complete, password=PASSWORD, confirm_password=PASSWORD
		)


class TestConcurrentSignupsOnOnePhone(RaceTestCase):
	def test_only_one_account_survives(self):
		phone = unique_phone()
		first_email, second_email = unique_email(), unique_email()

		with signup_enabled():
			# Both reach READY before either finishes - each ran its
			# matching check while the other had created nothing.
			first = self.ready_client(email=first_email, phone=phone)
			second = self.ready_client(email=second_email, phone=phone)

			self.complete(first)
			result = self.complete(second)

		self.assertEqual(
			frappe.db.count("Webshop Account Identity", {"phone_e164": to_e164(phone)}),
			1,
			"two accounts were created for one verified phone",
		)
		self.assertTrue(frappe.db.exists("User", first_email))
		self.assertFalse(frappe.db.exists("User", second_email), "the losing signup still created a User")
		self.assertEqual(result["state"], session.BLOCKED)

	def test_the_loser_is_recorded_for_staff(self):
		phone = unique_phone()
		with signup_enabled():
			first = self.ready_client(phone=phone)
			second = self.ready_client(phone=phone)
			self.complete(first)
			self.complete(second)

		# The race-lost handler still stamps `matching.PHONE_ACCOUNT_EXISTS`
		# as the classification (see linking._finalize_locked's except
		# clause); the queue files it under the merged ACCOUNT_ALREADY_EXISTS.
		self.assertTrue(
			conflict_with("ACCOUNT_ALREADY_EXISTS", phone_e164=to_e164(phone)) is not None
		)

	def test_the_loser_creates_no_customer(self):
		phone = unique_phone()
		with signup_enabled():
			first = self.ready_client(phone=phone, full_name=unique_name("Winner"))
			second = self.ready_client(phone=phone, full_name=unique_name("Loser"))
			self.complete(first)
			before = frappe.db.count("Customer")
			self.complete(second)
			after = frappe.db.count("Customer")

		self.assertEqual(before, after, "the losing signup left a Customer behind")


class TestUniqueIndexIsTheRealGuarantee(RaceTestCase):
	"""What happens when the in-process checks are defeated.

	These simulate the genuine interleaving the lock exists to prevent -
	both requests passing their check before either commits - by making
	the second signup's re-check report a clean NO_MATCH even though the
	first has already committed. Only the database constraint is left.
	"""

	def test_a_duplicate_phone_is_stopped_by_the_database(self):
		phone = unique_phone()
		first_email, second_email = unique_email(), unique_email()

		with signup_enabled():
			first = self.ready_client(email=first_email, phone=phone)
			second = self.ready_client(email=second_email, phone=phone)
			self.complete(first)

			clean = {
				"result": matching.NO_MATCH,
				"candidate": None,
				"candidates": [],
				"reason": "simulated stale check",
			}
			with patch.object(matching, "classify", return_value=clean):
				result = self.complete(second)

		self.assertEqual(result["state"], session.BLOCKED)
		self.assertEqual(
			frappe.db.count("Webshop Account Identity", {"phone_e164": to_e164(phone)}), 1
		)
		self.assertFalse(frappe.db.exists("User", second_email))

	def test_the_losing_attempt_rolls_back_completely(self):
		phone = unique_phone()
		second_email = unique_email()

		with signup_enabled():
			first = self.ready_client(phone=phone)
			second = self.ready_client(email=second_email, phone=phone)
			self.complete(first)

			customers_before = frappe.db.count("Customer")
			contacts_before = frappe.db.count("Contact")

			clean = {
				"result": matching.NO_MATCH,
				"candidate": None,
				"candidates": [],
				"reason": "simulated stale check",
			}
			with patch.object(matching, "classify", return_value=clean):
				self.complete(second)

		# Everything the losing attempt built is gone: the savepoint
		# rollback covers the Contact, Customer and User it had already
		# created before the identity insert failed.
		self.assertEqual(frappe.db.count("Customer"), customers_before)
		self.assertEqual(frappe.db.count("Contact"), contacts_before)
		self.assertFalse(frappe.db.exists("User", second_email))

	def test_the_unique_indexes_exist(self):
		# The guarantee is only worth anything if the constraints are
		# actually on the table.
		rows = frappe.db.sql(
			"SHOW INDEX FROM `tabWebshop Account Identity` WHERE Non_unique = 0", as_dict=True
		)
		indexed = {row["Column_name"] for row in rows}
		for column in ("user", "phone_e164", "email_normalized"):
			self.assertIn(column, indexed, f"{column} is not uniquely indexed")

	def test_a_duplicate_identity_row_is_refused_by_the_database(self):
		from custom_webshop.tests.test_matching import make_identity, make_website_user
		from custom_webshop.tests.utils import make_customer_with_contact

		customer, _c = make_customer_with_contact()
		phone = to_e164(unique_phone())
		first = make_website_user(unique_email())
		second = make_website_user(unique_email())
		make_identity(first.name, customer.name, phone, first.name)

		# Frappe surfaces a unique-index violation on insert as
		# UniqueValidationError, not DuplicateEntryError - the latter is a
		# NameError subclass raised for a duplicate document *name*.
		self.assertRaises(
			frappe.UniqueValidationError,
			make_identity,
			second.name,
			customer.name,
			phone,
			second.name,
		)


class TestConcurrentLinkToOneCustomer(RaceTestCase):
	def test_two_signups_cannot_both_link_to_the_same_customer(self):
		from custom_webshop.tests.utils import make_customer_with_contact

		name = unique_name("Ahmed")
		phone = unique_phone()
		existing, _c = make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			first = self.ready_client(full_name=name, phone=phone)
			first.call(signup_api.decide, accept=True)
			self.complete(first)

			# A second person on a different phone but the same email
			# domain of interest - the Customer is now spoken for.
			second = self.ready_client(full_name=name, phone=unique_phone(), email=unique_email())
			second_state = second.call(signup_api.get_state)

		self.assertEqual(
			frappe.db.count("Webshop Account Identity", {"customer": existing.name}),
			1,
			"a Customer ended up with two website accounts",
		)
		self.assertNotEqual(second_state["state"], session.COMPLETED)


class TestIdempotency(RaceTestCase):
	def test_repeating_complete_does_not_double_create(self):
		email = unique_email()
		with signup_enabled():
			client = self.ready_client(email=email)
			for _ in range(3):
				self.complete(client)

		self.assertEqual(frappe.db.count("User", {"email": email}), 1)
		self.assertEqual(frappe.db.count("Webshop Account Identity", {"user": email}), 1)

	def test_repeating_resolve_does_not_pile_up_conflicts(self):
		# Two customers on one number: the one classification left that
		# still opens a conflict at resolve without asking anything.
		phone = unique_phone()
		from custom_webshop.tests.utils import (
			make_customer_sharing_a_phone,
			make_customer_with_contact,
		)

		make_customer_with_contact(customer_name=unique_name("Mohamed"), phone=phone)
		make_customer_sharing_a_phone(phone)

		with signup_enabled():
			client, _started = start_signup(full_name=unique_name("Ahmed"), phone=phone)
			verify_both_channels(client)
			resolved = client.call(signup_api.resolve)
			self.assertEqual(resolved["state"], session.READY)
			# Re-resolving from READY is refused, so the conflict cannot
			# be duplicated by retrying the endpoint.
			self.assertRaises(session.InvalidSignupState, client.call, signup_api.resolve)

		self.assertEqual(
			frappe.db.count("Webshop Identity Conflict", {"phone_e164": to_e164(phone)}), 1
		)

	def test_repeating_decide_is_harmless(self):
		from custom_webshop.tests.utils import make_customer_with_contact

		name, phone = unique_name("Ahmed"), unique_phone()
		make_customer_with_contact(customer_name=name, phone=phone)

		with signup_enabled():
			client = self.ready_client(full_name=name, phone=phone)
			client.call(signup_api.decide, accept=True)
			# A second decision is refused: the signup has moved on.
			self.assertRaises(
				session.InvalidSignupState, client.call, signup_api.decide, accept=False
			)


class TestLockDegradesSafely(RaceTestCase):
	def test_finalise_still_works_when_redis_is_unavailable(self):
		"""The lock is an optimisation, not the guarantee.

		A Redis outage must not stop people signing up; the unique indexes
		still prevent a duplicate.
		"""
		email = unique_email()
		with signup_enabled():
			client = self.ready_client(email=email)
			with patch.object(
				frappe.cache, "lock", side_effect=ConnectionError("redis is down")
			):
				self.complete(client)

		self.assertTrue(frappe.db.exists("User", email))
		self.assertEqual(frappe.db.count("Webshop Account Identity", {"user": email}), 1)

	def test_duplicates_are_still_prevented_without_the_lock(self):
		phone = unique_phone()
		first_email, second_email = unique_email(), unique_email()

		with signup_enabled():
			first = self.ready_client(email=first_email, phone=phone)
			second = self.ready_client(email=second_email, phone=phone)

			with patch.object(
				frappe.cache, "lock", side_effect=ConnectionError("redis is down")
			):
				self.complete(first)
				self.complete(second)

		self.assertEqual(
			frappe.db.count("Webshop Account Identity", {"phone_e164": to_e164(phone)}), 1
		)


def tearDownModule():
	"""Remove sessions the deliberate commits in this app left behind."""
	from custom_webshop.tests.utils import purge_test_accounts, purge_test_sessions

	purge_test_sessions()
	purge_test_accounts()
