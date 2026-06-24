# Backend Integration Contracts (Frozen)

Do not modify backend business logic. Frontend must consume these endpoints as-is.

## Method Overrides (`hooks.py`)

| Original path | Override |
|---------------|----------|
| `webshop.webshop.shopping_cart.cart.place_order` | `custom_webshop.shopping_cart.cart_override.place_order_from_cart` |
| `webshop.webshop.shopping_cart.cart.request_for_quotation` | same as place_order |
| `webshop.webshop.shopping_cart.cart.update_cart` | `custom_webshop.shopping_cart.cart_override.update_cart` |
| `webshop.webshop.shopping_cart.cart.update_cart_address` | `custom_webshop.shopping_cart.cart_override.update_cart_address` |
| `frappe.core.doctype.user.user.sign_up` | `custom_webshop.api.auth.custom_sign_up` |

## Auth APIs

- `frappe.core.doctype.user.user.sign_up` (overridden) — signup with mobile
- `frappe.core.doctype.user.user.test_password_strength` — password validation
- Frappe session login at `/login`

## Product APIs

- `webshop.webshop.api.get_product_filter_data` — catalog listing
- `webshop.webshop.shopping_cart.product_info.get_product_info_for_website` — PDP
- Website Item generator routes — product detail pages

## Cart / Checkout APIs

- `webshop.webshop.shopping_cart.cart.update_cart` (overridden)
- `webshop.webshop.shopping_cart.cart.update_cart_address` (overridden)
- `webshop.webshop.shopping_cart.cart.get_cart_quotation`
- `webshop.webshop.shopping_cart.cart.apply_coupon_code`
- `webshop.webshop.shopping_cart.cart.place_order` (overridden → draft SO)
- `custom_webshop.shopping_cart.cart_override.add_customer_info`
- `custom_webshop.shopping_cart.cart_override.update_customer_info`
- `custom_webshop.shopping_cart.shipping_api.get_governorate_shipping_rules`
- `custom_webshop.shopping_cart.shipping_api.get_governorates`
- `custom_webshop.shopping_cart.shipping_api.update_cart_shipping`

## Orders / Payment APIs

- `custom_webshop.api.payment.confirm_payment` — base64 receipt upload, submits SO
- Order list context: Portal User → Customer → Sales Orders
- Order detail: `/shop/orders/<SO-name>` via webshop `order` template

## Checkout Flow

1. Cart quotation (session)
2. Address + governorate shipping on cart
3. `place_order` → draft Sales Order
4. Redirect to `/shop/payment?order_id=<SO>`
5. `confirm_payment` → submit SO

## Dependencies

- `webshop`, `erpnext`, `custom_shipping_rule` (Governorate shipping)
