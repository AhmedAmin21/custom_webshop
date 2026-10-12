/* ==========================================================================
   CNCLeaders — Orders History Page Controller
   Depends on: store.js
   Data source: window.ORDERS_DATA (injected by orders.py Jinja context)
   ========================================================================== */

/* ── Status mapping ──────────────────────────────────────────────────────── */
function getStatusInfo(order) {
    const status = order.status || "";
    const docstatus = order.docstatus;
    const isAr = Store.lang === "ar";

    if (docstatus === 2 || status === "Cancelled") {
        return { text: isAr ? "ملغي" : "Cancelled", cls: "status-cancelled", progress: "0%", step: 0 };
    }
    if (status === "Ordered" || status === "Completed") {
        return { text: isAr ? "طلب مؤكد" : "Order Confirmed", cls: "status-delivered", progress: "100%", step: 4 };
    }
    if (order.has_payment_receipt || !order.requires_payment) {
        return {
            text: isAr ? "قيد المراجعة / اتصال خدمة العملاء" : "Under Review / Agent Contact",
            cls: "status-processing",
            progress: "50%",
            step: 2
        };
    }
    if (order.requires_payment && !order.has_payment_receipt) {
        return {
            text: isAr ? "بانتظار سداد المبلغ" : "Pending Payment",
            cls: "status-pending",
            progress: "25%",
            step: 1
        };
    }
    return { text: isAr ? "قيد المراجعة" : "Under Review", cls: "status-processing", progress: "50%", step: 2 };
}

/* ── Build order card HTML ───────────────────────────────────────────────── */
function buildOrderCard(order) {
    const statusInfo = getStatusInfo(order);
    const isAr = Store.lang === "ar";
    const date = order.transaction_date
        ? new Date(order.transaction_date).toLocaleDateString(isAr ? "ar-EG" : "en-US", { year: "numeric", month: "short", day: "numeric" })
        : "—";
    const total = Store.formatCurrency(order.grand_total, order.currency || "EGP");

    // Track step classes and node icons
    const stepClass = (n) => statusInfo.step >= n ? "completed" : (statusInfo.step === n - 1 ? "active" : "");
    const stepNodeIcon = (n) => {
        if (statusInfo.step >= n) {
            return '<i data-lucide="check" style="width:14px;height:14px;"></i>';
        }
        return `${n}`;
    };

    const needsPayment = Boolean(order.requires_payment && !order.has_payment_receipt && order.docstatus !== 2 && order.status !== "Cancelled");
    const payBtn = needsPayment
        ? `<a href="/payment?order_id=${order.name}" class="btn btn-primary btn-sm" style="margin-top:8px;">${Store.t("order_pay_now")}</a>`
        : `<span style="font-size:0.85rem;color:var(--primary-blue,#2563EB);font-weight:600;display:inline-block;margin-top:8px;">${isAr ? "سيقوم فريق الدعم بالتواصل معك" : "Support team will contact you"}</span>`;

    const step1Label = isAr ? "تم إرسال الطلب" : "Quotation Placed";
    const step2Label = isAr ? "مراجعة الدعم" : "Agent Review";
    const step3Label = isAr ? "تأكيد الطلب" : "Order Confirmed";
    const step4Label = isAr ? "التجهيز والتسليم" : "Processing / Dispatched";

    return `
        <div class="order-history-card">
            <div class="order-card-header">
                <div class="order-header-main">
                    <span class="order-id-badge">${isAr ? "رقم الطلب" : "Quotation"}: #${order.name}</span>
                    <span class="order-date-text">${Store.t("order_date")}: ${date}</span>
                </div>
                <div class="order-status-flex">
                    <span class="order-status-pill ${statusInfo.cls}">${statusInfo.text}</span>
                </div>
            </div>

            <div class="order-card-body">
                <div class="order-meta-info-grid">
                    <div class="meta-field">
                        <span class="meta-lbl">${Store.t("order_total")}</span>
                        <span class="meta-val" style="color:var(--primary-blue);font-size:1.15rem;">${total}</span>
                    </div>
                    <div class="meta-field" style="text-align:right;">
                        ${payBtn}
                    </div>
                </div>

                <!-- Progress tracker -->
                <div class="tracking-flow">
                    <div class="tracking-progress-bar" style="width:${statusInfo.progress};"></div>
                    <div class="track-step ${stepClass(1)}">
                        <div class="step-node">${stepNodeIcon(1)}</div>
                        <span class="step-label">${step1Label}</span>
                    </div>
                    <div class="track-step ${stepClass(2)}">
                        <div class="step-node">${stepNodeIcon(2)}</div>
                        <span class="step-label">${step2Label}</span>
                    </div>
                    <div class="track-step ${stepClass(3)}">
                        <div class="step-node">${stepNodeIcon(3)}</div>
                        <span class="step-label">${step3Label}</span>
                    </div>
                    <div class="track-step ${stepClass(4)}">
                        <div class="step-node">${stepNodeIcon(4)}</div>
                        <span class="step-label">${step4Label}</span>
                    </div>
                </div>

                <!-- View order detail toggle -->
                <button class="order-details-toggle" data-order-name="${order.name}" onclick="toggleOrderDetails(this)">
                    <span>${Store.t("order_show_details")}</span>
                    <i data-lucide="chevron-down" style="width:16px;height:16px;"></i>
                </button>

                <div class="order-details-drawer">
                    <div class="details-product-list" id="order-items-${order.name}">
                        <p style="color:var(--text-muted);font-size:0.85rem;">${Store.t("order_loading_items")}</p>
                    </div>
                        ${needsPayment ? `
                        <div style="margin-top:12px;display:flex;gap:12px;flex-wrap:wrap;">
                            <a href="/payment?order_id=${order.name}" class="btn btn-primary btn-sm">${Store.t("order_pay_now")}</a>
                        </div>` : ""}
                </div>
            </div>
        </div>`;
}

