/* ==========================================================================
   CNCLeaders — Catalog / All Products Page Controller
   Depends on: store.js
   ========================================================================== */

let allProducts = [];
let filteredProducts = [];
let catalogViewMode = "grid";

// Currently active attribute filter: { attributeName: [value] } or {}
let activeAttributeFilter = {};
// Currently active brand filter: null = all brands, string = brand name
let activeBrandFilter = null;

function getCatalogQueryArgs(extraArgs = {}) {
    const field_filters = { ...(extraArgs.field_filters || {}) };
    if (activeBrandFilter) {
        field_filters.brand = [activeBrandFilter];
    }

    return {
        field_filters,
        attribute_filters: {
            ...activeAttributeFilter,
            ...(extraArgs.attribute_filters || {}),
        },
        start: 0,
        search: extraArgs.search || null,
        item_group: extraArgs.item_group || null,
    };
}

/* ── Build product card HTML ─────────────────────────────────────────────── */
function buildCatalogCard(item, mode) {
    const inStock = item.in_stock !== false;
    const badgeHTML = inStock ? "" : `<span class="product-badge out-of-stock">DEPLETED</span>`;
    const price = Store.productPrice(item);
    const img = item.website_image || item.image || "/assets/custom_webshop/images/placeholder.jpg";
    const productHref = Store.productLink(item);
    const displayName = item.web_item_name || item.item_name || item.name || "";
    const addBtn = inStock
        ? `<button class="card-add-btn" onclick="addToCartCatalog('${item.item_code || item.name}')" title="${Store.t("btn_add_to_cart")}"><i data-lucide="shopping-cart"></i></button>`
        : `<button class="card-add-btn disabled" disabled title="${Store.t("btn_out_of_stock")}"><i data-lucide="shopping-cart"></i></button>`;

    if (mode === "list") {
        return `
        <div class="product-card list-layout">
            <div class="product-img-wrapper" onclick="window.location.href='${productHref}'">
                <img src="${img}" alt="${displayName}" class="product-img" loading="lazy">
                ${badgeHTML}
            </div>
            <div class="product-info-list">
                <div class="product-main-details">
                    <span class="product-cat">${item.item_group || ""}</span>
                    <h3 class="product-name" onclick="window.location.href='${productHref}'">${displayName}</h3>
                    <p class="product-desc-short">${(item.short_description || item.description || "").substring(0, 120)}${(item.short_description || item.description || "").length > 120 ? "..." : ""}</p>
                </div>
                <div class="product-specs-list">
                    <div class="product-meta-specs">
                        ${item.brand ? `<div class="spec-line"><span>Brand:</span><span style="font-weight:700;">${item.brand}</span></div>` : ""}
                        <div class="spec-line"><span>Stock:</span><span>${inStock ? "Available" : "Depleted"}</span></div>
                    </div>
                </div>
                <div class="product-actions-list">
                    <span class="product-price">${price}</span>
                    ${inStock
                        ? `<button class="btn btn-primary btn-sm" onclick="addToCartCatalog('${item.item_code || item.name}')"><i data-lucide="shopping-cart" style="width:16px;height:16px;margin-right:6px;display:inline-block;vertical-align:middle;"></i>${Store.t("btn_add_to_cart")}</button>`
                        : `<button class="btn btn-primary btn-sm disabled" disabled>${Store.t("btn_out_of_stock")}</button>`
                    }
                </div>
            </div>
        </div>`;
    }

    return `
    <div class="product-card">
        <div class="product-img-wrapper" onclick="window.location.href='${productHref}'">
            <img src="${img}" alt="${displayName}" class="product-img" loading="lazy">
            ${badgeHTML}
        </div>
        <div class="product-info">
            <span class="product-cat">${item.item_group || ""}</span>
            <h3 class="product-name" onclick="window.location.href='${productHref}'">${displayName}</h3>
            <div class="product-meta-specs">
                ${item.brand ? `<div class="spec-line"><span>Brand:</span><span style="font-weight:700;">${item.brand}</span></div>` : ""}
            </div>
            <div class="product-bottom">
                <span class="product-price">${price}</span>
                ${addBtn}
            </div>
        </div>
    </div>`;
}

