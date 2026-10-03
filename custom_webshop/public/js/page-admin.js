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
                if (typeof setSlideImage === "function") setSlideImage("", "");
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
   SLIDE IMAGE PICKER (MEDIA LIBRARY & UPLOAD)
   ══════════════════════════════════════════════════════════════════════════ */

let cachedImageFiles = [];
let modalSelectedImage = null; // { file_url, file_name }

function setSlideImage(fileUrl, fileName) {
    const hiddenInput = document.getElementById("slide-image-url");
    const thumbImg = document.getElementById("slide-selected-thumb");
    const placeholderIcon = document.getElementById("slide-selected-placeholder-icon");
    const nameEl = document.getElementById("slide-selected-name");
    const pathEl = document.getElementById("slide-selected-path");
    const clearBtn = document.getElementById("clear-selected-image-btn");

    if (fileUrl) {
        if (hiddenInput) {
            hiddenInput.value = fileUrl;
            hiddenInput.dispatchEvent(new Event("input"));
        }
        if (thumbImg) {
            thumbImg.src = fileUrl;
            thumbImg.style.display = "block";
        }
        if (placeholderIcon) placeholderIcon.style.display = "none";
        if (nameEl) nameEl.textContent = fileName || fileUrl.split("/").pop();
        if (pathEl) pathEl.textContent = fileUrl;
        if (clearBtn) clearBtn.style.display = "inline-flex";
    } else {
        if (hiddenInput) {
            hiddenInput.value = "";
            hiddenInput.dispatchEvent(new Event("input"));
        }
        if (thumbImg) {
            thumbImg.src = "";
            thumbImg.style.display = "none";
        }
        if (placeholderIcon) placeholderIcon.style.display = "block";
        if (nameEl) nameEl.textContent = "No image selected";
        if (pathEl) pathEl.textContent = "Choose from media library or upload";
        if (clearBtn) clearBtn.style.display = "none";
    }
}

function openImagePickerModal() {
    const modal = document.getElementById("image-picker-modal");
    if (!modal) return;
    modal.style.display = "flex";
    modalSelectedImage = null;
    updateModalSelectionUI();
    loadLibraryImages();
    if (window.lucide) lucide.createIcons({ nodes: [modal] });
}

function closeImagePickerModal() {
    const modal = document.getElementById("image-picker-modal");
    if (modal) modal.style.display = "none";
}

function updateModalSelectionUI() {
    const statusEl = document.getElementById("img-modal-selected-status");
    const selectBtn = document.getElementById("img-modal-select-btn");
    if (!statusEl || !selectBtn) return;

    if (modalSelectedImage) {
        statusEl.innerHTML = `Selected: <strong>${modalSelectedImage.file_name}</strong>`;
        selectBtn.disabled = false;
    } else {
        statusEl.textContent = "No image selected";
        selectBtn.disabled = true;
    }

    // Update highlight on grid items
    document.querySelectorAll(".img-grid-item").forEach(card => {
        const check = card.querySelector(".img-grid-check");
        if (modalSelectedImage && card.dataset.url === modalSelectedImage.file_url) {
            card.style.borderColor = "var(--primary-blue, #2563eb)";
            card.style.boxShadow = "0 0 0 2px var(--primary-blue, #2563eb)";
            if (check) check.style.display = "flex";
        } else {
            card.style.borderColor = "var(--border-subtle)";
            card.style.boxShadow = "none";
            if (check) check.style.display = "none";
        }
    });
}

