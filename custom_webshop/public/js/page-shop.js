/* ==========================================================================
   CNCLeaders — Shop / Home Page Controller
   Handles: hero slider, brand grid, category carousels, trending products
   Depends on: store.js (Store, t)
   ========================================================================== */

/* ── Slide state ─────────────────────────────────────────────────────────── */
let slides = [];
let currentSlideIndex = 0;
let slideshowTimer = null;

/* ── Default fallback slides (bilingual support) ─────────────────────────── */
const DEFAULT_SLIDES_EN = [
    {
        eyebrow: "PRECISION CNC ENGINEERING",
        title: "Industrial Components Built for Micro-Tolerance Performance",
        subtitle: "Direct distributor of solid carbide cutting tools, high-torque spindle systems, and precision motion components.",
        link: "/catalog",
        image: "/assets/custom_webshop/images/assets/Aluminum%20and%20metal.jpeg"
    },
    {
        eyebrow: "HIGH-PERFORMANCE TOOLING",
        title: "Solid Carbide Spiral End Mills & Router Bits",
        subtitle: "AlTiN nano-coated 1-flute to 4-flute cutting tools for aluminum, wood, acrylic, and composite materials.",
        link: "/catalog?tool_families=SEM,EM,FEM",
        image: "/assets/custom_webshop/images/assets/Wood%20and%20mdf.jpeg"
    }
];

const DEFAULT_SLIDES_AR = [
    {
        eyebrow: "هندسة وحلول CNC فائقة الدقة",
        title: "أدوات قطع ومكونات صناعية مصممة لأعلى كفاءة تشغيل",
        subtitle: "الموزع المعتمد لبنط الراوتر الكاربيد، أدوات التفريز، ومستلزمات ماكينات الـ CNC ذات الجودة العالية.",
        link: "/catalog",
        image: "/assets/custom_webshop/images/assets/Aluminum%20and%20metal.jpeg"
    },
    {
        eyebrow: "أدوات قطع كاربيد متطورة",
        title: "بنط تفريز وأدوات توجيه كاربيد عالية التحمل",
        subtitle: "تشكيلة واسعة من بنط الألومنيوم والأخشاب والرخام بمختلف الأقطار والمواصفات المعتمدة.",
        link: "/catalog?tool_families=SEM,EM,FEM",
        image: "/assets/custom_webshop/images/assets/Wood%20and%20mdf.jpeg"
    }
];

function getDefaultSlides() {
    return Store.lang === "ar" ? DEFAULT_SLIDES_AR : DEFAULT_SLIDES_EN;
}

/* ── Hero Canvas Toolpath ────────────────────────────────────────────────── */
function initToolpathCanvas() {
    const canvas = document.getElementById("toolpath-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let width = canvas.width = canvas.offsetWidth;
    let height = canvas.height = canvas.offsetHeight;

    window.addEventListener("resize", () => {
        width = canvas.width = canvas.offsetWidth;
        height = canvas.height = canvas.offsetHeight;
    }, { passive: true });

    let mouse = { x: width / 2, y: height / 2, active: false };
    let cutter = { x: width / 2, y: height / 2, speed: 0.08 };
    let pathHistory = [];

    canvas.addEventListener("mousemove", (e) => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
        mouse.active = true;
        updateFloatingGCode(mouse.x, mouse.y);
    });
    canvas.addEventListener("mouseleave", () => { mouse.active = false; });

    function drawGrid() {
        const isDark = Store.theme === "dark";
        ctx.strokeStyle = isDark ? "rgba(255,255,255,0.03)" : "rgba(15,23,42,0.03)";
        ctx.lineWidth = 1;
        const gridSize = 40;
        for (let x = 0; x < width; x += gridSize) {
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
        }
        for (let y = 0; y < height; y += gridSize) {
            ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
        }
    }

    let isVisible = true;
    let animFrameId = null;

    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                isVisible = entry.isIntersecting;
                if (isVisible && !animFrameId) {
                    animFrameId = requestAnimationFrame(animate);
                }
            });
        }, { threshold: 0.05 });
        const heroEl = document.getElementById("hero-slider-container") || canvas;
        observer.observe(heroEl);
    }

    function animate() {
        if (!isVisible) {
            animFrameId = null;
            return;
        }
        ctx.clearRect(0, 0, width, height);
        drawGrid();
        const targetX = mouse.active ? mouse.x : width / 2 + Math.sin(Date.now() / 1500) * (width / 4);
        const targetY = mouse.active ? mouse.y : height / 2 + Math.cos(Date.now() / 1000) * (height / 5);
        cutter.x += (targetX - cutter.x) * cutter.speed;
        cutter.y += (targetY - cutter.y) * cutter.speed;
        pathHistory.push({ x: cutter.x, y: cutter.y });
        if (pathHistory.length > 100) pathHistory.shift();
        if (pathHistory.length > 1) {
            ctx.beginPath();
            ctx.moveTo(pathHistory[0].x, pathHistory[0].y);
            for (let i = 1; i < pathHistory.length; i++) ctx.lineTo(pathHistory[i].x, pathHistory[i].y);
            const isDark = Store.theme === "dark";
            ctx.strokeStyle = `rgba(37,99,235,${isDark ? "0.45" : "0.25"})`;
            ctx.lineWidth = 2;
            ctx.stroke();
        }
        animFrameId = requestAnimationFrame(animate);
    }
    animFrameId = requestAnimationFrame(animate);
}

