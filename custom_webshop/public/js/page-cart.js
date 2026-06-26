/* ==========================================================================
   CNCLeaders — Cart Page Controller
   Depends on: store.js
   Uses: get_cart_quotation, update_cart, get_governorate_shipping_rules,
         place_order_from_cart, add_customer_info, update_cart_address
   ========================================================================== */

let cartQuotation = null;
let cartBootstrap = window.CART_BOOTSTRAP || {};
let shippingControlsBound = false;

function getBootstrap() {
    return cartBootstrap && typeof cartBootstrap === "object" ? cartBootstrap : {};
}

/* ── Render live cart from ERPNext quotation ─────────────────────────────── */
function loadAndRenderCart() {
    const cartList = document.getElementById("cart-page-list");
    if (cartList) cartList.innerHTML = `<div style="padding:48px;text-align:center;color:var(--text-muted);">${Store.t("loading")}</div>`;

    Store.call("webshop.webshop.shopping_cart.cart.get_cart_quotation")
        .then(data => {
            cartQuotation = data && data.doc ? data.doc : null;
            renderCartItems(cartQuotation);
            refreshCartWeight();
            updateCartSummary(cartQuotation);
        })
        .catch(err => {
            if (cartList) cartList.innerHTML = `<div style="padding:48px;text-align:center;color:var(--text-muted);">${Store.t("error_generic")}</div>`;
            console.error("Cart load failed:", err);
        });
}

/* ── Render cart item rows ───────────────────────────────────────────────── */
function renderCartItems(doc) {
    const cartList = document.getElementById("cart-page-list");
    if (!cartList) return;

    const items = (doc && doc.items) ? doc.items : [];

    if (!items.length) {
        cartList.innerHTML = `
            <div class="drawer-empty-text" style="padding:48px 0;text-align:center;">
                <i data-lucide="shopping-cart" style="width:48px;height:48px;margin-bottom:16px;opacity:0.2;"></i>
                <p>${Store.t("cart_empty")}</p>
                <a href="/catalog" class="btn btn-secondary btn-sm" style="margin-top:16px;">${Store.t("cart_goto_shop")}</a>
            </div>`;
        if (window.lucide) lucide.createIcons({ nodes: [cartList] });
        return;
    }

    cartList.innerHTML = items.map(item => {
        const lineTotal = (item.qty || 1) * (item.rate || 0);
        const img = item.image || "/assets/custom_webshop/images/placeholder.jpg";
        return `
            <div class="cart-item">
                <img src="${img}" alt="${item.item_name || item.item_code}" class="cart-item-img">
                <div class="cart-item-info">
                    <a href="/product?item=${encodeURIComponent(item.item_code)}" class="cart-item-title">${item.item_name || item.item_code}</a>
                    <div class="cart-item-cat">Item Code: ${item.item_code} | Unit: ${parseFloat(item.rate || 0).toFixed(2)}</div>
                </div>
                <div class="qty-spinner" style="margin-right:16px;">
                    <button class="qty-btn" onclick="updateCartQty('${item.item_code}', ${(item.qty||1) - 1})">−</button>
                    <input type="text" value="${item.qty || 1}" class="qty-val" readonly>
                    <button class="qty-btn" onclick="updateCartQty('${item.item_code}', ${(item.qty||1) + 1})">+</button>
                </div>
                <div class="cart-item-price" style="min-width:90px;text-align:right;">${parseFloat(lineTotal).toFixed(2)}</div>
                <button class="cart-item-remove-btn" onclick="updateCartQty('${item.item_code}', 0)" title="${Store.t("btn_remove")}">
                    <i data-lucide="trash-2"></i>
                </button>
            </div>`;
    }).join("");

    if (window.lucide) lucide.createIcons({ nodes: [cartList] });
}

function formatWeight(weight, uom) {
    const w = parseFloat(weight || 0);
    if (!w) return "0";
    const unit = (uom || "").trim();
    return unit ? `${w} ${unit}` : String(w);
}

function refreshCartWeight() {
    const weightEl = document.getElementById("cart-total-weight");
    if (!weightEl) return;

    const bootstrap = getBootstrap();
    if (bootstrap.total_weight != null) {
        weightEl.textContent = formatWeight(bootstrap.total_weight, bootstrap.weight_uom);
    }

    Store.call("custom_webshop.shopping_cart.shipping_api.get_cart_total_weight")
        .then(info => {
            if (!info) return;
            cartBootstrap = { ...cartBootstrap, total_weight: info.total_weight, weight_uom: info.weight_uom };
            weightEl.textContent = formatWeight(info.total_weight, info.weight_uom);
        })
        .catch(() => {});
}

