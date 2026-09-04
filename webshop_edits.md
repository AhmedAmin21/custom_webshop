# Webshop Customization Edits

This document tracks all customizations, bug fixes, and new features implemented in the `custom_webshop` custom app.

---

## Architecture Principle

**Zero core changes.** All modifications live in `custom_webshop` and use:
- `override_whitelisted_methods` for backend API interception
- Template overrides (same path, loaded first because `custom_webshop` precedes `webshop` in `apps.txt`)
- Page-specific JS/CSS (loaded alongside template overrides)
- `web_include_css` for global styles

---

## Edit 1: Cart "Place Order" Button (Sales Order Creation)

**Goal:** Change the cart page button from **"Request for Quote"** to **"Place Order"**, and make it create a **Sales Order** directly instead of a Quotation.

**Context:**
- In standard webshop, when `enable_checkout = False`, the cart shows a **"Request for Quote"** button that creates a Quotation.
- We want customers to place orders directly, even without the checkout/payment flow enabled.
- The underlying cart document is still a Quotation (`order_type = "Shopping Cart"`), but we auto-submit it and immediately generate a Sales Order.

---

### Files Created / Modified

#### 1. Backend Override

**File:** `custom_webshop/custom_webshop/shopping_cart/cart_override.py`

```python
import frappe
from frappe import _
from frappe.utils import cint

from webshop.webshop.shopping_cart.cart import _get_cart_quotation
from webshop.webshop.doctype.webshop_settings.webshop_settings import get_shopping_cart_settings
from webshop.webshop.utils.product import get_web_item_qty_in_stock
from erpnext.selling.doctype.quotation.quotation import _make_sales_order


@frappe.whitelist()
def place_order_from_cart():
    """
    Override for 'Request for Quotation'.
    Submits the cart Quotation, creates a Sales Order, validates stock,
    clears the cart, and returns the Sales Order name.
    """
    quotation = _get_cart_quotation()
    cart_settings = frappe.get_cached_doc("Webshop Settings")
    quotation.company = cart_settings.company

    quotation.flags.ignore_permissions = True
    quotation.submit()

    if quotation.quotation_to == "Lead" and quotation.party_name:
        frappe.defaults.set_user_default("company", quotation.company)

    if not (quotation.shipping_address_name or quotation.customer_address):
        frappe.throw(_("Set Shipping Address or Billing Address"))

    sales_order = frappe.get_doc(
        _make_sales_order(quotation.name, ignore_permissions=True)
    )
    sales_order.payment_schedule = []

    if not cint(cart_settings.allow_items_not_in_stock):
        for item in sales_order.get("items"):
            item.warehouse = frappe.db.get_value(
                "Website Item", {"item_code": item.item_code}, "website_warehouse"
            )
            is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
            if is_stock_item:
                item_stock = get_web_item_qty_in_stock(item.item_code, "website_warehouse")
                if not cint(item_stock.in_stock):
                    frappe.throw(_("{0} Not in Stock").format(item.item_code))
                if item.qty > item_stock.stock_qty:
                    frappe.throw(
                        _("Only {0} in Stock for item {1}").format(
                            item_stock.stock_qty, item.item_code
                        )
                    )

    sales_order.flags.ignore_permissions = True
    sales_order.insert()
    sales_order.submit()

    if hasattr(frappe.local, "cookie_manager"):
        frappe.local.cookie_manager.delete_cookie("cart_count")

    return sales_order.name
```

**Hook in `custom_webshop/hooks.py`:**
```python
override_whitelisted_methods = {
    "webshop.webshop.shopping_cart.cart.request_for_quotation": "custom_webshop.shopping_cart.cart_override.place_order_from_cart"
}
```

> **Bug Fix:** The module path was originally `custom_webshop.custom_webshop.shopping_cart.cart_override` (wrong) and corrected to `custom_webshop.shopping_cart.cart_override`.

---

#### 2. Template Override — Button Label

**File:** `custom_webshop/templates/includes/cart/place_order.html`

```html
<div class="card h-100">
    <div class="card-body p-0">
        {% if cart_settings.enable_checkout %}
            <button class="btn btn-primary btn-place-order font-md w-100" type="button">
                {{ _("Place Order") }}
            </button>
        {% else %}
            <button class="btn btn-primary btn-request-for-quotation font-md w-100" type="button">
                {{ _("Place Order") }}
            </button>
        {% endif %}
    </div>
</div>
```

---

#### 3. Template Override — Cart Page Links

**File:** `custom_webshop/templates/pages/cart.html`

Overrides the original `webshop/templates/pages/cart.html`.

**Changes:**
- **Past Orders link:** Always links to `/orders` with label **"Past Orders"** (was conditional on `enable_checkout`, linking to `/quotations`).
- **Empty cart link:** Always links to `/orders` with label **"See past orders"** (was `/quotations` and "See past quotations").

> **Bug Fix:** The original template had an **unclosed `{% if doc.items %}`** block inside the Terms & Conditions section (line 65 in the original). This caused a `jinja2.exceptions.UndefinedError` when rendering the page. The block was removed, keeping only `{% if doc.terms %}`.

---

#### 4. Page Controller

**File:** `custom_webshop/templates/pages/cart.py`

