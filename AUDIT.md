# The data audit, explained

```bash
bench --site erpnext execute custom_webshop.signup.audit.report
```

Read-only. It runs eleven queries, changes nothing, and is safe at any time.
It exists because a migration would have to make judgement calls about
these records, and those calls belong to a person, not a script.

---

## Read this first

The raw counts look worse than the situation is. **Most of what the audit
finds is ERPNext's and Frappe's own test-fixture data** — records named
`_Test Customer`, `_Test Contact For _Test Supplier`, and the three demo
companies (`Palmer Productions Ltd.`, `West View Software Ltd.`,
`Grant Plastics Ltd.`) that ship with a fresh ERPNext install.

Current run, separated honestly:

| Check | Count | Actually real | What the real ones are |
|---|---|---|---|
| `contact_phones_missing_canonical_form` | 4 | **2** | `015545454545` (12 digits), `011011012121212121` (18 digits). Other 2 are `+91` fixtures. |
| `contacts_sharing_a_phone` | 1 | **1** | `+201101271160` on `Omar Sabry-1/-2/-3` |
| `contacts_sharing_an_email` | 1 | 0 | Two `_Test Contact` fixtures |
| `orphan_contacts` | 16 | **~5** | `Omar Sabry`, `Omar Sabry-2`, `Omar Sabry-3`, `Ahmed Sabry`, `Auto Direction Test` |
| `customers_missing_primary_contact` | 11 | **0** | All 11 are `_Test*` fixtures or the 3 demo companies |
| `customers_missing_primary_address` | 13 | **2** | `Amir Sabry`, `Master Ahmed Amin` |
| `website_users_without_a_customer` | 4 | 0 | All `_Test*` / `testperm@` fixtures |
| `users_with_multiple_customers` | 0 | 0 | — |
| `customers_with_multiple_accounts` | 0 | 0 | — |
| `accounts_without_a_verified_identity` | 0 | 0 | — |
| `unparseable_customer_mobiles` | 1 | **1** | `OMAR SABRY` → `011011012121212121` |

**The real backlog is about five records, all in one cluster** — the
"Omar Sabry / Ahmed Sabry" duplicates, plus one Customer carrying an
18-digit phone number.

---

## What each check means

### `contact_phones_missing_canonical_form`
Contact Phone rows with no E.164 value in `custom_phone_e164`, the indexed
column identity matching queries.

The `would_parse_now` flag splits two very different populations:

- **`True`** — a perfectly good number that simply predates the column.
  Invisible to matching until backfilled. **The backfill patch already ran**
  (`custom_webshop.patches.backfill_contact_phone_e164`): 16 canonicalised,
  4 rejected. There are none of these left.
- **`False`** — not a phone number at all. `015545454545` is 12 digits where
  an Egyptian mobile is 11; `011011012121212121` is 18. No amount of
  backfilling helps. Someone has to look at them.

**Impact:** the owner of one of those numbers signs up and matching finds
nothing, so they get a fresh Customer. That is the safe failure — a
duplicate for staff to merge, not a mis-attributed account.

**Action:** fix or clear the two bad numbers. Low priority.

### `contacts_sharing_a_phone`
One canonical number on more than one Contact.

`+201101271160` sits on `Omar Sabry-1`, `-2` and `-3`. This is exactly the
fragmentation the old signup produced: it deduplicated on the
`customer_name` string, so the same person signing up twice got
`Omar Sabry`, then `Omar Sabry-1`, and so on, courtesy of ERPNext's
`" - N"` collision suffix.

**Impact:** if two or more of them linked to *Customers*, a signup on that
number would classify `MULTIPLE_MATCH` — the engine refuses to choose and
raises a conflict. Here `-2` and `-3` are orphans with no Customer link at
all, so a signup on this number currently finds nothing and gets a clean
new record.

**Action:** decide whether these are one person and merge. This is a
judgement call — see *Why merging is not automated*.

### `orphan_contacts`
Contacts with no Dynamic Link to anything — no Customer, no Supplier, no
Lead. Dead weight that still occupies a phone number.

**Impact:** almost none. Matching resolves Contact → Customer through the
Dynamic Link table, so a Contact with no link contributes no candidate.

**Action:** housekeeping. Deleting them is safe but not urgent, and I have
deliberately not scripted it.

