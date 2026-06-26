/* ==========================================================================
   CNCLeaders — Admin Panel Controller
   Only loaded for System Manager / Website Manager role (injected by page-shop.js).
   Depends on: store.js
   Uses: custom_webshop.api.slides.*, custom_webshop.api.catalog.*
   ========================================================================== */

/* ══════════════════════════════════════════════════════════════════════════
   SHARED — Tab navigation
   ══════════════════════════════════════════════════════════════════════════ */

function initAdminTabs() {
    const links = document.querySelectorAll(".admin-menu-link");
    links.forEach(link => {
        link.addEventListener("click", e => {
            e.preventDefault();
            const tab = link.dataset.tab;
            // Update sidebar active state
            links.forEach(l => l.classList.remove("active"));
            link.classList.add("active");
            // Show correct tab panel via class (CSS controls visibility)
            document.querySelectorAll(".admin-tab-content").forEach(panel => {
                panel.classList.remove("active");
            });
            const panel = document.getElementById(`admin-tab-${tab}`);
            if (panel) panel.classList.add("active");
            // Load data for the tab that just became visible
            if (tab === "slideshow") loadAdminSlides();
            if (tab === "attributes") loadAdminAttributes();
        });
    });
}

/* ══════════════════════════════════════════════════════════════════════════
   TAB 1 — Slide Customizer
   ══════════════════════════════════════════════════════════════════════════ */

