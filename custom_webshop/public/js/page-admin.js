/* ==========================================================================
   CNCLeaders — Admin Page Controller
   Standalone admin page (/admin). Auth guard is enforced server-side.
   Depends on: store.js
   Uses: custom_webshop.api.slides.*, custom_webshop.api.catalog.*
   ========================================================================== */

/* ── Tab navigation ──────────────────────────────────────────────────────── */
function initAdminTabs() {
    document.querySelectorAll(".admin-menu-link").forEach(link => {
        link.addEventListener("click", e => {
            e.preventDefault();
            const tab = link.dataset.tab;

            document.querySelectorAll(".admin-menu-link").forEach(l => l.classList.remove("active"));
            link.classList.add("active");

            document.querySelectorAll(".admin-tab-content").forEach(p => p.classList.remove("active"));
            const panel = document.getElementById(`admin-tab-${tab}`);
            if (panel) panel.classList.add("active");

            if (tab === "slideshow")   loadAdminSlides();
            if (tab === "attributes")  loadAdminAttributes();
            if (tab === "toolfamilies") loadAdminToolFamilies();
        });
    });
}

/* ══════════════════════════════════════════════════════════════════════════
   SLIDE CUSTOMIZER
   ══════════════════════════════════════════════════════════════════════════ */

let adminSlides = [];

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

function loadAdminSlides() {
    Store.call("custom_webshop.api.slides.get_slides")
        .then(data => {
            adminSlides = Array.isArray(data) ? data : [];
            renderAdminSlideshowTable(adminSlides);
        })
        .catch(() => renderAdminSlideshowTable([]));
}

window.deleteSlide = function(slideName) {
    if (!confirm("Delete this slide from the hero carousel?")) return;
    Store.call("custom_webshop.api.slides.delete_slide", { slide_name: slideName })
        .then(() => { Store.toast("Slide deleted.", "info"); loadAdminSlides(); })
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

window.moveSlide = function(slideName, direction) {
    const idx = adminSlides.findIndex(s => s.name === slideName);
    if (idx < 0) return;
    const newIdx = direction === "up" ? idx - 1 : idx + 1;
    if (newIdx < 0 || newIdx >= adminSlides.length) return;
    [adminSlides[idx], adminSlides[newIdx]] = [adminSlides[newIdx], adminSlides[idx]];
    Store.call("custom_webshop.api.slides.reorder_slides", {
        slide_names: JSON.stringify(adminSlides.map(s => s.name))
    }).then(() => renderAdminSlideshowTable(adminSlides))
      .catch(err => { Store.toast(err.message || Store.t("error_generic"), "error"); loadAdminSlides(); });
};

/* ── Live preview ────────────────────────────────────────────────────────── */
function initSlidePreview() {
    const fields = {
        eyebrow: document.getElementById("slide-eyebrow"),
        title:   document.getElementById("slide-title"),
        subtitle:document.getElementById("slide-subtitle"),
        link:    document.getElementById("slide-link"),
        image:   document.getElementById("slide-image-url"),
    };
    const preview = {
        bg:      document.getElementById("slide-preview-bg"),
        eyebrow: document.getElementById("slide-preview-eyebrow"),
        title:   document.getElementById("slide-preview-title"),
        subtitle:document.getElementById("slide-preview-subtitle"),
        cta:     document.getElementById("slide-preview-cta"),
    };
    if (!preview.bg) return;

    function update() {
        const img = fields.image?.value?.trim();
        preview.bg.style.backgroundImage = img ? `url('${img}')` : "";
        preview.eyebrow.textContent  = fields.eyebrow?.value  || "EYEBROW CAPTION";
        preview.title.textContent    = fields.title?.value    || "Hero Title Text";
        preview.subtitle.textContent = fields.subtitle?.value || "Subtitle description goes here.";
        preview.cta.textContent      = fields.link?.value     || "/catalog";
    }
    Object.values(fields).forEach(el => el && el.addEventListener("input", update));
    update();
}

/* ── Add slide form ──────────────────────────────────────────────────────── */
function initAdminSlideForm() {
    const form = document.getElementById("admin-add-slide-form");
    if (!form) return;

    form.addEventListener("submit", e => {
        e.preventDefault();
        const eyebrow  = document.getElementById("slide-eyebrow")?.value?.trim();
        const title    = document.getElementById("slide-title")?.value?.trim();
        const subtitle = document.getElementById("slide-subtitle")?.value?.trim();
        const link     = document.getElementById("slide-link")?.value?.trim() || "/catalog";
        const image    = document.getElementById("slide-image-url")?.value?.trim() || "";

        if (!eyebrow || !title || !subtitle) {
            Store.toast("Please fill in all required fields.", "error");
            return;
        }

        const btn = form.querySelector('[type="submit"]');
        if (btn) { btn.disabled = true; btn.textContent = Store.t("loading"); }

        Store.call("custom_webshop.api.slides.save_slide", { eyebrow, title, subtitle, link, image })
            .then(() => {
                Store.toast("Slide added successfully!", "success");
                form.reset();
                // Reset preview
                const pb = document.getElementById("slide-preview-bg");
                const pe = document.getElementById("slide-preview-eyebrow");
                const pt = document.getElementById("slide-preview-title");
                const ps = document.getElementById("slide-preview-subtitle");
                const pc = document.getElementById("slide-preview-cta");
                if (pb) pb.style.backgroundImage = "";
                if (pe) pe.textContent = "EYEBROW CAPTION";
                if (pt) pt.textContent = "Hero Title Text";
                if (ps) ps.textContent = "Subtitle description goes here.";
                if (pc) pc.textContent = "/catalog";
                loadAdminSlides();
            })
            .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"))
            .finally(() => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '<i data-lucide="plus-circle" class="btn-icon"></i> Add Slide to Hero';
                    if (window.lucide) lucide.createIcons({ nodes: [btn] });
                }
            });
    });
}

