/* ==========================================================================
   CNCLeaders — Product Detail Page Controller
   Uses webshop APIs (get_product_filter_data, get_product_info_for_website)
   + server PRODUCT_BOOTSTRAP for specs, slideshow, recommended, wishlist
   Depends on: store.js
   ========================================================================== */

let currentDetailQty = 1;
let currentItemCode = null;
let currentBootstrap = null;
let currentWished = false;
let wishlistEnabled = false;

function getBootstrap() {
    if (currentBootstrap) return currentBootstrap;
    const raw = window.PRODUCT_BOOTSTRAP;
    if (!raw || raw === "null") {
        currentBootstrap = {};
        return currentBootstrap;
    }
    try {
        currentBootstrap = typeof raw === "string" ? JSON.parse(raw) : raw;
    } catch {
        currentBootstrap = {};
    }
    return currentBootstrap;
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function stripHtml(html) {
    if (!html) return "";
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    return (tmp.textContent || tmp.innerText || "").trim();
}

function fetchProductByFilter(field, value) {
    return Store.call("webshop.webshop.api.get_product_filter_data", {
        query_args: JSON.stringify({
            field_filters: { [field]: [value] },
            start: 0,
        }),
    }).then(data => {
        const items = (data && data.items) ? data.items : [];
        return items.length ? items[0] : null;
    });
}

function loadProductItem(itemName) {
    return fetchProductByFilter("route", itemName).then(item => {
        if (item) return item;
        return fetchProductByFilter("item_code", itemName);
    });
}

function fetchProductInfo(itemCode) {
    return Store.call(
        "webshop.webshop.shopping_cart.product_info.get_product_info_for_website",
        { item_code: itemCode, skip_quotation_creation: true }
    ).then(data => data || {});
}

/* ── Fetch Website Item data ─────────────────────────────────────────────── */
function loadProductDetail(itemName) {
    const container = document.getElementById("product-detail-container");
    if (!container) return;

    if (!itemName) {
        container.innerHTML = `<div style="text-align:center;padding:80px;color:var(--text-muted);">
            <p>No product specified. <a href="/catalog" style="color:var(--primary-blue);">Browse catalog</a></p></div>`;
        return;
    }

    container.innerHTML = `<div style="text-align:center;padding:80px;color:var(--text-muted);">${Store.t("loading")}</div>`;

    const bootstrap = getBootstrap();

    loadProductItem(itemName)
        .then(item => {
            if (!item) {
                container.innerHTML = `<div style="text-align:center;padding:80px;color:var(--text-muted);">
                    <p>Product not found. <a href="/catalog" style="color:var(--primary-blue);">Browse catalog</a></p></div>`;
                return;
            }
            currentItemCode = item.item_code || item.name;
            return Promise.all([
                fetchProductInfo(currentItemCode),
                Store.call("custom_webshop.api.catalog.get_item_master_details", { item_code: currentItemCode }).catch(() => ({}))
            ]).then(([info, master]) => {
                if (master) {
                    if (master.description) item.description = master.description;
                    if (master.image) item.image = master.image;
                }
                renderDetailView(item, info, bootstrap);
            });
        })
        .catch(err => {
            container.innerHTML = `<div style="text-align:center;padding:80px;color:var(--text-muted);">${Store.t("error_generic")}</div>`;
            console.error("Product detail load failed:", err);
        });
}

/* ── Render detail layout ────────────────────────────────────────────────── */
function renderDetailView(item, productInfoData, bootstrap) {
    const container = document.getElementById("product-detail-container");
    if (!container) return;

    bootstrap = bootstrap || getBootstrap();
    const settings = bootstrap.settings || {};
    const productInfo = (productInfoData && productInfoData.product_info) || {};
    const cartSettings = (productInfoData && productInfoData.cart_settings) || settings;

    wishlistEnabled = Boolean(settings.enable_wishlist);
    currentWished = Boolean(bootstrap.wished);

    const displayName = item.web_item_name || item.item_name || item.name || "";
    const rawDesc = (bootstrap.item_description || item.description || item.web_long_description || item.short_description || "").trim();
    const hasHtmlTags = /<[a-z][\s\S]*>/i.test(rawDesc);
    const descriptionHtml = hasHtmlTags ? rawDesc : (rawDesc ? `<p>${escapeHtml(rawDesc)}</p>` : "");
    const mainImg = bootstrap.item_image || item.image || item.website_image || "/assets/custom_webshop/images/placeholder.jpg";

    const slides = (bootstrap.slides && bootstrap.slides.length)
        ? bootstrap.slides
        : [{ image: mainImg }];
    const galleryImages = slides.map(s => s.image).filter(Boolean);
    const uniqueImages = [...new Set(galleryImages.length ? galleryImages : [mainImg])];

    const priceStr = productInfo.price
        ? (productInfo.price.formatted_price || productInfo.price.formatted_price_sales_uom || Store.productPrice(item))
        : Store.productPrice(item);

    const showStock = cartSettings.show_stock_availability !== false;
    const inStock = productInfo.in_stock !== false && productInfo.in_stock !== 0;
    const onBackorder = Boolean(productInfo.on_backorder);

    document.title = `CNCLeaders | ${displayName}`;

    function buildStockLabel() {
        if (onBackorder) {
            return `<span class="dot-status dot-instock" style="background:#3B82F6;box-shadow:0 0 10px rgba(59,130,246,0.4);"></span><span style="color:#3B82F6;">${Store.t("stock_backorder")}</span>`;
        }
        if (!inStock) {
            return `<span class="dot-status dot-outofstock"></span><span style="color:#EF4444;">${Store.t("stock_out")}</span>`;
        }
        let qty = null;
        if (productInfo.stock_qty != null && productInfo.stock_qty !== "") {
            const parsed = parseFloat(productInfo.stock_qty);
            if (!Number.isNaN(parsed)) qty = parsed;
        }
        if (qty != null && qty > 0 && qty <= 10) {
            const formattedQty = qty % 1 === 0 ? qty.toFixed(0) : qty.toFixed(2);
            return `<span class="dot-status dot-lowstock"></span><span style="color:#F59E0B;">${Store.t("stock_low", { qty: formattedQty })}</span>`;
        }
        return `<span class="dot-status dot-instock"></span><span style="color:#22C55E;">${Store.t("stock_in")}</span>`;
    }

    const stockHTML = !showStock ? "" : buildStockLabel();

    const canAddToCart = cartSettings.enabled !== false && (inStock || onBackorder || cartSettings.allow_items_not_in_stock)
        && (productInfo.price || !cartSettings.hide_price_for_guest || !Store.isGuest);

    const addBtnHTML = canAddToCart
        ? `<button class="btn btn-primary" style="flex-grow:1;" onclick="addDetailItemToCart()">
               <i data-lucide="shopping-cart"></i> ${Store.t("btn_add_to_cart")}
           </button>`
        : `<button class="btn btn-primary disabled" disabled style="flex-grow:1;">${Store.t("btn_out_of_stock")}</button>`;

    const wishlistHTML = wishlistEnabled
        ? `<button type="button" class="detail-wishlist-btn ${currentWished ? "wished" : ""}" id="detail-wishlist-btn" onclick="toggleDetailWishlist()" title="Wishlist">
               <i data-lucide="heart"></i>
           </button>`
        : "";

    const specs = bootstrap.specifications || [];
    const specsRows = specs.map(spec => `
        <tr><td class="spec-name">${escapeHtml(stripHtml(spec.label))}</td><td class="spec-val">${escapeHtml(stripHtml(spec.description))}</td></tr>
    `).join("");

    const specsSectionHTML = specs.length > 0 ? `
        <h3 class="specs-table-title">Product Specifications</h3>
        <table class="specs-table">
            <tbody>${specsRows}</tbody>
        </table>
    ` : "";

    const thumbsHTML = uniqueImages.map((src, i) => `
        <div class="gallery-thumb ${i === 0 ? "active" : ""}" data-src="${encodeURI(src)}" onclick="updateMainDetailImage(this.dataset.src, this)">
            <img src="${escapeHtml(src)}" alt="View ${i + 1}">
        </div>
    `).join("");

    container.innerHTML = `
        <div class="detail-layout">
            <div class="detail-gallery">
                <div class="detail-main-img-box">
                    <img src="${escapeHtml(uniqueImages[0])}" alt="${escapeHtml(displayName)}" id="detail-main-image-element" class="detail-main-img">
                </div>
                ${uniqueImages.length > 1 ? `<div class="detail-gallery-thumbs">${thumbsHTML}</div>` : ""}
            </div>

            <div class="detail-meta-panel">
                <div class="detail-title-row" style="justify-content:flex-end;">
                    ${wishlistHTML}
                </div>
                <h1 class="detail-title">${escapeHtml(displayName)}</h1>

                <div class="detail-price-status">
                    <span class="detail-price">${escapeHtml(priceStr)}</span>
                    ${stockHTML ? `<div class="stock-indicator">${stockHTML}</div>` : ""}
                </div>

                ${rawDesc ? `<div class="detail-desc">${descriptionHtml}</div>` : ""}

                ${specsSectionHTML}

                <div class="detail-actions">
                    <div class="qty-spinner">
                        <button class="qty-btn" onclick="adjustDetailQty(-1)">−</button>
                        <input type="text" value="1" id="detail-qty-input" class="qty-val" readonly>
                        <button class="qty-btn" onclick="adjustDetailQty(1)">+</button>
                    </div>
                    ${addBtnHTML}
                </div>
            </div>
        </div>

        <div class="related-section" id="detail-recommended-section" style="display:none;">
            <h2 class="specs-table-title" style="font-size:1.5rem;margin-bottom:24px;">Recommended For You</h2>
            <div class="featured-grid" id="detail-recommended-grid"></div>
        </div>`;

    if (window.lucide) lucide.createIcons({ nodes: [container] });

    renderRecommendedProducts(bootstrap.recommended_items || []);
}

function renderRecommendedProducts(recommended) {
    const section = document.getElementById("detail-recommended-section");
    const grid = document.getElementById("detail-recommended-grid");
    if (!section || !grid) return;

    if (!recommended.length) {
        section.style.display = "none";
        return;
    }

    section.style.display = "";
    grid.innerHTML = recommended.map(p => {
        const pImg = p.image || p.website_item_thumbnail || p.website_image
            || "/assets/custom_webshop/images/placeholder.jpg";
        const pName = p.website_item_name || p.item_code || "";
        const pPrice = p.formatted_price || "—";
        const pHref = Store.productLink({ route: p.route, item_code: p.item_code, name: p.item_code });
        const pDesc = stripHtml(p.description || "");
        const descHTML = pDesc ? `<p class="product-card-desc">${escapeHtml(pDesc)}</p>` : "";

        return `<div class="product-card">
            <div class="product-img-wrapper" onclick="window.location.href='${pHref}'">
                <img src="${escapeHtml(pImg)}" alt="${escapeHtml(pName)}" class="product-img" loading="lazy" onerror="this.onerror=null;this.src='/assets/custom_webshop/images/placeholder.jpg';">
            </div>
            <div class="product-info">
                <h4 class="product-name" onclick="window.location.href='${pHref}'">${escapeHtml(pName)}</h4>
                ${descHTML}
                <div class="product-bottom" style="margin-top:12px;">
                    <span class="product-price">${escapeHtml(pPrice)}</span>
                    <button class="card-add-btn" onclick="event.stopPropagation();addToCartFromRelated('${escapeHtml(p.item_code)}')">
                        <i data-lucide="shopping-cart"></i>
                    </button>
                </div>
            </div>
        </div>`;
    }).join("");
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
}

/* ── Wishlist ────────────────────────────────────────────────────────────── */
window.toggleDetailWishlist = function() {
    if (!wishlistEnabled || !currentItemCode) return;
    if (Store.isGuest) {
        window.location.href = "/login?redirect-to=" + encodeURIComponent(window.location.pathname + window.location.search);
        return;
    }

    const method = currentWished
        ? "webshop.webshop.doctype.wishlist.wishlist.remove_from_wishlist"
        : "webshop.webshop.doctype.wishlist.wishlist.add_to_wishlist";

    Store.call(method, { item_code: currentItemCode })
        .then(() => {
            currentWished = !currentWished;
            const btn = document.getElementById("detail-wishlist-btn");
            if (btn) btn.classList.toggle("wished", currentWished);
            Store.toast(currentWished ? "Added to wishlist" : "Removed from wishlist", "success");
        })
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

/* ── Interactive controls ────────────────────────────────────────────────── */
window.adjustDetailQty = function(delta) {
    const input = document.getElementById("detail-qty-input");
    if (!input) return;
    let val = parseInt(input.value, 10) + delta;
    if (val < 1) val = 1;
    currentDetailQty = val;
    input.value = val;
};

window.updateMainDetailImage = function(src, el) {
    const mainImg = document.getElementById("detail-main-image-element");
    if (mainImg) mainImg.src = src;
    document.querySelectorAll(".gallery-thumb").forEach(t => t.classList.remove("active"));
    if (el) el.classList.add("active");
};

window.addDetailItemToCart = function() {
    if (!currentItemCode) return;
    const qty = parseInt(document.getElementById("detail-qty-input")?.value || "1", 10);
    // Guests may fill a basket; the account is asked for at the full form.
    Store.addToCart(currentItemCode, qty)
        .then(() => Store.toast(Store.t("toast_added_cart"), "success"))
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

window.addToCartFromRelated = function(itemCode) {
    Store.addToCart(itemCode, 1)
        .then(() => Store.toast(Store.t("toast_added_cart"), "success"))
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initCartDrawer(() => Store.renderCartDrawer({
        loginRedirect: window.location.pathname + window.location.search,
    }));

    const itemName = window.ITEM_NAME || new URLSearchParams(window.location.search).get("item") || "";
    loadProductDetail(decodeURIComponent(itemName));

    if (window.lucide) lucide.createIcons();
});
