/* ==========================================================================
   CNCLeaders — Catalog / All Products Page Controller
   Depends on: store.js
   ========================================================================== */

let pageProducts = [];
let catalogViewMode = "grid";

let catalogPagination = { page: 1, size: 0, total: 0, totalPages: 0 };
let catalogQuery = {};
let catalogRequestSeq = 0;
let catalogSearchTimer = null;

// Currently active attribute filter: { attributeName: [value] } or {}
let activeAttributeFilter = {};
// Currently active tool family filter: null or string e.g. "SEM"
let activeToolFamilyFilter = null;
// Currently active material filter: null or string e.g. "C"
let activeMaterialFilter = null;

// Cached filter definitions for re-rendering upon language switch
let cachedAttributes = [];
let cachedFamilies = [];
let cachedMaterials = [];
let cachedBrands = [];

function getCatalogQueryArgs(extraArgs = {}) {
    return {
        field_filters: { ...(extraArgs.field_filters || {}) },
        attribute_filters: {
            ...activeAttributeFilter,
            ...(extraArgs.attribute_filters || {}),
        },
        search: document.getElementById("catalog-search")?.value?.trim() || null,
        sort: document.getElementById("sort-select")?.value || "default",
        item_group: extraArgs.item_group || null,
        tool_family: activeToolFamilyFilter || null,
        material: activeMaterialFilter || null,
    };
}

