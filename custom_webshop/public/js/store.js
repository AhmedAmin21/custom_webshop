/* ==========================================================================
   CNCLeaders — Shared Store
   Handles: state, i18n, theme, API adapter, cart badge, toast, session
   ========================================================================== */

const TRANSLATIONS = {
    en: {
        nav_home: "Home", nav_catalog: "All Products", nav_orders: "Track Orders", nav_admin: "Admin Panel",
        home_shop_material: "Shop by Material", home_shop_material_sub: "Browse components by manufacturing material",
        material_wood: "Wood & MDF", material_acrylic: "Marble & Glass", material_metal: "Aluminum & Metals",
        material_all: "View all categories", home_shop_category: "Shop by Category",
        home_shop_category_sub: "Swipe through certified high-precision parts by class",
        home_shop_attribute: "Shop by Attribute", home_shop_attribute_sub: "Browse products grouped by their attributes",
        filter_attribute: "Attribute",
        home_shop_tool_family: "Shop by Tool Family", home_shop_tool_family_sub: "Browse products by cutting tool family",
        filter_tool_family: "Tool Family", filter_material: "Material",
        home_trending: "Trending Equipment", home_trending_sub: "Most demanded components",
        home_shop_brand: "Shop by Certified Brand", home_shop_brand_sub: "Genuine components from authorized industrial manufacturers",
        filter_search: "Search", filter_search_placeholder: "Search by model or spec...",
        filter_category: "Category", filter_stock: "Stock Status", filter_instock_only: "In Stock Only",
        filter_max_price: "Max Price", filter_brand: "Brand", btn_reset_filters: "Reset Filters",
        catalog_sort: "Sort: ", sort_default: "Default Sync Order", sort_price_asc: "Price: Low to High",
        sort_price_desc: "Price: High to Low", sort_alpha: "A-Z Name", cart_selected: "Your Selected Hardware",
        cart_cost_structure: "Order Cost Structure", cart_subtotal: "Subtotal", cart_total_weight: "Total Weight",
        cart_shipping: "Shipping", cart_shipping_company: "Shipping Company",
        cart_total: "Grand Total", cart_delivery: "Delivery & Shipping Address", cart_name: "Full Name / Company Name *",
        cart_name_placeholder: "e.g. John Doe, Machining LLC", cart_phone: "Contact Phone Number *",
        cart_phone_placeholder: "e.g. +1 555-0199", cart_address: "Shipping Address *",
        cart_address_placeholder: "Street address, unit, city, state, zip code...", cart_notes: "Machining Details / Delivery Instructions",
        cart_notes_placeholder: "Notes (e.g. loading dock hours, fork-lift requirements)", cart_proceed: "Proceed to checkout",
        cart_empty: "Your cart is empty.", cart_goto_shop: "Browse Products",
        payment_title: "Checkout", payment_subtitle: "To complete order processing and trigger ERPNext packaging, please wire the total amount and upload your receipt screenshot below.",
        payment_amount_label: "Amount Outstanding", payment_method: "Choose Payment Method",
        payment_upload_title: "Provide Payment Confirmation", payment_upload_text: "Drag and drop your bank slip screenshot or click to browse files",
        payment_upload_note: "Accepted formats: JPG, PNG (Max 5MB)", payment_submit: "Submit Payment Proof",
        payment_track: "Back to Orders", orders_title: "Purchase Orders",
        orders_subtitle: "", btn_add_to_cart: "Add to Cart",
        btn_out_of_stock: "Out of Stock", btn_remove: "Remove", btn_details: "View Details",
        toast_added_cart: "Added to Cart!", toast_removed_cart: "Component removed from cart.",
        catalog_results: "Showing {count} components", catalog_no_results: "No components match your filters.",
        orders_empty: "No orders found.", order_status_draft: "Awaiting Payment", order_pay_now: "Pay Now",
        order_view: "View Order", order_date: "Date", order_total: "Total", order_status: "Status",
        auth_login_title: "Log in", auth_login_sub: "",
        auth_email: "E-mail Address", auth_password: "Password", auth_login_btn: "Authenticate",
        auth_no_account: "No account?", auth_signup_link: "Create one",
        auth_signup_title: "New Account", auth_signup_sub: "Register for industrial product procurement.",
        auth_name: "Full Name / Company", auth_phone: "Mobile Number", auth_confirm_password: "Confirm Password",
        auth_signup_btn: "Create Account", auth_has_account: "Already have an account?", auth_login_link: "Sign In",
        loading: "Loading...", error_generic: "Something went wrong. Please try again.",
        shipping_destination: "Shipping Destination (Governorate)", shipping_select: "Select governorate...",
        shipping_company_select: "Select shipping company...",
        cart_shipping_required: "Please select a shipping company and governorate.",
        cart_delivery_required: "Please fill in your name, phone, and shipping address."
    },
    ar: {
        nav_home: "الرئيسية", nav_catalog: "جميع المنتجات", nav_orders: "تتبع الطلبات", nav_admin: "لوحة التحكم",
        home_shop_material: "تسوق حسب خامة التشغيل", home_shop_material_sub: "تصفح المكونات حسب مادة التصنيع",
        material_wood: "الأخشاب و ال MDF", material_acrylic: "الرخام والزجاج", material_metal: "الألومنيوم والمعادن",
        material_all: "عرض كل التصنيفات", home_shop_category: "تسوق حسب الفئة",
        home_shop_category_sub: "تصفح أجزاء عالية الدقة معتمدة حسب الفئة",
        home_shop_attribute: "تسوق حسب الخصائص", home_shop_attribute_sub: "تصفح المنتجات مجمعةً حسب خصائصها",
        filter_attribute: "الخصائص",
        home_shop_tool_family: "تسوق حسب عائلة الأداة", home_shop_tool_family_sub: "تصفح المنتجات حسب عائلة أداة القطع",
        filter_tool_family: "عائلة الأداة", filter_material: "الخامة",
        home_trending: "المعدات الشائعة",
        home_trending_sub: "المكونات الأكثر طلباً", home_shop_brand: "تسوق حسب العلامة التجارية المعتمدة",
        home_shop_brand_sub: "مكونات أصلية من الشركات المصنعة الصناعية المعتمدة", filter_search: "بحث",
        filter_search_placeholder: "ابحث بالنموذج أو المواصفات...", filter_category: "الفئة", filter_stock: "حالة المخزون",
        filter_instock_only: "متوفر فقط", filter_max_price: "الحد الأقصى للسعر", filter_brand: "العلامة التجارية",
        btn_reset_filters: "إعادة ضبط المرشحات", catalog_sort: "ترتيب: ", sort_default: "الترتيب الافتراضي",
        sort_price_asc: "السعر: من الأقل للأعلى", sort_price_desc: "السعر: من الأعلى للأقل", sort_alpha: "أ-ي حسب الاسم",
        cart_selected: "أجهزتك المختارة", cart_cost_structure: "هيكل تكلفة الطلب", cart_subtotal: "المجموع الفرعي",
        cart_total_weight: "الوزن الإجمالي", cart_shipping: "الشحن", cart_shipping_company: "شركة الشحن",
        cart_total: "الإجمالي النهائي", cart_delivery: "عنوان التوصيل والشحن",
        cart_name: "الاسم الكامل / اسم الشركة *", cart_name_placeholder: "مثال: جون دو، شركة الآلات المحدودة",
        cart_phone: "رقم هاتف الاتصال *", cart_phone_placeholder: "مثال: +1 555-0199", cart_address: "عنوان الشحن *",
        cart_address_placeholder: "عنوان الشارع، الوحدة، المدينة، الولاية، الرمز البريدي...", cart_notes: "تفاصيل الآلات / تعليمات التوصيل",
        cart_notes_placeholder: "ملاحظات (مثل ساعات الرصيف، متطلبات الرافعة الشوكية)", cart_proceed: "متابعة لإتمام الشراء",
        cart_empty: "سلتك فارغة.", cart_goto_shop: "تصفح المنتجات",
        payment_title: "الدفع", payment_subtitle: "لإكمال معالجة الطلب وبدء التغليف، يرجى تحويل المبلغ الإجمالي وتحميل لقطة شاشة للإيصال أدناه.",
        payment_amount_label: "المبلغ المستحق", payment_method: "اختر طريقة الدفع", payment_upload_title: "تقديم تأكيد الدفع",
        payment_upload_text: "قم بسحب وإفلات لقطة شاشة لإيصال البنك أو انقر لاستعراض الملفات", payment_upload_note: "الصيغ المقبولة: JPG، PNG (الحد الأقصى 5 ميجابايت)",
        payment_submit: "إرسال إثبات الدفع", payment_track: "العودة للطلبات", orders_title: "طلبات الشراء",
        orders_subtitle: "", btn_add_to_cart: "أضف إلى السلة",
        btn_out_of_stock: "نفذت الكمية", btn_remove: "إزالة", btn_details: "عرض التفاصيل",
        toast_added_cart: "تمت الإضافة إلى السلة!", toast_removed_cart: "تم إزالة المكون من السلة.",
        catalog_results: "عرض {count} مكونات", catalog_no_results: "لا توجد مكونات تطابق معاييرك.",
        orders_empty: "لا توجد طلبات.", order_status_draft: "في انتظار الدفع", order_pay_now: "ادفع الآن",
        order_view: "عرض الطلب", order_date: "التاريخ", order_total: "الإجمالي", order_status: "الحالة",
        auth_login_title: "تسجيل الدخول", auth_login_sub: "",
        auth_email: "البريد الإلكتروني", auth_password: "كلمة المرور", auth_login_btn: "تسجيل الدخول",
        auth_no_account: "ليس لديك حساب؟", auth_signup_link: "إنشاء حساب",
        auth_signup_title: "حساب جديد", auth_signup_sub: "سجل لشراء المنتجات الصناعية.",
        auth_name: "الاسم الكامل / الشركة", auth_phone: "رقم الموبايل", auth_confirm_password: "تأكيد كلمة المرور",
        auth_signup_btn: "إنشاء حساب", auth_has_account: "هل لديك حساب بالفعل؟", auth_login_link: "تسجيل الدخول",
        loading: "جاري التحميل...", error_generic: "حدث خطأ. يرجى المحاولة مرة أخرى.",
        shipping_destination: "وجهة الشحن (المحافظة)", shipping_select: "اختر المحافظة...",
        shipping_company_select: "اختر شركة الشحن...",
        cart_shipping_required: "يرجى اختيار شركة الشحن والمحافظة.",
        cart_delivery_required: "يرجى إدخال الاسم والهاتف وعنوان الشحن."
    }
};

