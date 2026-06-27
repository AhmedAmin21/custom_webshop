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
// Currently active tool family filter: null or string e.g. "SEM"
let activeToolFamilyFilter = null;
// Currently active material filter: null or string e.g. "C"
let activeMaterialFilter = null;

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
        tool_family: activeToolFamilyFilter || null,
        material: activeMaterialFilter || null,
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
                <img src="${img}" alt="${displayName}" class="product-img" loading="eager" onerror="this.onerror=null;this.src='/assets/custom_webshop/images/placeholder.jpg';">
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
            <img src="${img}" alt="${displayName}" class="product-img" loading="eager" onerror="this.onerror=null;this.src='/assets/custom_webshop/images/placeholder.jpg';">
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

/* ── Shared: render a filter option list with "View More" collapse ──────── */
const FILTER_VISIBLE_LIMIT = 6;

/**
 * Render radio-button options into `parentEl`, collapsing anything beyond
 * FILTER_VISIBLE_LIMIT behind a "View More" toggle.
 *
 * @param {HTMLElement} parentEl   - The .filter-options div to populate.
 * @param {string[]}    htmlItems  - Pre-built <label> HTML strings, one per option.
 * @param {string}      groupName  - The radio `name` attribute (used as a unique key).
 */
function renderFilterOptions(parentEl, htmlItems, groupName) {
    if (htmlItems.length <= FILTER_VISIBLE_LIMIT) {
        parentEl.innerHTML = htmlItems.join("");
        return;
    }

    const visible = htmlItems.slice(0, FILTER_VISIBLE_LIMIT);
    const hidden  = htmlItems.slice(FILTER_VISIBLE_LIMIT);
    const collapseId = `filter-more-${groupName}`;

    parentEl.innerHTML =
        visible.join("") +
        `<div class="filter-collapse-extra" id="${collapseId}" style="display:none;">` +
        hidden.join("") +
        `</div>` +
        `<button type="button" class="filter-view-more-btn" data-collapse="${collapseId}"
            onclick="toggleFilterCollapse(this)">
            View More <i data-lucide="chevron-down" style="width:13px;height:13px;display:inline-block;vertical-align:middle;margin-left:3px;pointer-events:none;"></i>
        </button>`;

    if (window.lucide) lucide.createIcons({ nodes: [parentEl] });
}

window.toggleFilterCollapse = function(btn) {
    const collapseEl = document.getElementById(btn.dataset.collapse);
    if (!collapseEl) return;
    const isOpen = collapseEl.style.display === "flex";
    collapseEl.style.display = isOpen ? "none" : "flex";
    btn.innerHTML = isOpen
        ? `View More <i data-lucide="chevron-down" style="width:13px;height:13px;display:inline-block;vertical-align:middle;margin-left:3px;pointer-events:none;"></i>`
        : `View Less <i data-lucide="chevron-up"   style="width:13px;height:13px;display:inline-block;vertical-align:middle;margin-left:3px;pointer-events:none;"></i>`;
    if (window.lucide) lucide.createIcons({ nodes: [btn] });
};

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
            <div class="filter-options" id="filter-opts-attr-${safeName}"></div>
        </div>`;
    }).join("");

    attrs.forEach(attr => {
        const safeName = attr.attribute.replace(/\s+/g, "-");
        const optionsEl = document.getElementById(`filter-opts-attr-${safeName}`);
        if (!optionsEl) return;
        const allLabel = `<label class="checkbox-label">
            <input type="radio" name="attr-filter-${safeName}" value="all" checked onchange="onAttributeFilterChange('${attr.attribute}', 'all')">
            <span>All</span>
        </label>`;
        const valueLabels = attr.values.map(v => `
            <label class="checkbox-label">
                <input type="radio" name="attr-filter-${safeName}" value="${v}" onchange="onAttributeFilterChange('${attr.attribute}', '${v}')">
                <span>${v}</span>
            </label>`);
        renderFilterOptions(optionsEl, [allLabel, ...valueLabels], `attr-${safeName}`);
    });
}

/* ── Build brand filter sidebar ──────────────────────────────────────────── */
function buildBrandFilters(brands) {
    const brandList = document.getElementById("brand-filter-list");
    if (!brandList) return;

    if (!brands || !brands.length) {
        brandList.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">No brands found.</p>`;
        return;
    }

    const brandItems = [
        `<label class="checkbox-label">
            <input type="radio" name="brand-filter" value="all" checked onchange="onBrandFilterChange('all')">
            <span>All Brands</span>
        </label>`,
        ...brands.map(b => `
        <label class="checkbox-label">
            <input type="radio" name="brand-filter" value="${Store.escapeAttr(b)}" onchange="onBrandFilterChange('${Store.escapeAttr(b)}')">
            <span>${b}</span>
        </label>`),
    ];
    renderFilterOptions(brandList, brandItems, "brand");
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