/* ── Build product card HTML ─────────────────────────────────────────────── */
function buildCatalogCard(item, mode) {
    const badgeHTML = "";
    const price = Store.productPrice(item);
    const img = item.image || item.website_image || "/assets/custom_webshop/images/placeholder.svg";
    const productHref = Store.productLink(item);
    const displayName = item.web_item_name || item.item_name || item.name || "";
    const rawDesc = Store.stripHtml(item.description || item.short_description || "");
    const descHTML = rawDesc ? `<p class="product-card-desc">${Store.escapeHtml(rawDesc)}</p>` : "";
    const brand = item.brand || "";
    const brandHTML = brand ? `<div class="product-meta-specs"><div class="spec-line"><span>${Store.t("filter_brand")}:</span><span style="font-weight:700;">${Store.escapeHtml(brand)}</span></div></div>` : "";
    const addBtn = `<button class="card-add-btn" onclick="addToCartCatalog('${item.item_code || item.name}')" title="${Store.t("btn_add_to_cart")}"><i data-lucide="shopping-cart"></i></button>`;

    if (mode === "list") {
        return `
        <div class="product-card list-layout">
            <div class="product-img-wrapper" onclick="window.location.href='${productHref}'">
                <img src="${img}" alt="${Store.escapeAttr(displayName)}" class="product-img" loading="lazy" onerror="this.onerror=null;this.src='/assets/custom_webshop/images/placeholder.svg';">
            </div>
            <div class="product-info-list">
                <div class="product-main-details">
                    <h3 class="product-name" onclick="window.location.href='${productHref}'">${Store.escapeHtml(displayName)}</h3>
                    <p class="product-desc-short">${Store.escapeHtml(rawDesc.substring(0, 220))}${rawDesc.length > 220 ? "..." : ""}</p>
                </div>
                <div class="product-specs-list">
                    <div class="product-meta-specs">
                        ${brand ? `<div class="spec-line"><span>${Store.t("filter_brand")}:</span><span style="font-weight:700;">${Store.escapeHtml(brand)}</span></div>` : ""}
                    </div>
                </div>
                <div class="product-actions-list">
                    <span class="product-price">${price}</span>
                    <button class="btn btn-primary btn-sm" onclick="addToCartCatalog('${item.item_code || item.name}')"><i data-lucide="shopping-cart" style="width:16px;height:16px;margin-right:6px;display:inline-block;vertical-align:middle;"></i>${Store.t("btn_add_to_cart")}</button>
                </div>
            </div>
        </div>`;
    }

    return `
    <div class="product-card">
        <div class="product-img-wrapper" onclick="window.location.href='${productHref}'">
            <img src="${img}" alt="${Store.escapeAttr(displayName)}" class="product-img" loading="lazy" onerror="this.onerror=null;this.src='/assets/custom_webshop/images/placeholder.svg';">
            ${badgeHTML}
        </div>
        <div class="product-info">
            <h3 class="product-name" onclick="window.location.href='${productHref}'" title="${Store.escapeAttr(displayName)}">${Store.escapeHtml(displayName)}</h3>
            ${descHTML}
            ${brandHTML}
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
    if (countEl) {
        const { page, size, total, totalPages } = catalogPagination;
        const from = (page - 1) * size + 1;
        countEl.textContent = totalPages > 1
            ? Store.t("catalog_results_range", { from, to: from + products.length - 1, total })
            : Store.t("catalog_results", { count: total });
    }

    if (!products.length) {
        grid.innerHTML = `
            <div class="catalog-empty-state">
                <div class="empty-icon-box"><i data-lucide="package-search"></i></div>
                <h3 class="empty-title">${Store.t("catalog_no_results")}</h3>
                <button class="btn btn-secondary btn-sm" onclick="resetAllCatalogFilters()">${Store.t("btn_reset_filters")}</button>
            </div>`;
        if (window.lucide) lucide.createIcons({ nodes: [grid] });
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

/* ── Active Filter Chips ─────────────────────────────────────────────────── */
function renderActiveFilterChips() {
    const container = document.getElementById("active-filter-chips");
    const mobileBadge = document.getElementById("active-filters-count-badge");
    if (!container) return;

    const chips = [];

    // Search query chip
    const searchVal = document.getElementById("catalog-search")?.value?.trim();
    if (searchVal) {
        chips.push({
            type: "search",
            label: `${Store.t("filter_search")}: "${Store.escapeHtml(searchVal)}"`,
            clear: () => {
                const s = document.getElementById("catalog-search");
                if (s) s.value = "";
                renderActiveFilterChips();
                loadCatalogProducts();
            }
        });
    }

    // Tool family filter chips
    if (activeToolFamilyFilter) {
        activeToolFamilyFilter.split(",").forEach(tf => {
            chips.push({
                type: "tool_family",
                label: `${Store.t("filter_tool_family")}: ${tf}`,
                clear: () => {
                    const box = document.querySelector(`input[name="tool-family-filter"][value="${tf}"]`);
                    if (box) {
                        box.checked = false;
                        onToolFamilyCheckboxChange(box);
                    }
                }
            });
        });
    }

    // Material filter chips
    if (activeMaterialFilter) {
        activeMaterialFilter.split(",").forEach(mat => {
            chips.push({
                type: "material",
                label: `${Store.t("filter_material")}: ${Store.materialLabel(mat)}`,
                clear: () => {
                    const box = document.querySelector(`input[name="material-filter"][value="${mat}"]`);
                    if (box) {
                        box.checked = false;
                        onMaterialCheckboxChange(box);
                    }
                }
            });
        });
    }

    // Attribute & Brand chips
    for (const [attr, vals] of Object.entries(activeAttributeFilter)) {
        vals.forEach(val => {
            const attrLabel = attr === "Brand - الماركة" ? Store.t("filter_brand") : attr;
            chips.push({
                type: "attr",
                label: `${attrLabel}: ${val}`,
                clear: () => {
                    if (attr === "Brand - الماركة") {
                        onBrandFilterChange("all");
                        const r = document.querySelector('input[name="brand-filter"][value="all"]');
                        if (r) r.checked = true;
                    } else {
                        onAttributeFilterChange(attr, "all");
                        const safe = attr.replace(/\s+/g, "-");
                        const r = document.querySelector(`input[name="attr-filter-${safe}"][value="all"]`);
                        if (r) r.checked = true;
                    }
                }
            });
        });
    }

    // Update mobile filter badge
    if (mobileBadge) {
        if (chips.length > 0) {
            mobileBadge.textContent = chips.length;
            mobileBadge.style.display = "inline-flex";
        } else {
            mobileBadge.style.display = "none";
        }
    }

    if (!chips.length) {
        container.style.display = "none";
        container.innerHTML = "";
        return;
    }

    container.style.display = "flex";
    window._catalogChips = chips;

    container.innerHTML = `
        <span class="active-chips-label">${Store.t("filter_active")}</span>
        <div class="active-chips-list">
            ${chips.map((c, i) => `
                <div class="filter-chip">
                    <span>${c.label}</span>
                    <button type="button" class="filter-chip-remove" onclick="window._catalogChips[${i}].clear()" aria-label="Remove filter">
                        <i data-lucide="x"></i>
                    </button>
                </div>
            `).join("")}
            <button type="button" class="filter-chips-clear" onclick="resetAllCatalogFilters()">
                ${Store.t("filter_clear_all")}
            </button>
        </div>
    `;

    if (window.lucide) lucide.createIcons({ nodes: [container] });
}

/* ── Shared: render a filter option list with "View More" collapse ──────── */
const FILTER_VISIBLE_LIMIT = 6;

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
            ${Store.t("filter_view_more")} <i data-lucide="chevron-down" style="width:13px;height:13px;display:inline-block;vertical-align:middle;margin-left:3px;pointer-events:none;"></i>
        </button>`;

    if (window.lucide) lucide.createIcons({ nodes: [parentEl] });
}