```python
no_cache = 1

from webshop.webshop.shopping_cart.cart import get_cart_quotation


def get_context(context):
    context.body_class = "product-page"
    context.update(get_cart_quotation())
```

> **Bug Fix:** When you override a template in a custom app, Frappe loads the controller from the **same app**. Without this file, the template rendered with **no context**, causing `'doc' is undefined` errors.

---

#### 5. Page-Specific JavaScript

**File:** `custom_webshop/templates/pages/cart.js`

A complete copy of the original `cart.js` with our modifications integrated.

> **Bug Fix:** When the template lives in `custom_webshop`, Frappe looks for `custom_webshop/templates/pages/cart.js`. If missing, it **never loads the original JS** from `webshop`, so no event handlers are bound (buttons, quantity, delete all dead).

**Key modifications:**
- **`request_quotation()`** redirected to `/orders/` instead of `/quotations/`
- **Friendly address dialog** before API call — prompts user to add address if none selected
- **Button text** changed to "Place Order" in `frappe.ready`

> **Bug Fix:** Initially tried to use `web_include_js` with a global `cart_override.js`, but:
> 1. The original `cart.js` never loaded, so `shopping_cart` object didn't exist
> 2. Changing the button class from `btn-request-for-quotation` to `btn-place-order` caused the original click handler binding to fail (race condition)
>
> Solution: Move all logic into the page-specific `cart.js`.

---

### Result

| Scenario | Before | After |
|----------|--------|-------|
| Cart button label | "Request for Quote" | "Place Order" |
| Document created | Quotation | Sales Order |
| Redirect URL | `/quotations/{name}` | `/orders/{name}` |
| Past orders link | `/quotations` | `/orders` |
| Empty cart link | `/quotations` | `/orders` |
| Address missing | Server error thrown | Friendly dialog prompt |

---

### Testing Checklist

- [ ] Log in as a customer.
- [ ] Add items to cart.
- [ ] Navigate to `/cart`.
- [ ] Verify button shows **"Place Order"**.
- [ ] Click **"Place Order"** without selecting an address.
- [ ] Verify a friendly dialog appears asking to add an address.
- [ ] Add a shipping address.
- [ ] Click **"Place Order"** again.
- [ ] Verify browser redirects to `/orders/SO-XXXXX`.
- [ ] Verify a **Sales Order** is created in ERPNext backend.
- [ ] Verify the cart is empty after placing the order.
- [ ] Verify the **"Past Orders"** link on the cart page points to `/orders`.

---

---

## Edit 2: Debounced Quantity Updates & Improved Freeze UX

**Goal:** Fix two UX issues:
1. **Lag on +/- buttons** — every click triggered an immediate server round-trip, making the UI feel sluggish.
2. **Transparent white overlay** — the original `freeze()` used a Bootstrap `modal-backdrop` that covered the entire page. On errors or slow responses, it created a confusing "transparent white screen" effect.

---

### Files Created / Modified

#### 1. Page Controller + JS — Cart Page

**File:** `custom_webshop/templates/pages/cart.js`

##### A. Debounced Quantity Updates (1000ms)

Added `_debounceTimers` and `debouncedCartUpdate()`:

```javascript
_debounceTimers: {},

debouncedCartUpdate: function(item_code, qty, additional_notes) {
    if (this._debounceTimers[item_code]) {
        clearTimeout(this._debounceTimers[item_code]);
    }
    $(`.cart-qty[data-item-code="${item_code}"]`).addClass('cart-qty-updating');

    this._debounceTimers[item_code] = setTimeout(() => {
        $(`.cart-qty[data-item-code="${item_code}"]`).removeClass('cart-qty-updating');
        shopping_cart.shopping_cart_update({
            item_code: item_code,
            qty: qty,
            additional_notes: additional_notes
        });
        delete this._debounceTimers[item_code];
    }, 1000);
}
```

- User clicks `+` or `-` → input value updates **instantly** for visual feedback
- Input gets a **blue highlight** (`cart-qty-updating` class) to show a pending update
- API call is **debounced by 1000ms** — only fires after the user stops clicking for 1 second
- Rapid clicking no longer hammers the server

Applied to:
- Number spinner buttons (`+` / `-`)
- Direct quantity input change
- Notes textarea change

##### B. Custom Freeze / Unfreeze

Replaced the full-page Bootstrap `modal-backdrop` with scoped CSS classes on `.cart-container`:

```javascript
freeze: function(mode) {
    if (window.location.pathname !== "/cart") return;
    if (mode === 'strong') {
        $('.cart-container').addClass('cart-freeze-strong');
    } else {
        $('.cart-container').addClass('cart-freeze-subtle');
    }
},

unfreeze: function(mode) {
    if (window.location.pathname !== "/cart") return;
    if (mode === 'strong') {
        $('.cart-container').removeClass('cart-freeze-strong');
    } else {
        $('.cart-container').removeClass('cart-freeze-subtle');
    }
}
```

| Mode | CSS Class | Effect |
|------|-----------|--------|
| `subtle` (default) | `.cart-freeze-subtle` | Opacity 0.6 + pointer-events none — used for qty updates |
| `strong` | `.cart-freeze-strong` | Opacity 0.4 + pointer-events none — used for Place Order |

##### C. Place Order "Please Wait" State

When clicking **Place Order**:
- Button becomes `disabled` and text changes to **"Please wait..."**
- Strong freeze (opacity 0.4) is applied to the cart container
- On completion (success or error), button is restored and freeze is removed