function getShippingAmount(doc) {
    if (!doc) return 0;

    if (doc.custom_manual_shipping_amount != null && parseFloat(doc.custom_manual_shipping_amount) > 0) {
        return parseFloat(doc.custom_manual_shipping_amount);
    }

    const taxAmount = (tax) => parseFloat(tax.tax_amount || tax.base_tax_amount || 0);

    if (doc.taxes && doc.taxes.length) {
        // Governorate shipping adds a tax row named after the shipping rule (e.g. "jet express")
        if (doc.shipping_rule) {
            const ruleTax = doc.taxes.find(
                (tax) => (tax.description || "") === doc.shipping_rule
            );
            if (ruleTax) return taxAmount(ruleTax);
        }

        let shipping = 0;
        doc.taxes.forEach((tax) => {
            if ((tax.description || "").toLowerCase().includes("shipping")) {
                shipping += taxAmount(tax);
            }
        });
        if (shipping > 0) return shipping;
    }

    // Fallback: shipping is included in grand total but tax row name didn't match
    if (doc.shipping_rule) {
        const netTotal = parseFloat(doc.net_total != null ? doc.net_total : doc.total || 0);
        const grandTotal = parseFloat(doc.grand_total || 0);
        if (grandTotal > netTotal) return grandTotal - netTotal;
    }

    return 0;
}

/* ── Cart summary totals ─────────────────────────────────────────────────── */
function updateCartSummary(doc) {
    const subtotalEl = document.getElementById("cart-subtotal");
    const shippingEl = document.getElementById("cart-shipping");
    const grandtotalEl = document.getElementById("cart-grandtotal");

    if (!doc) {
        if (subtotalEl) subtotalEl.textContent = "—";
        if (shippingEl) shippingEl.textContent = "—";
        if (grandtotalEl) grandtotalEl.textContent = "—";
        return;
    }

    const subtotal = parseFloat(doc.net_total != null ? doc.net_total : doc.total || 0);
    const shipping = getShippingAmount(doc);
    const grandTotal = parseFloat(doc.grand_total != null ? doc.grand_total : subtotal + shipping);

    if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
    if (shippingEl) shippingEl.textContent = shipping.toFixed(2);
    if (grandtotalEl) grandtotalEl.textContent = grandTotal.toFixed(2);
}

/* ── Update cart item quantity ───────────────────────────────────────────── */
window.updateCartQty = function(itemCode, qty) {
    Store.call("webshop.webshop.shopping_cart.cart.update_cart", {
        item_code: itemCode,
        qty: Math.max(0, qty),
    }).then(() => {
        Store.updateCartBadge();
        loadAndRenderCart();
        if (qty === 0) Store.toast(Store.t("toast_removed_cart"), "info");
    }).catch(err => Store.toast(err.message || Store.t("error_generic"), "error"));
};

/* ── Shipping company + governorate controls ───────────────────────────────── */
function loadShippingControls() {
    const companySelect = document.getElementById("shipping-company");
    const destSelect = document.getElementById("shipping-dest");
    if (!companySelect || !destSelect) return;

    const bootstrap = getBootstrap();

    Promise.all([
        Store.call("custom_webshop.shopping_cart.shipping_api.get_governorate_shipping_rules"),
        Store.call("custom_webshop.shopping_cart.shipping_api.get_governorates"),
    ]).then(([rules, govs]) => {
        const hasRules = rules && rules.length;
        const hasGovs = govs && govs.length;

        // Shipping company select — populate independently of governorates
        if (hasRules) {
            companySelect.innerHTML = `<option value="">${Store.t("shipping_company_select")}</option>`;
            rules.forEach(rule => {
                const opt = document.createElement("option");
                opt.value = rule[0];
                opt.textContent = rule[1];
                companySelect.appendChild(opt);
            });
            if (bootstrap.shipping_rule) companySelect.value = bootstrap.shipping_rule;
        } else {
            const companyGroup = document.getElementById("shipping-company-group");
            if (companyGroup) companyGroup.style.display = "none";
        }

        // Governorate select
        if (hasGovs) {
            destSelect.innerHTML = `<option value="">${Store.t("shipping_select")}</option>`;
            govs.forEach(gov => {
                const opt = document.createElement("option");
                opt.value = gov.name;
                opt.textContent = gov.governorate_name || gov.name;
                destSelect.appendChild(opt);
            });
            if (bootstrap.shipping_destination) destSelect.value = bootstrap.shipping_destination;
        } else {
            const destGroup = document.getElementById("shipping-dest-group");
            if (destGroup) destGroup.style.display = "none";
        }

        if (!shippingControlsBound) {
            companySelect.addEventListener("change", onShippingChange);
            destSelect.addEventListener("change", onShippingChange);
            shippingControlsBound = true;
        }
    }).catch(() => {
        const companyGroup = document.getElementById("shipping-company-group");
        const destGroup = document.getElementById("shipping-dest-group");
        if (companyGroup) companyGroup.style.display = "none";
        if (destGroup) destGroup.style.display = "none";
    });
}

