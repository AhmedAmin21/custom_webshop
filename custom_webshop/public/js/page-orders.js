/* ==========================================================================
   CNCLeaders — Orders History Page Controller
   Depends on: store.js
   Data source: window.ORDERS_DATA (injected by orders.py Jinja context)
   ========================================================================== */

/* ── Status mapping ──────────────────────────────────────────────────────── */
function getStatusInfo(order) {
    const status = order.status || "";
    const docstatus = order.docstatus;

    if (docstatus === 0) {
        return { text: Store.t("order_status_draft"), cls: "status-pending", progress: "0%", step: 1 };
    }
    if (status === "To Deliver and Bill" || status === "To Bill") {
        return { text: "Processing", cls: "status-processing", progress: "33%", step: 2 };
    }
    if (status === "To Deliver") {
        return { text: "Shipped", cls: "status-shipped", progress: "66%", step: 3 };
    }
    if (status === "Completed") {
        return { text: "Delivered", cls: "status-delivered", progress: "100%", step: 4 };
    }
    if (status === "Cancelled") {
        return { text: "Cancelled", cls: "status-cancelled", progress: "0%", step: 0 };
    }
    return { text: status || "Processing", cls: "status-processing", progress: "10%", step: 2 };
}

/* ── Build order card HTML ───────────────────────────────────────────────── */
function buildOrderCard(order) {
    const statusInfo = getStatusInfo(order);
    const date = order.transaction_date
        ? new Date(order.transaction_date).toLocaleDateString(Store.lang === "ar" ? "ar-EG" : "en-US", { year: "numeric", month: "short", day: "numeric" })
        : "—";
    const total = order.grand_total_formatted || (parseFloat(order.grand_total || 0).toFixed(2));

    // Track step classes
    const stepClass = (n) => statusInfo.step >= n ? "completed" : (statusInfo.step === n - 1 ? "active" : "");

    const payBtn = order.docstatus === 0
        ? `<a href="/payment?order_id=${order.name}" class="btn btn-primary btn-sm" style="margin-top:8px;">${Store.t("order_pay_now")}</a>`
        : "";

    return `
        <div class="order-history-card">
            <div class="order-card-header">
                <div class="order-header-main">
                    <span class="order-id-badge">Order ID: #${order.name}</span>
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
                        <div class="step-node">
                            ${statusInfo.step >= 1 ? '<i data-lucide="check" style="width:14px;height:14px;"></i>' : "1"}
                        </div>
                        <span class="step-label">Order Placed</span>
                    </div>
                    <div class="track-step ${stepClass(2)}">
                        <div class="step-node">2</div>
                        <span class="step-label">ERP Sync</span>
                    </div>
                    <div class="track-step ${stepClass(3)}">
                        <div class="step-node">3</div>
                        <span class="step-label">Shipped</span>
                    </div>
                    <div class="track-step ${stepClass(4)}">
                        <div class="step-node">4</div>
                        <span class="step-label">Arrived</span>
                    </div>
                </div>

                <!-- View order detail toggle -->
                <button class="order-details-toggle" onclick="toggleOrderDetails(this)">
                    <span>Show Order Details</span>
                    <i data-lucide="chevron-down" style="width:16px;height:16px;"></i>
                </button>

                <div class="order-details-drawer">
                    <div class="details-product-list" id="order-items-${order.name}">
                        <p style="color:var(--text-muted);font-size:0.85rem;">Loading items...</p>
                    </div>
                    <div style="margin-top:12px;display:flex;gap:12px;flex-wrap:wrap;">
                        <a href="/orders/${order.name}" class="btn btn-secondary btn-sm">${Store.t("order_view")}</a>
                        ${order.docstatus === 0 ? `<a href="/payment?order_id=${order.name}" class="btn btn-primary btn-sm">${Store.t("order_pay_now")}</a>` : ""}
                    </div>
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
    btn.querySelector("span").textContent = isOpen ? "Hide Order Details" : "Show Order Details";
    if (icon) icon.style.transform = isOpen ? "rotate(180deg)" : "rotate(0deg)";

    // Load order items on first open
    const orderCard = btn.closest(".order-history-card");
    const orderName = orderCard?.querySelector(".order-id-badge")?.textContent?.replace("Order ID: #", "").trim();
    if (isOpen && orderName) loadOrderItems(orderName);
};

/* ── Load order line items from ERPNext ──────────────────────────────────── */
function loadOrderItems(orderName) {
    const itemsEl = document.getElementById(`order-items-${orderName}`);
    if (!itemsEl || itemsEl.dataset.loaded) return;

    Store.call("frappe.client.get", {
        doctype: "Sales Order",
        name: orderName,
        fields: ["name", "items", "grand_total", "taxes"],
    }).then(doc => {
        if (!doc || !doc.items || !doc.items.length) {
            itemsEl.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem;'>No items found.</p>";
            return;
        }
        itemsEl.innerHTML = doc.items.map(item => `
            <div class="details-prod-item">
                <span class="details-prod-name">${item.item_name || item.item_code}</span>
                <span class="details-prod-qty">x${item.qty}</span>
                <span class="details-prod-price">${parseFloat((item.qty || 1) * (item.rate || 0)).toFixed(2)}</span>
            </div>`).join("") + `
            <div class="details-prod-item" style="border-top:1px dashed var(--border-subtle);padding-top:8px;font-weight:bold;">
                <span>Grand Total</span>
                <span>${parseFloat(doc.grand_total || 0).toFixed(2)}</span>
            </div>`;
        itemsEl.dataset.loaded = "1";
    }).catch(() => {
        itemsEl.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem;'>Could not load items.</p>";
    });
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initCartDrawer(() => Store.renderCartDrawer({ loginRedirect: "/orders" }));
    renderOrdersList();
});