```javascript
$(btn).prop('disabled', true).text(__('Please wait...'));
shopping_cart.freeze('strong');
// ... API call ...
shopping_cart.unfreeze('strong');
$(btn).prop('disabled', false).text(__('Place Order'));
```

---

#### 2. Stylesheet

**File:** `custom_webshop/public/css/cart.css`

```css
/* Subtle freeze for qty updates */
.cart-freeze-subtle {
    opacity: 0.6;
    pointer-events: none;
    transition: opacity 0.2s ease;
}

/* Strong freeze for Place Order */
.cart-freeze-strong {
    opacity: 0.4;
    pointer-events: none;
    transition: opacity 0.2s ease;
}

/* Input highlight while waiting for debounce */
.cart-qty-updating {
    border-color: #5e64ff !important;
    background-color: #f0f2ff !important;
    transition: all 0.2s ease;
}

/* Button processing state */
.btn-place-order:disabled,
.btn-request-for-quotation:disabled {
    opacity: 0.85;
    cursor: not-allowed;
}
```

**Hook in `custom_webshop/hooks.py`:**
```python
web_include_css = "/assets/custom_webshop/css/cart.css"
```

---

### Result

| Scenario | Before | After |
|----------|--------|-------|
| Click `+` rapidly | 5 API calls queued, page frozen each time | 1 API call after 1s of inactivity, instant visual feedback |
| Qty input feedback | None | Blue border highlight while pending |
| Place Order clicked | Full-page white modal backdrop | Cart container dims, button shows "Please wait..." |
| Error during order | White screen stuck | Cart dims slightly, error message visible, button restored |

---

---

## Bug Fixes Summary

| # | Bug | Cause | Fix |
|---|-----|-------|-----|
| 1 | 417 error: `'doc' is undefined` | Custom template loaded but no page controller in custom app | Created `custom_webshop/templates/pages/cart.py` |
| 2 | 417 error: Jinja syntax error | Unclosed `{% if doc.items %}` in copied template | Removed redundant block, kept only `{% if doc.terms %}` |
| 3 | Buttons not working at all | Page-specific JS not loaded because template moved to custom app | Created `custom_webshop/templates/pages/cart.js` |
| 4 | `No module named 'custom_webshop.custom_webshop...'` | Wrong Python module path in `hooks.py` | Fixed to `custom_webshop.shopping_cart.cart_override` |
| 5 | Clicking "Place Order" did nothing | Button class changed before original JS bound click handler | Kept original class `btn-request-for-quotation`, only changed text |
| 6 | Transparent white overlay on errors | `freeze()` used Bootstrap `modal-backdrop` covering entire page | Replaced with scoped CSS classes on `.cart-container` |
| 7 | Lag on +/- buttons | Every click fired an immediate server API call | Added 1000ms debounce with instant visual feedback |

---

## File Inventory

```
custom_webshop/
├── custom_webshop/
│   ├── hooks.py                          # Hooks: override_whitelisted_methods, web_include_css
│   └── shopping_cart/
│       ├── __init__.py
│       └── cart_override.py              # Backend: place_order_from_cart()
├── templates/
│   ├── includes/cart/place_order.html    # Button label override
│   └── pages/
│       ├── cart.html                     # Cart page template (links + structure)
│       ├── cart.py                       # Cart page controller (provides context)
│       └── cart.js                       # Cart page JS (event bindings + overrides)
├── public/
│   └── css/
│       └── cart.css                      # Freeze styles + debounce highlight
└── webshop_edits.md                      # This document
```

---

---

## Edit 3: Unified Customer Information Dialog

**Goal:** Replace the separate address-only form with a unified dialog that collects both **contact info** (name, phone) and **shipping address** in one step. Store phone in the **Contact** doctype (not Address) following ERPNext best practices.

---

### Problem with Original

- **9 fields** in the address form: Title, Line 1, Line 2, City, State, Country, Type, Postal Code, Phone
- Phone stored in `Address.phone` — wrong data model (phone belongs to a person, not a location)
- Billing address section shown even though we only need shipping
- "Add a new address" label doesn't reflect that we're collecting customer info

---

### Solution

**Unified Dialog with 5 fields:**

| Section | Field | Behavior |
|---------|-------|----------|
| **Contact Info** | Full Name | Auto-filled from `frappe.session.user_fullname` |
| | Mobile / Phone | User enters (required) → stored in **Contact** doctype |
| **Shipping Address** | Address | Single line (required) |
| | City / Town | User enters (required) |
| | Country | Dropdown (required) |

**Backend:**
- Creates **Contact** doctype with phone, email (from user account), linked to Customer
- Creates **Address** doctype with location info, linked to Customer
- Address Type = "Shipping" (hidden, default)
- Address Title auto-generated: "{Customer Name} - Shipping"

---

### Files Created / Modified

#### 1. Backend API

**File:** `custom_webshop/custom_webshop/shopping_cart/cart_override.py`

**Three new functions:**

**`add_customer_info(address_data, contact_data)`**
```python
# Creates Contact + Address
# Links both to Customer
# Returns address.name for cart linking
```

**`update_customer_info(address_name, address_data, contact_name, contact_data)`**
```python
# Updates existing Contact + Address
# Returns address.name
```

