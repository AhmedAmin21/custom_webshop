# Frontend-to-Backend Page Mapping

Base URL: `/shop` (`http://<IP>/shop`)

| Page | Route | Template | Context / API | User flow |
|------|-------|----------|---------------|-----------|
| Home | `/shop` | `www/shop/index.html` | Item groups, trending Website Items | Browse → catalog/PDP |
| All Products | `/shop/all-products` | `www/shop/all-products.html` | `get_product_filter_data`, filter engine | Filter → PDP → cart |
| Product Detail | Website Item `route` | webshop generator | `get_product_info_for_website` | View → add to cart |
| Cart | `/shop/cart` | `www/shop/cart.html` | `get_cart_quotation`, cart overrides | Edit → ship → place order |
| Orders | `/shop/orders` | `www/shop/orders.html` | Portal User SO list | View → pay or detail |
| Order Detail | `/shop/orders/<SO>` | webshop `order` template | SO doc + permissions | View status |
| Payment | `/shop/payment?order_id=` | `www/shop/payment.html` | `confirm_payment` | Upload proof → submit |
| Login | `/shop/login` | redirect | Frappe `/login` | Auth → return to shop |
| Signup | `/shop/signup` | redirect | Frappe signup + custom template | Register → login |

## Legacy Redirects

- `/cart` → `/shop/cart`
- `/orders` → `/shop/orders`
- `/payment` → `/shop/payment`
- `/all-products` → `/shop/all-products`

## UI Components by Page

- **Shared**: `templates/includes/cnc/*` (top bar, navbar, footer, drawer, toasts)
- **Cart**: `templates/includes/shop/cart_page.html` + cart includes
- **Payment**: payment method cards, upload form
- **Orders**: order cards + `order_stepper.html`
