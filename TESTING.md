# Testing the verified signup flow

Everything here has been run against this bench. Commands assume you are in
`/home/frappe/frappe-bench` and the site is `erpnext` — substitute your own
site name if it differs.

---

## 0. Sixty-second version

```bash
# 1. run the automated suite
bench --site erpnext run-tests --app custom_webshop

# 2. turn the flow on in dev mode (no email/SMS gateway needed)
bench --site erpnext console
```
```python
frappe.db.set_single_value("Website Settings", "disable_signup", 0)
frappe.db.set_single_value("Webshop Signup Settings", {
    "signup_enabled": 1, "email_otp_enabled": 1,
    "phone_otp_enabled": 1, "email_otp_dev_mode": 1, "phone_otp_dev_mode": 1,
})
frappe.db.commit()
```
```bash
# 3. serve, then open /login and press "Create one"
bench serve --port 8000

# 4. read the passcodes it would have sent
tail -f logs/custom_webshop.signup.log | grep --line-buffered otp_dev_mode
```

When you are done, go to **§9 Resetting**.

---

## 1. The six switches

Signup only runs when **all** of these agree. `custom_webshop.api.signup.is_available()`
is the single function that decides, and the login page renders its
"Create one" button from that same function — so the button appears if and
only if the flow behind it will work.

| Switch | Where | Purpose |
|---|---|---|
| `disable_signup` | Website Settings | Site-wide kill switch. **Must be 0.** Outermost layer — flipping it to 1 stops everything instantly with no deploy. |
| `signup_enabled` | Webshop Signup Settings | This app's own switch. |
| `email_otp_enabled` | Webshop Signup Settings | Email verification step. |
| `phone_otp_enabled` | Webshop Signup Settings | SMS verification step. |
| `email_otp_dev_mode` | Webshop Signup Settings | Writes email passcodes to the log **instead of emailing them**. Lets you test with no Email Account. |
| `phone_otp_dev_mode` | Webshop Signup Settings | Writes phone passcodes to the log **instead of texting them**. Lets you test with no SMS gateway. Independent of the email flag — one channel can go live while the other stays in dev mode. |

One more worth knowing about, though it is not a switch:
`signup_starts_per_hour_per_ip` (default **30**) caps how many signups one IP
may begin per hour. Keep it generous — Egyptian mobile carriers put many
subscribers behind a single public address, so a tight value turns away real
customers long before it inconveniences anyone abusing the endpoint. The
controls that actually bound abuse are per-session: five codes per channel,
five verify attempts per code, and a resend cooldown.

The flow **fails closed**: if either channel is off and dev mode is off,
signup refuses to start. That is deliberate — the phone number is the
primary identity signal, so a site that cannot send an SMS must not be
resolving customers against unproven numbers.

Open the settings in the Desk at **Webshop Signup Settings**, or set them
from the console as in §0.

---

## 2. Reading passcodes in dev mode

Passcodes are never returned by any endpoint and never stored in plaintext —
only a keyed HMAC is written down. In dev mode the code goes to the log
instead of to the person.

```bash
# follow live
tail -f logs/custom_webshop.signup.log | grep --line-buffered otp_dev_mode

# or just grab the most recent one
grep -o "'code': '[0-9]*'" logs/custom_webshop.signup.log | tail -1 | grep -o "[0-9]\{6\}"
```

A line looks like this — note the destination is masked even here:

```
2026-08-29 21:39:32 WARNING custom_webshop.signup {'event': 'otp_dev_mode_not_sent',
 'channel': 'email', 'destination': 'g**********@example.com', 'code': '376223'}
```

There are two copies of the log: `logs/custom_webshop.signup.log` (bench-wide)
and `sites/erpnext/logs/custom_webshop.signup.log` (per-site). Either works.

> **Never enable `email_otp_dev_mode` or `phone_otp_dev_mode` in
> production.** They are the only place a passcode is ever written down.

---

## 3. Browser walkthrough — the happy path

1. Go to `/login`. You should see the login card with a **"No account?"**
   divider and a **"Create one"** button underneath.
   *If the button is missing, one of the five switches in §1 is off.*
2. Press it. You land on **step 1 of 5: "Who is this account for?"** —
   *For myself* / *For my company*.