**`get_customer_addresses_with_contacts()`**
```python
# Returns customer's addresses + primary contact
# Used for displaying phone on address cards
```

#### 2. Page Controller

**File:** `custom_webshop/templates/pages/cart.py`

Added SQL query to fetch primary contact for the customer:
```python
contact = frappe.db.sql("""
    SELECT c.name, c.first_name, c.mobile_no
    FROM `tabContact` c
    JOIN `tabDynamic Link` dl ON dl.parent = c.name
    WHERE dl.link_doctype = 'Customer'
    AND dl.link_name = %s
    LIMIT 1
"", party.name, as_dict=True)
context.primary_contact = contact[0] if contact else None
```

#### 3. Frontend JS

**File:** `custom_webshop/templates/pages/cart.js`

**`open_customer_info_dialog(mode, existingData)`**
- Opens unified dialog with 5 fields
- Auto-fills name from session
- Mode: `'add'` or `'edit'`
- On save: calls `add_customer_info` or `update_customer_info`
- After save: links address to cart via `update_cart_address`

**`bind_address_events()`**
- Binds click on `.btn-customer-info` → opens add dialog
- Binds click on `.btn-edit-address` → opens edit dialog with pre-filled data

#### 4. Templates

**`custom_webshop/templates/includes/cart/cart_address.html`**
- Changed link text: **"Customer Information"**
- Hidden billing address section (`display: none`)
- Hidden checkbox (billing = shipping by default)

**`custom_webshop/templates/includes/cart/address_card.html`**
- Shows: name, address line, city, country, phone
- Edit icon button (top-right corner)
- `data-contact-name` attribute for edit functionality

#### 5. Styles

**File:** `custom_webshop/public/css/cart.css`

Added:
```css
.btn-customer-info { color: var(--primary); cursor: pointer; }
.btn-edit-address { z-index: 10; background: transparent; }
.address-phone { font-size: 0.9rem; }
[data-section="billing-address"] { display: none !important; }
```

---

### Result

| Scenario | Before | After |
|----------|--------|-------|
| Form fields | 9 fields | 5 fields |
| Phone stored | Address.phone | Contact.mobile_no |
| Button label | "Add a new address" | "Customer Information" |
| Billing section | Visible checkbox | Hidden (auto same-as-shipping) |
| Edit existing | Link to /address/{name} | Inline edit icon → unified dialog |
| Address title | User must type | Auto-generated from customer name |

---

### Testing Checklist

- [ ] Button shows **"Customer Information"**
- [ ] Dialog opens with name pre-filled
- [ ] Creating new: both Contact and Address created in backend
- [ ] Phone visible on address card
- [ ] Edit icon opens dialog with pre-filled data
- [ ] Updating: both Contact and Address updated
- [ ] Billing address auto-set to same as shipping
- [ ] Validation works for required fields

---

---

## Edit 4: Verified Signup & ERPNext Customer Identity Resolution

**Goal:** Replace the one-step signup with a flow that proves the email and the phone before deciding whether the person is an existing ERPNext Customer — and that never links an account to a Customer on a guess.

### Why this replaced the old flow rather than patching it

| # | Defect in the old flow | Consequence |
|---|---|---|
| 1 | `api/auth.py:153` linked a signup to any Customer whose `customer_name` equalled the submitted name, then granted a Portal User row | `www/orders.py` lists Sales Orders for every Customer a user has a Portal User row on, with `ignore_permissions=True` — so signing up under someone else's name inherited their order history |
| 2 | Validation ran *after* `user.insert()` | A name that `contact_enhancements`' Arabic rules rejected (most names ending in `ي` or `ة`) stranded a User with no Customer. Names are now **repaired, not rejected** — see below |
| 3 | `escape_html(full_name)` before storage | A name with `&` or `'` was stored as `&amp;`/`&#39;`, which then failed the "no symbols" rule |
| 4 | Three code paths created Customers, using three different lookup keys | Duplicates by construction — the live DB had 5 Contacts for one person, 3 orphaned |
| 5 | Nothing verified | Phone, the strongest identity signal available, was entirely untrusted |

### Architecture

```
Browser (page-signup.js)      api/signup.py            signup/
─────────────────────────     ─────────────            ───────
POST start               →    start()             →    identity.py   normalise + validate
                         ←    {state, allowed_actions} session.py    state machine (DocType)
POST verify_email        →    verify_email()      →    otp.py        issue / verify / throttle
POST verify_phone        →    verify_phone()      →    notifications.py  email / SMS / dev mode
POST resolve             →    resolve()           →    matching.py   candidates + classification
POST decide              →    decide()            →    conflicts.py  staff queue
POST complete            →    complete()          →    linking.py    atomic create/link
```

Nothing in ERPNext is created until `complete`. A signup abandoned at any earlier point leaves one expiring row.

### New DocTypes

| DocType | Purpose |
|---|---|
| `Webshop Signup Session` | The in-progress signup: state machine, OTP hashes, audit trail. Holds no password, ever. |
| `Webshop Account Identity` | **The authoritative User ↔ Customer link.** Unique indexes on `user`, `phone_e164`, `email_normalized` are what make concurrent signups safe. |
| `Webshop Identity Conflict` | Staff review queue for anything the engine refuses to resolve alone. |
| `Webshop Signup Settings` | Feature flags and tunables; the kill switch. |

