/* ==========================================================================
   CNCLeaders — Shop / Home Page Controller
   Handles: hero slider, brand grid, category carousels, trending products
   Depends on: store.js (Store, t)
   ========================================================================== */

/* ── Slide state ─────────────────────────────────────────────────────────── */
let slides = [];
let currentSlideIndex = 0;
let slideshowTimer = null;

/* ── Default fallback slides (used until server data loads) ──────────────── */
const DEFAULT_SLIDES = [
    {
        eyebrow: "PRECISION CNC ENGINEERING",
        title: "Industrial Components built for micro-tolerance performance",
        subtitle: "Direct distributor of high-torque spindle systems, premium linear rails, high-resolution stepper systems, and carbide tooling. ERPNext Synced.",
        link: "/catalog",
        image: "/assets/custom_webshop/images/cnc_spindle_motor.jpg"
    },
    {
        eyebrow: "MOTION CONTROL TELEMETRY",
        title: "Linear Motion Guides & Precision Ball Screws",
        subtitle: "H Class GCr15 carbon steel rails with heavy duty flanged blocks. Low axial backlash SFU actuators.",
        link: "/catalog?item_group=Linear+Guides",
        image: "/assets/custom_webshop/images/linear_guide_rail.jpg"
    },
    {
        eyebrow: "HARDENED ROTARY CUTTERS",
        title: "Solid Carbide Spiral End Mill Kits",
        subtitle: "AlTiN nano-blue coated 4-flute routing bits. Resists friction and high thermal loads up to 55 HRC.",
        link: "/catalog?item_group=Carbide+Tooling",
        image: "/assets/custom_webshop/images/carbide_end_mills.jpg"
    }
];

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

    function animate() {
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
        requestAnimationFrame(animate);
    }
    animate();
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

    const activeSlides = slides.length ? slides : DEFAULT_SLIDES;
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
                    <a href="${slide.link || "/catalog"}" class="btn btn-primary">Inspect Details</a>
                    <a href="/catalog" class="btn btn-secondary">Browse All Catalog</a>
                </div>
                <div class="gcode-scroll"></div>
            </div>`;
        wrapper.appendChild(slideDiv);

        const dot = document.createElement("button");
        dot.className = `slide-dot ${idx === currentSlideIndex ? "active" : ""}`;
        dot.addEventListener("click", () => goToSlide(idx));
        dotsContainer.appendChild(dot);
    });

    const activeSlide = wrapper.querySelector(".hero-slide.active");
    if (activeSlide) triggerTypewriterForSlide(activeSlide);
}

function goToSlide(index) {
    const activeSlides = slides.length ? slides : DEFAULT_SLIDES;
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
    const activeSlides = slides.length ? slides : DEFAULT_SLIDES;
    if (activeSlides.length <= 1) return;
    slideshowTimer = setInterval(() => goToSlide(currentSlideIndex + 1), 4000);
}

function stopSlideshowRotation() {
    if (slideshowTimer) { clearInterval(slideshowTimer); slideshowTimer = null; }
}

/* ── Product Card HTML Helper ────────────────────────────────────────────── */
function buildProductCard(item, badge = "STOCK") {
    const inStock = item.in_stock !== false;
    const badgeHTML = inStock
        ? `<span class="product-badge" style="background:var(--primary-blue);border-color:var(--primary-blue);">${badge}</span>`
        : `<span class="product-badge out-of-stock">DEPLETED</span>`;
    const price = Store.productPrice(item);
    const img = item.website_image || item.image || "/assets/custom_webshop/images/placeholder.jpg";
    const productHref = Store.productLink(item);
    const displayName = item.web_item_name || item.item_name || item.name || "";
    const brand = item.brand || "";
    const addBtn = inStock
        ? `<button class="card-add-btn" onclick="addToCartItem('${item.item_code || item.name}')" title="${Store.t("btn_add_to_cart")}"><i data-lucide="shopping-cart"></i></button>`
        : `<button class="card-add-btn disabled" disabled title="${Store.t("btn_out_of_stock")}"><i data-lucide="shopping-cart"></i></button>`;

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
                    ${brand ? `<div class="spec-line"><span>Brand:</span><span style="font-weight:700;">${brand}</span></div>` : ""}
                </div>
                <div class="product-bottom">
                    <span class="product-price">${price}</span>
                    ${addBtn}
                </div>
            </div>
        </div>`;
}

/* ── Add to cart (calls ERPNext update_cart override) ────────────────────── */
window.addToCartItem = function(itemCode) {
    if (Store.isGuest) {
        window.location.href = "/login?redirect-to=/shop";
        return;
    }
    Store.call("webshop.webshop.shopping_cart.cart.update_cart", {
        item_code: itemCode,
        qty: 1,
    }).then(() => {
        Store.toast(Store.t("toast_added_cart"), "success");
        Store.updateCartBadge();
    }).catch(err => {
        Store.toast(err.message || Store.t("error_generic"), "error");
    });
};