### `customers_missing_primary_contact` / `..._primary_address`
Customers that **staff cannot save from the Desk**, because
`contact_enhancements` makes both fields mandatory
(`setup/property_setters.py`). Opening one and pressing Save is blocked
until the missing field is filled.

`customers_missing_primary_address` is expected to grow: **every Customer
the signup flow creates starts without an address**, because a signup has
no address to record until checkout. That is by design, not a defect. The
`primary_contact` list is the one that indicates a genuine gap — and right
now every entry in it is fixture or demo data.

**Action:** none required. Worth knowing before staff hit it.

### `website_users_without_a_customer`
Accounts that can log in but resolve to no Customer — no cart, no orders,
no identity. All four here are Frappe's own test users.

### `users_with_multiple_customers` / `customers_with_multiple_accounts`
Ambiguity that a person has to resolve before an identity row can be
written. **Both are zero**, which is the important part of this report.

### `accounts_without_a_verified_identity`
Portal accounts that predate this flow. They still resolve through the
Portal User fallback in `signup/resolution.py`, and the portal-access guard
deliberately leaves them alone — with no verified identity there is no
opinion to enforce.

**This is zero too.** There are no Portal User rows for Customers on this
site at all. Which means:

> **The identity backfill everyone is worried about would currently do
> nothing.** There is no legacy portal account to migrate. It becomes
> relevant only once real customers have signed up, or if Portal User rows
> get created some other way.

### `unparseable_customer_mobiles`
`Customer.mobile_no` values that are not valid numbers. One: `OMAR SABRY`
with `011011012121212121`.

Note this field is a **read-only mirror** of the primary contact
(`fetch_from: customer_primary_contact.mobile_no`), so a value like this
was written directly with `db_set`, bypassing the mirror. Fixing it means
fixing the Contact, not the Customer.

---

## Why merging is not automated

Three of these checks — duplicate phones, duplicate emails, and
`users_with_multiple_customers` — can only be resolved by deciding **that
two records are the same person**. That decision is not reversible in the
way code changes are:

- `frappe.rename_doc(..., merge=True)` on a Customer moves **Sales Orders,
  Sales Invoices, Payment Entries, Addresses, Contacts and the whole
  accounting history** onto the surviving record.
- ERPNext's own `Customer.before_rename` blocks a merge when the two
  records' GL currencies conflict — because getting it wrong corrupts the
  ledger.
- There is no undo. Restoring from a backup is the undo.

A script deciding that `Omar Sabry-2` and `Omar Sabry-3` are the same
person would be guessing on exactly the evidence — a shared phone number,
a similar name — that the whole matching engine is built to treat as
*insufficient on its own*. It would be inconsistent to refuse that
inference at signup and then make it in bulk at migration time.

So the audit surfaces them and stops. What **is** automated is the one
migration that cannot be wrong: filling in a derived column this app owns
and nothing else reads.

---

## What the backfill actually did

`custom_webshop.patches.backfill_contact_phone_e164`, run automatically on
`bench migrate`:

```
custom_webshop: canonicalised 16 phone number(s); 4 could not be parsed
and were left empty.
```

It wrote to **one column, `Contact Phone.custom_phone_e164`**, created by
this app, read by nothing else, and displayed nowhere. It never touched
`phone`, never touched a Customer, Contact or Address record, and cannot
change what any existing record means. A row it could not parse was left
exactly as it already was — empty.

It also used `update_modified=False`, so a data-quality backfill did not
make every Contact in the system look freshly edited.

That is why it ships unattended and the identity backfill does not.

---

## If you want to act on this

Reasonable order, none of it urgent:

1. **Fix the two bad phone numbers.** Edit the Contacts; the validate hook
   recomputes the canonical column on save.
2. **Look at the Omar Sabry cluster.** Three Contacts, one phone, two
   orphaned. Decide if it is one person, then merge or delete in the Desk.
3. **Leave the `_Test*` fixtures alone** unless you are cleaning the site
   generally — they are framework test data and will come back.
4. **Ignore `customers_missing_primary_address`** as a signal. It grows by
   design.

Re-run the audit afterwards to confirm.

## Writing it to CSV

```bash
bench --site erpnext console
```
```python
from custom_webshop.signup.audit import report
report(out_dir="/tmp/signup-audit")
```

One file per non-empty check, for review in a spreadsheet.
