/* ==========================================================================
   CNCLeaders — Payment Page Controller
   Depends on: store.js
   Uses: window.PAYMENT_DATA (injected by Jinja), confirm_payment API
   ========================================================================== */

let pendingReceiptFile = null;
let selectedPaymentMethod = null;

const IMAGE_EXTENSIONS = /\.(jpe?g|png|webp|heic|heif|gif|bmp)$/i;

function isImageFile(file) {
    if (!file) return false;
    if (file.type && file.type.startsWith("image/")) return true;
    // Mobile browsers often omit MIME type; fall back to extension
    return IMAGE_EXTENSIONS.test(file.name || "");
}

/* ── Payment method card selection ──────────────────────────────────────── */
window.selectPaymentMethodUI = function(methodKey) {
    selectedPaymentMethod = methodKey;

    document.querySelectorAll(".payment-method-card").forEach(card => {
        card.classList.toggle("active", card.dataset.method === methodKey);
    });

    // Show details box for the selected method
    const card = document.querySelector(`.payment-method-card[data-method="${methodKey}"]`);
    const detailsBox = document.getElementById("payment-details-box");
    if (!card || !detailsBox) return;

    const label = card.dataset.label || methodKey;
    const number = card.dataset.number || "—";

    detailsBox.innerHTML = `
        <div class="method-details-wrapper animate-fade-in">
            <div class="method-details-header">
                <span class="details-title">${label} Details</span>
                <span class="details-note">Transfer the exact amount shown above.</span>
            </div>
            <div class="details-row">
                <div class="details-item">
                    <span class="details-lbl">Send to</span>
                    <div class="details-val-copy-container">
                        <span class="details-val highlight-val">${number}</span>
                        <button class="copy-btn" onclick="navigator.clipboard.writeText('${number}').then(() => Store.toast('Copied!', 'success'))" title="Copy">
                            <i data-lucide="copy" class="small-copy-icon"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>`;

    if (window.lucide) lucide.createIcons({ nodes: [detailsBox] });
};

function setUploadPreviewVisible(visible) {
    const fileInput = document.getElementById("payment-file-input");
    const trigger = document.getElementById("upload-zone-trigger");
    const previewArea = document.getElementById("upload-preview-area");
    // When preview is showing, hide the transparent input so remove-button is clickable
    if (fileInput) fileInput.style.display = visible ? "none" : "block";
    if (trigger) trigger.style.display = visible ? "none" : "block";
    if (previewArea) previewArea.style.display = visible ? "flex" : "none";
}

function resetReceiptUpload() {
    pendingReceiptFile = null;
    const fileInput = document.getElementById("payment-file-input");
    if (fileInput) fileInput.value = "";
    setUploadPreviewVisible(false);

    const submitBtn = document.getElementById("submit-payment-btn");
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.style.opacity = "0.5";
        submitBtn.style.cursor = "not-allowed";
    }
}

/* ── File upload handling ────────────────────────────────────────────────── */
function initPaymentUpload() {
    const dropZone = document.getElementById("payment-drop-zone");
    const fileInput = document.getElementById("payment-file-input");
    const submitBtn = document.getElementById("submit-payment-btn");

    if (!dropZone || !fileInput) return;

    // Drag and drop (desktop)
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file) handleUploadedFile(file);
    });

    // Native file picker — label opens input; no programmatic .click()
    fileInput.addEventListener("change", (e) => {
        const file = e.target.files && e.target.files[0];
        if (file) handleUploadedFile(file);
    });

    const removeBtn = document.getElementById("remove-receipt-btn");
    if (removeBtn) {
        removeBtn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            resetReceiptUpload();
        });
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.style.opacity = "0.5";
        submitBtn.style.cursor = "not-allowed";
    }
}

function handleUploadedFile(file) {
    if (!isImageFile(file)) {
        Store.toast("Please upload an image file (JPG, PNG).", "error");
        const fileInput = document.getElementById("payment-file-input");
        if (fileInput) fileInput.value = "";
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        Store.toast("File size exceeds 5MB limit.", "error");
        const fileInput = document.getElementById("payment-file-input");
        if (fileInput) fileInput.value = "";
        return;
    }

    pendingReceiptFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        const preview = document.getElementById("receipt-preview-img");
        const fileName = document.getElementById("receipt-file-name");
        if (preview) preview.src = e.target.result;
        if (fileName) fileName.textContent = file.name;
        setUploadPreviewVisible(true);
        if (window.lucide) lucide.createIcons();
    };
    reader.onerror = () => {
        Store.toast("Could not read the selected image. Please try again.", "error");
        resetReceiptUpload();
    };
    reader.readAsDataURL(file);

    const submitBtn = document.getElementById("submit-payment-btn");
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.style.opacity = "1";
        submitBtn.style.cursor = "pointer";
    }
}

/* ── Submit payment proof ────────────────────────────────────────────────── */
function initSubmitButton() {
    const submitBtn = document.getElementById("submit-payment-btn");
    if (!submitBtn) return;

    submitBtn.addEventListener("click", () => {
        const payData = window.PAYMENT_DATA;
        if (!payData || !payData.order_id) {
            Store.toast("No order found.", "error");
            return;
        }
        if (!selectedPaymentMethod) {
            Store.toast("Please select a payment method.", "error");
            return;
        }
        if (!pendingReceiptFile) {
            Store.toast("Please upload your payment receipt.", "error");
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = Store.t("loading");

        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result.split(",")[1];

            Store.call("custom_webshop.api.payment.confirm_payment", {
                order_id: payData.order_id,
                payment_method: selectedPaymentMethod,
                filename: pendingReceiptFile.name,
                file_content: base64,
            }).then(() => {
                Store.toast("Payment confirmed! Order submitted.", "success");
                setTimeout(() => { window.location.href = "/orders"; }, 1500);
            }).catch(err => {
                const msg = err.message || Store.t("error_generic");
                Store.toast(msg, "error");
                submitBtn.disabled = false;
                submitBtn.textContent = Store.t("payment_submit");
            });
        };
        reader.onerror = () => {
            Store.toast("Could not read the selected image. Please try again.", "error");
            submitBtn.disabled = false;
            submitBtn.textContent = Store.t("payment_submit");
        };
        reader.readAsDataURL(pendingReceiptFile);
    });
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();

    const firstCard = document.querySelector(".payment-method-card");
    if (firstCard) {
        selectedPaymentMethod = firstCard.dataset.method;
        selectPaymentMethodUI(selectedPaymentMethod);
    }

    initPaymentUpload();
    initSubmitButton();

    if (!window.PAYMENT_DATA) return;

    const amountEl = document.getElementById("payment-amount");
    if (amountEl && window.PAYMENT_DATA.grand_total_formatted) {
        amountEl.textContent = window.PAYMENT_DATA.grand_total_formatted;
    }
});