### Schema additions

- `Contact Phone.custom_phone_e164` — indexed canonical phone, maintained by a non-throwing `Contact.validate` hook. `phone` itself keeps the local `01…` format that `contact_enhancements` and all existing rows use.
- Indexes on `Contact Email.email_id` and `Customer.mobile_no` — both were unindexed and read on every match.
- Patch `backfill_contact_phone_e164` — additive, fills only the derived column. Canonicalised 16 rows; 4 were genuinely not phone numbers.

### Matching rules

Deterministic, never a similarity score. Name never authorises a link — it only ever *downgrades* a phone match.

| Candidates | Name | Result | Outcome |
|---|---|---|---|
| none | — | `NO_MATCH` | create new |
| 1, by phone | matches | `STRONG_MATCH` | ask, then link |
| 1, by phone | differs | `PHONE_NAME_MISMATCH` | **new Customer + conflict, never linked** |
| 1, by email | matches | `EMAIL_MATCH` | ask, then link |
| 1, by email | differs | `EMAIL_NAME_MISMATCH` | new Customer + conflict |
| ≥ 2 | any | `MULTIPLE_MATCH` | never auto-pick; new Customer + conflict |

Blocking pre-checks run first: email already a User, phone already an account (identity row **or** a legacy `User.mobile_no`, which Frappe uniquely indexes), or the candidate Customer already linked.

### Files created

```
custom_webshop/
├── api/signup.py                       # 12 whitelisted endpoints, one envelope shape
├── signup/
│   ├── identity.py                     # E.164, email, name normalise + validate
│   ├── session.py                      # state machine + browser binding
│   ├── otp.py                          # issue / verify / throttle
│   ├── notifications.py                # email, SMS, dev mode
│   ├── matching.py                     # candidates + classification (read-only)
│   ├── linking.py                      # the atomic finalise
│   ├── conflicts.py                    # staff queue
│   ├── resolution.py                   # user → Customer, the single answer
│   ├── settings.py                     # cached settings accessor
│   ├── telemetry.py                    # structured logging with redaction
│   └── audit.py                        # read-only data audit
├── contact_hooks.py                    # Contact.validate → canonical phone
├── customer_hooks.py                   # Customer.validate → strip unearned portal access
├── setup/custom_fields.py, install.py
├── patches/backfill_contact_phone_e164.py
├── templates/emails/signup_otp.html
├── public/js/page-signup.js            # state-rendering wizard
└── tests/                              # 221 tests
```

### Files modified

| File | Change | Risk to existing behaviour |
|---|---|---|
| `api/auth.py` | Now a shim that declines. Frappe's own `sign_up` stays intercepted, so there is exactly one way to create an account. | Old cached clients get a message, not an error |
| `www/orders.py` | Resolves via `resolution.get_customer_names()` instead of raw Portal User; removed a stale `_debug_log` writing to a non-existent path | Narrows what a user can see — by design |
| `www/payment.py` | Ownership via `resolution.owns_customer()` | Same |
| `shopping_cart/cart_override.py` | `get_customer_for_user` delegates to `resolution` | Wrapper kept, callers unchanged |
| `public/js/page-login.js` | Signup handling removed | Login and forgot-password untouched |
| `www/login/index.html` | Signup form → `#signup-wizard` shell + wizard styles | Login and forgot views untouched |
| `public/js/store.js` | ~45 new `su_*` keys in `en` and `ar` | Additive |
| `hooks.py` | `doc_events`, `scheduler_events`, `after_install`/`after_migrate`; removed `web_include_js` and `signup_form_template` | — |

**Deleted:** `public/js/custom_signup.js`, `templates/signup.html`.

### Security

- OTP: 6 digits, 5 attempts per code, 5 sends per channel — 25 guesses against 10⁶, then the session is spent. Stored as an HMAC keyed with the site `encryption_key`, which is not in the database.
- Wrong and expired codes are indistinguishable, by design.
- The signup is bound to the browser by an **httpOnly cookie**, not `frappe.session.sid` — all Frappe guests share the sid `"Guest"` (`frappe/sessions.py:251`), so binding to it would bind to nothing.
- No endpoint accepts a Customer identifier; `decide` takes only yes or no; `complete` re-runs matching inside the lock and discards a stored decision the fresh result disagrees with.
- The "already has an account" verdict is only delivered *after* the relevant channel is verified, so it cannot be used to enumerate.

### Race safety, in increasing order of reliability

1. Matching re-runs inside the critical section, immediately before writing.
2. A Redis lock on the verified phone — best-effort, degrades to a no-op if Redis is down.
3. The unique indexes on `Webshop Account Identity`. This is the guarantee.

### Testing

221 tests: `bench --site erpnext run-tests --app custom_webshop`

| Module | Tests | Covers |
|---|---|---|
| `test_identity` | 47 | E.164 across 4 prefixes × 9 formats, email, name rules, Arabic folding |
| `test_otp` | 26 | issue, verify, expiry, attempts, cooldown, cross-channel replay |
| `test_signup_session` | 23 | every valid transition and every forbidden one |
| `test_contact_hooks` | 8 | canonical phone maintenance |
| `test_matching` | 27 | every classification row + recognition-card privacy |
| `test_resolution` | 11 | identity beats stray Portal User rows |
| `test_legacy_signup` | 5 | the old endpoint is closed |
| `test_signup_flow` | 40 | all 18 end-to-end scenarios |
| `test_signup_security` | 21 | brute force, replay, enumeration, forged candidates |
| `test_signup_races` | 13 | concurrency, idempotency, Redis-down |