window.toggleFilterCollapse = function(btn) {
    const collapseEl = document.getElementById(btn.dataset.collapse);
    if (!collapseEl) return;
    const isOpen = collapseEl.style.display === "flex";
    collapseEl.style.display = isOpen ? "none" : "flex";
    btn.innerHTML = isOpen
        ? `${Store.t("filter_view_more")} <i data-lucide="chevron-down" style="width:13px;height:13px;display:inline-block;vertical-align:middle;margin-left:3px;pointer-events:none;"></i>`
        : `${Store.t("filter_view_less")} <i data-lucide="chevron-up"   style="width:13px;height:13px;display:inline-block;vertical-align:middle;margin-left:3px;pointer-events:none;"></i>`;
    if (window.lucide) lucide.createIcons({ nodes: [btn] });
};

/* ── Filter Card Section Collapse Toggle ─────────────────────────────────── */
window.toggleSectionCollapse = function(headerEl) {
    const card = headerEl.closest(".filter-card");
    if (!card) return;
    const isCollapsed = card.classList.toggle("is-collapsed");
    const toggleBtn = card.querySelector(".filter-section-toggle");
    if (toggleBtn) {
        toggleBtn.textContent = isCollapsed ? "+" : "−";
    }
};

/* ── Build attribute filter sidebar ──────────────────────────────────────── */
function buildAttributeFilters(attrs) {
    // Filter out brand attribute since it has its own dedicated filter card right after material
    const filteredAttrs = (attrs || []).filter(attr => {
        const name = (attr.attribute || "").toLowerCase();
        return name !== "brand - الماركة".toLowerCase() && name !== "brand" && !name.includes("الماركة");
    });
    cachedAttributes = filteredAttrs;
    const container = document.getElementById("attribute-filters-container");
    if (!container) return;

    if (!filteredAttrs.length) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = filteredAttrs.map(attr => {
        const safeName = attr.attribute.replace(/\s+/g, "-");
        return `
        <div class="filter-card" id="filter-card-attr-${safeName}">
            <div class="filter-header-row" onclick="toggleSectionCollapse(this)">
                <h3 class="filter-title">${Store.escapeHtml(attr.attribute)}</h3>
                <button type="button" class="filter-section-toggle" aria-label="Toggle Section">−</button>
            </div>
            <div class="filter-section-body">
                <div class="filter-options" id="filter-opts-attr-${safeName}"></div>
            </div>
        </div>`;
    }).join("");

    filteredAttrs.forEach(attr => {
        const safeName = attr.attribute.replace(/\s+/g, "-");
        const optionsEl = document.getElementById(`filter-opts-attr-${safeName}`);
        if (!optionsEl) return;
        const currentSelected = activeAttributeFilter[attr.attribute] ? activeAttributeFilter[attr.attribute][0] : "all";
        const allLabel = `<label class="checkbox-label">
            <input type="radio" name="attr-filter-${safeName}" value="all" ${currentSelected === "all" ? "checked" : ""} onchange="onAttributeFilterChange('${attr.attribute}', 'all')">
            <span>${Store.t("filter_all")}</span>
        </label>`;
        const valueLabels = attr.values.map(v => `
            <label class="checkbox-label">
                <input type="radio" name="attr-filter-${safeName}" value="${Store.escapeAttr(v)}" ${currentSelected === v ? "checked" : ""} onchange="onAttributeFilterChange('${attr.attribute}', '${Store.escapeAttr(v)}')">
                <span>${Store.escapeHtml(v)}</span>
            </label>`);
        renderFilterOptions(optionsEl, [allLabel, ...valueLabels], `attr-${safeName}`);
    });
}