function onShippingChange() {
    const companySelect = document.getElementById("shipping-company");
    const destSelect = document.getElementById("shipping-dest");
    if (!companySelect || !destSelect) return;

    const shippingRule = companySelect.value;
    const shippingDestination = destSelect.value;

    if (!shippingRule || !shippingDestination) return;

    Store.call("custom_webshop.shopping_cart.shipping_api.update_cart_shipping", {
        shipping_rule: shippingRule,
        shipping_destination: shippingDestination,
    }).then(data => {
        cartQuotation = data && data.doc ? data.doc : cartQuotation;
        cartBootstrap = {
            ...getBootstrap(),
            shipping_rule: shippingRule,
            shipping_destination: shippingDestination,
        };
        renderCartItems(cartQuotation);
        refreshCartWeight();
        updateCartSummary(cartQuotation);
    }).catch(err => {
        console.warn("Shipping update:", err);
        loadAndRenderCart();
    });
}

/* ── Prefill delivery form from server bootstrap ─────────────────────────── */
function prefillDeliveryForm() {
    const bootstrap = getBootstrap();
    const nameEl = document.getElementById("cust-name");
    const phoneEl = document.getElementById("cust-phone");
    const addressEl = document.getElementById("cust-address");

    if (nameEl && bootstrap.user_fullname) nameEl.value = bootstrap.user_fullname;
    if (phoneEl && bootstrap.mobile_no) phoneEl.value = bootstrap.mobile_no;

    if (addressEl) {
        const parts = [bootstrap.address_line1, bootstrap.city].filter(Boolean);
        if (parts.length) addressEl.value = parts.join(", ");
    }
}

function getDeliveryFormData() {
    const companySelect = document.getElementById("shipping-company");
    const destSelect = document.getElementById("shipping-dest");
    const nameEl = document.getElementById("cust-name");
    const phoneEl = document.getElementById("cust-phone");
    const addressEl = document.getElementById("cust-address");
    const bootstrap = getBootstrap();

    const governorateName = destSelect && destSelect.selectedIndex > 0
        ? destSelect.options[destSelect.selectedIndex].textContent.trim()
        : "";

    return {
        shipping_rule: companySelect ? companySelect.value : "",
        shipping_destination: destSelect ? destSelect.value : "",
        first_name: (nameEl && nameEl.value.trim()) || bootstrap.user_fullname || "",
        mobile_no: (phoneEl && phoneEl.value.trim()) || "",
        address_line1: (addressEl && addressEl.value.trim()) || "",
        city: governorateName || bootstrap.city || "",
        country: bootstrap.country || "Egypt",
        address_name: bootstrap.address_name || null,
        contact_name: bootstrap.contact_name || null,
    };
}

function saveCustomerInfo(formData) {
    const address_data = {
        address_line1: formData.address_line1,
        city: formData.city,
        country: formData.country,
    };
    const contact_data = {
        first_name: formData.first_name,
        mobile_no: formData.mobile_no,
    };

    if (formData.address_name && formData.contact_name) {
        return Store.call("custom_webshop.shopping_cart.cart_override.update_customer_info", {
            address_name: formData.address_name,
            address_data: JSON.stringify(address_data),
            contact_name: formData.contact_name,
            contact_data: JSON.stringify(contact_data),
        });
    }

    return Store.call("custom_webshop.shopping_cart.cart_override.add_customer_info", {
        address_data: JSON.stringify(address_data),
        contact_data: JSON.stringify(contact_data),
    });
}

/* ── Place Order ─────────────────────────────────────────────────────────── */
function placeOrder(e) {
    e.preventDefault();

    const btn = document.getElementById("place-order-btn");
    const formData = getDeliveryFormData();

    if (!formData.shipping_rule || !formData.shipping_destination) {
        Store.toast(Store.t("cart_shipping_required"), "error");
        return;
    }
    if (!formData.first_name || !formData.mobile_no || !formData.address_line1) {
        Store.toast(Store.t("cart_delivery_required"), "error");
        return;
    }

    if (btn) { btn.disabled = true; btn.textContent = Store.t("loading"); }

    saveCustomerInfo(formData)
        .then(addressName => {
            return Store.call("webshop.webshop.shopping_cart.cart.update_cart_address", {
                address_type: "Shipping",
                address_name: addressName,
            });
        })
        .then(() => Store.call("custom_webshop.shopping_cart.cart_override.place_order_from_cart"))
        .then(orderName => {
            Store.toast("Order placed! Redirecting to payment...", "success");
            Store.updateCartBadge();
            setTimeout(() => {
                window.location.href = `/payment?order_id=${orderName}`;
            }, 1000);
        })
        .catch(err => {
            const msg = err.message || Store.t("error_generic");
            Store.toast(msg, "error");
            if (btn) { btn.disabled = false; btn.textContent = Store.t("cart_proceed"); }
        });
}

/* ── Cart drawer for mini view ───────────────────────────────────────────── */
function renderCartPageDrawer() {
    Store.renderCartDrawer({
        customMessage: `<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:0.9rem;">You're already on the cart page.</div>`,
    });
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initCartDrawer(renderCartPageDrawer);

    prefillDeliveryForm();
    loadAndRenderCart();
    loadShippingControls();

    const form = document.getElementById("checkout-delivery-form");
    if (form) form.addEventListener("submit", placeOrder);
});
