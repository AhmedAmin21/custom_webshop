# QA & Rollout Checklist

## Pre-deploy

- [ ] `bench --site <site> clear-cache`
- [ ] `bench build --app custom_webshop`
- [ ] Verify `/shop` returns 200
- [ ] Verify `/shop/all-products` loads filters + product grid
- [ ] Verify `/shop/cart` with items in quotation
- [ ] Verify place order → `/shop/payment?order_id=`
- [ ] Verify `confirm_payment` submits draft SO
- [ ] Verify `/shop/orders` lists customer SOs
- [ ] Verify legacy redirects (`/cart`, `/orders`, `/payment`)
- [ ] Guest → login redirect on payment page
- [ ] Signup creates Customer + Portal User

## Test Matrix

| Journey | Steps | Expected |
|---------|-------|----------|
| Browse | `/shop` → all-products | Categories, trending items |
| Add to cart | PDP → add | Cart count cookie updates |
| Checkout | cart → address → shipping → place order | Draft SO, payment redirect |
| Pay | payment → upload → submit | SO submitted, order detail |
| Orders | `/shop/orders` | List with Pay Now for draft |
| Auth | signup → login → shop | Session established |

## Rollout

1. Deploy to staging
2. Run full test matrix
3. Visual diff vs `New_Frontend/` prototype
4. Production cutover
5. Monitor Error Log for 48h

## Prototype Cleanup (post-cutover)

- Keep `New_Frontend/` as design reference only
- Remove any localStorage cart/order logic from new JS
- Do not expose admin panel from prototype on public site
