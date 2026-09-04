# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for custom_webshop.signup.matching - identity resolution.

Every row of the classification table has a test here, and so does every
rule that must *not* fire: a shared name is never a match on its own, two
candidates are never resolved to one, and a disabled record is never
linked to automatically.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from custom_webshop.signup import matching
from custom_webshop.signup.identity import to_e164, to_local
from custom_webshop.tests.test_signup_session import make_session
from custom_webshop.tests.utils import (
	make_contact,
	make_customer,
	make_customer_sharing_a_phone,
	make_customer_with_contact,
	unique_email,
	unique_name,
	unique_phone,
)


def make_identity(user, customer, phone_e164, email):
	"""Insert an account identity row, the way a completed signup would.

	Args:
		user: an existing User's name.
		customer: an existing Customer's name.
		phone_e164: the verified number.
		email: the verified address.

	Returns:
		The inserted document.
	"""
	identity = frappe.new_doc("Webshop Account Identity")
	identity.update(
		{
			"user": user,
			"customer": customer,
			"phone_e164": phone_e164,
			"email_normalized": email,
			"verified_on": now_datetime(),
		}
	)
	identity.flags.ignore_permissions = True
	identity.insert(ignore_permissions=True)
	return identity


def make_website_user(email):
	"""Insert a minimal Website User.

	Args:
		email: the account email.

	Returns:
		The inserted User document.
	"""
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": unique_name(),
			"enabled": 1,
			"user_type": "Website User",
		}
	)
	user.flags.ignore_permissions = True
	user.flags.no_welcome_mail = True
	user.insert(ignore_permissions=True)
	return user


