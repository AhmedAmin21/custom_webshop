/* ==========================================================================
   CNCLeaders — Login / Signup Page Controller
   Matches original frontend auth design (auth-wrapper / auth-card)
   Depends on: store.js
   ========================================================================== */

let currentPanel = "login";

/* ── Resolve post-login redirect ─────────────────────────────────────────── */
function resolveRedirect(data) {
    if (data && data.redirect_to) return data.redirect_to;
    const urlParam = new URLSearchParams(window.location.search).get("redirect-to");
    if (urlParam) return urlParam;
    const ctx = window.LOGIN_CONTEXT || {};
    if (ctx.redirect_to && ctx.redirect_to.trim()) return ctx.redirect_to.trim();
    // Website Users get home_page="/app" from Frappe — never send customers to desk
    const home = data && data.home_page;
    if (home && !home.startsWith("/app")) return home;
    return "/shop";
}

/* ── Tab / view switcher ─────────────────────────────────────────────────── */
window.switchTab = function (panel) {
    currentPanel = panel;
    clearStatus();

    const views = { login: "login-view", signup: "signup-view", forgot: "forgot-view" };
    let found = false;
    Object.entries(views).forEach(([key, id]) => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.toggle("active", key === panel);
            if (key === panel) found = true;
        }
    });

    // #region agent log
    Store.debugLog("page-login.js:switchTab", "tab switched", { panel, found }, "H3");
    // #endregion

    if (history.replaceState) {
        history.replaceState(null, "", `#${panel}`);
    } else {
        window.location.hash = panel;
    }
    if (window.lucide) lucide.createIcons();
};

function applyHashRoute() {
    const hash = window.location.hash.replace("#", "") || "login";
    if (["login", "signup", "forgot"].includes(hash)) switchTab(hash);
}

/* ── Status helpers ──────────────────────────────────────────────────────── */
function showStatus(message, type = "error") {
    ["auth-status", "auth-status-signup"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = message;
            el.className = `auth-status ${type}`;
        }
    });
    if (message && type === "error") Store.toast(message, "error");
    if (message && type === "success") Store.toast(message, "success");
}

function clearStatus() {
    ["auth-status", "auth-status-signup"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = "";
            el.className = "auth-status";
        }
    });
}

function setButtonLoading(btnId, loading, loadingKey, defaultKey, iconName = "arrow-right") {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    if (loading) {
        const text = Store.t(loadingKey) || "Loading...";
        btn.innerHTML = `<span class="auth-btn-spinner"></span><span>${Store.escapeHtml(text)}</span>`;
    } else {
        const text = Store.t(defaultKey) || "Submit";
        btn.innerHTML = `<span data-i18n="${defaultKey}">${Store.escapeHtml(text)}</span><i data-lucide="${iconName}"></i>`;
        if (window.lucide) lucide.createIcons({ nodes: [btn] });
    }
}

/* ── LOGIN ───────────────────────────────────────────────────────────────── */
function handleLogin(e) {
    e.preventDefault();
    clearStatus();

    const email = (document.getElementById("login-email")?.value || "").trim();
    const pwd = document.getElementById("login-password")?.value || "";

    if (!email) { showStatus("Please enter your email address.", "error"); return; }
    if (!pwd) { showStatus("Please enter your password.", "error"); return; }

    setButtonLoading("login-submit-btn", true, "auth_login_btn_loading", "auth_login_btn", "arrow-right");

    const body = new URLSearchParams();
    body.set("cmd", "login");
    body.set("usr", email);
    body.set("pwd", pwd);
    body.set("device", "desktop");

    fetch("/api/method/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Frappe-CSRF-Token": (window.LOGIN_CONTEXT || {}).csrf_token || "",
            "Accept": "application/json",
        },
        body: body.toString(),
    })
    .then(res => res.json())
    .then(data => {
        const msg = data && data.message;
        // "Logged In" = System User success
        // "No App"    = Website User (Customer) success — NOT an error
        if (msg === "Logged In" || msg === "No App") {
            const target = resolveRedirect(data);
            showStatus("Logged in! Redirecting…", "success");
            window.location.assign(target);
        } else if (data && data.exc) {
            showStatus(data.exc_type || data.message || "Invalid credentials.", "error");
            setButtonLoading("login-submit-btn", false, "auth_login_btn_loading", "auth_login_btn", "arrow-right");
        } else {
            showStatus(String(msg) || "Invalid credentials. Please try again.", "error");
            setButtonLoading("login-submit-btn", false, "auth_login_btn_loading", "auth_login_btn", "arrow-right");
        }
    })
    .catch(() => {
        showStatus("Connection error. Please try again.", "error");
        setButtonLoading("login-submit-btn", false, "auth_login_btn_loading", "auth_login_btn", "arrow-right");
    });
}

/* ── SIGNUP (mirrors custom_signup.js + hooks.py sign_up override) ─────── */

function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function sanitiseRedirect(url) {
    if (!url || typeof url !== "string") return "";
    const trimmed = url.trim();
    if (trimmed.startsWith("/") && !trimmed.startsWith("//")) return trimmed;
    return "";
}

function getSignupRedirectTo() {
    return sanitiseRedirect(new URLSearchParams(window.location.search).get("redirect-to") || "");
}

/** POST to / with cmd — same transport as custom_signup.js login.call() */
function signupViaHook(email, fullName, pwd, redirectTo, mobile) {
    const body = new URLSearchParams();
    body.set("cmd", "frappe.core.doctype.user.user.sign_up");
    body.set("email", email);
    body.set("full_name", fullName);
    body.set("pwd", pwd);
    body.set("mobile_no", mobile);
    body.set("redirect_to", redirectTo || "");

    const token = (window.LOGIN_CONTEXT || {}).csrf_token ||
        (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";

    return fetch("/", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Frappe-CSRF-Token": token,
            "Accept": "application/json",
        },
        body: body.toString(),
    }).then(res => res.json()).then(data => {
        if (data.exc) {
            throw new Error(Store.extractApiError(data) || data.exc_type || "Signup failed");
        }
        return data;
    });
}