Plus an HTTP smoke test over the real request path — the only way to exercise the binding cookie. It caught one bug the unit tests masked: clearing the cookie on `COMPLETED` broke idempotent re-submits.

### Bugs found by walking the runbook end to end

The 18-scenario walkthrough, driven over real HTTP rather than in-process,
surfaced four defects the unit tests could not see. Every one of them is a
case of code that behaves correctly inside a single function and wrongly
across a request boundary.

| # | Defect | Why the tests missed it |
|---|---|---|
| 1 | **OTP brute-force cap did nothing.** `verify` reports a wrong code by raising; Frappe rolls the request transaction back on an unhandled exception, so the incremented attempt counter was discarded. Seven wrong guesses over HTTP left `attempts` at 0 and the code live. | Unit tests call `verify` in-process, where nothing rolls back. Fixed by `otp._persist_failed_attempt`, which commits the counter before the throw. |
| 2 | **Session expiry never persisted**, for the same reason — `load` marked a session EXPIRED and then raised, discarding the write. | Same. Fixed by `session._mark_expired`. |
| 3 | **A new Int setting arrives as `0`** on an already-saved Single, because Frappe only applies DocType defaults on insert. `signup_starts_per_hour_per_ip` landed as 0, and a 0 rate limit refuses *every* request — signup would have gone down site-wide on the next migrate. Fixed by `settings.MUST_BE_POSITIVE` plus the `backfill_zeroed_signup_settings` patch. | No test had ever added a setting to an existing Single. |
| 4 | **Changing your email was blocked by the resend cooldown.** A typo'd address could not be corrected for a minute. The cooldown exists to stop one address being mail-bombed; a change targets a different address. `otp.reset` now clears it, while the send cap — the control that actually bounds abuse — is untouched. | The cooldown was only ever tested against a resend, never against a change. |

Also raised the per-IP signup cap from 10/hour to a configurable 30: mobile
carriers in Egypt route many subscribers through one public address, so the
original value would have blocked real customers.

### Country picker on the phone field

The phone field is now a country selector plus a national-number input, the
shape people expect from `intl-tel-input` and similar — but with no library
and no bundled country table.

**Where the data comes from.** Names from Frappe's own `Country` doctype (the
same list the Desk shows, already translated); dialling codes and example
numbers from `phonenumbers`, which ships with Frappe; flags as emoji derived
from the ISO code, so no image assets. 243 countries, assembled once and
cached, with the cache invalidated by a `Country` doc_event.

**What choosing a country does.** It sets the dialling code, swaps the
placeholder and hint for a real example from that country, and — the point of
the exercise — decides which rules the number is validated against.
`506 234 5678` is a valid 🇨🇦 number and an invalid 🇪🇬 one, and vice versa for
`01012345678`.

| Piece | Where |
|---|---|
| `flag_emoji`, `dial_code`, `example_national_number`, `normalize_region` | `signup/identity.py` |
| List assembly, caching, guest endpoint | `signup/countries.py` |
| `phone_country` on `start` / `change_phone`, region resolution | `api/signup.py` |
| `phone_country` column, carried in the envelope | `Webshop Signup Session`, `signup/session.py` |
| Picker UI, search, RTL-aware styles | `public/js/page-signup.js`, `www/login/index.html` |

**Two details worth keeping in mind.** An unknown or missing region falls back
to the configured default rather than meaning "no rules at all". And a number
typed in full international form is honoured whatever the picker says, so a
pasted `+20…` always works.

Adding the picker also exposed a message bug: the invalid-number error was
hard-coded to the Egyptian example, so someone entering a Canadian number was
told to type `01012345678`. It now quotes the selected country's own format.

Storage was still split at this point — Egyptian numbers in local `01…` form,
everything else in E.164. That is what the next section changes.

### Rollback

1. `Website Settings.disable_signup = 1` — instant, no deploy.
2. `Webshop Signup Settings.signup_enabled = 0`.
3. `phone_otp_enabled = 0` if the SMS gateway fails.
4. `git revert` + `bench migrate`. Every schema change is additive; no rollback step deletes data.

### Before this can go live

Both are configuration, not code:

- [ ] An **Email Account** with `enable_outgoing` and `default_outgoing` — the site has only test accounts today, so email OTP cannot deliver.
- [ ] **SMS Settings** gateway URL and parameters — unconfigured today, so phone OTP cannot deliver. Any HTTP provider works by config alone; an SDK-based one goes in `sms_sender_method`.
- [ ] Run `bench --site <site> execute custom_webshop.signup.audit.report` and review.
- [ ] Then: `email_otp_enabled` → soak → `phone_otp_enabled` → `signup_enabled=1` → `disable_signup=0`.

### Deliberately not automated

Merging duplicate Customers, and backfilling identity rows for accounts that predate this flow. Both make identity judgements that touch sales, invoices and accounting history. The audit report surfaces them; a person decides.

---

## Edit 5: One stored phone format, and per-country input rules