3. **Step 2: Your details.** Full name (three parts minimum), email, mobile.
   Company accounts get an extra company-name field.
4. **Step 3: Check your email.** Grab the code from the log (§2), type it in.
   Try **Resend** and **Change email** here too.
5. **Step 4: Check your phone.** Same again, with **Change number**.
6. **Step 5: Choose a password.** Password + confirm.
7. You are logged in and redirected to `/shop`.

Refresh the page at any step — the wizard resumes exactly where you were.
Switch the language with the globe button — the whole wizard is translated
and flips to RTL.

### Things worth trying by hand

| Try | Expect |
|---|---|
| Name with two parts | *"at least 3 parts"* — the one name problem that is still refused, since a name cannot be invented |
| `Ahmed & Sons Ltd 2026` | Repaired to `Ahmed Sons Ltd`; digits and symbols become spaces |
| `أحمد مُحمَّد الجويلي` | **Accepted and repaired** to `احمد محمد الجويلى`, with a toast saying what was saved |
| `01312345678` | Rejected — not an issued Egyptian prefix |
| `+20 101 234 5678`, `00201012345678`, `201012345678` | All accepted, all the same identity |
| Pick 🇨🇦 Canada, enter `506 234 5678` | Accepted, stored as `+15062345678` |
| Pick 🇨🇦 Canada, enter `01012345678` | Rejected — *"Example: (506) 234-5678"*, the format of the country you picked |
| Pick any country | Placeholder and the rules change to that country's own |
| Type `01012345678` under 🇪🇬 | Settles to `1012345678`. The leading zero is a trunk prefix, dropped once `+20` is in front — the row reads `+20 1012345678` |
| Type just `0` | It stays. Nothing is taken away until there is a number behind it |
| Paste `+201012345678` or `00201012345678` | Both become `1012345678` |
| Pick 🇪🇬 Egypt, type an 11th digit | Refused — the field stops at 10 |
| Pick 🇪🇬 Egypt, type `101234` | *"Numbers in Egypt have 10 digits — you have typed 6."* A tick appears once it is right |
| Type a full 🇪🇬 number, then switch to 🇸🇦 | Now flagged too long — 🇸🇦 numbers are 9 digits. What you typed is kept, not silently trimmed |
| Pick 🇮🇹 Italy, type `3123456789` | Nothing stripped — Italian numbers keep their leading digits |
| Finish a signup from any country | Stored as `+…` everywhere. Check with §8 |
| Wrong code six times | Locked out of that code; **Resend** gives a fresh one |
| Close the tab at step 3 | Nothing at all is created. Check with §8. |

---

### The country picker

The phone field is a country selector plus a national-number input. Choosing a
country changes three things at once: the dialling code shown, the placeholder
and hint (drawn from a real example number for that country), and **which rules
the number is validated against**. `506 234 5678` is valid under 🇨🇦 and invalid
under 🇪🇬, and the error message quotes the format of whichever country is
selected.

Nothing about the list is hard-coded. Names come from Frappe's own **Country**
doctype — the same list the Desk uses, already translated — and the dialling
codes and example numbers from `phonenumbers`, which ships with Frappe. Flags
are emoji derived from the ISO code, so there are no image assets. The list is
cached and rebuilt automatically when a Country record changes.

A number typed in full international form (`+20…`) is honoured whatever the
picker says, so a pasted number always works.

**The field holds the national number, with no trunk prefix.** `+20` beside
`01012345678` is not a number anyone can dial; the real one is
`+20 10 01234567`. Type the leading zero out of habit and it comes off as you
go. The server still accepts every form — `1012345678`, `01012345678`,
`+201012345678`, `00201012345678` — so this is a display rule, not a
validation one.

**Every number is stored in international form** — `+201012345678`, whatever
country it came from and however it was typed. One column, one convention:
`Contact Phone.phone`, `Contact Phone.custom_phone_e164`, `User.mobile_no`,
`Customer.mobile_no` and `Webshop Account Identity.phone_e164` all agree, so no
reader has to know which country a row came from to understand it.

Reading stays deliberately forgiving. Rows written before this rule, and rows
`contact_enhancements` writes on its own paths, still hold the local `01…`
form; matching searches for every written form, so those people are still
found. Canonical on write, forgiving on read.