class TestCandidateGathering(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_finds_customer_through_contact_phone(self):
		phone = unique_phone()
		customer, _contact = make_customer_with_contact(phone=phone)
		found = matching.find_customers_by_phone(to_e164(phone))
		self.assertIn(customer.name, found)

	def test_phone_lookup_is_format_independent(self):
		# The record stores 01…; the signup verified +20…. They are one
		# identity, which is the entire point of the canonical column.
		phone = unique_phone()
		customer, _contact = make_customer_with_contact(phone=phone)
		e164 = to_e164(phone)
		self.assertIn(customer.name, matching.find_customers_by_phone(e164))
		self.assertIn(customer.name, matching.find_customers_by_phone(to_e164(to_local(e164))))

	def test_finds_customer_through_legacy_mobile_no_field(self):
		# Covers rows whose mobile_no was written directly with db_set,
		# bypassing the read-only fetch_from mirror - the live database
		# has exactly these.
		phone = unique_phone()
		customer = make_customer()
		frappe.db.set_value("Customer", customer.name, "mobile_no", phone, update_modified=False)
		self.assertIn(customer.name, matching.find_customers_by_phone(to_e164(phone)))

	def test_finds_customer_through_contact_email(self):
		email = unique_email()
		customer, _contact = make_customer_with_contact(email=email)
		self.assertIn(customer.name, matching.find_customers_by_email(email))

	def test_email_lookup_is_case_insensitive(self):
		email = unique_email()
		customer, _contact = make_customer_with_contact(email=email.upper())
		self.assertIn(customer.name, matching.find_customers_by_email(email.lower()))

	def test_blank_inputs_find_nothing(self):
		self.assertEqual(matching.find_customers_by_phone(None), set())
		self.assertEqual(matching.find_customers_by_email(""), set())

	def test_unlinked_contact_is_not_a_candidate(self):
		# A Contact with no Dynamic Link to a Customer resolves to nothing;
		# the live database has several such orphans.
		phone = unique_phone()
		make_contact(phone=phone)
		self.assertEqual(matching.find_customers_by_phone(to_e164(phone)), set())


class TestClassification(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def _session(self, name=None, phone=None, email=None, account_type="Individual", company_name=None):
		phone = phone or unique_phone()
		doc = make_session(
			full_name=name or unique_name(),
			email=email or unique_email(),
			phone_raw=phone,
			phone_e164=to_e164(phone),
			account_type=account_type,
			company_name=company_name,
		)
		doc.email_verified = 1
		doc.phone_verified = 1
		return doc

	def test_no_match_when_nothing_exists(self):
		verdict = matching.classify(self._session())
		self.assertEqual(verdict["result"], matching.NO_MATCH)
		self.assertIsNone(verdict["candidate"])
		self.assertEqual(verdict["candidates"], [])

	def test_strong_match_on_phone_and_name(self):
		name = unique_name("Ahmed")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(customer_name=name, phone=phone)

		verdict = matching.classify(self._session(name=name, phone=phone))
		self.assertEqual(verdict["result"], matching.STRONG_MATCH)
		self.assertEqual(verdict["candidate"], customer.name)

	def test_phone_name_mismatch_is_never_a_strong_match(self):
		phone = unique_phone()
		customer, _c = make_customer_with_contact(customer_name=unique_name("Mohamed"), phone=phone)

		verdict = matching.classify(self._session(name=unique_name("Ahmed"), phone=phone))
		self.assertEqual(verdict["result"], matching.PHONE_NAME_MISMATCH)
		self.assertEqual(verdict["candidate"], customer.name)

	def test_email_match_on_email_and_name(self):
		name = unique_name("Ahmed")
		email = unique_email()
		customer, _c = make_customer_with_contact(customer_name=name, email=email)

		verdict = matching.classify(self._session(name=name, email=email))
		self.assertEqual(verdict["result"], matching.EMAIL_MATCH)
		self.assertEqual(verdict["candidate"], customer.name)

	def test_email_name_mismatch(self):
		email = unique_email()
		make_customer_with_contact(customer_name=unique_name("Mohamed"), email=email)

		verdict = matching.classify(self._session(name=unique_name("Ahmed"), email=email))
		self.assertEqual(verdict["result"], matching.EMAIL_NAME_MISMATCH)

	def test_multiple_matches_are_never_resolved_to_one(self):
		phone = unique_phone()
		first, _a = make_customer_with_contact(phone=phone)
		second = make_customer_sharing_a_phone(phone)

		verdict = matching.classify(self._session(phone=phone))
		self.assertEqual(verdict["result"], matching.MULTIPLE_MATCH)
		self.assertIsNone(verdict["candidate"], "the engine must not pick a winner")
		self.assertEqual(len(verdict["candidates"]), 2)
		self.assertEqual(
			{entry["customer"] for entry in verdict["candidates"]}, {first.name, second.name}
		)

	def test_a_shared_name_alone_is_never_a_match(self):
		# Rule 6: two people genuinely do have the same name.
		name = unique_name("Ahmed")
		make_customer_with_contact(customer_name=name, phone=unique_phone(), email=unique_email())

		verdict = matching.classify(self._session(name=name))
		self.assertEqual(verdict["result"], matching.NO_MATCH)

	def test_disabled_customer_is_never_linked_automatically(self):
		name = unique_name("Ahmed")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(customer_name=name, phone=phone)
		frappe.db.set_value("Customer", customer.name, "disabled", 1, update_modified=False)

		verdict = matching.classify(self._session(name=name, phone=phone))
		# Downgraded out of STRONG_MATCH, which is what "never linked
		# automatically" means: the person is asked, and even a yes only
		# reaches a link the engine re-derives at finalise. What must not
		# happen is the engine deciding on its own.
		self.assertEqual(verdict["result"], matching.PHONE_NAME_MISMATCH)
		self.assertNotEqual(verdict["result"], matching.STRONG_MATCH)
		# Not a claim about disclosure. A verified phone now discloses the
		# name whatever the record's state; what "never linked
		# automatically" means is that the engine stops and asks.
		self.assertIn(verdict["result"], matching.CONFIRMABLE_RESULTS)

	def test_company_signup_matches_on_company_name(self):
		company = unique_name("Acme")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(customer_name=company, phone=phone)
		# A business name only matches a business's name. On an individual
		# record the customer_name is a person's, and a company signup
		# claiming it would be comparing two different kinds of thing.
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		doc = self._session(phone=phone, account_type="Company", company_name=company)
		verdict = matching.classify(doc)
		self.assertEqual(verdict["result"], matching.STRONG_MATCH)
		self.assertEqual(verdict["candidate"], customer.name)

	def test_a_company_name_does_not_match_a_persons_record(self):
		"""The rule that used to be missing.

		`candidate_names` returned the Customer's own name whatever the
		Customer was, so "Acme Trading" agreeing with an individual named
		"Acme Trading" read as a confirmed match - two different kinds of
		name compared with each other.
		"""
		name = unique_name("Acme")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(customer_name=name, phone=phone)
		# Left as Individual on purpose.
		doc = self._session(phone=phone, account_type="Company", company_name=name)

		verdict = matching.classify(doc)
		self.assertEqual(verdict["result"], matching.PHONE_NAME_MISMATCH)

	def test_a_persons_name_does_not_match_a_company_record(self):
		person = unique_name("Ahmed")
		phone = unique_phone()
		# The contact is somebody else, so nothing on the record is this
		# person - only the company name, which is not a person's name.
		customer, _contact = make_customer_with_contact(
			customer_name=person, contact_name=unique_name("Mohamed"), phone=phone
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", "Company")

		doc = self._session(phone=phone, name=person)
		verdict = matching.classify(doc)
		self.assertEqual(verdict["result"], matching.PHONE_NAME_MISMATCH)

	def test_company_signup_matches_on_the_contact_person(self):
		# The Customer carries the company name; the person signing up
		# gives their own. Matching the primary contact is enough for the
		# name not to contradict the phone.
		person = unique_name("Ahmed")
		phone = unique_phone()
		customer, _c = make_customer_with_contact(
			customer_name=unique_name("Acme"), phone=phone, contact_name=person
		)

		doc = self._session(
			name=person, phone=phone, account_type="Company", company_name=unique_name("Other")
		)
		verdict = matching.classify(doc)
		self.assertEqual(verdict["result"], matching.STRONG_MATCH)
		self.assertEqual(verdict["candidate"], customer.name)

	def test_candidate_audit_records_the_matching_signal(self):
		phone = unique_phone()
		customer, _c = make_customer_with_contact(phone=phone)
		verdict = matching.classify(self._session(phone=phone))
		self.assertEqual(verdict["candidates"][0]["customer"], customer.name)
		self.assertEqual(verdict["candidates"][0]["matched_on"], ["phone"])


class TestBlockingChecks(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def _verified_session(self, phone=None, email=None, name=None):
		phone = phone or unique_phone()
		doc = make_session(
			full_name=name or unique_name(),
			email=email or unique_email(),
			phone_raw=phone,
			phone_e164=to_e164(phone),
		)
		doc.email_verified = 1
		doc.phone_verified = 1
		return doc

	def test_existing_website_account_on_the_email_blocks(self):
		email = unique_email()
		make_website_user(email)
		verdict = matching.classify(self._verified_session(email=email))
		self.assertEqual(verdict["result"], matching.EMAIL_ACCOUNT_EXISTS)

	def test_existing_account_on_the_phone_blocks(self):
		phone = unique_phone()
		customer, _c = make_customer_with_contact()
		user = make_website_user(unique_email())
		make_identity(user.name, customer.name, to_e164(phone), user.name)

		verdict = matching.classify(self._verified_session(phone=phone))
		self.assertEqual(verdict["result"], matching.PHONE_ACCOUNT_EXISTS)

	def test_candidate_customer_already_linked_blocks(self):
		phone = unique_phone()
		customer, _c = make_customer_with_contact(phone=phone)
		user = make_website_user(unique_email())
		make_identity(user.name, customer.name, to_e164(unique_phone()), user.name)

		verdict = matching.classify(self._verified_session(phone=phone))
		self.assertEqual(verdict["result"], matching.CUSTOMER_ALREADY_LINKED)

	def test_blocking_checks_run_before_classification(self):
		# An email that already has an account must block even when the
		# phone would otherwise be a clean strong match.
		name = unique_name("Ahmed")
		phone = unique_phone()
		email = unique_email()
		make_customer_with_contact(customer_name=name, phone=phone)
		make_website_user(email)

		verdict = matching.classify(self._verified_session(name=name, phone=phone, email=email))
		self.assertEqual(verdict["result"], matching.EMAIL_ACCOUNT_EXISTS)


class TestRecognitionPayload(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def _customer_with_address(self, name):
		customer, _contact = make_customer_with_contact(customer_name=name)
		address = frappe.new_doc("Address")
		address.update(
			{
				"address_title": name,
				"address_type": "Shipping",
				"address_line1": "12 Secret Street, Flat 9",
				"city": "Damietta",
				"country": "Egypt",
			}
		)
		address.append("links", {"link_doctype": "Customer", "link_name": customer.name})
		address.flags.ignore_permissions = True
		address.insert(ignore_permissions=True)
		return customer

	def test_payload_carries_no_field_the_api_would_accept_back(self):
		"""The card is display-only.

		Note this site names Customers by their `customer_name` (Selling
		Settings `cust_master_name`), so on a confirmed match the shown
		name *is* the primary key. That is harmless precisely because no
		endpoint takes a Customer identifier as input - `decide` accepts
		only yes or no - so the guarantee asserted here is about the
		payload's shape, not about hiding a string.
		"""
		customer = self._customer_with_address(unique_name("Ahmed"))
		doc = make_session(phone_e164="+201012345678")
		payload = matching.recognition_payload(doc, matching.STRONG_MATCH, customer.name)

		self.assertEqual(
			set(payload),
			{"kind", "phone", "name", "company", "company_on_record",
			 "address", "governorate", "country", "blurred"},
		)
		for forbidden in ("customer", "candidate", "candidate_customer", "docname", "id"):
			self.assertNotIn(forbidden, payload)

	def test_the_street_is_shown_and_the_governorate_is_not(self):
		"""The opposite of the instinctive choice, and deliberate.

		Recognition is the card's only job. A governorate shared by
		millions helps nobody pick out their own record; a street does it
		at a glance. The cost is stated in `recognition_payload` and
		accepted: somebody who proves a matching phone or email and types
		an agreeing name is shown a third party's street.
		"""
		customer = self._customer_with_address(unique_name("Ahmed"))
		doc = make_session(phone_e164="+201012345678")
		payload = matching.recognition_payload(doc, matching.STRONG_MATCH, customer.name)

		self.assertEqual(payload["address"], "12 Secret Street, Flat 9")
		self.assertEqual(payload["governorate"], matching.BLOCK * len("Damietta"))
		self.assertEqual(payload["country"], matching.BLOCK * len("Egypt"))
		self.assertEqual(sorted(payload["blurred"]), ["country", "governorate"])

	def test_hidden_values_are_replaced_before_they_are_sent(self):
		# The blur on the card is styling. What makes it a guarantee is
		# that the characters are gone from the response, so there is
		# nothing in the page to read back out of it.
		customer = self._customer_with_address(unique_name("Ahmed"))
		doc = make_session(phone_e164="+201012345678")
		payload = matching.recognition_payload(doc, matching.STRONG_MATCH, customer.name)

		serialised = frappe.as_json(payload)
		self.assertNotIn("Damietta", serialised)
		self.assertNotIn("Egypt", serialised)

	def test_a_governorate_in_the_state_field_is_preferred_to_the_city(self):
		# `state` is the governorate on a properly filled Address. It is
		# empty on every record this site currently holds, which is why
		# the city is the fallback - but records arriving correctly filled
		# must not be read wrongly.
		customer = self._customer_with_address(unique_name("Ahmed"))
		address = frappe.db.get_value(
			"Dynamic Link",
			{"parenttype": "Address", "link_doctype": "Customer", "link_name": customer.name},
			"parent",
		)
		frappe.db.set_value("Address", address, "state", "Kafr El Sheikh", update_modified=False)

		doc = make_session(phone_e164="+201012345678")
		payload = matching.recognition_payload(doc, matching.STRONG_MATCH, customer.name)

		self.assertEqual(payload["governorate"], matching.BLOCK * len("Kafr El Sheikh"))

	def test_masks_the_phone_number(self):
		customer = self._customer_with_address(unique_name("Ahmed"))
		doc = make_session(phone_e164="+201012345678")
		payload = matching.recognition_payload(doc, matching.STRONG_MATCH, customer.name)
		self.assertNotIn("1012345678", payload["phone"])
		self.assertIn("*", payload["phone"])

	def test_a_verified_phone_shows_the_name_it_disagrees_with(self):
		"""The business decision, stated as a test.

		A verified Egyptian mobile is trusted to identify its holder, so
		the stored name is shown even when it disagrees with what was
		typed - that disagreement is precisely what the person needs to
		see to answer the question, and answering it is what the name
		card is for.

		The accepted cost: a reassigned number shows the previous
		holder's name. What bounds it is that the answer renames their
		own login and nothing else - the Contact and the Customer wait
		for staff either way.
		"""
		other_name = unique_name("Mohamed")
		customer = self._customer_with_address(other_name)
		doc = make_session(phone_e164="+201012345678")

		payload = matching.recognition_payload(doc, matching.PHONE_NAME_MISMATCH, customer.name)
		self.assertEqual(payload["name"], other_name)
		self.assertNotIn("name", payload["blurred"])

	def test_shows_the_whole_name_when_it_already_agrees(self):
		"""In full, not half of it.

		A half-shown name is worse than none: recognising your own record
		is the card's entire job, and "Ahmed ▓▓▓▓ ▓▓▓▓" asks somebody to
		do that from a first name a great many people share. What protects
		a third party is sending no name at all, which is what a
		disagreeing one still gets.
		"""
		name = unique_name("Ahmed")
		customer = self._customer_with_address(name)
		doc = make_session(phone_e164="+201012345678")
		payload = matching.recognition_payload(doc, matching.STRONG_MATCH, customer.name)

		self.assertEqual(payload["name"], name)
		self.assertNotIn(matching.BLOCK, payload["name"])


class TestTheCardKnowsWhatKindOfRecordItIs(FrappeTestCase):
	"""A company's name is not the name of whoever answers its phone.

	The card used to print `customer_name` under "Name" whatever the
	Customer was, so an individual signing up was told their name was
	"الارف" - the business that happened to hold the number. The person
	and the business are separate fields now, and which of them is filled
	depends on what the record actually is.
	"""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def record(self, *, customer_type, customer_name, contact_name=None):
		customer, _c = make_customer_with_contact(
			customer_name=customer_name,
			contact_name=contact_name or customer_name,
			phone=unique_phone(),
		)
		frappe.db.set_value("Customer", customer.name, "customer_type", customer_type)
		return customer.name

	def test_an_individual_record_shows_a_person_and_no_company(self):
		person = unique_name("Ahmed")
		customer = self.record(customer_type="Individual", customer_name=person)
		doc = make_session(phone_e164="+201012345678", full_name=person)

		card = matching.recognition_payload(doc, matching.STRONG_MATCH, customer)
		self.assertEqual(card["name"], person)
		self.assertIsNone(card["company"])
		self.assertFalse(card["company_on_record"])

	def test_a_company_record_shows_the_business_and_its_contact(self):
		company, person = unique_name("Acme"), unique_name("Ahmed")
		customer = self.record(
			customer_type="Company", customer_name=company, contact_name=person
		)
		doc = make_session(phone_e164="+201012345678", full_name=person)

		card = matching.recognition_payload(doc, matching.STRONG_MATCH, customer)
		# The person is the contact; the company is named as the company.
		self.assertEqual(card["name"], person)
		self.assertEqual(card["company"], company)

	def test_a_company_signup_on_a_company_record_is_not_warned(self):
		company, person = unique_name("Acme"), unique_name("Ahmed")
		customer = self.record(
			customer_type="Company", customer_name=company, contact_name=person
		)
		doc = make_session(
			phone_e164="+201012345678", full_name=person,
			account_type="Company", company_name=company,
		)

		card = matching.recognition_payload(doc, matching.STRONG_MATCH, customer)
		self.assertEqual(card["company"], company)
		# They said they were a business and the record is one. Telling
		# them a business holds the number would be telling them what they
		# just said.
		self.assertFalse(card["company_on_record"])

	def test_an_individual_signup_is_told_a_business_holds_the_number(self):
		company, person = unique_name("Acme"), unique_name("Ahmed")
		customer = self.record(
			customer_type="Company", customer_name=company, contact_name=person
		)
		doc = make_session(phone_e164="+201012345678", full_name=person)

		card = matching.recognition_payload(doc, matching.STRONG_MATCH, customer)
		self.assertEqual(card["company"], company)
		self.assertTrue(
			card["company_on_record"],
			"an individual was shown a company's record with nothing said about it",
		)

	def test_a_partnership_is_a_business_too(self):
		firm, person = unique_name("Beta"), unique_name("Ahmed")
		customer = self.record(
			customer_type="Partnership", customer_name=firm, contact_name=person
		)
		doc = make_session(phone_e164="+201012345678", full_name=person)

		card = matching.recognition_payload(doc, matching.STRONG_MATCH, customer)
		self.assertEqual(card["company"], firm)
		self.assertTrue(card["company_on_record"])

	def test_a_withheld_card_discloses_neither(self):
		company = unique_name("Acme")
		customer = self.record(customer_type="Company", customer_name=company)
		doc = make_session(phone_e164="+201012345678")

		card = matching.recognition_payload(doc, matching.EMAIL_NAME_MISMATCH, customer)
		self.assertIsNone(card["name"])
		self.assertIsNone(card["company"])
		self.assertFalse(card["company_on_record"])
		self.assertNotIn(company, str(card))