/* ── Render the admin slides table ──────────────────────────────────────── */
function renderAdminSlideshowTable(slides) {
    const tbody = document.getElementById("admin-slides-rows");
    if (!tbody) return;

    if (!slides || !slides.length) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:24px;">No slides configured yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = slides.map((slide, idx) => {
        const img = slide.image || "/assets/custom_webshop/images/placeholder.jpg";
        return `
        <tr>
            <td style="font-weight:700;color:var(--primary-blue);">${idx + 1}</td>
            <td>
                <div style="width:80px;height:50px;overflow:hidden;border-radius:4px;background:#111;">
                    <img src="${img}" style="width:100%;height:100%;object-fit:cover;" alt="slide">
                </div>
            </td>
            <td>
                <div style="font-weight:600;font-size:0.9rem;">${slide.title || "—"}</div>
                <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px;">${slide.eyebrow || ""}</div>
            </td>
            <td><a href="${slide.link || "/catalog"}" style="color:var(--primary-blue);font-size:0.85rem;">${slide.link || "/catalog"}</a></td>
            <td>
                <div style="display:flex;gap:8px;">
                    <button class="btn btn-secondary btn-sm" onclick="moveSlide('${slide.name}','up')" title="Move Up">
                        <i data-lucide="arrow-up" style="width:14px;height:14px;"></i>
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="moveSlide('${slide.name}','down')" title="Move Down">
                        <i data-lucide="arrow-down" style="width:14px;height:14px;"></i>
                    </button>
                    <button class="btn btn-secondary btn-sm" style="color:#EF4444;" onclick="deleteSlide('${slide.name}')" title="Delete">
                        <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join("");

    if (window.lucide) lucide.createIcons({ nodes: [tbody] });
}

/* ── Load slides from server ─────────────────────────────────────────────── */
let adminSlides = [];

function loadAdminSlides() {
    Store.call("custom_webshop.api.slides.get_slides")
        .then(data => {
            adminSlides = Array.isArray(data) ? data : [];
            renderAdminSlideshowTable(adminSlides);
        })
        .catch(err => {
            console.error("Failed to load admin slides:", err);
            renderAdminSlideshowTable([]);
        });
}

/* ── Live slide preview ──────────────────────────────────────────────────── */
function initSlidePreview() {
    const fields = {
        eyebrow:  document.getElementById("slide-eyebrow"),
        title:    document.getElementById("slide-title"),
        subtitle: document.getElementById("slide-subtitle"),
        link:     document.getElementById("slide-link"),
        image:    document.getElementById("slide-image-url"),
    };
    const preview = {
        bg:       document.getElementById("slide-preview-bg"),
        eyebrow:  document.getElementById("slide-preview-eyebrow"),
        title:    document.getElementById("slide-preview-title"),
        subtitle: document.getElementById("slide-preview-subtitle"),
        cta:      document.getElementById("slide-preview-cta"),
    };

    if (!preview.bg) return; // preview panel not in DOM

    function updatePreview() {
        const img = fields.image?.value?.trim();
        preview.bg.style.backgroundImage = img ? `url('${img}')` : "";
        preview.eyebrow.textContent = fields.eyebrow?.value || "EYEBROW CAPTION";
        preview.title.textContent   = fields.title?.value   || "Hero Title Text";
        preview.subtitle.textContent = fields.subtitle?.value || "Subtitle description goes here.";
        preview.cta.textContent     = fields.link?.value    || "/catalog";
    }

    Object.values(fields).forEach(el => {
        if (el) el.addEventListener("input", updatePreview);
    });

    updatePreview(); // set initial state
}

/* ── Add slide form submission ───────────────────────────────────────────── */
function initAdminSlideForm() {
    const form = document.getElementById("admin-add-slide-form");
    if (!form) return;

    form.addEventListener("submit", (e) => {
        e.preventDefault();

        const eyebrow   = document.getElementById("slide-eyebrow")?.value?.trim();
        const title     = document.getElementById("slide-title")?.value?.trim();
        const subtitle  = document.getElementById("slide-subtitle")?.value?.trim();
        const link      = document.getElementById("slide-link")?.value?.trim() || "/catalog";
        const imageUrl  = document.getElementById("slide-image-url")?.value?.trim() || "";

        if (!eyebrow || !title || !subtitle) {
            Store.toast("Please fill in all required fields.", "error");
            return;
        }

        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = Store.t("loading"); }

        Store.call("custom_webshop.api.slides.save_slide", {
            eyebrow, title, subtitle, link, image: imageUrl,
        }).then(() => {
            Store.toast("Slide added successfully!", "success");
            form.reset();
            // Reset preview to defaults
            const previewEyebrow = document.getElementById("slide-preview-eyebrow");
            const previewTitle   = document.getElementById("slide-preview-title");
            const previewSub     = document.getElementById("slide-preview-subtitle");
            const previewCta     = document.getElementById("slide-preview-cta");
            const previewBg      = document.getElementById("slide-preview-bg");
            if (previewEyebrow) previewEyebrow.textContent = "EYEBROW CAPTION";
            if (previewTitle)   previewTitle.textContent   = "Hero Title Text";
            if (previewSub)     previewSub.textContent     = "Subtitle description goes here.";
            if (previewCta)     previewCta.textContent     = "/catalog";
            if (previewBg)      previewBg.style.backgroundImage = "";
            loadAdminSlides();
            if (typeof loadSlides === "function") loadSlides();
        }).catch(err => {
            Store.toast(err.message || Store.t("error_generic"), "error");
        }).finally(() => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i data-lucide="plus-circle" class="btn-icon"></i> Inject Slide to Live Hero';
                if (window.lucide) lucide.createIcons({ nodes: [submitBtn] });
            }
        });
    });
}

/* ── Delete slide ────────────────────────────────────────────────────────── */
window.deleteSlide = function(slideName) {
    if (!confirm("Delete this slide from the hero carousel?")) return;

    Store.call("custom_webshop.api.slides.delete_slide", { slide_name: slideName })
        .then(() => {
            Store.toast("Slide deleted.", "info");
            loadAdminSlides();
            if (typeof loadSlides === "function") loadSlides();
        })
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

/* ── Reorder slides (move up/down) ──────────────────────────────────────── */
window.moveSlide = function(slideName, direction) {
    const idx = adminSlides.findIndex(s => s.name === slideName);
    if (idx < 0) return;

    const newIdx = direction === "up" ? idx - 1 : idx + 1;
    if (newIdx < 0 || newIdx >= adminSlides.length) return;

    [adminSlides[idx], adminSlides[newIdx]] = [adminSlides[newIdx], adminSlides[idx]];

    const orderedNames = adminSlides.map(s => s.name);
    Store.call("custom_webshop.api.slides.reorder_slides", { slide_names: JSON.stringify(orderedNames) })
        .then(() => {
            renderAdminSlideshowTable(adminSlides);
            if (typeof loadSlides === "function") loadSlides();
        })
        .catch(err => {
            Store.toast(err.message || Store.t("error_generic"), "error");
            loadAdminSlides();
        });
};

/* ══════════════════════════════════════════════════════════════════════════
   TAB 2 — Attribute Display Manager
   ══════════════════════════════════════════════════════════════════════════ */

// Working list: [{ attribute, values, enabled }] in current display order
let adminAttrList = [];

function renderAdminAttributeList() {
    const container = document.getElementById("admin-attributes-list");
    if (!container) return;

    if (!adminAttrList.length) {
        container.innerHTML = `<p style="color:var(--text-muted);">No attributes found in your product catalog.</p>`;
        return;
    }

    container.innerHTML = adminAttrList.map((row, idx) => `
        <div class="admin-attr-row" data-idx="${idx}" style="display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--border-subtle);border-radius:6px;margin-bottom:8px;background:var(--bg-card,#fff);">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;flex:1;min-width:0;">
                <input type="checkbox" class="attr-enabled-cb" data-idx="${idx}" ${row.enabled ? "checked" : ""} style="width:16px;height:16px;accent-color:var(--primary-blue);">
                <span style="font-weight:600;font-size:0.95rem;">${row.attribute}</span>
                <span style="font-size:0.75rem;color:var(--text-muted);margin-left:4px;">(${row.values.length} value${row.values.length !== 1 ? "s" : ""})</span>
            </label>
            <div style="display:flex;gap:6px;flex-shrink:0;">
                <button class="btn btn-secondary btn-sm attr-move-btn" data-idx="${idx}" data-dir="up" title="Move Up" ${idx === 0 ? "disabled" : ""}>
                    <i data-lucide="arrow-up" style="width:14px;height:14px;pointer-events:none;"></i>
                </button>
                <button class="btn btn-secondary btn-sm attr-move-btn" data-idx="${idx}" data-dir="down" title="Move Down" ${idx === adminAttrList.length - 1 ? "disabled" : ""}>
                    <i data-lucide="arrow-down" style="width:14px;height:14px;pointer-events:none;"></i>
                </button>
            </div>
        </div>`).join("");

    if (window.lucide) lucide.createIcons({ nodes: [container] });

    // Wire checkbox toggles
    container.querySelectorAll(".attr-enabled-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            const i = parseInt(cb.dataset.idx, 10);
            adminAttrList[i].enabled = cb.checked;
        });
    });

    // Wire move buttons via delegation
    container.querySelectorAll(".attr-move-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const i = parseInt(btn.dataset.idx, 10);
            const dir = btn.dataset.dir;
            const newIdx = dir === "up" ? i - 1 : i + 1;
            if (newIdx < 0 || newIdx >= adminAttrList.length) return;
            [adminAttrList[i], adminAttrList[newIdx]] = [adminAttrList[newIdx], adminAttrList[i]];
            renderAdminAttributeList();
        });
    });
}

function loadAdminAttributes() {
    const container = document.getElementById("admin-attributes-list");
    if (container) container.innerHTML = `<p style="color:var(--text-muted);">Loading…</p>`;

    Promise.all([
        Store.call("custom_webshop.api.catalog.get_item_attributes"),
        Store.call("custom_webshop.api.catalog.get_display_attributes"),
    ]).then(([allAttrs, displayAttrs]) => {
        const displayNames = (displayAttrs || []).map(a => a.attribute);
        const displaySet = new Set(displayNames);

        // Build sorted list: configured display attributes first (in their saved order),
        // then remaining attributes appended at the end (disabled by default).
        const orderedMap = {};
        displayNames.forEach((name, i) => { orderedMap[name] = i; });

        const inDisplay = (allAttrs || [])
            .filter(a => displaySet.has(a.attribute))
            .sort((a, b) => orderedMap[a.attribute] - orderedMap[b.attribute])
            .map(a => ({ ...a, enabled: true }));

        const notInDisplay = (allAttrs || [])
            .filter(a => !displaySet.has(a.attribute))
            .map(a => ({ ...a, enabled: false }));

        adminAttrList = [...inDisplay, ...notInDisplay];
        renderAdminAttributeList();
    }).catch(err => {
        console.error("Failed to load attributes:", err);
        if (container) container.innerHTML = `<p style="color:var(--danger-red,#EF4444);">Failed to load attributes.</p>`;
    });
}

function initAttributeTab() {
    const saveBtn = document.getElementById("save-attributes-btn");
    if (!saveBtn) return;

    saveBtn.addEventListener("click", () => {
        const enabledNames = adminAttrList
            .filter(a => a.enabled)
            .map(a => a.attribute);

        const statusEl = document.getElementById("save-attributes-status");
        saveBtn.disabled = true;
        if (statusEl) statusEl.textContent = "Saving…";

        Store.call("custom_webshop.api.catalog.save_display_attributes", {
            attribute_names: JSON.stringify(enabledNames),
        }).then(() => {
            Store.toast("Attribute display order saved!", "success");
            if (statusEl) statusEl.textContent = "Saved.";
            // Refresh the shop page carousels live
            if (typeof loadAttributeCarousels === "function") loadAttributeCarousels();
        }).catch(err => {
            Store.toast(err.message || Store.t("error_generic"), "error");
            if (statusEl) statusEl.textContent = "Error saving.";
        }).finally(() => {
            saveBtn.disabled = false;
            setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
        });
    });
}

/* ══════════════════════════════════════════════════════════════════════════
   Admin view toggle (nav link → show/hide admin section)
   ══════════════════════════════════════════════════════════════════════════ */

window.showAdminView = function() {
    const adminView = document.getElementById("admin-view");
    const homeView  = document.getElementById("home-view");
    const adminLink = document.getElementById("nav-admin-link");

    // Use .active class — same pattern as the rest of the page
    if (homeView)  homeView.classList.remove("active");
    if (adminView) adminView.classList.add("active");
    if (adminLink) adminLink.classList.add("active");

    // Ensure exactly one tab panel has the active class (default: slideshow)
    const hasActive = document.querySelector(".admin-tab-content.active");
    if (!hasActive) {
        const first = document.getElementById("admin-tab-slideshow");
        if (first) first.classList.add("active");
    }

    // Load data for whichever tab is active
    const activeTab = document.querySelector(".admin-tab-content.active");
    if (!activeTab || activeTab.id === "admin-tab-slideshow") loadAdminSlides();
    else if (activeTab.id === "admin-tab-attributes") loadAdminAttributes();
};

function initAdminViewToggle() {
    const adminLink = document.getElementById("nav-admin-link");
    const adminView = document.getElementById("admin-view");
    const homeView  = document.getElementById("home-view");

    if (adminLink && adminView) {
        adminLink.addEventListener("click", (e) => {
            e.preventDefault();
            const isShowing = adminView.classList.contains("active");
            if (isShowing) {
                adminView.classList.remove("active");
                if (homeView) homeView.classList.add("active");
                adminLink.classList.remove("active");
            } else {
                showAdminView();
            }
        });
    }
}

/* ══════════════════════════════════════════════════════════════════════════
   Entry point — called once admin access is confirmed
   ══════════════════════════════════════════════════════════════════════════ */
(function initSlideAdmin() {
    function init() {
        initAdminViewToggle();
        initAdminTabs();
        initAdminSlideForm();
        initSlidePreview();
        initAttributeTab();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            init();
            if (window.location.hash === "#admin") showAdminView();
        });
    } else {
        init();
        if (window.location.hash === "#admin") showAdminView();
    }
})();