/* --------------------------------------------------------------------------
   Material label map — mirrors item_parser.py MATERIAL_LABELS
   -------------------------------------------------------------------------- */
const MATERIAL_LABELS_JS = {
    "C":   { en: "Carbide",                                 ar: "كربيد" },
    "HSS": { en: "HSS",                                     ar: "صلب عالي السرعات" },
    "TCT": { en: "TCT",                                     ar: "عود كربيد ملحوم في جسم صلب" },
    "CW":  { en: "CW",                                      ar: "شفرات كربيد ملحومة فى جسم صلب" },
    "CM":  { en: "CM",                                      ar: "كربيد يستخدم فى المعادن" },
    "M&G": { en: "M&G",                                     ar: "رخام و زجاج" },
};

/* --------------------------------------------------------------------------
   Store — singleton state container
   -------------------------------------------------------------------------- */
const Store = {
    lang: "ar",
    theme: "light",
    user: null,
    isGuest: true,
    csrfToken: "",

    /* ------------------------------------------------------------------
       Translation helper
       ------------------------------------------------------------------ */
    t(key, params = {}) {
        const dict = TRANSLATIONS[this.lang] || TRANSLATIONS["en"];
        let str = dict[key] !== undefined ? dict[key] : key;
        for (const [k, v] of Object.entries(params)) {
            str = str.replace(`{${k}}`, v);
        }
        return str;
    },

    /* ------------------------------------------------------------------
       Material label helper
       ------------------------------------------------------------------ */
    materialLabel(code) {
        const entry = MATERIAL_LABELS_JS[code];
        if (!entry) return code;
        return entry[this.lang] || entry["en"] || code;
    },

    /* ------------------------------------------------------------------
       Language
       ------------------------------------------------------------------ */
    applyLanguage(lang) {
        this.lang = lang;
        localStorage.setItem("cnc_lang_v2", lang);
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
        if (lang === "ar") {
            document.body.classList.add("rtl");
        } else {
            document.body.classList.remove("rtl");
        }
        // Update all i18n elements
        document.querySelectorAll("[data-i18n]").forEach(el => {
            el.textContent = this.t(el.getAttribute("data-i18n"));
        });
        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            el.setAttribute("placeholder", this.t(el.getAttribute("data-i18n-placeholder")));
        });
        // Update lang button label
        const langBtnText = document.getElementById("lang-btn-text");
        if (langBtnText) langBtnText.textContent = lang === "en" ? "AR" : "EN";
        // Update cart badge
        this.updateCartBadge();
    },

    /* ------------------------------------------------------------------
       Theme
       ------------------------------------------------------------------ */
    applyTheme(theme) {
        this.theme = theme;
        localStorage.setItem("cnc_theme", theme);
        if (theme === "dark") {
            document.body.classList.add("dark-theme");
        } else {
            document.body.classList.remove("dark-theme");
        }
        const themeBtn = document.getElementById("theme-btn");
        if (themeBtn) {
            const sun = themeBtn.querySelector(".icon-sun");
            const moon = themeBtn.querySelector(".icon-moon");
            if (theme === "dark") {
                if (sun) sun.style.display = "none";
                if (moon) moon.style.display = "block";
            } else {
                if (sun) sun.style.display = "block";
                if (moon) moon.style.display = "none";
            }
        }
    },

    /* ------------------------------------------------------------------
       Debug log — posts to server (browser cannot reach localhost ingest)
       ------------------------------------------------------------------ */
    debugLog(location, message, data = {}, hypothesisId = "", runId = "") {
        fetch("/api/method/custom_webshop.api.debug_log.log_client_event", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({
                location,
                message,
                data: JSON.stringify(data),
                hypothesis_id: hypothesisId,
                run_id: runId,
            }),
        }).catch(() => {});
    },

    productPrice(item) {
        if (!item) return "—";
        if (item.formatted_price) return item.formatted_price;
        if (item.price_list_rate != null) return parseFloat(item.price_list_rate).toFixed(2);
        if (item.price != null) return parseFloat(item.price).toFixed(2);
        return "—";
    },

    productLink(item) {
        const slug = item.route || item.item_code || item.name || "";
        return `/product?item=${encodeURIComponent(slug)}`;
    },

    /* ------------------------------------------------------------------
       API Adapter — wraps frappe.call via fetch with CSRF
       Usage: Store.call("app.module.method", { arg: val }).then(r => ...)
       ------------------------------------------------------------------ */
    call(method, args = {}) {
        const token = this.csrfToken ||
            (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";

        return fetch(`/api/method/${method}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Frappe-CSRF-Token": token,
                "Accept": "application/json",
            },
            body: JSON.stringify(args),
        })
        .then(res => {
            // #region agent log
            if (method.includes("get_product_filter_data") || method.includes("is_slide_admin") || method.includes("custom_sign_up")) {
                this.debugLog("store.js:call", "api response", { method, status: res.status, ok: res.ok }, "H3");
            }
            // #endregion
            if (!res.ok) {
                return res.json().then(data => {
                    throw new Error(this.extractApiError(data) || `HTTP ${res.status}`);
                });
            }
            return res.json();
        })
        .then(data => {
            if (data.exc) {
                throw new Error(this.extractApiError(data) || data.exc_type || "Server error");
            }
            return data.message !== undefined ? data.message : data;
        });
    },

    extractApiError(data) {
        if (!data) return "";
        if (data._server_messages) {
            try {
                const msgs = JSON.parse(data._server_messages);
                const parsed = msgs.map(m => {
                    try { return JSON.parse(m).message; } catch { return m; }
                }).filter(Boolean);
                if (parsed.length) return parsed.join(" ");
            } catch { /* ignore */ }
        }
        if (data.message && typeof data.message === "string") return data.message;
        return data.exc_type || "";
    },

    /* ------------------------------------------------------------------
       Cart Badge — reads live count from ERPNext quotation
       For guests, hides badge at 0. For logged-in users, fetches count.
       ------------------------------------------------------------------ */
    updateCartBadge() {
        const badge = document.getElementById("cart-badge");
        if (!badge) return;

        if (this.isGuest) {
            badge.textContent = "0";
            return;
        }

        this.call("webshop.webshop.shopping_cart.cart.get_cart_quotation")
            .then(data => {
                const items = (data && data.doc && data.doc.items) ? data.doc.items : [];
                const count = items.reduce((sum, item) => sum + (item.qty || 0), 0);
                badge.textContent = count;
            })
            .catch(() => {
                badge.textContent = "0";
            });
    },

    /* ------------------------------------------------------------------
       Toast notification
       ------------------------------------------------------------------ */
    toast(message, type = "info") {
        const container = document.getElementById("toast-container");
        if (!container) return;

        const toast = document.createElement("div");
        toast.className = "toast";
        const iconName = type === "success" ? "check-circle" : type === "error" ? "alert-circle" : "info";
        toast.innerHTML = `
            <i data-lucide="${iconName}" class="toast-icon"></i>
            <span>${message}</span>
        `;
        container.appendChild(toast);
        if (window.lucide) lucide.createIcons({ nodes: [toast] });

        setTimeout(() => {
            toast.classList.add("fade-out");
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    /* ------------------------------------------------------------------
       Mobile menu
       ------------------------------------------------------------------ */
    initMobileMenu() {
        const mobileBtn = document.getElementById("mobile-menu-btn");
        const navLinks = document.querySelector(".nav-links");

        if (!mobileBtn || !navLinks) return;

        mobileBtn.addEventListener("click", () => {
            const isActive = navLinks.classList.toggle("mobile-active");
            const iconMenu = mobileBtn.querySelector(".icon-menu");
            const iconX = mobileBtn.querySelector(".icon-x");
            if (isActive) {
                if (iconMenu) iconMenu.style.display = "none";
                if (iconX) iconX.style.display = "block";
            } else {
                if (iconMenu) iconMenu.style.display = "block";
                if (iconX) iconX.style.display = "none";
            }
        });

        navLinks.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                navLinks.classList.remove("mobile-active");
                const iconMenu = mobileBtn.querySelector(".icon-menu");
                const iconX = mobileBtn.querySelector(".icon-x");
                if (iconMenu) iconMenu.style.display = "block";
                if (iconX) iconX.style.display = "none";
            });
        });
    },

    escapeAttr(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    },

    /* ------------------------------------------------------------------
       Cart Drawer
       ------------------------------------------------------------------ */
    renderCartDrawer(options = {}) {
        const body = document.getElementById("cart-drawer-body");
        const subtotalEl = document.getElementById("drawer-subtotal");
        if (!body) return;

        if (options.customMessage) {
            body.innerHTML = options.customMessage;
            return;
        }

        if (this.isGuest) {
            const redirect = options.loginRedirect || window.location.pathname;
            body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">
                <p>Please <a href="/login?redirect-to=${encodeURIComponent(redirect)}" style="color:var(--primary-blue);">log in</a> to view your cart.</p>
            </div>`;
            if (subtotalEl) subtotalEl.textContent = "—";
            return;
        }

        body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">${this.t("loading")}</div>`;

        this.call("webshop.webshop.shopping_cart.cart.get_cart_quotation")
            .then(data => {
                const doc = data && data.doc;
                const items = (doc && doc.items) ? doc.items : [];

                if (!items.length) {
                    body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">
                        <i data-lucide="shopping-cart" style="width:40px;height:40px;margin-bottom:12px;opacity:0.3;"></i>
                        <p>${this.t("cart_empty")}</p>
                        <a href="/catalog" class="btn btn-secondary" style="margin-top:12px;">${this.t("cart_goto_shop")}</a>
                    </div>`;
                    if (subtotalEl) subtotalEl.textContent = "—";
                    if (window.lucide) lucide.createIcons({ nodes: [body] });
                    return;
                }

                let subtotal = 0;
                body.innerHTML = items.map(item => {
                    const qty = item.qty || 1;
                    const lineTotal = qty * (item.rate || 0);
                    subtotal += lineTotal;
                    const img = item.image || "/assets/custom_webshop/images/placeholder.jpg";
                    const code = item.item_code || "";
                    const name = item.item_name || code;
                    return `
                        <div class="drawer-item" data-item-code="${this.escapeAttr(code)}">
                            <img src="${img}" alt="${this.escapeAttr(name)}" class="drawer-item-img">
                            <div class="drawer-item-info">
                                <span class="drawer-item-name">${this.escapeAttr(name)}</span>
                                <div class="drawer-item-qty-row">
                                    <button type="button" class="qty-btn drawer-qty-dec" aria-label="Decrease quantity">−</button>
                                    <span class="qty-val">${qty}</span>
                                    <button type="button" class="qty-btn drawer-qty-inc" aria-label="Increase quantity">+</button>
                                </div>
                            </div>
                            <div class="drawer-item-price">${parseFloat(lineTotal).toFixed(2)}</div>
                            <button type="button" class="remove-drawer-item-btn drawer-qty-remove" title="${this.t("btn_remove")}" aria-label="${this.t("btn_remove")}">
                                <i data-lucide="trash-2"></i>
                            </button>
                        </div>`;
                }).join("");

                if (!body._drawerBound) {
                    body.addEventListener("click", (e) => {
                        const row = e.target.closest(".drawer-item");
                        if (!row) return;
                        const itemCode = row.dataset.itemCode;
                        if (!itemCode) return;
                        const qtyEl = row.querySelector(".qty-val");
                        const currentQty = parseInt(qtyEl && qtyEl.textContent, 10) || 1;

                        if (e.target.closest(".drawer-qty-remove")) {
                            window.updateDrawerQty(itemCode, 0);
                        } else if (e.target.closest(".drawer-qty-dec")) {
                            window.updateDrawerQty(itemCode, currentQty - 1);
                        } else if (e.target.closest(".drawer-qty-inc")) {
                            window.updateDrawerQty(itemCode, currentQty + 1);
                        }
                    });
                    body._drawerBound = true;
                }

                if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
                if (window.lucide) lucide.createIcons({ nodes: [body] });
            })
            .catch(() => {
                body.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);">${this.t("error_generic")}</div>`;
            });
    },

    initCartDrawer(renderFn) {
        const cartToggle = document.getElementById("cart-toggle-btn");
        const closeBtn = document.getElementById("close-drawer-btn");
        const overlay = document.getElementById("cart-drawer-overlay");
        const drawer = document.getElementById("cart-drawer");

        const open = () => {
            if (typeof renderFn === "function") renderFn();
            if (drawer) drawer.classList.add("active");
            if (overlay) overlay.classList.add("active");
        };
        const close = () => {
            if (drawer) drawer.classList.remove("active");
            if (overlay) overlay.classList.remove("active");
        };

        if (cartToggle) cartToggle.addEventListener("click", open);
        if (closeBtn) closeBtn.addEventListener("click", close);
        if (overlay) overlay.addEventListener("click", close);

        const checkoutBtn = document.getElementById("drawer-checkout-btn");
        if (checkoutBtn) checkoutBtn.addEventListener("click", close);
    },

    /* ------------------------------------------------------------------
       Language toggle button wiring
       ------------------------------------------------------------------ */
    initLangToggle() {
        const langBtn = document.getElementById("lang-btn");
        if (!langBtn) return;
        langBtn.addEventListener("click", () => {
            this.applyLanguage(this.lang === "en" ? "ar" : "en");
        });
    },

    /* ------------------------------------------------------------------
       Theme toggle button wiring
       ------------------------------------------------------------------ */
    initThemeToggle() {
        const themeBtn = document.getElementById("theme-btn");
        if (!themeBtn) return;
        themeBtn.addEventListener("click", () => {
            this.applyTheme(this.theme === "dark" ? "light" : "dark");
        });
    },

    /* ------------------------------------------------------------------
       Navbar scroll shadow effect
       ------------------------------------------------------------------ */
    initNavbarScroll() {
        const navbar = document.querySelector(".navbar");
        if (!navbar) return;
        window.addEventListener("scroll", () => {
            if (window.scrollY > 20) {
                navbar.classList.add("scrolled");
            } else {
                navbar.classList.remove("scrolled");
            }
        }, { passive: true });
    },

    /* ------------------------------------------------------------------
       Initialize — call once on DOMContentLoaded
       Reads localStorage preferences, wires global UI, syncs cart badge
       ------------------------------------------------------------------ */
    init() {
        // Restore theme
        const savedTheme = localStorage.getItem("cnc_theme");
        if (savedTheme) this.applyTheme(savedTheme);

        // Restore language
        const savedLang = localStorage.getItem("cnc_lang_v2") || "ar";
        this.applyLanguage(savedLang);

        // Wire global controls
        this.initLangToggle();
        this.initThemeToggle();
        this.initMobileMenu();
        this.initNavbarScroll();

        // Mark session user — window.FRAPPE_SESSION injected by each page's Jinja
        if (window.FRAPPE_SESSION) {
            this.user = window.FRAPPE_SESSION.user || "Guest";
            this.csrfToken = window.FRAPPE_SESSION.csrf_token || "";
            this.isGuest = this.user === "Guest";
        }

        // Fallback to Frappe's live global (injected per-response via base template)
        if (!this.csrfToken && window.frappe && frappe.csrf_token) {
            this.csrfToken = frappe.csrf_token;
        }

        // Refresh token when returning from desk or another tab
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible" && window.frappe && frappe.csrf_token) {
                this.csrfToken = frappe.csrf_token;
            }
        });

        // Re-render lucide icons after page setup
        if (window.lucide) lucide.createIcons();

        // Sync cart badge
        this.updateCartBadge();
    }
};

/* Expose globally */
window.Store = Store;
window.t = (key, params) => Store.t(key, params);

window.updateDrawerQty = function(itemCode, qty) {
    Store.call("webshop.webshop.shopping_cart.cart.update_cart", {
        item_code: itemCode,
        qty: Math.max(0, qty),
    }).then(() => {
        Store.updateCartBadge();
        Store.renderCartDrawer();
        if (qty === 0) Store.toast(Store.t("toast_removed_cart"), "info");
    }).catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};