/* ── Render all orders ───────────────────────────────────────────────────── */
function renderOrdersList() {
    const container = document.getElementById("orders-history-list");
    if (!container) return;

    const orders = window.ORDERS_DATA || [];

    if (!orders.length) {
        container.innerHTML = `
            <div class="drawer-empty-text" style="padding:64px 0;text-align:center;">
                <i data-lucide="package" style="width:48px;height:48px;margin-bottom:16px;opacity:0.2;"></i>
                <p>${Store.t("orders_empty")}</p>
                <a href="/catalog" class="btn btn-secondary btn-sm" style="margin-top:16px;">${Store.t("nav_catalog")}</a>
            </div>`;
        if (window.lucide) lucide.createIcons({ nodes: [container] });
        return;
    }

    container.innerHTML = orders.map(o => buildOrderCard(o)).join("");
    if (window.lucide) lucide.createIcons({ nodes: [container] });
}

/* ── Toggle order details drawer ─────────────────────────────────────────── */
window.toggleOrderDetails = function(btn) {
    const drawer = btn.nextElementSibling;
    const icon = btn.querySelector("[data-lucide]");
    const isOpen = drawer.classList.toggle("open");
    btn.querySelector("span").textContent = isOpen ? Store.t("order_hide_details") : Store.t("order_show_details");
    if (icon) icon.style.transform = isOpen ? "rotate(180deg)" : "rotate(0deg)";

    // Load order items on first open
    const orderName = btn.dataset.orderName || btn.closest(".order-history-card")?.querySelector(".order-id-badge")?.textContent?.split("#")[1]?.trim();
    if (isOpen && orderName) loadOrderItems(orderName);
};

/* ── Render order line items HTML helper ─────────────────────────────────── */
function renderOrderItemsContent(itemsEl, items, grandTotal, currency) {
    if (!items || !items.length) {
        itemsEl.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">${Store.t("order_no_items")}</p>`;
        return;
    }
    const curr = currency || "EGP";
    itemsEl.innerHTML = items.map(item => `
        <div class="details-prod-item">
            <span class="details-prod-name">${item.item_name || item.item_code}</span>
            <span class="details-prod-qty">x${item.qty}</span>
            <span class="details-prod-price">${Store.formatCurrency((item.qty || 1) * (item.rate || 0), curr)}</span>
        </div>`).join("") + `
        <div class="details-prod-item" style="border-top:1px dashed var(--border-subtle);padding-top:8px;font-weight:bold;">
            <span>${Store.t("order_grand_total")}</span>
            <span>${Store.formatCurrency(grandTotal, curr)}</span>
        </div>`;
    itemsEl.dataset.loaded = "1";
}

/* ── Load order line items ──────────────────────────────────────────────── */
function loadOrderItems(orderName) {
    const itemsEl = document.getElementById(`order-items-${orderName}`);
    if (!itemsEl || itemsEl.dataset.loaded) return;

    // 1. Check if items were already preloaded in window.ORDERS_DATA
    const cachedOrder = (window.ORDERS_DATA || []).find(o => o.name === orderName);
    if (cachedOrder && cachedOrder.items && cachedOrder.items.length) {
        renderOrderItemsContent(itemsEl, cachedOrder.items, cachedOrder.grand_total, cachedOrder.currency);
        return;
    }

    // 2. Fallback to dedicated secure endpoint
    Store.call("custom_webshop.api.orders.get_order_items", {
        order_name: orderName,
    }).then(res => {
        const data = res?.message || res;
        if (!data || !data.items || !data.items.length) {
            itemsEl.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">${Store.t("order_no_items")}</p>`;
            return;
        }
        renderOrderItemsContent(itemsEl, data.items, data.grand_total, data.currency);
    }).catch(() => {
        itemsEl.innerHTML = `<p style="color:var(--text-muted);font-size:0.85rem;">${Store.t("order_error_items")}</p>`;
    });
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initCartDrawer(() => Store.renderCartDrawer({ loginRedirect: "/orders" }));
    renderOrdersList();

    // Re-render dynamically when language changes
    window.addEventListener("cnc_language_changed", () => {
        renderOrdersList();
    });
});

