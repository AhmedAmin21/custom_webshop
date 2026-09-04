# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Delete everything one A-scenario run created.

Works from the run's own manifest rather than a name pattern: fixtures go
by the exact names the builder recorded, and the accounts by the run's
stamped address. Neither can reach a record this test did not make.
"""

import json
import os

import frappe

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT") or os.path.join(HERE, ".run")
manifest = os.path.join(OUT, "afix.json")
if not os.path.exists(manifest):
	print("  nothing to purge")
	raise SystemExit(0)

RUN = json.load(open(manifest))
like = f"%fix{RUN['stamp']}@example.com"

contacts = {f["contact"] for f in RUN["fixtures"].values() if f["contact"]}
customers = {f["customer"] for f in RUN["fixtures"].values() if f["customer"]}
users = frappe.get_all("User", filters={"email": ["like", like]}, pluck="name")

for row in frappe.get_all("Webshop Account Identity", filters={"user": ["like", like]},
                          fields=["name", "customer", "contact"]):
	if row.customer:
		customers.add(row.customer)
	if row.contact:
		contacts.add(row.contact)
	frappe.delete_doc("Webshop Account Identity", row.name, force=True, ignore_permissions=True)

for doctype in ("Webshop Identity Conflict", "Webshop Signup Session"):
	for name in frappe.get_all(doctype, filters={"email_normalized": ["like", like]}, pluck="name"):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)

# Addresses and the primary-contact pointers go before the records they
# point at, or the deletes trip over link validation.
for customer in list(customers):
	if not frappe.db.exists("Customer", customer):
		continue
	for address in frappe.get_all("Dynamic Link",
	                              filters={"parenttype": "Address", "link_doctype": "Customer",
	                                       "link_name": customer}, pluck="parent"):
		frappe.delete_doc("Address", address, force=True, ignore_permissions=True)
	frappe.db.set_value("Customer", customer,
	                    {"customer_primary_contact": None, "customer_primary_address": None},
	                    update_modified=False)

for name in contacts:
	if frappe.db.exists("Contact", name):
		frappe.delete_doc("Contact", name, force=True, ignore_permissions=True)
for name in customers:
	if frappe.db.exists("Customer", name):
		frappe.delete_doc("Customer", name, force=True, ignore_permissions=True)
for name in users:
	frappe.delete_doc("User", name, force=True, ignore_permissions=True)

frappe.db.commit()
os.remove(manifest)
print(f"  purged users={len(users)} contacts={len(contacts)} customers={len(customers)}")