`contact_enhancements` rewrites phone numbers into local form on *every*
Contact save. This app is registered after it and so has the last word, but it
only reclaims numbers it is answerable for — one that is the verified identity
of a webshop account. A Contact staff maintain by hand keeps the local form
that app intends.

## 4. Running the automated suite

```bash
# everything
bench --site erpnext run-tests --app custom_webshop

# one module
bench --site erpnext run-tests --module custom_webshop.tests.test_signup_flow

# one test
bench --site erpnext run-tests --module custom_webshop.tests.test_signup_flow \
      --test test_scenario_1_new_individual
```

328 tests, ~20 seconds. They need `allow_tests` on the site (already set here):

```bash
bench --site erpnext set-config allow_tests true
```

| Module | Tests | What it pins down |
|---|---|---|
| `test_countries` | 21 | the country picker: dial codes, flags, per-country rules |
| `test_identity` | 57 | E.164 across 4 prefixes × 9 formats, email, name rules, Arabic folding |
| `test_otp` | 27 | issue, verify, expiry, attempts, cooldown, cross-channel replay |
| `test_signup_session` | 24 | every valid transition **and every forbidden one** |
| `test_contact_hooks` | 14 | canonical column stays in step; verified numbers stay international |
| `test_matching` | 27 | every classification row, recognition-card privacy |
| `test_resolution` | 11 | identity beats stray Portal User rows |
| `test_login_page` | 20 | the signup entry point matches API availability |
| `test_legacy_signup` | 5 | the old unverified endpoint is closed |
| `test_signup_flow` | 53 | all 18 scenarios end to end |
| `test_phone_rules` | 33 | per-country digit rules, trunk prefixes, one stored format, the migration |
| `test_signup_security` | 23 | brute force, replay, enumeration, forged candidates |
| `test_signup_races` | 13 | concurrency, idempotency, Redis-down |

The tests do not need a running web server, and they roll back — they leave
no data behind.

---

## 5. The 18 scenarios by hand

Each is covered by an automated test, but here is how to drive them yourself.

Paste this into `bench --site erpnext console` first — it is the seed helper
the rest of the table uses:

```python
from custom_webshop.signup.identity import to_e164

def seed_customer(name, phone=None, email=None, contact_name=None):
    """Create a Customer + linked Contact to match a signup against."""
    c = frappe.new_doc("Contact")
    c.first_name = contact_name or name
    if phone: c.append("phone_nos", {"phone": phone, "is_primary_mobile_no": 1})
    if email: c.append("email_ids", {"email_id": email, "is_primary": 1})
    c.insert(ignore_permissions=True)

    cu = frappe.new_doc("Customer")
    cu.update({"customer_name": name, "customer_type": "Individual",
               "customer_group": "Individual", "territory": "Egypt",
               "customer_primary_contact": c.name})
    cu.flags.ignore_mandatory = True
    cu.insert(ignore_permissions=True)

    c.reload()
    c.append("links", {"link_doctype": "Customer", "link_name": cu.name})
    c.save(ignore_permissions=True)
    frappe.db.commit()
    print("seeded:", cu.name, "/", c.name)
    return cu.name
```