/* ── Build tool-family filter sidebar ────────────────────────────────────── */
// initialValues: null | string (single) | comma-separated string (multi)
function buildToolFamilyFilters(families, initialValues) {
    const container = document.getElementById("tool-family-filters-container");
    if (!container) return;

    if (!families || !families.length) {
        container.innerHTML = "";
        return;
    }

    // Build a Set of pre-selected values for fast lookup
    const preSelected = new Set(
        initialValues ? initialValues.split(",").map(v => v.trim().toUpperCase()) : []
    );
    const hasSelection = preSelected.size > 0;

    container.innerHTML = `
        <div class="filter-card">
            <h3 class="filter-title">${Store.t("filter_tool_family")}</h3>
            <div class="filter-options" id="filter-opts-tool-family"></div>
        </div>`;

    const tfItems = [
        `<label class="checkbox-label">
            <input type="checkbox" name="tool-family-filter" value="all" ${!hasSelection ? "checked" : ""}
                onchange="onToolFamilyCheckboxChange(this)">
            <span>All</span>
        </label>`,
        ...families.map(f => {
            const val = Store.escapeAttr(f.tool_family);
            const checked = preSelected.has(f.tool_family.toUpperCase()) ? "checked" : "";
            return `
        <label class="checkbox-label">
            <input type="checkbox" name="tool-family-filter" value="${val}" ${checked}
                onchange="onToolFamilyCheckboxChange(this)">
            <span>${f.tool_family}</span>
        </label>`;
        }),
    ];
    const tfOptsEl = document.getElementById("filter-opts-tool-family");
    if (tfOptsEl) renderFilterOptions(tfOptsEl, tfItems, "tool-family");
}