/* ── Render the product grid ─────────────────────────────────────────────── */
function renderCatalogGrid(products) {
    const grid = document.getElementById("catalog-product-grid");
    if (!grid) return;

    const countEl = document.getElementById("results-count-text");
    if (countEl) countEl.textContent = Store.t("catalog_results", { count: products.length });

    if (!products.length) {
        grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-muted);">${Store.t("catalog_no_results")}</div>`;
        return;
    }

    if (catalogViewMode === "list") {
        grid.classList.add("list-mode");
    } else {
        grid.classList.remove("list-mode");
    }

    grid.innerHTML = products.map(p => buildCatalogCard(p, catalogViewMode)).join("");
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
}

/* ── Build attribute filter sidebar ──────────────────────────────────────── */
function buildAttributeFilters(attrs) {
    const container = document.getElementById("attribute-filters-container");
    if (!container) return;

    if (!attrs || !attrs.length) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = attrs.map(attr => {
        const safeName = attr.attribute.replace(/\s+/g, "-");
        return `
        <div class="filter-card">
            <h3 class="filter-title">${attr.attribute}</h3>
            <div class="filter-options">
                <label class="checkbox-label">
                    <input type="radio" name="attr-filter-${safeName}" value="all" checked onchange="onAttributeFilterChange('${attr.attribute}', 'all')">
                    <span>All</span>
                </label>
                ${attr.values.map(v => `
                <label class="checkbox-label">
                    <input type="radio" name="attr-filter-${safeName}" value="${v}" onchange="onAttributeFilterChange('${attr.attribute}', '${v}')">
                    <span>${v}</span>
                </label>`).join("")}
            </div>
        </div>`;
    }).join("");
}

/* ── Build brand filter sidebar ──────────────────────────────────────────── */
function buildBrandFilters(brands) {
    const brandList = document.getElementById("brand-filter-list");
    if (!brandList) return;

    if (!brands || !brands.length) {
        brandList.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">No brands found.</p>`;
        return;
    }

    brandList.innerHTML = `
        <label class="checkbox-label">
            <input type="radio" name="brand-filter" value="all" checked onchange="onBrandFilterChange('all')">
            <span>All Brands</span>
        </label>` +
        brands.map(b => `
        <label class="checkbox-label">
            <input type="radio" name="brand-filter" value="${Store.escapeAttr(b)}" onchange="onBrandFilterChange('${Store.escapeAttr(b)}')">
            <span>${b}</span>
        </label>`).join("");
}

function loadBrandFilters(initialBrand) {
    Store.call("custom_webshop.api.catalog.get_brands")
        .then(rows => {
            const brands = (rows || []).map(r => r.brand).filter(Boolean);
            buildBrandFilters(brands);
            if (initialBrand) {
                activeBrandFilter = initialBrand;
                const radio = document.querySelector(`input[name="brand-filter"][value="${initialBrand}"]`);
                if (radio) radio.checked = true;
            }
        })
        .catch(() => {
            const brandList = document.getElementById("brand-filter-list");
            if (brandList) {
                brandList.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">No brands found.</p>`;
            }
        });
}

/* ── Attribute filter change → server re-fetch ────────────────────────────── */
window.onAttributeFilterChange = function(attrName, value) {
    if (value === "all") {
        delete activeAttributeFilter[attrName];
    } else {
        activeAttributeFilter[attrName] = [value];
    }
    loadCatalogProducts();
};

window.onBrandFilterChange = function(value) {
    activeBrandFilter = value === "all" ? null : value;
    loadCatalogProducts();
};

/* ── Apply local filters (search, sort) ──────────────────────────────────── */
function applyLocalFilters() {
    const searchVal = (document.getElementById("catalog-search")?.value || "").toLowerCase();
    const sortVal = document.getElementById("sort-select")?.value || "default";

    filteredProducts = allProducts.filter(p => {
        const name = (p.web_item_name || p.item_name || p.name || "").toLowerCase();
        const desc = (p.short_description || p.description || "").toLowerCase();
        return !searchVal || name.includes(searchVal) || desc.includes(searchVal);
    });

    if (sortVal === "price-asc") filteredProducts.sort((a, b) => (a.price || 0) - (b.price || 0));
    else if (sortVal === "price-desc") filteredProducts.sort((a, b) => (b.price || 0) - (a.price || 0));
    else if (sortVal === "alpha") filteredProducts.sort((a, b) => (a.web_item_name || a.name || "").localeCompare(b.web_item_name || b.name || ""));

    renderCatalogGrid(filteredProducts);
}