Two requests, and they turned out to be the same problem seen from both ends:
save every number in international form, and make choosing a country actually
constrain what can be typed for it.

### The storage rule

Every phone this app writes is now E.164 — `+201012345678` — whatever country
it came from and however it was typed:

| Column | Before | Now |
|---|---|---|
| `Contact Phone.phone` | `01101271160` (local for 🇪🇬, E.164 elsewhere) | `+201101271160` |
| `Contact Phone.custom_phone_e164` | `+201101271160` | unchanged |
| `User.mobile_no` | `01101271160` | `+201101271160` |
| `Customer.mobile_no` | `01101271160` | `+201101271160` |
| `Webshop Account Identity.phone_e164` | `+201101271160` | unchanged |

One column, one convention. **Reading stays forgiving**: rows written before
this rule, and rows `contact_enhancements` writes on its own paths, still hold
the local form, and `matching.phone_variants` still searches for every written
form — so nobody becomes invisible to matching. `identity.to_local` therefore
survives, no longer as a storage helper but as the thing that reproduces the
legacy form for lookup.

### The conflict this ran into

Partway through this work `contact_enhancements` gained a Contact `validate`
hook, `normalize_and_validate_contact_phones`, which rewrites **every** phone
row into its local national form on every save, judged against a new mandatory
`Contact.country` field. That app is read-only to us, and its rule is a
deliberate one for the Contacts staff maintain.

So this app does not fight it in general. `custom_webshop` is registered after
it and therefore always has the last word, and using that to overrule it
everywhere would quietly delete a feature its author had just added. Instead it
reclaims exactly the numbers it is answerable for — one that is the verified
identity of a webshop account, which `Webshop Account Identity.phone_e164`
names. A Contact staff edit by hand keeps the local form that app intends.

Three things were needed to make that hold:

- **`Contact.country` is set from the signup's own country**, so a verified
  Saudi number is judged under the Saudi plan instead of the Egyptian default.
  Guarded on `has_field`, so this app still works whether or not that one is
  installed. On an existing Contact it only ever fills a blank — changing it
  would re-judge phone numbers this signup never touched.
- **The canonical column is read under the Contact's own country.** Once a
  Saudi number has been localised to `0512345678`, reading it as Egyptian
  yields nothing at all, which would have left every foreign Contact invisible
  to phone matching.
- **The verified number is announced on the request** for the length of a
  finalise. The identity row that would otherwise prove the number is written
  last, and most of the Contact saves during a finalise are made by other
  people's code holding their own copy of the document.

### A duplicate-row bug this uncovered

Frappe's own `Contact.add_phone` — reached from `create_contact` inside
`User.on_update` — decides whether a number is already present with an **exact
string** comparison. A Contact left in local form while `User.mobile_no` held
E.164 read as two different numbers, so Frappe appended a second phone row for
the same phone, and then a third, because granting a role fires `on_update`
again. Keeping the Contact canonical throughout the finalise fixes it at the
source. `test_the_same_number_is_not_appended_twice` pins it.

### The dial code and the number now read as one

`+20` sitting beside `01012345678` is not a number anyone can dial. The
leading zero is a **trunk prefix**, dropped the moment a country code goes in
front; the real number is `+20 10 01234567`. The same misread affected every
country with a trunk zero — Saudi, the UK, Germany, the UAE.

So the field drops it as you type. People go on typing `01012345678` out of
habit and the zero comes off, leaving `+20` and `1012345678` reading as one
correct number. A pasted `+20…` or `0020…` loses its country code the same way.

`trunk` comes from `phonenumbers`' own metadata, so this is right everywhere —
`0` across most of the world, `1` in North America, and **nothing at all** in
Italy, where the leading zero really is part of the number and stripping it
would break it. The first `0` someone types is left alone until there is a
number behind it, so nothing vanishes under them mid-keystroke.

Stripping is a display rule, never a validation one: `to_e164` still accepts
`1012345678`, `01012345678`, `+201012345678` and `00201012345678`, so the field
being forgiving never depends on the client behaving.

Two consequences worth noting:

- **Lengths are now the national significant number** — Egypt is 10, not 10-or-11.
  That is what the field holds.
- **Placeholders lost their trunk prefix too** (`10 01234567`, not `010 01234567`),
  because a placeholder that shows a shape the field then rewrites teaches the
  wrong thing. The grouping still comes from the library, so it is the one that
  country really uses.

The name placeholder stopped being a real person's name at the same time —
*"Your full name"* / *"اسمك الثلاثي"* instead of a plausible customer.

### Per-country input rules

`phonenumbers` publishes the lengths a mobile number may have in each region,
so the country payload now carries them and the field enforces them:

| Country | Accepted digit counts |
|---|---|
| 🇪🇬 Egypt | 10 or 11 (`1012345678` or `01012345678`) |
| 🇸🇦 Saudi Arabia | 9 or 10 |
| 🇩🇪 Germany | 10, 11 or 12 |

The metadata gives the national significant number; people also type the
national prefix, so both are offered.

- The input **stops accepting digits** at the country's maximum.
- A wrong length shows a correction under the field — *"Numbers in Egypt have
  10 / 11 digits — you have typed 7."* — and a tick appears once it is right.
  Neither is a standing hint: an untouched field says nothing, which is why the
  old permanent "we store it as +20…" line stays gone.
