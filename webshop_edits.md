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

## Future Edits (Planned)

- Auto-login & redirect after signup.
- Guest cart merge on login/signup.
- Custom checkout flow replacement.