function updateFloatingGCode(x, y) {
    const activeSlide = document.querySelector(".hero-slide.active");
    if (!activeSlide) return;
    const banner = activeSlide.querySelector(".gcode-scroll");
    if (!banner) return;
    const mmX = (x / 2).toFixed(2);
    const mmY = (y / 2).toFixed(2);
    const feed = (1000 + Math.random() * 500).toFixed(0);
    banner.innerHTML = `<span>G90 G21 G17 G94</span><span style="color:white;">G01 X${mmX} Y${mmY} F${feed}</span><span>M03 S18000</span><span>X${(x/3).toFixed(2)} Y${(y/3).toFixed(2)}</span>`;
}

/* ── Typewriter effect ───────────────────────────────────────────────────── */
function triggerTypewriterForSlide(slide) {
    const titleEl = slide.querySelector(".hero-title");
    if (!titleEl) return;
    const fullText = titleEl.getAttribute("data-title") || "";
    if (!fullText) return;
    if (titleEl.getAttribute("data-currently-typing") === fullText) return;
    if (titleEl.typingInterval) clearInterval(titleEl.typingInterval);
    titleEl.setAttribute("data-currently-typing", fullText);
    titleEl.innerHTML = "";
    const cursor = document.createElement("span");
    cursor.className = "typewriter-cursor";
    cursor.textContent = "|";
    titleEl.appendChild(cursor);
    let charIndex = 0;
    titleEl.typingInterval = setInterval(() => {
        if (charIndex < fullText.length) {
            titleEl.insertBefore(document.createTextNode(fullText.charAt(charIndex)), cursor);
            charIndex++;
        } else {
            clearInterval(titleEl.typingInterval);
            titleEl.typingInterval = null;
            setTimeout(() => cursor.classList.add("finished"), 1000);
        }
    }, 25);
}

function clearTypewriterForSlide(slide) {
    const titleEl = slide.querySelector(".hero-title");
    if (!titleEl) return;
    if (titleEl.typingInterval) { clearInterval(titleEl.typingInterval); titleEl.typingInterval = null; }
    titleEl.removeAttribute("data-currently-typing");
    titleEl.textContent = "";
}