function renderImageGrid(images) {
    const grid = document.getElementById("img-modal-grid");
    if (!grid) return;

    if (!images || !images.length) {
        grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px 20px; color:var(--text-muted);">
            <i data-lucide="image-off" style="width:36px; height:36px; margin-bottom:8px; opacity:0.6;"></i>
            <p style="margin:0; font-size:0.9rem;">No image files found in media library.</p>
        </div>`;
        if (window.lucide) lucide.createIcons({ nodes: [grid] });
        return;
    }

    grid.innerHTML = images.map(img => {
        const isSelected = modalSelectedImage && modalSelectedImage.file_url === img.file_url;
        return `
        <div class="img-grid-item" data-url="${img.file_url}" data-name="${img.file_name}"
            style="position:relative; cursor:pointer; border-radius:8px; overflow:hidden; border:2px solid ${isSelected ? "var(--primary-blue, #2563eb)" : "var(--border-subtle)"}; background:var(--bg-subtle, #1e293b); transition:all 0.15s ease; ${isSelected ? "box-shadow:0 0 0 2px var(--primary-blue, #2563eb);" : ""}">
            <div style="aspect-ratio:4/3; width:100%; overflow:hidden; background:#111; display:flex; align-items:center; justify-content:center;">
                <img src="${img.file_url}" alt="${img.file_name}" style="width:100%; height:100%; object-fit:cover;" loading="lazy">
            </div>
            <div style="padding:6px 8px; font-size:0.75rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; background:rgba(0,0,0,0.5); color:#fff;" title="${img.file_name}">
                ${img.file_name}
            </div>
            <div class="img-grid-check" style="position:absolute; top:6px; right:6px; width:22px; height:22px; border-radius:50%; background:var(--primary-blue, #2563eb); color:#fff; display:${isSelected ? "flex" : "none"}; align-items:center; justify-content:center; box-shadow:0 2px 4px rgba(0,0,0,0.3);">
                <i data-lucide="check" style="width:14px; height:14px;"></i>
            </div>
        </div>`;
    }).join("");

    if (window.lucide) lucide.createIcons({ nodes: [grid] });

    grid.querySelectorAll(".img-grid-item").forEach(card => {
        card.addEventListener("click", () => {
            modalSelectedImage = {
                file_url: card.dataset.url,
                file_name: card.dataset.name,
            };
            updateModalSelectionUI();
        });

        card.addEventListener("dblclick", () => {
            modalSelectedImage = {
                file_url: card.dataset.url,
                file_name: card.dataset.name,
            };
            setSlideImage(modalSelectedImage.file_url, modalSelectedImage.file_name);
            closeImagePickerModal();
        });
    });
}

function loadLibraryImages(search = "") {
    const grid = document.getElementById("img-modal-grid");
    if (grid && !cachedImageFiles.length) {
        grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:30px; color:var(--text-muted); font-size:0.9rem;">Loading images…</div>`;
    }

    Store.call("custom_webshop.api.slides.get_image_files", { search: (search || "").trim() })
        .then(files => {
            cachedImageFiles = Array.isArray(files) ? files : [];
            renderImageGrid(cachedImageFiles);
        })
        .catch(err => {
            if (grid) {
                grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:30px; color:#EF4444; font-size:0.9rem;">Failed to load images: ${err.message || "Error"}</div>`;
            }
        });
}

function initSlideImagePicker() {
    const openBtn = document.getElementById("open-image-picker-btn");
    const clearBtn = document.getElementById("clear-selected-image-btn");
    const closeBtn = document.getElementById("close-image-modal-btn");
    const cancelBtn = document.getElementById("img-modal-cancel-btn");
    const selectBtn = document.getElementById("img-modal-select-btn");
    const refreshBtn = document.getElementById("img-modal-refresh-btn");
    const searchInput = document.getElementById("img-modal-search");
    const modal = document.getElementById("image-picker-modal");

    if (openBtn) openBtn.addEventListener("click", openImagePickerModal);
    if (closeBtn) closeBtn.addEventListener("click", closeImagePickerModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeImagePickerModal);

    // Backdrop click closes
    if (modal) {
        modal.addEventListener("click", (e) => {
            if (e.target === modal) closeImagePickerModal();
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            setSlideImage("", "");
        });
    }

    if (selectBtn) {
        selectBtn.addEventListener("click", () => {
            if (modalSelectedImage) {
                setSlideImage(modalSelectedImage.file_url, modalSelectedImage.file_name);
                closeImagePickerModal();
            }
        });
    }

    // Modal tabs (Library vs Upload)
    document.querySelectorAll(".img-modal-tab-btn").forEach(tabBtn => {
        tabBtn.addEventListener("click", () => {
            const target = tabBtn.dataset.imgTab;
            document.querySelectorAll(".img-modal-tab-btn").forEach(b => {
                b.classList.remove("active");
                b.style.borderBottomColor = "transparent";
                b.style.color = "var(--text-muted)";
            });
            tabBtn.classList.add("active");
            tabBtn.style.borderBottomColor = "var(--primary-blue, #2563eb)";
            tabBtn.style.color = "var(--primary-blue, #2563eb)";

            const libPanel = document.getElementById("img-tab-library-panel");
            const upPanel = document.getElementById("img-tab-upload-panel");
            if (target === "library") {
                if (libPanel) libPanel.style.display = "block";
                if (upPanel) upPanel.style.display = "none";
            } else {
                if (libPanel) libPanel.style.display = "none";
                if (upPanel) upPanel.style.display = "block";
            }
        });
    });

    // Search filter with debounce
    let searchTimeout = null;
    if (searchInput) {
        searchInput.addEventListener("input", () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadLibraryImages(searchInput.value);
            }, 300);
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            loadLibraryImages(searchInput ? searchInput.value : "");
        });
    }

    // Upload zone handling
    const dropzone = document.getElementById("img-modal-dropzone");
    const fileInput = document.getElementById("img-modal-file-input");
    const uploadStatus = document.getElementById("img-modal-upload-status");

    if (dropzone && fileInput) {
        dropzone.addEventListener("click", () => fileInput.click());

        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "var(--primary-blue, #2563eb)";
            dropzone.style.background = "rgba(37,99,235,0.06)";
        });

        ["dragleave", "drop"].forEach(evName => {
            dropzone.addEventListener(evName, () => {
                dropzone.style.borderColor = "var(--border-subtle)";
                dropzone.style.background = "var(--bg-subtle, rgba(255,255,255,0.01))";
            });
        });

        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            const file = e.dataTransfer.files && e.dataTransfer.files[0];
            if (file) handleSlideFileUpload(file);
        });

        fileInput.addEventListener("change", (e) => {
            const file = e.target.files && e.target.files[0];
            if (file) handleSlideFileUpload(file);
        });
    }

    function handleSlideFileUpload(file) {
        const validTypes = ["image/jpeg", "image/png", "image/webp", "image/svg+xml", "image/gif"];
        if (!validTypes.includes(file.type) && !file.name.match(/\.(jpe?g|png|webp|svg|gif)$/i)) {
            Store.toast("Please select a valid image file (JPG, PNG, WEBP, SVG, GIF).", "error");
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            Store.toast("File size exceeds 10MB limit.", "error");
            return;
        }

        if (uploadStatus) {
            uploadStatus.style.display = "block";
            uploadStatus.innerHTML = `<span style="color:var(--primary-blue,#2563eb);">Uploading ${file.name}…</span>`;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result;
            Store.call("custom_webshop.api.slides.upload_slide_image", {
                filename: file.name,
                file_content: base64,
            }).then(res => {
                if (uploadStatus) uploadStatus.style.display = "none";
                Store.toast("Image uploaded successfully!", "success");
                setSlideImage(res.file_url, res.file_name);
                closeImagePickerModal();
                if (fileInput) fileInput.value = "";
                cachedImageFiles = [res, ...cachedImageFiles];
            }).catch(err => {
                if (uploadStatus) {
                    uploadStatus.innerHTML = `<span style="color:#EF4444;">Upload failed: ${err.message || "Error"}</span>`;
                }
                Store.toast(err.message || "Failed to upload image.", "error");
            });
        };
        reader.onerror = () => {
            if (uploadStatus) uploadStatus.style.display = "none";
            Store.toast("Failed to read image file.", "error");
        };
        reader.readAsDataURL(file);
    }
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
        <div class="admin-attr-row" data-idx="${idx}" style="display:flex;flex-direction:column;gap:8px;padding:12px 14px;border:1px solid var(--border-subtle);border-radius:8px;margin-bottom:10px;background:var(--bg-card,#fff);">
            <div style="display:flex;align-items:center;gap:12px;">
                <label style="display:flex;align-items:center;gap:8px;cursor:pointer;flex:1;min-width:0;">
                    <input type="checkbox" class="tf-enabled-cb" data-idx="${idx}" ${row.enabled ? "checked" : ""} style="width:16px;height:16px;accent-color:var(--primary-blue);">
                    <span style="font-weight:600;font-size:0.95rem;">${Store.escapeHtml(row.tool_family)}</span>
                </label>
                <div style="display:flex;gap:6px;flex-shrink:0;">
                    <button class="btn btn-secondary btn-sm tf-move-btn" data-idx="${idx}" data-dir="up" title="Move Up" ${idx === 0 ? "disabled" : ""}>
                        <i data-lucide="arrow-up" style="width:14px;height:14px;pointer-events:none;"></i>
                    </button>
                    <button class="btn btn-secondary btn-sm tf-move-btn" data-idx="${idx}" data-dir="down" title="Move Down" ${idx === adminToolFamilyList.length - 1 ? "disabled" : ""}>
                        <i data-lucide="arrow-down" style="width:14px;height:14px;pointer-events:none;"></i>
                    </button>
                </div>
            </div>
            <div style="padding-left:24px;">
                <input type="text" class="form-input tf-desc-input" data-idx="${idx}" placeholder="Description for ${Store.escapeHtml(row.tool_family)} (displayed on home page under title)..." value="${Store.escapeHtml(row.description || '')}" style="width:100%;font-size:0.875rem;padding:7px 10px;border-radius:6px;border:1px solid var(--border-subtle);background:var(--bg-input,#fff);">
            </div>
        </div>`).join("");

    if (window.lucide) lucide.createIcons({ nodes: [container] });

    container.querySelectorAll(".tf-enabled-cb").forEach(cb => {
        cb.addEventListener("change", () => {
            adminToolFamilyList[parseInt(cb.dataset.idx, 10)].enabled = cb.checked;
        });
    });

    container.querySelectorAll(".tf-desc-input").forEach(input => {
        input.addEventListener("input", () => {
            const i = parseInt(input.dataset.idx, 10);
            if (adminToolFamilyList[i]) {
                adminToolFamilyList[i].description = input.value;
            }
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
        const displayMap = new Map();
        (displayFamilies || []).forEach((f, i) => {
            const name = typeof f === "string" ? f : (f && f.tool_family);
            const desc = (typeof f === "object" && f && f.description) ? f.description : "";
            if (name) displayMap.set(name, { order: i, description: desc });
        });

        const inDisplay = (allFamilies || [])
            .filter(f => displayMap.has(f.tool_family))
            .sort((a, b) => displayMap.get(a.tool_family).order - displayMap.get(b.tool_family).order)
            .map(f => ({
                ...f,
                description: displayMap.get(f.tool_family).description || "",
                enabled: true
            }));

        const notInDisplay = (allFamilies || [])
            .filter(f => !displayMap.has(f.tool_family))
            .map(f => ({ ...f, description: "", enabled: false }));

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
        const payload = adminToolFamilyList
            .filter(f => f.enabled)
            .map(f => ({
                tool_family: f.tool_family,
                description: (f.description || "").trim()
            }));
        const statusEl = document.getElementById("save-tool-families-status");
        saveBtn.disabled = true;
        if (statusEl) statusEl.textContent = "Saving…";

        Store.call("custom_webshop.api.catalog.save_display_tool_families", {
            tool_family_names: JSON.stringify(payload),
        }).then(() => {
            Store.toast("Tool family display order and descriptions saved!", "success");
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
    initSlideImagePicker();
    initToolFamilyTab();
    // Load data for the default (first) tab
    loadAdminSlides();
});
