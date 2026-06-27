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

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    btn.style.opacity = loading ? "0.7" : "1";
}

/* ── LOGIN ───────────────────────────────────────────────────────────────── */
function handleLogin(e) {
    e.preventDefault();
    clearStatus();

    const email = (document.getElementById("login-email")?.value || "").trim();
    const pwd = document.getElementById("login-password")?.value || "";

    if (!email) { showStatus("Please enter your email address.", "error"); return; }
    if (!pwd) { showStatus("Please enter your password.", "error"); return; }

    setLoading("login-submit-btn", true);

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
        // #region agent log
        Store.debugLog("page-login.js:handleLogin", "login response", {
            message: msg,
            hasRedirect: !!(data && data.redirect_to),
            homePage: data && data.home_page,
        }, "H1");
        // #endregion

        // "Logged In" = System User success
        // "No App"    = Website User (Customer) success — NOT an error
        if (msg === "Logged In" || msg === "No App") {
            const target = resolveRedirect(data);
            // #region agent log
            Store.debugLog("page-login.js:handleLogin", "redirecting", { target, message: msg }, "H1");
            // #endregion
            showStatus("Logged in! Redirecting…", "success");
            window.location.assign(target);
        } else if (data && data.exc) {
            showStatus(data.exc_type || data.message || "Invalid credentials.", "error");
            setLoading("login-submit-btn", false);
        } else {
            showStatus(String(msg) || "Invalid credentials. Please try again.", "error");
            setLoading("login-submit-btn", false);
        }
    })
    .catch(() => {
        showStatus("Connection error. Please try again.", "error");
        setLoading("login-submit-btn", false);
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

        // #region agent log
        Store.debugLog("page-login.js:submitSignup", "signup response", {
            status: String(status),
            msg: String(msgText).slice(0, 120),
        }, "H2");
        // #endregion

        if (status === 1) {
            showStatus(String(msgText) || "Account created successfully! Please log in.", "success");
            Store.toast(String(msgText) || "Account created! Please log in.", "success");
            document.getElementById("signup-form")?.reset();
            setLoading("signup-submit-btn", false);
            setTimeout(() => { clearStatus(); switchTab("login"); }, 2000);
        } else {
            showStatus(String(msgText) || "Signup failed. Please try again.", "error");
            setLoading("signup-submit-btn", false);
            throw new Error(String(msgText) || "Signup failed");
        }
    });
}

function handleSignup(e) {
    if (e) e.preventDefault();
    clearStatus();

    // #region agent log
    Store.debugLog("page-login.js:handleSignup", "submit triggered", {}, "H4");
    // #endregion

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

    setLoading("signup-submit-btn", true);

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
                setLoading("signup-submit-btn", false);
                return;
            }
            return submitSignup(email, fullName, pwd, redirectTo, mobile);
        })
        .catch(() => {
            // Policy might be disabled — submit anyway (custom_signup.js error callback)
            return submitSignup(email, fullName, pwd, redirectTo, mobile);
        })
        .catch(err => {
            // #region agent log
            Store.debugLog("page-login.js:handleSignup", "signup error", {
                error: String(err.message || err).slice(0, 200),
            }, "H2");
            // #endregion
            showStatus(err.message || "Signup failed. Please try again.", "error");
            setLoading("signup-submit-btn", false);
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

    setLoading("forgot-submit-btn", true);

    Store.call("frappe.core.doctype.user.user.reset_password", { user: email })
    .then(() => {
        showStatus("If that address is registered, a reset link has been sent.", "success");
        setLoading("forgot-submit-btn", false);
    })
    .catch(() => {
        showStatus("If that address is registered, a reset link has been sent.", "success");
        setLoading("forgot-submit-btn", false);
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
    // Fallback: direct button click (in case form submit is swallowed)
    document.getElementById("signup-submit-btn")?.addEventListener("click", (e) => {
        e.preventDefault();
        handleSignup(e);
    });

    document.getElementById("forgot-form")?.addEventListener("submit", handleForgot);

    initHashLinks();
    applyHashRoute();

    if (window.lucide) lucide.createIcons();
});