/* ── Hero Slides ─────────────────────────────────────────────────────────── */
function renderHeroSlides() {
    const wrapper = document.getElementById("hero-slides-wrapper");
    const dotsContainer = document.getElementById("hero-slide-dots");
    if (!wrapper || !dotsContainer) return;

    wrapper.querySelectorAll(".hero-title").forEach(el => {
        if (el.typingInterval) { clearInterval(el.typingInterval); el.typingInterval = null; }
    });
    wrapper.innerHTML = "";
    dotsContainer.innerHTML = "";

    const activeSlides = (slides && slides.length) ? slides : getDefaultSlides();
    if (currentSlideIndex >= activeSlides.length) currentSlideIndex = 0;

    activeSlides.forEach((slide, idx) => {
        const slideDiv = document.createElement("div");
        slideDiv.className = `hero-slide ${idx === currentSlideIndex ? "active" : ""}`;
        const subtitleHTML = (slide.subtitle || "").split(" ")
            .map((w, i) => `<span class="reveal-word" style="animation-delay:${i * 0.04}s">${w}</span>`)
            .join(" ");
        slideDiv.innerHTML = `
            <div class="hero-slide-bg" style="background-image:url('${slide.image}');"></div>
            <div class="hero-slide-content">
                <span class="hero-eyebrow">${slide.eyebrow || ""}</span>
                <h1 class="hero-title" data-title="${(slide.title || "").replace(/"/g, "&quot;")}"></h1>
                <p class="hero-subtitle">${subtitleHTML}</p>
                <div class="hero-actions">
                    <a href="${slide.link || "/catalog"}" class="btn btn-primary">${Store.t("home_hero_browse")}</a>
                    <a href="#" class="btn btn-secondary">${Store.t("home_hero_catalog")}</a>
                </div>
                <div class="gcode-scroll"></div>
            </div>`;
        wrapper.appendChild(slideDiv);

        if (activeSlides.length > 1) {
            const dot = document.createElement("button");
            dot.className = `slide-dot ${idx === currentSlideIndex ? "active" : ""}`;
            dot.setAttribute("aria-label", `Slide ${idx + 1}`);
            dot.addEventListener("click", () => goToSlide(idx));
            dotsContainer.appendChild(dot);
        }
    });

    const activeSlide = wrapper.querySelector(".hero-slide.active");
    if (activeSlide) triggerTypewriterForSlide(activeSlide);
}

function goToSlide(index) {
    const activeSlides = (slides && slides.length) ? slides : getDefaultSlides();
    if (index < 0) index = activeSlides.length - 1;
    if (index >= activeSlides.length) index = 0;
    currentSlideIndex = index;
    document.querySelectorAll(".hero-slide").forEach((s, i) => {
        if (i === currentSlideIndex) { s.classList.add("active"); triggerTypewriterForSlide(s); }
        else { s.classList.remove("active"); clearTypewriterForSlide(s); }
    });
    document.querySelectorAll(".slide-dot").forEach((d, i) => {
        d.classList.toggle("active", i === currentSlideIndex);
    });
}

function startSlideshowRotation() {
    stopSlideshowRotation();
    const activeSlides = (slides && slides.length) ? slides : getDefaultSlides();
    if (activeSlides.length <= 1) return;
    slideshowTimer = setInterval(() => goToSlide(currentSlideIndex + 1), 5000);
}

function stopSlideshowRotation() {
    if (slideshowTimer) { clearInterval(slideshowTimer); slideshowTimer = null; }
}

