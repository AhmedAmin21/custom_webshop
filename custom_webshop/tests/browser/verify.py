# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Check the records each A-scenario left behind.

The walk records what the page showed; this is where the scenario book's
promises are actually tested - which Customer the account ended up on,
whether the verified number moved, and exactly which conflicts were
queued.
"""

import json
import os

import frappe

from custom_webshop.signup.identity import to_e164

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT") or os.path.join(HERE, ".run")
RUN = json.load(open(os.path.join(OUT, "afix.json")))
_walk = json.load(open(os.path.join(OUT, "walk.json")))
FIX, PLAN = RUN["fixtures"], RUN["plan"]

# A walk that died partway leaves the previous run's results behind, and
# comparing this run's fixtures against those produces a page of failures
# that have nothing to do with the code. Refuse rather than report them.
if _walk.get("stamp") != RUN["stamp"]:
	raise SystemExit(
		f"walk.json is from run {_walk.get('stamp')}, fixtures are from {RUN['stamp']} - "
		"the browser walk did not finish, so there is nothing to check."
	)

WALK = _walk["cases"]

FAIL = []

def check(case, label, got, want):
	ok = got == want
	if not ok:
		FAIL.append(f"{case} · {label}: got {got!r} want {want!r}")
	print(f"    [{'ok  ' if ok else 'FAIL'}] {label}: {got!r}")


def account(email):
	"""The identity row a finished signup leaves, or None."""
	return frappe.db.get_value("Webshop Account Identity", {"user": email},
	                           ["user", "contact", "customer", "phone_e164"], as_dict=True)


def conflicts(email):
	"""Everything queued for this signup, by problem.

	One conflict is opened per signup now and each thing wrong with it is
	a row on that conflict, so the case's problems are what to check -
	`conflict_type` is only the headline the queue lists it under.
	"""
	found = []
	for name in frappe.get_all("Webshop Identity Conflict",
	                           filters={"email_normalized": email}, pluck="name"):
		found += frappe.get_all("Webshop Identity Problem",
		                        filters={"parent": name}, pluck="problem_type")

	return sorted(found)


def phone_rows(contact):
	return frappe.get_all("Contact Phone", filters={"parent": contact, "parenttype": "Contact"},
	                      pluck="phone")


def shows_the_record_name(case):
	"""Whether an unblurred row on the card carried the record's own name."""
	stored = (FIX[case]["stored_name"] or "").strip()
	rows = WALK.get(case, {}).get("rows") or []
	return bool(stored) and any(stored in r["value"] and not r["blurred"] for r in rows)


for case in sorted(PLAN):
	plan, fix, seen = PLAN[case], FIX[case], WALK.get(case, {})
	email = plan["email"]
	acct, found, e164 = account(email), conflicts(email), to_e164(plan["phone"])
	print(f"\n{case}  state={seen.get('state')}  conflicts={found or 'none'}")

	if not acct:
		FAIL.append(f"{case}: no account was created for {email}")
		print(f"    [FAIL] no account for {email}")
		continue

	if case == "A1":
		check(case, "no card offered", seen.get("state"), "READY")
		check(case, "customer points back at the contact",
		      frappe.db.get_value("Customer", acct.customer, "customer_primary_contact"),
		      acct.contact)
		check(case, "number on the contact", e164 in phone_rows(acct.contact), True)
		# A signup that has to make its own Customer has no address to put
		# on it - `customer_primary_address` is genuinely required - but
		# that no longer raises a conflict of its own (it fired on every
		# such case and held nothing open; see conflicts.INFORMATIONAL).
		check(case, "nothing queued", found, [])

	elif case == "A2":
		check(case, "card was shown", seen.get("state"), "MATCH_REVIEW")
		check(case, "name shown in the clear", shows_the_record_name(case), True)
		check(case, "linked to the existing customer", acct.customer, fix["customer"])
		check(case, "no second contact", acct.contact, fix["contact"])
		check(case, "nothing queued", found, [])

	elif case in ("A3", "A6"):
		check(case, "card was shown", seen.get("state"), "MATCH_REVIEW")
		check(case, "own new customer", acct.customer != fix["customer"], True)
		check(case, "verified number not written to the new contact", phone_rows(acct.contact), [])
		check(case, "number held as pending",
		      frappe.db.get_value("Contact", acct.contact, "custom_pending_phone_e164"), e164)
		check(case, "number still on the original contact", e164 in phone_rows(fix["contact"]), True)
		check(case, "both conflicts queued", found,
		      sorted(["PHONE_ALREADY_ASSOCIATED", "USER_REJECTED_MATCH"]))

	elif case == "A4":
		check(case, "card was shown", seen.get("state"), "MATCH_REVIEW")
		check(case, "name shown even though it disagrees", shows_the_record_name(case), True)
		check(case, "linked to the existing customer", acct.customer, fix["customer"])
		check(case, "the record kept its own name",
		      frappe.db.get_value("Customer", acct.customer, "customer_name"), fix["stored_name"])
		check(case, "nothing queued", found, [])

	elif case == "A5":
		# A verified phone is trusted to identify its holder, so the name
		# is shown even though only the phone matched - and the walk keeps
		# the record's own spelling, which disputes nothing. Nothing is
		# queued; the review only happens when somebody takes a name that
		# disagrees, which is B-territory.
		check(case, "card was shown", seen.get("state"), "MATCH_REVIEW")
		check(case, "the name is shown, on the strength of the phone",
		      shows_the_record_name(case), True)
		check(case, "linked to the existing customer", acct.customer, fix["customer"])
		check(case, "the record was not rewritten",
		      frappe.db.get_value("Customer", acct.customer, "customer_name"), fix["stored_name"])
		check(case, "nothing queued", found, [])

	elif case == "A7":
		check(case, "card was shown", seen.get("state"), "MATCH_REVIEW")
		check(case, "name shown in the clear", shows_the_record_name(case), True)
		check(case, "linked to the existing customer", acct.customer, fix["customer"])
		check(case, "reused the existing contact", acct.contact, fix["contact"])
		check(case, "new number added to that contact", e164 in phone_rows(fix["contact"]), True)
		check(case, "nothing queued", found, [])

	elif case == "A8":
		check(case, "no card offered", seen.get("state"), "READY")
		check(case, "own new customer", acct.customer != fix["customer"], True)
		check(case, "queued for review", found, ["NAME_MISMATCH"])

	elif case == "A9":
		# `classify` refuses to link a disabled record automatically -
		# "re-opening a disabled customer is not a matching rule's
		# decision" - so the person is asked, and whatever they answer a
		# person sees it. The link itself is allowed: both channels
		# matched, and turning away a real owner over a flag they cannot
		# see would be worse. What must never happen is it passing
		# silently, or the record being re-enabled on the way through.
		check(case, "never linked automatically - asked instead",
		      seen.get("state"), "MATCH_REVIEW")
		check(case, "the disabled record was not silently re-opened",
		      frappe.db.get_value("Customer", fix["customer"], "disabled"), 1)
		check(case, "the outcome reaches staff", found, ["MATCHED_CUSTOMER_DISABLED"])

print("\n" + "=" * 72)
print("A-SCENARIOS ALL PASS" if not FAIL else f"{len(FAIL)} FAILURES:")
for problem in FAIL:
	print("   -", problem)
raise SystemExit(1 if FAIL else 0)