/* ── Load products from ERPNext ──────────────────────────────────────────── */
function loadCatalogProducts(queryArgs = {}) {
    const grid = document.getElementById("catalog-product-grid");
    if (grid) grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-muted);" data-i18n="loading">${Store.t("loading")}</div>`;

    Store.call("webshop.webshop.api.get_product_filter_data", {
        query_args: JSON.stringify(getCatalogQueryArgs(queryArgs))
    }).then(data => {
        allProducts = (data && data.items) ? data.items : [];
        applyLocalFilters();
    }).catch(err => {
        console.error("Catalog load failed:", err);
        if (grid) grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-muted);">${Store.t("error_generic")}</div>`;
    });
}

/* ── Add to cart ─────────────────────────────────────────────────────────── */
window.addToCartCatalog = function(itemCode) {
    if (Store.isGuest) {
        window.location.href = "/login?redirect-to=/catalog";
        return;
    }
    Store.call("webshop.webshop.shopping_cart.cart.update_cart", {
        item_code: itemCode,
        qty: 1,
    }).then(() => {
        Store.toast(Store.t("toast_added_cart"), "success");
        Store.updateCartBadge();
    }).catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

/* ── View toggle ─────────────────────────────────────────────────────────── */
function initViewToggle() {
    const gridBtn = document.getElementById("grid-toggle-btn");
    const listBtn = document.getElementById("list-toggle-btn");
    const slider = document.getElementById("toggle-slider");

    const savedMode = localStorage.getItem("cnc_catalog_view_mode") || "grid";
    catalogViewMode = savedMode;
    if (savedMode === "list") {
        gridBtn?.classList.remove("active");
        listBtn?.classList.add("active");
        if (slider) slider.style.transform = "translateX(100%)";
    }

    gridBtn?.addEventListener("click", () => {
        catalogViewMode = "grid";
        localStorage.setItem("cnc_catalog_view_mode", "grid");
        gridBtn.classList.add("active");
        listBtn?.classList.remove("active");
        if (slider) slider.style.transform = "translateX(0)";
        applyLocalFilters();
    });

    listBtn?.addEventListener("click", () => {
        catalogViewMode = "list";
        localStorage.setItem("cnc_catalog_view_mode", "list");
        listBtn.classList.add("active");
        gridBtn?.classList.remove("active");
        if (slider) slider.style.transform = "translateX(100%)";
        applyLocalFilters();
    });
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initCartDrawer(() => Store.renderCartDrawer({ loginRedirect: "/catalog" }));
    initViewToggle();

    // Wire local filter inputs
    document.getElementById("catalog-search")?.addEventListener("input", () => applyLocalFilters());
    document.getElementById("sort-select")?.addEventListener("change", () => applyLocalFilters());

    document.getElementById("clear-filters-btn")?.addEventListener("click", () => {
        document.getElementById("catalog-search").value = "";
        document.getElementById("sort-select").value = "default";
        // Reset all attribute radios to "all"
        document.querySelectorAll('[name^="attr-filter-"]').forEach(radio => {
            if (radio.value === "all") radio.checked = true;
        });
        const allBrandRadio = document.querySelector('input[name="brand-filter"][value="all"]');
        if (allBrandRadio) allBrandRadio.checked = true;
        activeAttributeFilter = {};
        activeBrandFilter = null;
        loadCatalogProducts({});
    });

    // Load attribute filter options from API (sidebar structure, once)
    Store.call("custom_webshop.api.catalog.get_item_attributes")
        .then(attrs => buildAttributeFilters(attrs))
        .catch(() => {});

    // Read URL params for initial filters
    const urlParams = new URLSearchParams(window.location.search);
    const itemGroup = urlParams.get("item_group");
    const attrName = urlParams.get("attribute");
    const attrValue = urlParams.get("value");
    const brand = urlParams.get("brand");

    const queryArgs = {};
    if (itemGroup) queryArgs.item_group = itemGroup;
    if (attrName && attrValue) {
        activeAttributeFilter[attrName] = [attrValue];
    }
    if (brand) {
        activeBrandFilter = brand;
    }

    loadBrandFilters(brand);

    // Pre-select the attribute radio after the sidebar is built
    if (attrName && attrValue) {
        // Wait a tick for buildAttributeFilters to finish
        setTimeout(() => {
            const safeName = attrName.replace(/\s+/g, "-");
            const radio = document.querySelector(`input[name="attr-filter-${safeName}"][value="${attrValue}"]`);
            if (radio) radio.checked = true;
        }, 100);
    }

    loadCatalogProducts(queryArgs);
});