/* ── Build brand filter sidebar ──────────────────────────────────── */
function buildBrandFilters(brands) {
    cachedBrands = brands || [];
    const brandList = document.getElementById("brand-filter-list");
    if (!brandList) return;

    if (!brands || !brands.length) {
        brandList.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">${Store.lang === 'ar' ? 'لا توجد علامات تجارية' : 'No brands found.'}</p>`;
        return;
    }

    const currentBrand = activeAttributeFilter["Brand - الماركة"] ? activeAttributeFilter["Brand - الماركة"][0] : "all";

    const brandItems = [
        `<label class="checkbox-label">
            <input type="radio" name="brand-filter" value="all" ${currentBrand === "all" ? "checked" : ""} onchange="onBrandFilterChange('all')">
            <span>${Store.t("filter_all_brands")}</span>
        </label>`,
        ...brands.map(b => `
        <label class="checkbox-label">
            <input type="radio" name="brand-filter" value="${Store.escapeAttr(b)}" ${currentBrand === b ? "checked" : ""} onchange="onBrandFilterChange('${Store.escapeAttr(b)}')">
            <span>${Store.escapeHtml(b)}</span>
        </label>`),
    ];
    renderFilterOptions(brandList, brandItems, "brand");
}

/* ── Build tool-family filter sidebar ────────────────────────────────────── */
function buildToolFamilyFilters(families, initialValues) {
    cachedFamilies = families || [];
    const container = document.getElementById("tool-family-filters-container");
    if (!container) return;

    if (!families || !families.length) {
        container.innerHTML = "";
        return;
    }

    const activeVals = activeToolFamilyFilter || initialValues || "";
    const preSelected = new Set(
        activeVals ? activeVals.split(",").map(v => v.trim().toUpperCase()) : []
    );
    const hasSelection = preSelected.size > 0;

    container.innerHTML = `
        <div class="filter-card" id="filter-card-tool-family">
            <div class="filter-header-row" onclick="toggleSectionCollapse(this)">
                <h3 class="filter-title">${Store.t("filter_tool_family")}</h3>
                <button type="button" class="filter-section-toggle" aria-label="Toggle Section">−</button>
            </div>
            <div class="filter-section-body">
                <div class="filter-options" id="filter-opts-tool-family"></div>
            </div>
        </div>`;

    const tfItems = [
        `<label class="checkbox-label">
            <input type="checkbox" name="tool-family-filter" value="all" ${!hasSelection ? "checked" : ""}
                onchange="onToolFamilyCheckboxChange(this)">
            <span>${Store.t("filter_all")}</span>
        </label>`,
        ...families.map(f => {
            const val = Store.escapeAttr(f.tool_family);
            const checked = preSelected.has(f.tool_family.toUpperCase()) ? "checked" : "";
            return `
        <label class="checkbox-label">
            <input type="checkbox" name="tool-family-filter" value="${val}" ${checked}
                onchange="onToolFamilyCheckboxChange(this)">
            <span>${Store.escapeHtml(f.tool_family)}</span>
        </label>`;
        }),
    ];
    const tfOptsEl = document.getElementById("filter-opts-tool-family");
    if (tfOptsEl) renderFilterOptions(tfOptsEl, tfItems, "tool-family");
}