- Switching country **re-judges what is already typed** without trimming it.
  Silently deleting digits somebody typed would be worse than telling them.
- The invalid-number message quotes the selected country's example.

The length check is feedback, never authority — `0101234567` is a length Egypt
uses and is not a real number. `identity.to_e164` still decides.

### The blocked panel was a dead end

Reported from the live site: a signup that used an email which already has an
account showed *"You already have an account"* and stopped there. The verdict
was right — `EMAIL_ACCOUNT_EXISTS`, delivered only after the address was
verified, so the page still cannot be used to probe which emails exist — but
the panel offered only **Sign in** and **Reset password**, both of which assume
the account we found is yours.

The ordinary way to arrive there is mistyping one of your own addresses, and
there was nothing on the panel that starts a new signup. Worse, `BLOCKED` is
not in the list of states that get discarded on reload, so the session came
back from `sessionStorage` every time: a dead end that followed you. The only
escape was clearing browser storage by hand.

The panel now carries a third, quieter action — *"Sign up with different
details"* — reusing the existing `#restart` handler, which forgets the session
and returns to step one. Two cosmetic defects on the same panel went with it:
`.auth-submit-btn` had no `text-decoration: none`, so the one place it is used
as a real `<a>` rendered underlined, and the two actions were split into equal
halves, which broke the short Arabic label across two lines while the longer
one beside it had room to spare.

### A leaking-listener bug this uncovered

The country popup installed a document-level click closer that returned early
when the click was inside the field — without removing itself. Every open left
another behind, and each one re-rendered the page on the next click anywhere
else, which replaced the DOM mid-submit and wiped the validation message the
person needed to read. Both listeners are now owned and released in one place.

### contact_enhancements moved the goalposts mid-flight

That app's phone hook was rewritten while this work was in progress. The
numbering plan it validates against now lives on **each phone row**
(`Contact Phone.country`), not on the Contact, and it fills that in itself from
any number written with a country code.

That turns out to suit us: because this app always writes E.164, its detection
always succeeds, so nothing here needs to set a country at all — the
`Contact.country` code written against the previous shape was removed rather
than ported. Two things had to follow it:

- The canonical column is derived per row, from `Contact Phone.country`, read
  with `.get` so a site where that field is not yet installed still works.
- `_store_phone_canonically` no longer matches rows by `custom_phone_e164`.
  That column is derived by our own hook, and for a foreign number left in
  local form it cannot be derived at all — `0512345678` is not a number in
  Egypt, so the row would never have been found. It now parses each row under
  the region of the number the signup just verified, which is not in doubt.

### Files

| Piece | Where |
|---|---|
| `national_number_lengths`, `national_trunk_prefix`, `example_significant_number`, `region_for_e164` | `signup/identity.py` |
| `lengths`, `max_len`, `trunk`, trunk-free `example` | `signup/countries.py` |
| E.164 writes, `Contact.country`, the request-scoped announcement | `signup/linking.py` |
| Region-aware canonicalisation, reclaiming verified numbers | `contact_hooks.py` |
| Trunk stripping, input cap, live verdict, country-aware error | `public/js/page-signup.js` |
| Valid / invalid states, the note | `www/login/index.html` |
| Migration for accounts created before the rule | `patches/canonicalize_webshop_owned_phones.py` |
| 20 tests | `tests/test_phone_rules.py` |

### Migration

`canonicalize_webshop_owned_phones` converts what earlier signups already
stored. Deliberately narrow: only a phone that is the verified number of an
account this app created, reached from its identity row. It does not sweep the
`Contact Phone` table — most rows there belong to Contacts
`contact_enhancements` maintains and would be written back in local form on the
next Lead conversion, so converting them would be churn, not consistency.
Numbers it cannot parse (this site has two) are left untouched rather than
blanked. Idempotent.

### Test hygiene fixed along the way

Completing a signup commits, so every test that ran one survived its own
rollback; two dozen accounts had accumulated on this site. `unique_phone` now
starts from a random base instead of handing out the same numbers every run,
`purge_test_accounts` removes what a run leaves behind, and the migration test
stubs the patch's commit so it can no longer rewrite live records as a side
effect of running the suite.

### Verified

- 314 tests green.
- A real HTTP signup with a Saudi number typed as `512345678` stored
  `+966512345678` in all five columns, with `Contact.country` = Saudi Arabia.
- Browser checks across 🇪🇬/🇸🇦/🇩🇪: maxlength, the digit cap, the note, the
  tick, re-judging on country switch, and a wrong-length submit refused before
  the server.
- The blocked panel's escape: the session is forgotten, step one returns, and
  it does not come back on reload.
- A live signup completed after these changes (`شركة العمال`) stored
  `+201101275568` in every column.
- 328 tests green after the trunk change.
- Browser: typing `01012345678` settles to `1012345678`, a lone `0` is not
  snatched away, pasted `+20…` and `0020…` lose their country code, Saudi and
  Italy behave per their own metadata, and the row reads `+20 1012345678`.
- HTTP: submitting the trunk-free `1012349876` stored `+201012349876`
  everywhere.

---

## Future Edits (Planned)

- Guest cart merge on login/signup.
- Multi-user company accounts (`Webshop Account Identity.customer` is indexed, not unique, to leave room for this).
- Custom checkout flow replacement.