/* ── Home Page Sections ──────────────────────────────────────────────────── */

/* Load brands from dedicated API and render brand cards */
function loadBrands() {
    Store.call("custom_webshop.api.catalog.get_brands")
        .then(brands => {
            const brandGrid = document.getElementById("home-brand-grid");
            if (!brandGrid) return;
            if (!brands || !brands.length) {
                brandGrid.innerHTML = `<p style="color:var(--text-muted);padding:16px;">No brands found.</p>`;
                return;
            }
            brandGrid.innerHTML = brands.map(b => `
                <div class="brand-card" onclick="window.location.href='/catalog?brand=${encodeURIComponent(b.brand)}'">
                    <div class="brand-logo-text">
                        <span style="color:var(--primary-blue);font-family:var(--font-heading);font-weight:800;">[</span>
                        ${b.brand}
                        <span style="color:var(--primary-blue);font-family:var(--font-heading);font-weight:800;">]</span>
                    </div>
                    <div class="brand-logo-sub">Certified Partner</div>
                </div>`).join("");
        })
        .catch(() => {});
}

/* Load tool-family carousels: one carousel per tool family (SEM, FEM, …) */
function loadToolFamilyCarousels() {
    const container = document.getElementById("home-category-carousels");
    if (!container) return;

    Store.call("custom_webshop.api.catalog.get_display_tool_families")
        .then(families => {
            if (!families || !families.length) {
                container.innerHTML = `<p style="color:var(--text-muted);padding:16px;">No tool families found.</p>`;
                return;
            }

            container.innerHTML = "";

            const renderFamilyCarousel = (familyName, products) => {
                if (!products.length) return;
                const safeId = familyName.replace(/[^a-zA-Z0-9]/g, "-");
                const trackId = `carousel-track-${safeId}`;
                const section = document.createElement("div");
                section.className = "category-carousel-section";
                section.innerHTML = `
                    <div class="category-carousel-header">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <h3 class="carousel-title">${familyName}</h3>
                            <a href="/catalog?tool_family=${encodeURIComponent(familyName)}" class="carousel-view-all">View More →</a>
                        </div>
                        <div class="carousel-nav">
                            <button class="nav-btn-arrow" onclick="scrollCarousel('${safeId}',-1)"><i data-lucide="chevron-left"></i></button>
                            <button class="nav-btn-arrow" onclick="scrollCarousel('${safeId}',1)"><i data-lucide="chevron-right"></i></button>
                        </div>
                    </div>
                    <div class="category-carousel-track-wrapper">
                        <div class="category-carousel-track" id="${trackId}">
                            ${products.map(p => buildProductCard(p, "STOCK")).join("")}
                        </div>
                    </div>`;
                container.appendChild(section);
                if (window.lucide) lucide.createIcons({ nodes: [section] });
            };

            // Fetch products for each tool family in parallel (limited preview)
            const promises = families.map(f =>
                Store.call("custom_webshop.api.catalog.get_items_by_tool_family", {
                    tool_family: f.tool_family,
                    start: 0,
                    page_length: 8,
                }).then(data => ({ family: f.tool_family, products: (data && data.items) || [] }))
                  .catch(() => ({ family: f.tool_family, products: [] }))
            );

            Promise.all(promises).then(results => {
                results.forEach(r => renderFamilyCarousel(r.family, r.products));
            });
        })
        .catch(() => {});
}

window.scrollCarousel = function(safeId, dir) {
    const track = document.getElementById(`carousel-track-${safeId}`);
    if (!track) return;
    track.scrollBy({ left: dir * 300, behavior: "smooth" });
};

function renderTrendingGrid(products) {
    const grid = document.getElementById("home-trending-grid");
    if (!grid) return;
    const top = products.slice(0, 6);
    grid.innerHTML = top.map(p => buildProductCard(p, "TRENDING")).join("");
    if (window.lucide) lucide.createIcons({ nodes: [grid] });
}

/* ── Load slides from server ─────────────────────────────────────────────── */
function loadSlides() {
    Store.call("custom_webshop.api.slides.get_slides")
        .then(data => {
            if (Array.isArray(data) && data.length) slides = data;
            else slides = DEFAULT_SLIDES;
        })
        .catch(() => { slides = DEFAULT_SLIDES; })
        .finally(() => {
            renderHeroSlides();
            startSlideshowRotation();
        });
}

/* ── Load products from ERPNext ──────────────────────────────────────────── */
function loadHomeProducts() {
    Store.call("webshop.webshop.api.get_product_filter_data", {
        query_args: JSON.stringify({ field_filters: {}, start: 0 })
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
});