/* ── Product Card HTML Helper ────────────────────────────────────────────── */
function buildProductCard(item, badge = "") {
    let badgeHTML = "";
    if (badge && badge !== "STOCK") {
        badgeHTML = `<span class="product-badge">${badge}</span>`;
    }

    const price = Store.productPrice(item);
    const img = item.image || item.website_image || "/assets/custom_webshop/images/placeholder.svg";
    const productHref = Store.productLink(item);
    const displayName = item.web_item_name || item.item_name || item.name || "";
    const rawDesc = Store.stripHtml(item.description || item.short_description || "");
    const descHTML = rawDesc ? `<p class="product-card-desc">${Store.escapeHtml(rawDesc)}</p>` : "";
    const brand = item.brand || "";
    const brandHTML = brand ? `<div class="product-meta-specs"><div class="spec-line"><span>${Store.t("filter_brand")}:</span><span style="font-weight:700;">${Store.escapeHtml(brand)}</span></div></div>` : "";
    const addBtn = `<button class="card-add-btn" onclick="addToCartItem('${item.item_code || item.name}')" title="${Store.t("btn_add_to_cart")}"><i data-lucide="shopping-cart"></i></button>`;

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

/* ── Add to cart (calls ERPNext update_cart override) ────────────────────── */
window.addToCartItem = function(itemCode) {
    // No account needed to fill a basket. Store.addToCart puts a guest's
    // in this browser and a signed-in visitor's on the server; the ask to
    // sign up comes at the full order form, not here.
    Store.addToCart(itemCode, 1)
        .then(() => Store.toast(Store.t("toast_added_cart"), "success"))
        .catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

/* ── Home Page Sections ──────────────────────────────────────────────────── */

/* Load brands from dedicated API and render brand marquee cards */
function loadBrands() {
    Store.call("custom_webshop.api.catalog.get_brands")
        .then(brands => {
            const brandGrid = document.getElementById("home-brand-grid");
            if (!brandGrid) return;
            if (!brands || !brands.length) {
                brandGrid.innerHTML = `<p style="color:var(--text-muted);padding:16px;">${Store.lang === 'ar' ? 'لا توجد علامات تجارية حالياً' : 'No brands found.'}</p>`;
                return;
            }
            // Repeat brand list for smooth infinite marquee looping
            const displayBrands = brands.length > 2 ? [...brands, ...brands, ...brands] : brands;
            brandGrid.innerHTML = displayBrands.map(b => {
                const brandName = b.brand || b.attribute_value || "";
                const attrName = b.attribute || "Brand - الماركة";
                const targetUrl = `/catalog?attribute=${encodeURIComponent(attrName)}&value=${encodeURIComponent(brandName)}`;
                return `
                <div class="brand-card" onclick="window.location.href='${targetUrl}'">
                    <div class="brand-badge-icon"><i data-lucide="shield-check"></i></div>
                    <div class="brand-logo-text">${Store.escapeHtml(brandName)}</div>
                    <div class="brand-logo-sub">${Store.t("certified_partner")}</div>
                </div>`;
            }).join("");
            if (window.lucide) lucide.createIcons({ nodes: [brandGrid] });
        })
        .catch(() => {});
}

/* ── Tool Family Progressive Carousel Loading ──────────────────────────── */
const TOOL_FAMILY_BATCH_SIZE = 6;
let tfGeneration = 0;
let pendingFamilies = [];
let failedFamilies = [];
let isLoadingTfBatch = false;
let renderedFamilyCount = 0;

function buildFamilyCarouselSection(family, products) {
    const familyName = (typeof family === "object" ? family.tool_family : family) || "";
    const description = (typeof family === "object" ? family.description : "") || "";
    const safeId = familyName.replace(/[^a-zA-Z0-9]/g, "-");
    const trackId = `carousel-track-${safeId}`;
    const section = document.createElement("div");
    section.className = "category-carousel-section";
    section.innerHTML = `
        <div class="category-carousel-header">
            <div class="carousel-title-group" style="display:flex;flex-direction:column;gap:4px;">
                <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                    <h3 class="carousel-title" style="margin:0;">${Store.escapeHtml(familyName)}</h3>
                    <a href="/catalog?tool_family=${encodeURIComponent(familyName)}" class="carousel-view-all">${Store.t("view_more")} &rarr;</a>
                </div>
                ${description ? `<p class="carousel-subtitle" style="margin:0;font-size:0.9rem;color:var(--text-muted);font-weight:400;line-height:1.4;">${Store.escapeHtml(description)}</p>` : ""}
            </div>
            <div class="carousel-nav">
                <button class="nav-btn-arrow" onclick="scrollCarousel('${safeId}',-1)" aria-label="Previous"><i data-lucide="chevron-left"></i></button>
                <button class="nav-btn-arrow" onclick="scrollCarousel('${safeId}',1)" aria-label="Next"><i data-lucide="chevron-right"></i></button>
            </div>
        </div>
        <div class="category-carousel-track-wrapper">
            <div class="category-carousel-track" id="${trackId}">
                ${products.map(p => buildProductCard(p, "")).join("")}
            </div>
        </div>`;
    return section;
}

function getOrCreateViewMoreContainer(container) {
    let btnWrapper = document.getElementById("view-more-families-container");
    if (!btnWrapper) {
        btnWrapper = document.createElement("div");
        btnWrapper.id = "view-more-families-container";
        btnWrapper.className = "view-more-families-container";
        btnWrapper.style.display = "none";
        container.appendChild(btnWrapper);
    }
    return btnWrapper;
}

function updateViewMoreButton(container, gen) {
    if (gen !== tfGeneration) return;
    const btnWrapper = getOrCreateViewMoreContainer(container);
    const remainingCount = pendingFamilies.length + failedFamilies.length;

    if (remainingCount <= 0) {
        btnWrapper.style.display = "none";
        btnWrapper.innerHTML = "";
        return;
    }

    const btnLabel = Store.t("btn_view_more_cutting_tools");

    btnWrapper.style.display = "flex";
    btnWrapper.innerHTML = `
        <button class="view-more-families-btn" id="view-more-families-btn" type="button">
            <span>${btnLabel}</span>
            <i data-lucide="chevron-down" style="width:16px;height:16px;"></i>
        </button>
    `;
    if (window.lucide) lucide.createIcons({ nodes: [btnWrapper] });

    const btn = document.getElementById("view-more-families-btn");
    if (btn) {
        btn.addEventListener("click", () => {
            if (isLoadingTfBatch) return;
            loadNextToolFamilyBatch(container, gen);
        });
    }
}

function processToolFamilyBatch(container, batch, gen) {
    const btnWrapper = getOrCreateViewMoreContainer(container);
    const slots = [];

    // Pre-insert placeholder slots in order before the View More button
    batch.forEach(family => {
        const slot = document.createElement("div");
        slot.className = "category-carousel-placeholder";
        const familyName = (typeof family === "object" ? family.tool_family : family) || "";
        slot.dataset.family = familyName;
        container.insertBefore(slot, btnWrapper);
        slots.push({ family, slot });
    });

    const requests = slots.map(({ family, slot }) => {
        const familyName = (typeof family === "object" ? family.tool_family : family) || "";
        return Store.call("custom_webshop.api.catalog.get_items_by_tool_family", {
            tool_family: familyName,
            start: 0,
            page_length: 8,
        }).then(data => {
            if (gen !== tfGeneration) return;
            const items = (data && data.items) || [];
            if (items.length > 0) {
                const section = buildFamilyCarouselSection(family, items);
                if (slot.parentNode) {
                    slot.parentNode.replaceChild(section, slot);
                    if (window.lucide) lucide.createIcons({ nodes: [section] });
                    renderedFamilyCount++;
                }
            } else {
                // Successful response with no published items: skip and remove slot
                if (slot.parentNode) {
                    slot.parentNode.removeChild(slot);
                }
            }
        }).catch(() => {
            if (gen !== tfGeneration) return;
            // Network/server failure: preserve for retry and remove ghost slot
            if (slot.parentNode) {
                slot.parentNode.removeChild(slot);
            }
            failedFamilies.push(family);
        });
    });

    Promise.allSettled(requests).then(() => {
        if (gen !== tfGeneration) return;
        isLoadingTfBatch = false;
        updateViewMoreButton(container, gen);

        if (renderedFamilyCount === 0 && pendingFamilies.length === 0 && failedFamilies.length === 0) {
            container.innerHTML = `<p style="color:var(--text-muted);padding:16px;">${Store.lang === 'ar' ? 'لا توجد منتجات حالياً' : 'No tool families found.'}</p>`;
        }
    });
}

function loadNextToolFamilyBatch(container, gen) {
    if (isLoadingTfBatch || gen !== tfGeneration) return;
    if (pendingFamilies.length === 0 && failedFamilies.length === 0) return;

    isLoadingTfBatch = true;
    const btn = document.getElementById("view-more-families-btn");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="btn-spinner"></span> <span>${Store.t("loading")}</span>`;
    }

    const batch = [];
    while (batch.length < TOOL_FAMILY_BATCH_SIZE && failedFamilies.length > 0) {
        batch.push(failedFamilies.shift());
    }
    while (batch.length < TOOL_FAMILY_BATCH_SIZE && pendingFamilies.length > 0) {
        batch.push(pendingFamilies.shift());
    }

    processToolFamilyBatch(container, batch, gen);
}

/* Load tool-family carousels: one carousel per tool family (SEM, FEM, …) */
function loadToolFamilyCarousels() {
    const container = document.getElementById("home-category-carousels");
    if (!container) return;

    tfGeneration++;
    const currentGen = tfGeneration;
    pendingFamilies = [];
    failedFamilies = [];
    isLoadingTfBatch = false;
    renderedFamilyCount = 0;
    container.innerHTML = "";

    Store.call("custom_webshop.api.catalog.get_display_tool_families")
        .then(families => {
            if (currentGen !== tfGeneration) return;
            if (!families || !families.length) {
                container.innerHTML = `<p style="color:var(--text-muted);padding:16px;">${Store.lang === 'ar' ? 'لا توجد منتجات حالياً' : 'No tool families found.'}</p>`;
                return;
            }

            pendingFamilies = [...families];
            loadNextToolFamilyBatch(container, currentGen);
        })
        .catch(() => {
            if (currentGen !== tfGeneration) return;
            container.innerHTML = `<p style="color:var(--text-muted);padding:16px;">${Store.lang === 'ar' ? 'فشل تحميل عائلات الأدوات' : 'Failed to load tool families.'}</p>`;
        });
}

window.scrollCarousel = function(safeId, dir) {
    const track = document.getElementById(`carousel-track-${safeId}`);
    if (!track) return;
    const scrollAmount = dir * 320;
    track.scrollBy({ left: scrollAmount, behavior: "smooth" });
};

function renderTrendingGrid(products) {
    const grid = document.getElementById("home-trending-grid");
    if (!grid) return;
    const section = document.getElementById("home-trending-section");
    if (section) section.style.display = products.length ? "" : "none";
    const top = products.slice(0, 6);
    grid.innerHTML = top.map(p => buildProductCard(p, "TRENDING")).join("");
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
}

/* ── Load slides from server ─────────────────────────────────────────────── */
function loadSlides() {
    Store.call("custom_webshop.api.slides.get_slides")
        .then(data => {
            if (Array.isArray(data) && data.length) slides = data;
            else slides = null;
        })
        .catch(() => { slides = null; })
        .finally(() => {
            renderHeroSlides();
            startSlideshowRotation();
        });
}

/* ── Load products from ERPNext ──────────────────────────────────────────── */
// Trending = top items by qty sold on submitted Sales Invoices (ranked daily server-side)
function loadHomeProducts() {
    Store.call("custom_webshop.api.catalog.get_trending_products", {
        limit: 6
    }).then(data => {
        const products = (data && data.items) ? data.items : [];
        renderTrendingGrid(products);
    }).catch(err => {
        console.error("Failed to load products:", err);
    });
}


/* ── Admin check (show admin nav link if manager) ────────────────────────── */
function checkAdminAccess() {
    if (Store.isGuest) return;

    Store.call("custom_webshop.api.slides.is_slide_admin")
        .then(isAdmin => {
            if (!isAdmin) return;
            const adminLink = document.getElementById("nav-admin-link");
            if (adminLink) adminLink.style.display = "";
        })
        .catch(() => {});
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    // Initialize shared store (theme, lang, session, cart badge)
    Store.init();

    // Wire cart drawer
    Store.initCartDrawer(() => Store.renderCartDrawer({ loginRedirect: "/shop" }));

    // Animate navbar scroll
    Store.initNavbarScroll();

    // Hero canvas animation
    initToolpathCanvas();

    // Load slides from ERPNext (falls back to defaults)
    loadSlides();

    // Load trending products
    loadHomeProducts();
    // Load brands from dedicated API
    loadBrands();
    // Load tool-family-based carousels
    loadToolFamilyCarousels();

    // Check admin access after a tick
    setTimeout(checkAdminAccess, 500);

    // Wire hero container slideshow pause on hover
    const sliderContainer = document.getElementById("hero-slider-container");
    if (sliderContainer) {
        sliderContainer.addEventListener("mouseenter", stopSlideshowRotation);
        sliderContainer.addEventListener("mouseleave", startSlideshowRotation);
    }

    // Live re-render all dynamic home components on language toggle
    window.addEventListener("cnc_language_changed", () => {
        renderHeroSlides();
        loadBrands();
        loadToolFamilyCarousels();
        loadHomeProducts();
    });
});