/* ══════════════════════════════════════════════════════════════════════════
   ATTRIBUTE DISPLAY MANAGER
   ══════════════════════════════════════════════════════════════════════════ */

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

    container.querySelectorAll(".attr-enabled-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            adminAttrList[parseInt(cb.dataset.idx, 10)].enabled = cb.checked;
        });
    });

    container.querySelectorAll(".attr-move-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const i = parseInt(btn.dataset.idx, 10);
            const newIdx = btn.dataset.dir === "up" ? i - 1 : i + 1;
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
        const displaySet   = new Set(displayNames);
        const orderMap     = {};
        displayNames.forEach((n, i) => { orderMap[n] = i; });

        const inDisplay = (allAttrs || [])
            .filter(a => displaySet.has(a.attribute))
            .sort((a, b) => orderMap[a.attribute] - orderMap[b.attribute])
            .map(a => ({ ...a, enabled: true }));

        const notInDisplay = (allAttrs || [])
            .filter(a => !displaySet.has(a.attribute))
            .map(a => ({ ...a, enabled: false }));

        adminAttrList = [...inDisplay, ...notInDisplay];
        renderAdminAttributeList();
    }).catch(() => {
        if (container) container.innerHTML = `<p style="color:#EF4444;">Failed to load attributes.</p>`;
    });
}