/* ── Build material filter sidebar ──────────────────────────────────────── */
function buildMaterialFilters(materials, initialValues) {
    cachedMaterials = materials || [];
    const container = document.getElementById("material-filters-container");
    if (!container) return;

    if (!materials || !materials.length) {
        container.innerHTML = "";
        return;
    }

    const activeVals = activeMaterialFilter || initialValues || "";
    const preSelected = new Set(
        activeVals ? activeVals.split(",").map(v => v.trim().toUpperCase()) : []
    );
    const hasSelection = preSelected.size > 0;

    container.innerHTML = `
        <div class="filter-card" id="filter-card-material">
            <div class="filter-header-row" onclick="toggleSectionCollapse(this)">
                <h3 class="filter-title">${Store.t("filter_material")}</h3>
                <button type="button" class="filter-section-toggle" aria-label="Toggle Section">−</button>
            </div>
            <div class="filter-section-body">
                <div class="filter-options" id="filter-opts-material"></div>
            </div>
        </div>`;

    const matItems = [
        `<label class="checkbox-label">
            <input type="checkbox" name="material-filter" value="all" ${!hasSelection ? "checked" : ""}
                onchange="onMaterialCheckboxChange(this)">
            <span>${Store.t("filter_all")}</span>
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
    renderActiveFilterChips();
    loadCatalogProducts();
};

window.onBrandFilterChange = function(value) {
    if (value === "all") {
        delete activeAttributeFilter["Brand - الماركة"];
    } else {
        activeAttributeFilter["Brand - الماركة"] = [value];
    }
    renderActiveFilterChips();
    loadCatalogProducts();
};

window.onToolFamilyCheckboxChange = function(changedBox) {
    const allBox = document.querySelector('input[name="tool-family-filter"][value="all"]');

    if (changedBox.value === "all") {
        document.querySelectorAll('input[name="tool-family-filter"]').forEach(cb => {
            cb.checked = cb.value === "all" ? changedBox.checked : false;
        });
    } else {
        if (allBox) allBox.checked = false;
    }

    const checked = [...document.querySelectorAll('input[name="tool-family-filter"]:checked')]
        .map(cb => cb.value)
        .filter(v => v !== "all");

    activeToolFamilyFilter = checked.length ? checked.join(",") : null;

    if (!activeToolFamilyFilter && allBox) allBox.checked = true;

    renderActiveFilterChips();
    loadCatalogProducts();
};

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

    renderActiveFilterChips();
    loadCatalogProducts();
};

/* ── Reset all filters helper ────────────────────────────────────────────── */
window.resetAllCatalogFilters = function() {
    const searchInput = document.getElementById("catalog-search");
    if (searchInput) searchInput.value = "";
    const sortSelect = document.getElementById("sort-select");
    if (sortSelect) sortSelect.value = "default";

    document.querySelectorAll('[name^="attr-filter-"]').forEach(radio => {
        if (radio.value === "all") radio.checked = true;
    });
    const allBrandRadio = document.querySelector('input[name="brand-filter"][value="all"]');
    if (allBrandRadio) allBrandRadio.checked = true;

    document.querySelectorAll('input[name="tool-family-filter"]').forEach(cb => {
        cb.checked = cb.value === "all";
    });
    document.querySelectorAll('input[name="material-filter"]').forEach(cb => {
        cb.checked = cb.value === "all";
    });

    activeAttributeFilter = {};
    activeToolFamilyFilter = null;
    activeMaterialFilter = null;

    renderActiveFilterChips();
    loadCatalogProducts({});
};

function writeCatalogUrl(query) {
    const params = new URLSearchParams();
    if (query.search) params.set("search", query.search);
    if (query.item_group) params.set("item_group", query.item_group);
    if (query.tool_family) params.set("tool_families", query.tool_family);
    if (query.material) params.set("materials", query.material);
    for (const [attr, values] of Object.entries(query.attribute_filters || {})) {
        if (attr === "Brand - الماركة") {
            params.set("brand", values[0]);
        } else {
            params.append("attribute", attr);
            params.append("value", values[0]);
        }
    }
    if (query.sort && query.sort !== "default") params.set("sort", query.sort);
    if (query.page > 1) params.set("page", query.page);

    const qs = params.toString();
    history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
}

function loadCatalogProducts(queryArgs = {}, page = 1) {
    clearTimeout(catalogSearchTimer);
    catalogQuery = { ...getCatalogQueryArgs(queryArgs), page };
    loadCatalogPage();
}

function loadCatalogPage() {
    const grid = document.getElementById("catalog-product-grid");
    if (grid) grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-muted);" data-i18n="loading">${Store.t("loading")}</div>`;

    const requestId = ++catalogRequestSeq;
    const query = catalogQuery;
    writeCatalogUrl(query);

    Store.call("custom_webshop.api.catalog.get_catalog_products", {
        tool_family: query.tool_family || null,
        material: query.material || null,
        item_group: query.item_group || null,
        attribute_filters: JSON.stringify(query.attribute_filters || {}),
        field_filters: JSON.stringify(query.field_filters || {}),
        search: query.search || null,
        sort: query.sort,
        page: query.page,
    }).then(data => {
        if (requestId !== catalogRequestSeq) return;
        const { items, page, size, total, totalPages } = data;
        pageProducts = items;
        catalogPagination = { page, size, total, totalPages };
        if (page !== query.page) {
            catalogQuery = { ...query, page };
            writeCatalogUrl(catalogQuery);
        }
        renderCatalogGrid(pageProducts);
        renderCatalogPagination();
    }).catch(err => {
        if (requestId !== catalogRequestSeq) return;
        console.error("Catalog load failed:", err);
        if (grid) grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-muted);">${Store.t("error_generic")}</div>`;
        const pager = document.getElementById("catalog-pagination");
        if (pager) pager.style.display = "none";
    });
}

