# Folder Layout & Ownership

```
custom_webshop/
  shop/                    # Integration Lead — routes + context helpers
  docs/                    # Integration Lead — contracts, mapping, QA
  www/shop/                # Integration Lead — route templates + page .py/.js
  templates/
    shop/web.html          # Frontend Platform — base layout
    includes/cnc/          # Frontend Platform — shared chrome
    includes/shop/         # Page teams — page-specific partials
    includes/cart/         # Cart team — backend cart fragments (read-only)
    pages/cart.*           # Cart team — legacy /cart override (kept for API)
  public/
    css/cnc/base.css       # Frontend Platform — design tokens + layout
    css/cart.css           # Cart team — cart UX
    js/shared/             # Frontend Platform — ui, i18n, api
    js/pages/              # Page teams — home, catalog, etc.
  New_Frontend/            # Design reference only — do not edit in production
```

## Ownership Rules

| Path | Owner |
|------|-------|
| `templates/includes/cnc/*` | Frontend Platform |
| `public/css/cnc/*` | Frontend Platform |
| `public/js/shared/*` | Frontend Platform |
| `public/js/pages/home.js` | Home team |
| `www/shop/all-products.*` | Catalog team |
| `www/shop/cart.*` | Cart/Checkout team |
| `www/shop/orders.*`, `payment.*` | Account team |
| `shop/*`, `hooks.py`, `path_resolver.py` | Integration Lead |
| `shopping_cart/*`, `api/*` | Backend (frozen) |
