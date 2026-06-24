# Team Collaboration Workflow

## Workstreams

1. **Frontend Platform** — `templates/shop/web.html`, `includes/cnc/*`, `public/css/cnc/*`, `public/js/shared/*`
2. **Catalog/PDP** — `www/shop/all-products.*`, product generator skins
3. **Cart/Checkout** — `www/shop/cart.*`, cart drawer wiring
4. **Account** — `www/shop/orders.*`, `payment.*`, auth skinning
5. **Integration Lead** — `hooks.py`, `shop/*`, merge arbitration
6. **QA** — test matrix in `docs/qa-rollout.md`

## Branching

- `main` — production
- `integration/webshop-frontend` — weekly merge target
- Feature branches: `feat/webshop-shell`, `feat/catalog-pdp-ui`, `feat/cart-checkout-ui`, `feat/orders-payment-ui`, `feat/auth-ui`

## Merge Rules

- Shared chrome merges only via Frontend Platform owner
- Route templates via Integration Lead
- Rebase daily on integration branch during migration window
- PRs scoped to one page family or one shared component set

## Review Cadence

- Daily 15-min integration sync
- Twice-weekly visual QA vs `New_Frontend/` prototype
- Weekly E2E demo on staging