function initAttributeTab() {
    const saveBtn = document.getElementById("save-attributes-btn");
    if (!saveBtn) return;

    saveBtn.addEventListener("click", () => {
        const enabledNames = adminAttrList.filter(a => a.enabled).map(a => a.attribute);
        const statusEl = document.getElementById("save-attributes-status");
        saveBtn.disabled = true;
        if (statusEl) statusEl.textContent = "Saving…";

        Store.call("custom_webshop.api.catalog.save_display_attributes", {
            attribute_names: JSON.stringify(enabledNames),
        }).then(() => {
            Store.toast("Attribute display order saved!", "success");
            if (statusEl) statusEl.textContent = "Saved.";
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
   TOOL FAMILY DISPLAY MANAGER
   ══════════════════════════════════════════════════════════════════════════ */

let adminToolFamilyList = [];

function renderAdminToolFamilyList() {
    const container = document.getElementById("admin-tool-families-list");
    if (!container) return;

    if (!adminToolFamilyList.length) {
        container.innerHTML = `<p style="color:var(--text-muted);">No tool families found in your product catalog.</p>`;
        return;
    }

    container.innerHTML = adminToolFamilyList.map((row, idx) => `
        <div class="admin-attr-row" data-idx="${idx}" style="display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--border-subtle);border-radius:6px;margin-bottom:8px;background:var(--bg-card,#fff);">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;flex:1;min-width:0;">
                <input type="checkbox" class="tf-enabled-cb" data-idx="${idx}" ${row.enabled ? "checked" : ""} style="width:16px;height:16px;accent-color:var(--primary-blue);">
                <span style="font-weight:600;font-size:0.95rem;">${row.tool_family}</span>
            </label>
            <div style="display:flex;gap:6px;flex-shrink:0;">
                <button class="btn btn-secondary btn-sm tf-move-btn" data-idx="${idx}" data-dir="up" title="Move Up" ${idx === 0 ? "disabled" : ""}>
                    <i data-lucide="arrow-up" style="width:14px;height:14px;pointer-events:none;"></i>
                </button>
                <button class="btn btn-secondary btn-sm tf-move-btn" data-idx="${idx}" data-dir="down" title="Move Down" ${idx === adminToolFamilyList.length - 1 ? "disabled" : ""}>
                    <i data-lucide="arrow-down" style="width:14px;height:14px;pointer-events:none;"></i>
                </button>
            </div>
        </div>`).join("");

    if (window.lucide) lucide.createIcons({ nodes: [container] });

    container.querySelectorAll(".tf-enabled-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            adminToolFamilyList[parseInt(cb.dataset.idx, 10)].enabled = cb.checked;
        });
    });

    container.querySelectorAll(".tf-move-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const i = parseInt(btn.dataset.idx, 10);
            const newIdx = btn.dataset.dir === "up" ? i - 1 : i + 1;
            if (newIdx < 0 || newIdx >= adminToolFamilyList.length) return;
            [adminToolFamilyList[i], adminToolFamilyList[newIdx]] = [adminToolFamilyList[newIdx], adminToolFamilyList[i]];
            renderAdminToolFamilyList();
        });
    });
}

function loadAdminToolFamilies() {
    const container = document.getElementById("admin-tool-families-list");
    if (container) container.innerHTML = `<p style="color:var(--text-muted);">Loading…</p>`;

    Promise.all([
        Store.call("custom_webshop.api.catalog.get_all_tool_families"),
        Store.call("custom_webshop.api.catalog.get_display_tool_families"),
    ]).then(([allFamilies, displayFamilies]) => {
        const displayNames = (displayFamilies || []).map(f => f.tool_family);
        const displaySet   = new Set(displayNames);
        const orderMap     = {};
        displayNames.forEach((n, i) => { orderMap[n] = i; });

        const inDisplay = (allFamilies || [])
            .filter(f => displaySet.has(f.tool_family))
            .sort((a, b) => orderMap[a.tool_family] - orderMap[b.tool_family])
            .map(f => ({ ...f, enabled: true }));

        const notInDisplay = (allFamilies || [])
            .filter(f => !displaySet.has(f.tool_family))
            .map(f => ({ ...f, enabled: false }));

        adminToolFamilyList = [...inDisplay, ...notInDisplay];
        renderAdminToolFamilyList();
    }).catch(() => {
        if (container) container.innerHTML = `<p style="color:#EF4444;">Failed to load tool families.</p>`;
    });
}

function initToolFamilyTab() {
    const saveBtn = document.getElementById("save-tool-families-btn");
    if (!saveBtn) return;

    saveBtn.addEventListener("click", () => {
        const enabledNames = adminToolFamilyList.filter(f => f.enabled).map(f => f.tool_family);
        const statusEl = document.getElementById("save-tool-families-status");
        saveBtn.disabled = true;
        if (statusEl) statusEl.textContent = "Saving…";

        Store.call("custom_webshop.api.catalog.save_display_tool_families", {
            tool_family_names: JSON.stringify(enabledNames),
        }).then(() => {
            Store.toast("Tool family display order saved!", "success");
            if (statusEl) statusEl.textContent = "Saved.";
        }).catch(err => {
            Store.toast(err.message || Store.t("error_generic"), "error");
            if (statusEl) statusEl.textContent = "Error saving.";
        }).finally(() => {
            saveBtn.disabled = false;
            setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 3000);
        });
    });
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initNavbarScroll();
    initAdminTabs();
    initAdminSlideForm();
    initSlidePreview();
    initAttributeTab();
    initToolFamilyTab();
    // Load data for the default (first) tab
    loadAdminSlides();
});