function getCatalogPageItems(current, totalPages) {
    const items = [];
    for (let p = 1; p <= totalPages; p++) {
        if (p === 1 || p === totalPages || Math.abs(p - current) <= 1) {
            items.push(p);
        } else if (items[items.length - 1] !== "…") {
            items.push("…");
        }
    }
    return items;
}

function renderCatalogPagination() {
    const pager = document.getElementById("catalog-pagination");
    if (!pager) return;

    const { page, totalPages } = catalogPagination;
    if (totalPages <= 1) {
        pager.style.display = "none";
        pager.innerHTML = "";
        return;
    }

    const pageButtons = getCatalogPageItems(page, totalPages).map(p => {
        if (p === "…") return `<span class="pagination-ellipsis" aria-hidden="true">…</span>`;
        const current = p === page;
        return `<button type="button" class="pagination-btn${current ? " active" : ""}" onclick="goToCatalogPage(${p})"
            aria-label="${Store.t("pagination_page", { page: p })}"${current ? ' aria-current="page"' : ""}>${p}</button>`;
    }).join("");

    pager.setAttribute("aria-label", Store.t("pagination_label"));
    pager.innerHTML = `
        <button type="button" class="pagination-btn" onclick="goToCatalogPage(${page - 1})"
            aria-label="${Store.t("pagination_prev")}" title="${Store.t("pagination_prev")}"${page <= 1 ? " disabled" : ""}>
            <i data-lucide="chevron-left"></i>
        </button>
        ${pageButtons}
        <button type="button" class="pagination-btn" onclick="goToCatalogPage(${page + 1})"
            aria-label="${Store.t("pagination_next")}" title="${Store.t("pagination_next")}"${page >= totalPages ? " disabled" : ""}>
            <i data-lucide="chevron-right"></i>
        </button>`;
    pager.style.display = "flex";
    if (window.lucide) lucide.createIcons({ nodes: [pager] });
}

