# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Build one fixture per A-scenario, and the plan for walking it.

Each scenario needs a Customer that staff might plausibly have left
behind - a Contact with a number, sometimes an email, an Address - and a
statement of what the browser should type against it. Both are written
together into `afix.json` so the intent of a case is readable in one
place, and so the purge afterwards can work from the exact names this
built rather than a pattern that might match something real.

Fixture names carry no digits on purpose: `contact_enhancements` strips
them on every Contact save, so `Ahmed Sabry Test1234` reads back as
`Ahmed Sabry Test` and every "same name" scenario would quietly become a
mismatch and test the wrong branch.
"""

import json
import os
import time

import frappe

from custom_webshop.signup.audit import clear_rate_limits

OUT = os.environ.get("OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".run")
S = int(time.time())

GROUP = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
TERRITORY = frappe.db.get_value("Territory", {"is_group": 0}, "name")


def tag(n):
	"""A unique all-letter suffix, so normalisation leaves the name alone."""
	out, v = "", S * 10 + n
	while v:
		out, v = chr(ord("a") + v % 26) + out, v // 26
	return out.capitalize()


def phone(n):
	"""A unique Egyptian mobile.

	The `010` prefix is pinned rather than derived: a run whose timestamp
	produced `013` or `019` would build numbers `phonenumbers` rejects,
	and the whole walk would fail on the details step for a reason that
	has nothing to do with what is being tested.
	"""
	return "010{:08d}".format((S * 7 + n * 131) % 100000000)


def fresh_phone(n):
	return "010{:08d}".format((S * 7 + 900 + n * 131) % 100000000)


def build(n, *, street, disabled=False, with_email=True):
	"""A Customer with its Contact and Address, as staff would have left it."""
	name = f"Ahmed Sabry {tag(n)}"
	email = f"a{n}fix{S}@example.com"
	number = phone(n)

	contact = frappe.new_doc("Contact")
	contact.first_name = name
	contact.append("phone_nos", {"phone": number, "is_primary_mobile_no": 1})
	if with_email:
		contact.append("email_ids", {"email_id": email, "is_primary": 1})
	contact.insert(ignore_permissions=True)

	customer = frappe.new_doc("Customer")
	customer.update({
		"customer_name": name,
		"customer_type": "Individual",
		"customer_group": GROUP,
		"territory": TERRITORY,
		"customer_primary_contact": contact.name,
		"disabled": 1 if disabled else 0,
	})
	customer.flags.ignore_mandatory = True
	customer.insert(ignore_permissions=True)

	contact.reload()
	contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	contact.save(ignore_permissions=True)

	address = frappe.new_doc("Address")
	address.update({
		"address_title": name, "address_type": "Shipping",
		"address_line1": street, "city": "دمياط", "country": "Egypt",
	})
	address.append("links", {"link_doctype": "Customer", "link_name": customer.name})
	address.insert(ignore_permissions=True)
	frappe.db.set_value("Customer", customer.name, "customer_primary_address", address.name,
	                    update_modified=False)

	contact.reload()
	return {"customer": customer.name, "contact": contact.name,
	        "stored_name": contact.full_name, "email": email if with_email else None,
	        "phone": number, "street": street}


fixtures = {
	# A1 is the empty-system case - there is nothing to build.
	"A1": {"customer": None, "contact": None, "stored_name": None,
	       "email": None, "phone": phone(1), "street": None},
	"A2": build(2, street="12 El Nasr Street"),
	"A3": build(3, street="7 Corniche Road"),
	"A4": build(4, street="44 Ahmed Orabi Street"),
	# A5 and A6 must be reachable by the phone alone, so no email.
	"A5": build(5, street="3 Gomhoria Street", with_email=False),
	"A6": build(6, street="19 El Geish Road", with_email=False),
	"A7": build(7, street="8 Port Said Street"),
	"A8": build(8, street="21 El Horreya Avenue"),
	"A9": build(9, street="5 El Zahraa Street", disabled=True),
}

other = f"Kareem Adel {tag(90)}"
fresh_email = lambda n: f"new{n}fix{S}@example.com"  # noqa: E731

#: What the browser types, and how it answers. `answer` is None where the
#: scenario expects to never be asked; `name_choice` answers the second
#: card, which only appears when the stored name differs from the typed
#: one - the book's A4 and A5 both keep the record's own spelling.
plan = {
	"A1": dict(email=fresh_email(1), phone=fixtures["A1"]["phone"],
	           name=f"Ahmed Sabry {tag(1)}", answer=None),
	"A2": dict(email=fixtures["A2"]["email"], phone=fixtures["A2"]["phone"],
	           name=fixtures["A2"]["stored_name"], answer=True),
	"A3": dict(email=fixtures["A3"]["email"], phone=fixtures["A3"]["phone"],
	           name=fixtures["A3"]["stored_name"], answer=False),
	"A4": dict(email=fixtures["A4"]["email"], phone=fixtures["A4"]["phone"],
	           name=other, answer=True, name_choice="keep"),
	"A5": dict(email=fresh_email(5), phone=fixtures["A5"]["phone"],
	           name=other, answer=True, name_choice="keep"),
	"A6": dict(email=fresh_email(6), phone=fixtures["A6"]["phone"],
	           name=other, answer=False),
	"A7": dict(email=fixtures["A7"]["email"], phone=fresh_phone(7),
	           name=fixtures["A7"]["stored_name"], answer=True),
	"A8": dict(email=fixtures["A8"]["email"], phone=fresh_phone(8),
	           name=other, answer=None),
	"A9": dict(email=fixtures["A9"]["email"], phone=fixtures["A9"]["phone"],
	           name=fixtures["A9"]["stored_name"], answer=True),
}

#: Languages are alternated rather than doubled: every scenario is walked
#: once, and both renderings are still exercised across the set.
langs = {"A1": "en", "A2": "en", "A3": "ar", "A4": "en", "A5": "ar",
         "A6": "en", "A7": "ar", "A8": "en", "A9": "ar"}

# Nine signups from one address in five minutes is exactly the per-IP cap
# the endpoint is there to enforce, and hitting it halfway through reads
# as "no code arrived" rather than as a limit. Clearing first is the
# documented way to walk the list - see signup/audit.clear_rate_limits.
cleared = clear_rate_limits()

frappe.db.commit()
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "afix.json"), "w") as fh:
	json.dump({"stamp": S, "fixtures": fixtures, "plan": plan, "langs": langs},
	          fh, indent=1, ensure_ascii=False)
print(f"  built 8 fixtures, stamp {S}; cleared {cleared} rate-limit counters")