/* ── Build material filter sidebar ──────────────────────────────────────── */
// initialValues: null | string (single) | comma-separated string (multi)
function buildMaterialFilters(materials, initialValues) {
    const container = document.getElementById("material-filters-container");
    if (!container) return;

    if (!materials || !materials.length) {
        container.innerHTML = "";
        return;
    }

    const preSelected = new Set(
        initialValues ? initialValues.split(",").map(v => v.trim().toUpperCase()) : []
    );
    const hasSelection = preSelected.size > 0;

    container.innerHTML = `
        <div class="filter-card">
            <h3 class="filter-title">${Store.t("filter_material")}</h3>
            <div class="filter-options" id="filter-opts-material"></div>
        </div>`;

    const matItems = [
        `<label class="checkbox-label">
            <input type="checkbox" name="material-filter" value="all" ${!hasSelection ? "checked" : ""}
                onchange="onMaterialCheckboxChange(this)">
            <span>All</span>
        </label>`,
        ...materials.map(m => {
            const val = Store.escapeAttr(m.material);
            const checked = preSelected.has(m.material.toUpperCase()) ? "checked" : "";
            const label = Store.materialLabel(m.material);
            return `
        <label class="checkbox-label">
            <input type="checkbox" name="material-filter" value="${val}" ${checked}
                onchange="onMaterialCheckboxChange(this)">
            <span>${label}</span>
        </label>`;
        }),
    ];
    const matOptsEl = document.getElementById("filter-opts-material");
    if (matOptsEl) renderFilterOptions(matOptsEl, matItems, "material");
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

// Collect all checked Tool Family checkboxes and rebuild the active filter string.
window.onToolFamilyCheckboxChange = function(changedBox) {
    const allBox = document.querySelector('input[name="tool-family-filter"][value="all"]');

    if (changedBox.value === "all") {
        // "All" toggled — uncheck every specific option
        document.querySelectorAll('input[name="tool-family-filter"]').forEach(cb => {
            cb.checked = cb.value === "all" ? changedBox.checked : false;
        });
    } else {
        // Specific option toggled — uncheck "All"
        if (allBox) allBox.checked = false;
    }

    const checked = [...document.querySelectorAll('input[name="tool-family-filter"]:checked')]
        .map(cb => cb.value)
        .filter(v => v !== "all");

    activeToolFamilyFilter = checked.length ? checked.join(",") : null;

    // If nothing is checked, restore "All"
    if (!activeToolFamilyFilter && allBox) allBox.checked = true;

    loadCatalogProducts();
};

// Kept for backward compat (single-value callers)
window.onToolFamilyFilterChange = function(value) {
    activeToolFamilyFilter = value === "all" ? null : value;
    loadCatalogProducts();
};

// Collect all checked Material checkboxes and rebuild the active filter string.
window.onMaterialCheckboxChange = function(changedBox) {
    const allBox = document.querySelector('input[name="material-filter"][value="all"]');

    if (changedBox.value === "all") {
        document.querySelectorAll('input[name="material-filter"]').forEach(cb => {
            cb.checked = cb.value === "all" ? changedBox.checked : false;
        });
    } else {
        if (allBox) allBox.checked = false;
    }

    const checked = [...document.querySelectorAll('input[name="material-filter"]:checked')]
        .map(cb => cb.value)
        .filter(v => v !== "all");

    activeMaterialFilter = checked.length ? checked.join(",") : null;

    if (!activeMaterialFilter && allBox) allBox.checked = true;

    loadCatalogProducts();
};

// Kept for backward compat
window.onMaterialFilterChange = function(value) {
    activeMaterialFilter = value === "all" ? null : value;
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

    const args = getCatalogQueryArgs(queryArgs);

    // Use the custom endpoint when tool_family or material filters are active,
    // because the standard webshop API has no item_name awareness.
    const useCustomApi = !!(args.tool_family || args.material);

    let apiCall;
    if (useCustomApi) {
        apiCall = Store.call("custom_webshop.api.catalog.get_catalog_products", {
            tool_family: args.tool_family || null,
            material: args.material || null,
            attribute_filters: JSON.stringify(args.attribute_filters || {}),
            field_filters: JSON.stringify(args.field_filters || {}),
            search: args.search || null,
            start: args.start || 0,
        });
    } else {
        apiCall = Store.call("webshop.webshop.api.get_product_filter_data", {
            query_args: JSON.stringify(args),
        });
    }

    apiCall.then(data => {
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
        // Tool family: uncheck all specific options, check "All"
        document.querySelectorAll('input[name="tool-family-filter"]').forEach(cb => {
            cb.checked = cb.value === "all";
        });
        // Material: uncheck all specific options, check "All"
        document.querySelectorAll('input[name="material-filter"]').forEach(cb => {
            cb.checked = cb.value === "all";
        });
        activeAttributeFilter = {};
        activeBrandFilter = null;
        activeToolFamilyFilter = null;
        activeMaterialFilter = null;
        loadCatalogProducts({});
    });

    // Read URL params for initial filters.
    // Singular params (tool_family, material) = single-value sidebar filters.
    // Plural params (tool_families, materials) = comma-separated multi-value
    // deep links from the "Shop by Material" cards on the home page.
    const urlParams = new URLSearchParams(window.location.search);
    const itemGroup   = urlParams.get("item_group");
    const attrName    = urlParams.get("attribute");
    const attrValue   = urlParams.get("value");
    const brand       = urlParams.get("brand");
    const toolFamily  = urlParams.get("tool_family");
    const material    = urlParams.get("material");
    const toolFamilies = urlParams.get("tool_families"); // e.g. "SEM,FEM,EM"
    const materials    = urlParams.get("materials");     // e.g. "HSS,C,CW,TCT"

    const queryArgs = {};
    if (itemGroup) queryArgs.item_group = itemGroup;
    if (attrName && attrValue) activeAttributeFilter[attrName] = [attrValue];
    if (brand) activeBrandFilter = brand;

    // Multi-value params take precedence over single-value params
    if (toolFamilies)     activeToolFamilyFilter = toolFamilies;
    else if (toolFamily)  activeToolFamilyFilter = toolFamily;

    if (materials)      activeMaterialFilter = materials;
    else if (material)  activeMaterialFilter = material;

    // Load sidebar filter panels in parallel
    Promise.all([
        Store.call("custom_webshop.api.catalog.get_item_attributes"),
        Store.call("custom_webshop.api.catalog.get_all_tool_families"),
        Store.call("custom_webshop.api.catalog.get_all_materials"),
        Store.call("custom_webshop.api.catalog.get_brands"),
    ]).then(([attrs, families, mats, brandRows]) => {
        // Pass the full active filter value (single or multi) so checkboxes
        // can pre-tick every matching option on deep-link arrival.
        const initTf  = activeToolFamilyFilter || null;
        const initMat = activeMaterialFilter   || null;
        buildToolFamilyFilters(families || [], initTf);
        buildMaterialFilters(mats || [], initMat);
        buildAttributeFilters(attrs || []);
        buildBrandFilters((brandRows || []).map(r => r.brand).filter(Boolean));
        if (brand) {
            activeBrandFilter = brand;
            const radio = document.querySelector(`input[name="brand-filter"][value="${brand}"]`);
            if (radio) radio.checked = true;
        }
        // Pre-select attribute radio
        if (attrName && attrValue) {
            const safeName = attrName.replace(/\s+/g, "-");
            const radio = document.querySelector(`input[name="attr-filter-${safeName}"][value="${attrValue}"]`);
            if (radio) radio.checked = true;
        }
    }).catch(() => {});

    loadCatalogProducts(queryArgs);
});