function submitSignup(email, fullName, pwd, redirectTo, mobile) {
    return signupViaHook(email, fullName, pwd, redirectTo, mobile).then(r => {
        const result = r.message;
        const status = Array.isArray(result) ? parseInt(result[0], 10) : 0;
        const msgObj = Array.isArray(result) ? result[1] : result;
        const msgText = (msgObj && (msgObj.message || msgObj)) || "";
        const targetRedirect = (msgObj && msgObj.redirect_to) || redirectTo || resolveRedirect();

        if (status === 1) {
            showStatus(String(msgText) || "Account created! Redirecting…", "success");
            Store.toast(String(msgText) || "Account created! Redirecting…", "success");
            window.location.assign(targetRedirect || "/shop");
        } else {
            showStatus(String(msgText) || "Signup failed. Please try again.", "error");
            setButtonLoading("signup-submit-btn", false, "auth_signup_btn_loading", "auth_signup_btn", "check-circle");
            isSubmittingSignup = false;
            throw new Error(String(msgText) || "Signup failed");
        }
    });
}

let isSubmittingSignup = false;

function handleSignup(e) {
    if (e) e.preventDefault();
    if (isSubmittingSignup) return;
    clearStatus();

    const email = (document.getElementById("signup_email")?.value || "").trim();
    const fullName = (document.getElementById("signup_fullname")?.value || "").trim();
    const mobile = (document.getElementById("signup_mobile")?.value || "").trim();
    const pwd = document.getElementById("signup_password")?.value || "";
    const confirmPwd = document.getElementById("signup_confirm_password")?.value || "";
    const redirectTo = getSignupRedirectTo();

    if (!email || !validateEmail(email) || !fullName) {
        showStatus("Valid email and name required", "error");
        return;
    }
    if (!mobile) {
        showStatus("Please enter your mobile number", "error");
        return;
    }
    if (!pwd || !confirmPwd) {
        showStatus("Please enter both password fields", "error");
        return;
    }
    if (pwd !== confirmPwd) {
        showStatus("Passwords do not match", "error");
        return;
    }

    isSubmittingSignup = true;
    setButtonLoading("signup-submit-btn", true, "auth_signup_btn_loading", "auth_signup_btn", "check-circle");

    // Password strength check — same as custom_signup.js
    Store.call("frappe.core.doctype.user.user.test_password_strength", { new_password: pwd })
        .then(strengthResult => {
            const feedback = strengthResult && strengthResult.feedback;
            // Only block when policy explicitly failed (not when policy disabled → empty {})
            if (feedback && feedback.password_policy_validation_passed === false) {
                const msg = feedback.warning ||
                    (feedback.suggestions && feedback.suggestions[0]) ||
                    "Password is too weak";
                showStatus(msg, "error");
                setButtonLoading("signup-submit-btn", false, "auth_signup_btn_loading", "auth_signup_btn", "check-circle");
                isSubmittingSignup = false;
                return;
            }
            return submitSignup(email, fullName, pwd, redirectTo, mobile);
        })
        .catch(() => {
            // Policy might be disabled — submit anyway
            return submitSignup(email, fullName, pwd, redirectTo, mobile);
        })
        .catch(err => {
            showStatus(err.message || "Signup failed. Please try again.", "error");
            setButtonLoading("signup-submit-btn", false, "auth_signup_btn_loading", "auth_signup_btn", "check-circle");
            isSubmittingSignup = false;
        });
}

/* ── FORGOT PASSWORD ─────────────────────────────────────────────────────── */
function handleForgot(e) {
    e.preventDefault();
    clearStatus();

    const email = (document.getElementById("forgot-email")?.value || "").trim();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showStatus("Please enter a valid email address.", "error"); return;
    }

    setButtonLoading("forgot-submit-btn", true, "auth_forgot_btn_loading", "auth_forgot_btn", "send");

    Store.call("frappe.core.doctype.user.user.reset_password", { user: email })
    .then(() => {
        showStatus("If that address is registered, a reset link has been sent.", "success");
        setButtonLoading("forgot-submit-btn", false, "auth_forgot_btn_loading", "auth_forgot_btn", "send");
    })
    .catch(() => {
        showStatus("If that address is registered, a reset link has been sent.", "success");
        setButtonLoading("forgot-submit-btn", false, "auth_forgot_btn_loading", "auth_forgot_btn", "send");
    });
}

/* ── Wire hash links + hashchange ────────────────────────────────────────── */
function initHashLinks() {
    document.addEventListener("click", e => {
        const link = e.target.closest('a[href="#login"], a[href="#signup"], a[href="#forgot"]');
        if (!link) return;
        e.preventDefault();
        const panel = (link.getAttribute("href") || "").replace("#", "");
        if (panel) switchTab(panel);
    });

    window.addEventListener("hashchange", applyHashRoute);
}

/* ── Entry point ─────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
    Store.init();
    Store.initNavbarScroll();

    document.getElementById("login-form")?.addEventListener("submit", handleLogin);

    const signupForm = document.getElementById("signup-form");
    if (signupForm) {
        signupForm.addEventListener("submit", handleSignup);
        signupForm.setAttribute("action", "#");
        signupForm.setAttribute("method", "post");
    }

    document.getElementById("forgot-form")?.addEventListener("submit", handleForgot);

    initHashLinks();
    applyHashRoute();

    if (window.lucide) lucide.createIcons();
});