| # | Scenario | Setup | Expected |
|---|---|---|---|
| 1 | New individual | none | New Customer, Contact, Portal User, identity row |
| 2 | New company | none — pick *For my company* | `customer_type=Company`, Customer named after the company, Contact named after the person |
| 3 | Existing customer, exact match | `seed_customer("Ahmed Amin Algewily", phone="01099988877")` then sign up with the **same name and phone** | Step 4 shows an **"Is this you?"** card → *Yes* → linked, **no duplicate Customer** |
| 4 | Same phone, different name | seed as above, sign up with **a different name**, same phone | **No card, no question.** New Customer + a `PHONE_NAME_MISMATCH` conflict for staff |
| 5 | User rejects a match | scenario 3, then press *No, this isn't me* | New Customer + `USER_REJECTED_MATCH` conflict |
| 6 | Two customers, one phone | run `seed_customer` **twice** with the same phone, different names | `MULTIPLE_PHONE_MATCHES` conflict. The engine never picks a winner. |
| 7 | Customer already has an account | complete scenario 3, then sign up again on the same phone with a new email | **BLOCKED** — "you already have an account" |
| 8 | Email already registered | sign up with an email that is already a User | BLOCKED, but only **after** the email OTP — proving you own it |
| 9 | Phone already registered | complete any signup, start another on the same number | BLOCKED after the **phone** OTP |
| 10 | Change email | press *Change email* at step 3 | Old code dies immediately; new address must be verified |
| 11 | Change phone | press *Change number* at step 4 | Same, and the old number stops counting as verified |
| 12 | Wrong code | type `000000` | *"That code is not correct"* |
| 13 | Expired code | wait 10 min, or expire it from the console (below) | **Identical** message to #12, by design |
| 14 | Too many attempts | five wrong codes | Code destroyed; you must resend |
| 15 | Resend | press *Resend* | New code; the old one stops working; counter decrements |
| 16 | Abandoned | close the tab mid-flow | Nothing created — verify with §8 |
| 17 | Concurrent | two browsers, same phone, both to the password step, submit both | Exactly one account; the loser is told an account exists |
| 18 | Duplicate submit | double-click *Create account* | One account; the second call returns the same result |

### You will hit the rate limit

Walking this list from one machine spends the per-IP signup cap well before
you reach the end. Clear this app's own counters and carry on:

```bash
bench --site erpnext execute custom_webshop.signup.audit.clear_rate_limits
```

It only touches counters for `custom_webshop.api.signup.*`, so no other
endpoint's protection is affected, and they rebuild from the next request.

Expiring a code by hand, for #13:

```python
frappe.db.sql("""UPDATE `tabWebshop Signup Session`
                 SET email_otp_expires_at = DATE_SUB(NOW(), INTERVAL 1 MINUTE)
                 WHERE status = 'EMAIL_PENDING'""")
frappe.db.commit()
```

---

## 6. Testing over HTTP

Useful because the wizard is bound to your browser by an **httpOnly cookie** —
possessing the `signup_id` is not enough. Only a real request exercises that.

```bash
JAR=/tmp/signup-jar.txt; rm -f $JAR
B=http://127.0.0.1:8000/api/method/custom_webshop.api.signup

# start
curl -s -c $JAR -b $JAR -H "Content-Type: application/json" -X POST $B.start \
  -d '{"account_type":"Individual","full_name":"Http Test Userx",
       "email":"http-test@example.com","phone":"01055500022"}' | python3 -m json.tool

# copy signup_id from the response, then:
SID=<paste>
CODE=$(grep -o "'code': '[0-9]*'" logs/custom_webshop.signup.log | tail -1 | grep -o "[0-9]\{6\}")
curl -s -c $JAR -b $JAR -H "Content-Type: application/json" -X POST $B.verify_email \
  -d "{\"signup_id\":\"$SID\",\"code\":\"$CODE\"}" | python3 -m json.tool
```

Then `send_phone_otp` → `verify_phone` → `resolve` → `complete`, each with
`{"signup_id": "..."}`.

**Prove the cookie binding matters:** repeat any call with `-b /dev/null`
(no cookie jar). You get `SignupNotFound` — deliberately the same error as a
made-up id, so a guessed id cannot be confirmed by the difference.

Every response has the same shape:

```json
{"signup_id": "...", "state": "EMAIL_PENDING",
 "allowed_actions": ["verify_email", "resend_email_otp", "change_email", "cancel"],
 "message": "...", "data": {...}}
```

`state` and `allowed_actions` are the backend telling the browser what is
possible. The browser decides nothing.

---

## 7. Checking what landed in the database

```python
# the authoritative record — one row per verified account
frappe.get_all("Webshop Account Identity",
    fields=["user", "customer", "phone_e164", "email_normalized",
            "linked_existing_customer"], limit=10)

# in-progress and finished signups
frappe.get_all("Webshop Signup Session",
    fields=["signup_id", "status", "full_name", "email_normalized",
            "phone_e164", "match_result", "resolution"],
    order_by="creation desc", limit=10)

# the staff queue
frappe.get_all("Webshop Identity Conflict",
    fields=["name", "conflict_type", "status", "submitted_name",
            "phone_e164", "created_customer"],
    filters={"status": "Open"})
```

After an abandoned signup, confirm nothing was created:

```python
frappe.db.exists("User", "the-email@example.com")          # -> None
frappe.db.exists("Webshop Account Identity",
                 {"email_normalized": "the-email@example.com"})  # -> None
```

Conflicts are also a normal Desk list — search **Webshop Identity Conflict**.

---

## 8. Resetting between tests

Remove one test account and everything attached to it:

```python
email = "the-email@example.com"
row = frappe.db.get_value("Webshop Account Identity", {"user": email},
                          ["name", "customer", "contact"], as_dict=True)
if row:
    frappe.db.delete("Portal User", {"parent": row.customer, "user": email})
    frappe.delete_doc("Webshop Account Identity", row.name, force=True)
    frappe.delete_doc("Customer", row.customer, force=True, delete_permanently=True)
    frappe.delete_doc("User", email, force=True)
frappe.db.delete("Webshop Signup Session", {"email_normalized": email})
frappe.db.commit()
```

Clear out abandoned sessions:

```python
from custom_webshop.signup.session import expire_stale_sessions
expire_stale_sessions()          # also runs daily on the scheduler
frappe.db.commit()
```

### Switching testing off again

```python
frappe.db.set_single_value("Webshop Signup Settings",
                           {"signup_enabled": 0, "email_otp_dev_mode": 0,
                            "phone_otp_dev_mode": 0, "otp_resend_cooldown_seconds": 60})
frappe.db.set_single_value("Website Settings", "disable_signup", 1)
frappe.db.commit()
```

---

## 9. Troubleshooting

| Symptom | Cause |
|---|---|
| No "Create one" button on `/login` | One of the six switches (§1). Check `custom_webshop.api.signup.is_available()`. |
| *"Sign up is currently unavailable"* | Same. With both dev-mode flags off, **both** OTP channels must be enabled. |
| *"We could not send the verification email"* | No outgoing Email Account. Turn on `email_otp_dev_mode` for testing, or configure one. |
| *"SMS verification is not available right now"* | SMS Settings has no gateway URL. Turn on `phone_otp_dev_mode` for testing, or configure one. |
| `SignupNotFound` on every call after `start` | You are not sending the cookie. Use the same cookie jar / browser. |
| *"This signup has expired"* | Past `session_ttl_minutes` (default 30). Start again. |
| *"Please wait N seconds"* | Resend cooldown. Set `otp_resend_cooldown_seconds` to 0 while testing. |
| Nothing in the OTP log for a channel | That channel's own dev-mode flag (`email_otp_dev_mode`/`phone_otp_dev_mode`) is off, so it really tried to send. |
| *"You hit the rate limit"* | The per-IP signup cap. Run `custom_webshop.signup.audit.clear_rate_limits`. |
| Every signup refused right after a `bench migrate` | A newly-added Int setting lands on the existing Single as **0**. `settings.get_int` now falls back to the default for these, and `backfill_zeroed_signup_settings` repairs the stored values — check that patch ran. |
| Customer creation fails site-wide | Not this app — check `contact_enhancements`, which makes `customer_primary_contact` and `customer_primary_address` mandatory. |

---

## 10. Before production

Both remaining items are **configuration, not code**:

- [ ] An **Email Account** with `enable_outgoing` **and** `default_outgoing` set.
      The site currently has only test accounts, so email OTP cannot deliver.
- [ ] **SMS Settings**: gateway URL, receiver parameter, message parameter.
      Any HTTP provider works by config alone. An SDK-based provider goes in
      `sms_sender_method` as a dotted path called `sender(phone_e164, message)`.
- [ ] Run the data audit (below) and act on it.
- [ ] `bench --site erpnext run-tests --app custom_webshop` green.
- [ ] Enable in this order, soaking between each:
      `email_otp_enabled` → `phone_otp_enabled` → `signup_enabled` → `disable_signup=0`.

**Rollback** is layered, fastest first: `disable_signup=1` (instant, no deploy)
→ `signup_enabled=0` → `phone_otp_enabled=0` → `git revert` + `bench migrate`.
No rollback step deletes data; every schema change is additive.

---

## 11. The data audit

```bash
bench --site erpnext execute custom_webshop.signup.audit.report
```

Read-only — it changes nothing, and is safe to run any time. See
`AUDIT.md` for what each number means and what to do about it.