window.goToCatalogPage = function(page) {
    if (page === catalogQuery.page) return;
    catalogQuery = { ...catalogQuery, page };
    loadCatalogPage();
    document.querySelector(".catalog-content")?.scrollIntoView({ behavior: "smooth", block: "start" });
    document.getElementById("results-count-text")?.focus({ preventScroll: true });
};

/* ── Add to cart ─────────────────────────────────────────────────────────── */
window.addToCartCatalog = function(itemCode) {
    // Guests may fill a basket; the account is asked for at the full form.
    Store.addToCart(itemCode, 1)
        .then(() => Store.toast(Store.t("toast_added_cart"), "success"))
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

/* ── View toggle ─────────────────────────────────────────────────────────── */
function updateViewToggleSlider(mode) {
    const slider = document.getElementById("toggle-slider");
    if (!slider) return;
    const isRtl = document.documentElement.getAttribute("dir") === "rtl" || Store.lang === "ar";
    if (mode === "list") {
        slider.style.transform = isRtl ? "translateX(-100%)" : "translateX(100%)";
    } else {
        slider.style.transform = "translateX(0)";
    }
}

function initViewToggle() {
    const gridBtn = document.getElementById("grid-toggle-btn");
    const listBtn = document.getElementById("list-toggle-btn");

    const savedMode = localStorage.getItem("cnc_catalog_view_mode") || "grid";
    catalogViewMode = savedMode;
    if (savedMode === "list") {
        gridBtn?.classList.remove("active");
        listBtn?.classList.add("active");
    }
    updateViewToggleSlider(savedMode);

    gridBtn?.addEventListener("click", () => {
        catalogViewMode = "grid";
        localStorage.setItem("cnc_catalog_view_mode", "grid");
        gridBtn.classList.add("active");
        listBtn?.classList.remove("active");
        updateViewToggleSlider("grid");
        renderCatalogGrid(pageProducts);
    });

    listBtn?.addEventListener("click", () => {
        catalogViewMode = "list";
        localStorage.setItem("cnc_catalog_view_mode", "list");
        listBtn.classList.add("active");
        gridBtn?.classList.remove("active");
        updateViewToggleSlider("list");
        renderCatalogGrid(pageProducts);
    });
}

/* ── Mobile Filter Modal ─────────────────────────────────────────────────── */
window.openCatalogFilterModal = function() {
    const sidebar = document.getElementById("catalog-sidebar");
    const overlay = document.getElementById("catalog-sidebar-overlay");
    sidebar?.classList.add("mobile-open");
    overlay?.classList.add("active");
    document.body.style.overflow = "hidden";
};

window.closeCatalogFilterModal = function() {
    const sidebar = document.getElementById("catalog-sidebar");
    const overlay = document.getElementById("catalog-sidebar-overlay");
    sidebar?.classList.remove("mobile-open");
    overlay?.classList.remove("active");
    document.body.style.overflow = "";
};

function initMobileFilterDrawer() {
    const triggerBtn = document.getElementById("mobile-filter-btn");
    const closeBtn = document.getElementById("sidebar-close-btn");
    const overlay = document.getElementById("catalog-sidebar-overlay");

    triggerBtn?.addEventListener("click", window.openCatalogFilterModal);
    closeBtn?.addEventListener("click", window.closeCatalogFilterModal);
    overlay?.addEventListener("click", window.closeCatalogFilterModal);
}

/* ── Re-render all filters and products on language switch ───────────────── */
function reRenderCatalogOnLangSwitch() {
    buildToolFamilyFilters(cachedFamilies);
    buildMaterialFilters(cachedMaterials);
    buildAttributeFilters(cachedAttributes);
    buildBrandFilters(cachedBrands);
    updateViewToggleSlider(catalogViewMode);
    renderActiveFilterChips();
    renderCatalogGrid(pageProducts);
    renderCatalogPagination();
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initCartDrawer(() => Store.renderCartDrawer({ loginRedirect: "/catalog" }));
    initViewToggle();
    initMobileFilterDrawer();

    // Wire local filter inputs
    document.getElementById("catalog-search")?.addEventListener("input", () => {
        renderActiveFilterChips();
        clearTimeout(catalogSearchTimer);
        catalogSearchTimer = setTimeout(() => loadCatalogProducts(), 300);
    });
    document.getElementById("sort-select")?.addEventListener("change", () => loadCatalogProducts());
    document.getElementById("clear-filters-btn")?.addEventListener("click", () => resetAllCatalogFilters());

    // Read URL params for initial filters.
    const urlParams = new URLSearchParams(window.location.search);
    const itemGroup    = urlParams.get("item_group");
    const attrName     = urlParams.get("attribute");
    const attrValue    = urlParams.get("value");
    const brand        = urlParams.get("brand");
    const toolFamily   = urlParams.get("tool_family");
    const material     = urlParams.get("material");
    const toolFamilies = urlParams.get("tool_families"); // e.g. "SEM,FEM,EM"
    const materials    = urlParams.get("materials");     // e.g. "HSS,C,CW,TCT"
    const searchParam  = urlParams.get("search");
    const sortParam    = urlParams.get("sort");
    const pageParam    = parseInt(urlParams.get("page"), 10) || 1;

    if (searchParam) {
        const searchInput = document.getElementById("catalog-search");
        if (searchInput) searchInput.value = searchParam;
    }
    const sortSelect = document.getElementById("sort-select");
    if (sortSelect && [...sortSelect.options].some(o => o.value === sortParam)) {
        sortSelect.value = sortParam;
    }

    const queryArgs = {};
    if (itemGroup) queryArgs.item_group = itemGroup;
    const attrValues = urlParams.getAll("value");
    urlParams.getAll("attribute").forEach((name, i) => {
        if (name && attrValues[i]) activeAttributeFilter[name] = [attrValues[i]];
    });
    if (brand) activeAttributeFilter["Brand - الماركة"] = [brand];

    if (toolFamilies)    activeToolFamilyFilter = toolFamilies;
    else if (toolFamily) activeToolFamilyFilter = toolFamily;

    if (materials)     activeMaterialFilter = materials;
    else if (material) activeMaterialFilter = material;

    // Load sidebar filter panels in parallel
    Promise.all([
        Store.call("custom_webshop.api.catalog.get_item_attributes"),
        Store.call("custom_webshop.api.catalog.get_all_tool_families"),
        Store.call("custom_webshop.api.catalog.get_all_materials"),
        Store.call("custom_webshop.api.catalog.get_brands"),
    ]).then(([attrs, families, mats, brandRows]) => {
        const initTf  = activeToolFamilyFilter || null;
        const initMat = activeMaterialFilter   || null;
        buildToolFamilyFilters(families || [], initTf);
        buildMaterialFilters(mats || [], initMat);
        buildAttributeFilters(attrs || []);
        buildBrandFilters((brandRows || []).map(r => r.brand).filter(Boolean));

        const activeBrandAttr = brand || (attrName === "Brand - الماركة" ? attrValue : null);
        if (activeBrandAttr) {
            const safeName = "Brand - الماركة".replace(/\s+/g, "-");
            const radio = document.querySelector(`input[name="attr-filter-${safeName}"][value="${activeBrandAttr}"]`);
            if (radio) radio.checked = true;
            const brandRadio = document.querySelector(`input[name="brand-filter"][value="${activeBrandAttr}"]`);
            if (brandRadio) brandRadio.checked = true;
        } else if (attrName && attrValue) {
            const safeName = attrName.replace(/\s+/g, "-");
            const radio = document.querySelector(`input[name="attr-filter-${safeName}"][value="${attrValue}"]`);
            if (radio) radio.checked = true;
        }

        renderActiveFilterChips();
    }).catch(() => {});

    loadCatalogProducts(queryArgs, pageParam);

    // Live re-render on language switch
    window.addEventListener("cnc_language_changed", () => {
        reRenderCatalogOnLangSwitch();
    });
});
