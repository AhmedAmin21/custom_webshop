/* ==========================================================================
   CNCLeaders — Verified Signup Wizard
   Renders whatever state the backend says the signup is in. Depends on: store.js

   This file contains no identity logic and never sends a customer
   identifier. The backend decides which panel is possible via
   `allowed_actions`, decides whether an existing customer record is
   involved, and decides what may be shown about it. The only thing this
   file contributes to that decision is a yes or a no.
   ========================================================================== */

const API = "custom_webshop.api.signup.";

//: States reached only after both channels are verified. From here the
//: signup is a half-built account rather than a form somebody is still
//: deciding whether to fill in.
const PAST_VERIFICATION = new Set(["MATCH_REVIEW", "READY", "COMPLETED"]);

const Signup = {
    signupId: null,
    state: null,
    envelope: null,
    // Local-only, before the backend has a session: the type chooser and
    // the details form. Every other panel is named after a server state.
    localStep: "type",
    accountType: "Individual",
    details: { full_name: "", company_name: "", email: "", phone: "", phone_otp_channel: "SMS" },
    resendTimer: null,
    // Country picker: the list comes from the server (Frappe's own Country
    // doctype plus phonenumbers), so no country table ships in this file.
    countries: [],
    countryCode: null,
    countryOpen: false,
    // The document-level listeners an open country popup owns.
    countryListeners: null,

    /* ── Entry ─────────────────────────────────────────────────────── */
    init() {
        this.root = document.getElementById("signup-wizard");
        if (!this.root) return;

        // Resume a signup this browser already started. The binding
        // cookie is httpOnly, so possessing this id alone is not enough
        // for anyone else to continue it.
        try {
            this.signupId = sessionStorage.getItem("cnc_signup_id");
        } catch (e) {
            this.signupId = null;
        }

        if (this.signupId) {
            this.call("get_state", {})
                .then(env => {
                    // A signup that already finished must not resurrect.
                    // Without this, someone who signed up, logged out and
                    // came back would be shown "you're all set" and
                    // redirected, instead of being able to start again.
                    if (["COMPLETED", "CANCELLED"].includes(env.state)) {
                        this.forget();
                        this.render();
                        return;
                    }
                    this.apply(env);
                })
                .catch(() => {
                    this.forget();
                    this.render();
                });
        } else {
            this.render();
        }

        this.loadCountries();
        window.addEventListener("cnc_language_changed", () => {
            // Country names are translated server-side, so the list has to
            // be fetched again rather than just re-rendered.
            this.countries = [];
            this.loadCountries().then(() => this.render());
            this.render();
        });
    },

    forget() {
        this.signupId = null;
        this.state = null;
        this.envelope = null;
        this.localStep = "type";
        try {
            sessionStorage.removeItem("cnc_signup_id");
        } catch (e) { /* private mode */ }
    },

    remember(id) {
        this.signupId = id;
        try {
            sessionStorage.setItem("cnc_signup_id", id);
        } catch (e) { /* private mode */ }
    },

    /* ── Country picker ────────────────────────────────────────────── */
    loadCountries() {
        // The language is the browser's own toggle, not Frappe's request
        // language - they are independent, so it has to be sent.
        return Store.call("custom_webshop.signup.countries.for_signup", { lang: Store.lang })
            .then(data => {
                this.countries = data.countries || [];
                if (!this.countryCode) this.countryCode = data.default || "EG";
                if (this.localStep === "details" || this.state) this.render();
            })
            .catch(() => { /* the field still works; the server re-validates */ });
    },

    country(code) {
        return this.countries.find(c => c.code === (code || this.countryCode)) || null;
    },

    /* The marker is the ISO code, not a flag emoji.
     * Regional-indicator emoji do not render on Windows at all - it shows
     * the two letters instead - and plenty of Linux builds ship no emoji
     * font either, so a flag column degrades into unstyled letters exactly
     * where you cannot see it happening. A deliberate code chip renders
     * identically everywhere, and reads better on a machine-tools site
     * than a row of little flags. */
    countryButton() {
        const c = this.country();
        return `
            <button type="button" class="country-btn" id="country-btn"
                    aria-haspopup="listbox" aria-expanded="${this.countryOpen}"
                    aria-label="${this.esc(c ? c.name : this.t("su_country_search"))}">
                <span class="country-code">${this.esc(c ? c.code : "··")}</span>
                <span class="country-dial" dir="ltr">+${c ? c.dial : "?"}</span>
                <i data-lucide="chevron-down"></i>
            </button>`;
    },

    countryList() {
        if (!this.countryOpen) return "";
        const rows = this.countries.map(c => `
            <li role="option" class="country-item${c.code === this.countryCode ? " selected" : ""}"
                data-code="${this.esc(c.code)}" tabindex="-1"
                aria-selected="${c.code === this.countryCode}">
                <span class="country-code">${this.esc(c.code)}</span>
                <span class="country-name" dir="auto">${this.esc(c.name)}</span>
                <span class="country-dial" dir="ltr">+${c.dial}</span>
            </li>`).join("");

        return `
            <div class="country-pop">
                <input type="search" id="country-search" class="country-search"
                       placeholder="${this.esc(this.t("su_country_search"))}" autocomplete="off">
                <ul class="country-list" role="listbox">${rows}</ul>
                <p class="country-empty" id="country-empty" hidden>
                    ${this.esc(this.t("su_country_none"))}
                </p>
            </div>`;
    },

    /** The digit rules for the selected country.
     *  `lengths` comes from phonenumbers' own metadata by way of
     *  signup.countries - the real set of lengths a mobile number may
     *  have there, not a guess. An empty list means that region publishes
     *  no mobile metadata, and is read as "impose no length rule": better
     *  to let the server have the final word than to refuse a number we
     *  simply know nothing about. */
    phoneRule() {
        const c = this.country();
        const lengths = (c && c.lengths) || [];
        return {
            lengths: lengths,
            max: (c && c.max_len) || 0,
            trunk: String((c && c.trunk) || ""),
            // Stringified deliberately: the payload carries the dialling
            // code as a number, and `rule.dial.length` on a number is
            // undefined - which silently skipped the country-code strip
            // and left a pasted "+20…" with its 20 still attached.
            dial: String((c && c.dial) || ""),
        };
    },

    /** Remove whatever sits in front of the national number.
     *
     *  The field shows the country code beside what you type, so the two
     *  have to read as one number. `+20` followed by `01012345678` does
     *  not: the leading zero is a trunk prefix, dropped the moment a
     *  country code is in front, and the real number is `+20 10 01234567`.
     *
     *  So people go on typing `01012345678` the way they always have and
     *  the zero comes off as they go. A pasted `+20…` or `0020…` loses
     *  its country code the same way. `trunk` comes from phonenumbers'
     *  own metadata, so this is right for every country - `0` in Egypt,
     *  Saudi, the UK and Germany, `1` in North America, nothing at all in
     *  Italy, where the leading zero really is part of the number. */
    stripPrefixes(value, rule) {
        // Keep only what can belong to a phone number, and allow "+" only
        // at the front. Autofill and pasted rich text otherwise leave
        // things like "1 +201101271" sitting in the field - which counts
        // ten digits, so it passed the length rule while being no number
        // at all.
        let out = String(value || "").replace(/[^\d\s().+-]/g, "").replace(/^\s+/, "");
        out = out.charAt(0) === "+"
            ? "+" + out.slice(1).replace(/\+/g, "")
            : out.replace(/\+/g, "");

        if (rule.dial) {
            const marker = out.startsWith("+") ? 1 : (out.startsWith("00") ? 2 : 0);
            if (marker) {
                const after = out.slice(marker).replace(/^\s+/, "");
                if (after.replace(/\D/g, "").startsWith(rule.dial)) {
                    out = this.dropLeadingDigits(after, rule.dial.length);
                }
            }
        }

        // A bare country code, with no "+" or "00" announcing it. Removed
        // only when the number cannot be right with it and is right
        // without it, so a national number that merely happens to begin
        // with those digits is never touched. Without this, pasting
        // "201101271160" was cut to its first ten digits - "2011012711" -
        // which is a different number that passes the length rule.
        if (rule.dial && rule.lengths.length) {
            const digits = out.replace(/\D/g, "");
            if (digits.startsWith(rule.dial)
                && !rule.lengths.includes(digits.length)
                && rule.lengths.includes(digits.length - rule.dial.length)) {
                out = this.dropLeadingDigits(out, rule.dial.length);
            }
        }

        // Only once there is a number behind it, so the first "0" someone
        // types does not vanish under them before they have typed anything
        // for it to be a prefix of.
        if (rule.trunk && out.startsWith(rule.trunk)
            && out.replace(/\D/g, "").length > rule.trunk.length) {
            out = out.slice(rule.trunk.length).replace(/^\s+/, "");
        }

        return out;
    },

    /** Judge a typed number against the selected country's lengths.
     *  Returns "empty", "short", "long" or "ok". This is feedback, not
     *  authority: a number can be exactly the right length and still not
     *  be a real number, so `identity.to_e164` on the server still
     *  decides. It only spares someone submitting a number that could
     *  not possibly be right. */
    phoneVerdict(value) {
        const raw = String(value || "").trim();
        const digits = raw.replace(/\D/g, "");
        if (!digits) return "empty";

        // Backstop for a value that reached the field without passing
        // through stripPrefixes. Digits and separators, at most one
        // leading "+", nothing else.
        if (!/^\+?[\d\s().-]*$/.test(raw)) return "malformed";

        const rule = this.phoneRule();
        if (!rule.lengths.length) return digits.length >= 4 ? "ok" : "short";
        if (rule.lengths.includes(digits.length)) return "ok";
        return digits.length > rule.max ? "long" : "short";
    },

    /** Drop the first `count` digits, keeping any separators around them. */
    dropLeadingDigits(value, count) {
        let seen = 0;
        let i = 0;
        const text = String(value);
        while (i < text.length && seen < count) {
            if (text[i] >= "0" && text[i] <= "9") seen += 1;
            i += 1;
        }
        return text.slice(i).replace(/^[\s\-()]+/, "");
    },

    /** Cut a typed string back to `max` digits, keeping its separators.
     *  Rebuilding the value as bare digits instead would move the caret
     *  to the end mid-word, so the separators someone typed are kept and
     *  only the overflowing tail is dropped - which is what a native
     *  maxlength does. */
    trimToDigits(value, max) {
        let seen = 0;
        let out = "";
        for (const ch of String(value)) {
            if (ch >= "0" && ch <= "9") {
                if (seen === max) break;
                seen += 1;
            }
            out += ch;
        }
        return out;
    },

    /** The "that is not a valid number" message, in the selected
     *  country's terms - a hard-coded Egyptian example is no help to
     *  someone who has just picked Germany. */
    phoneError() {
        const c = this.country();
        return this.t("su_err_phone", { example: (c && c.example) || this.t("su_phone_ph") });
    },

    /** The phone row: country button, popup, and the national-number input. */
    phoneField() {
        const c = this.country();
        const placeholder = c && c.example ? c.example : this.t("su_phone_ph");
        // Deliberately no maxlength. It counts characters, not digits, and
        // it truncates the raw text *before* stripPrefixes can take the
        // country code off - so pasting "0020 110 127 1160" lost its last
        // digit and became a different, shorter number that still looked
        // valid. The digit cap belongs after the prefixes come off.
        return `
            <div class="field">
            <label class="signup-label" for="su-phone">${this.esc(this.t("su_phone"))}</label>
            <div class="phone-row">
                ${this.countryButton()}
                <input type="tel" id="su-phone" class="phone-input" dir="ltr"
                       inputmode="tel" autocomplete="tel-national"
                       aria-describedby="phone-note"
                       value="${this.esc(this.details.phone || "")}"
                       placeholder="${this.esc(placeholder)}">
                <svg class="phone-ok" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="3" stroke-linecap="round" stroke-linejoin="round"
                     aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>
                ${this.countryList()}
            </div>
            <p class="field-note" id="phone-note" role="status" aria-live="polite"></p>
            </div>`;
    },

    /** The delivery-channel row: SMS vs WhatsApp for the phone code.
     * Only rendered when the site has WhatsApp/Evolution API configured -
     * `window.LOGIN_CONTEXT.whatsapp_otp_enabled` is the single source of
     * truth for that, set from `Webshop Signup Settings` at page load. A
     * site that hasn't configured it sees no trace of this control. */
    otpChannelField() {
        if (!(window.LOGIN_CONTEXT || {}).whatsapp_otp_enabled) return "";

        const option = (value, labelKey) => `
            <button type="button" class="otp-channel-choice${this.details.phone_otp_channel === value ? " selected" : ""}"
                    data-channel="${value}" aria-pressed="${this.details.phone_otp_channel === value}">
                <span class="signup-choice-label">${this.esc(this.t(labelKey))}</span>
                <i data-lucide="check" class="signup-choice-check"></i>
            </button>`;

        return `
            <div class="field">
                <span class="signup-label">${this.esc(this.t("su_otp_channel_label"))}</span>
                <div class="otp-channel-choices">
                    ${option.call(this, "SMS", "su_otp_channel_sms")}
                    ${option.call(this, "WhatsApp", "su_otp_channel_whatsapp")}
                </div>
            </div>`;
    },

    bindCountry() {
        const btn = document.getElementById("country-btn");
        if (btn) {
            btn.addEventListener("click", e => {
                e.stopPropagation();
                this.countryOpen = !this.countryOpen;
                this.render();
            });
        }

        const search = document.getElementById("country-search");
        if (search) {
            search.focus();
            search.addEventListener("input", () => {
                const term = search.value.trim().toLowerCase();
                let shown = 0;

                document.querySelectorAll(".country-item").forEach(item => {
                    const c = this.country(item.dataset.code);
                    // Matches either language, the ISO code, and the dial
                    // code with or without its plus - so "eg", "مصر",
                    // "egypt", "20" and "+20" all find Egypt.
                    const hay = [c.name, c.name_en, c.code, c.dial, `+${c.dial}`]
                        .join(" ").toLowerCase();
                    const hit = !term || hay.includes(term);
                    // A class, not the `hidden` attribute: `.country-item`
                    // sets `display: flex`, which beats the user agent's
                    // `[hidden] { display: none }` on specificity, so
                    // setting `hidden` did nothing at all.
                    item.classList.toggle("is-filtered", !hit);
                    if (hit) shown += 1;
                });

                const empty = document.getElementById("country-empty");
                if (empty) empty.hidden = shown > 0;
            });
        }

        document.querySelectorAll(".country-item").forEach(item => {
            item.addEventListener("click", () => {
                this.countryCode = item.dataset.code;
                this.countryOpen = false;
                // Keep whatever they typed; only the rules and the hint change.
                const input = document.getElementById("su-phone");
                if (input) this.details.phone = input.value;
                this.render();
                const phone = document.getElementById("su-phone");
                if (phone) phone.focus();
            });
        });

        // Detach the previous pair before considering a new one.
        //
        // These are document-level listeners, and the popup does not
        // always close by the route that removed them: clicking a country
        // *inside* the field returned early from the closer, so it stayed
        // attached, and Escape was the only thing that ever removed the
        // key handler. Every open therefore left another closer behind,
        // and each one re-rendered the page on the next click anywhere
        // else - which quietly replaced the DOM while a form was being
        // submitted, wiping the validation message the person needed to
        // read. Ownership belongs here, where both are created.
        this.releaseCountryListeners();

        if (this.countryOpen) {
            this.placeCountryPop();

            const close = e => {
                if (e.target.closest(".phone-row")) return;
                this.countryOpen = false;
                this.render();
            };
            document.addEventListener("click", close);

            // Escape closes it, which is what a keyboard user expects.
            const esc = e => {
                if (e.key !== "Escape") return;
                this.countryOpen = false;
                this.render();
                document.getElementById("country-btn")?.focus();
            };
            document.addEventListener("keydown", esc);

            this.countryListeners = { close, esc };
        }
    },

    /** Remove the document-level listeners the open popup installed. */
    releaseCountryListeners() {
        if (!this.countryListeners) return;
        document.removeEventListener("click", this.countryListeners.close);
        document.removeEventListener("keydown", this.countryListeners.esc);
        this.countryListeners = null;
    },

    /** Apply the selected country's rules to the phone input.
     *  Re-run on every render, so picking a country immediately re-judges
     *  whatever is already typed against the new country's lengths. */
    bindPhone() {
        const input = document.getElementById("su-phone");
        if (!input) return;

        input.addEventListener("input", () => {
            const rule = this.phoneRule();
            const before = input.value;
            const caret = input.selectionStart;
            const previous = this.details.phone || "";

            const stripped = this.stripPrefixes(before, rule);
            const frontRemoved = before.length - stripped.length;

            // The cap applies to typing, where it reads as "the field will
            // not take an eleventh digit". It deliberately does not apply
            // to a paste: something still too long after its prefixes came
            // off is a number we do not understand, and trimming its tail
            // would invent a different one that happens to pass the length
            // rule. Better to leave it and say it is too long.
            const typingOneChar = before.length - previous.length === 1;
            let next = stripped;
            if (rule.max && typingOneChar && next.replace(/\D/g, "").length > rule.max) {
                next = this.trimToDigits(next, rule.max);
            }

            if (next !== before) {
                input.value = next;
                // Only the front-stripping moves the caret; trimming the
                // tail leaves anything before the cut where it was.
                const pos = Math.max(0, caret - frontRemoved);
                try {
                    input.setSelectionRange(pos, pos);
                } catch (e) { /* not focused */ }
            }

            this.details.phone = input.value;
            this.paintPhoneState();
        });

        // Also on arrival, so switching country re-normalises what is
        // already there and a resumed session shows the stored number in
        // the same shape as a freshly typed one.
        const settled = this.stripPrefixes(input.value, this.phoneRule());
        if (settled !== input.value) {
            input.value = settled;
            this.details.phone = settled;
        }

        this.paintPhoneState();
    },

    /** Paint the phone field's verdict without re-rendering.
     *  A full render would rebuild the input and drop the caret, so this
     *  touches only the classes and the note. The note appears solely
     *  when the length is wrong - it is a correction, not a standing
     *  explainer, and an empty field says nothing. */
    paintPhoneState() {
        const input = document.getElementById("su-phone");
        if (!input) return;

        const verdict = this.phoneVerdict(input.value);
        const row = input.closest(".phone-row");
        if (row) {
            row.classList.toggle("is-valid", verdict === "ok");
            row.classList.toggle("is-invalid", verdict !== "ok" && verdict !== "empty");
        }

        const note = document.getElementById("phone-note");
        if (!note) return;

        if (verdict === "malformed") {
            note.textContent = this.phoneError();
            note.classList.add("is-shown");
        } else if (verdict === "short" || verdict === "long") {
            const rule = this.phoneRule();
            note.textContent = this.t("su_phone_len", {
                country: this.country()?.name || "",
                need: rule.lengths.join(" / "),
                have: input.value.replace(/\D/g, "").length,
            });
            note.classList.add("is-shown");
        } else {
            note.textContent = "";
            note.classList.remove("is-shown");
        }
    },

    /** Size and place the country list against the real viewport.
     *  The field can sit anywhere down the card, so a fixed height either
     *  runs off the bottom of the screen or wastes the room available.
     *  This measures the popup's own chrome - search box, padding, borders
     *  - rather than guessing at it, works out what is genuinely free above
     *  and below the button, opens toward the roomier side, and caps the
     *  list so it always keeps a margin from the window edge. */
    placeCountryPop() {
        const pop = document.querySelector(".country-pop");
        const btn = document.getElementById("country-btn");
        if (!pop || !btn) return;

        const MARGIN = 20;   // never touch the window edge
        const OFFSET = 8;    // gap between field and popup, matches the CSS
        const MIN = 160;     // below this a list is not worth opening
        const MAX = 280;     // a taller list is just a longer scroll

        // Collapse the list to measure everything that is not the list.
        pop.style.setProperty("--country-list-max", "0px");
        const chrome = pop.getBoundingClientRect().height;

        const rect = btn.getBoundingClientRect();
        const below = window.innerHeight - rect.bottom - OFFSET - chrome - MARGIN;
        const above = rect.top - OFFSET - chrome - MARGIN;

        const up = below < MIN && above > below;
        pop.classList.toggle("opens-up", up);

        const room = Math.max(MIN, Math.min(MAX, up ? above : below));
        pop.style.setProperty("--country-list-max", `${Math.floor(room)}px`);
    },

    /* ── Transport ─────────────────────────────────────────────────── */
    call(method, args) {
        const payload = Object.assign({}, args);
        if (this.signupId && method !== "start") payload.signup_id = this.signupId;
        return Store.call(API + method, payload);
    },

    apply(envelope) {
        this.envelope = envelope;
        this.state = envelope.state;
        if (envelope.signup_id) this.remember(envelope.signup_id);
        // Put the picker back on the country this signup was started with.
        if (envelope.phone_country) this.countryCode = envelope.phone_country;
        this.render();

        if (envelope.message) Store.toast(envelope.message, "success");

        // The server repairs names rather than refusing them, so say what
        // was actually saved instead of letting it differ silently.
        const adjusted = envelope.data && envelope.data.name_adjusted;
        if (adjusted) {
            Store.toast(this.t("su_name_adjusted", { name: adjusted }), "info");
        }

        // States the backend expects the client to move through without
        // asking the person anything.
        if (this.state === "EMAIL_VERIFIED") {
            this.run("send_phone_otp", {});
        } else if (this.state === "PHONE_VERIFIED") {
            this.run("resolve", {});
        } else if (this.state === "COMPLETED") {
            const target = (envelope.data && envelope.data.redirect_to) || "/shop";
            setTimeout(() => window.location.assign(target), 900);
        }
    },

    /** Call an endpoint, render the result, surface any error inline. */
    run(method, args, button) {
        this.setError("");
        if (button) this.setBusy(button, true);

        return this.call(method, args)
            .then(env => this.apply(env))
            .catch(err => {
                this.setError(err.message || Store.t("su_err_generic"));
                if (button) this.setBusy(button, false);
            });
    },

    /* ── Rendering ─────────────────────────────────────────────────── */
    t(key, params) { return Store.t(key, params || {}); },
    esc(value) { return Store.escapeHtml(value == null ? "" : String(value)); },

    render() {
        if (!this.root) return;

        const panel = this.state ? this.state : this.localStep;
        const builder = this.panels[panel];
        this.root.innerHTML = builder ? builder.call(this) : this.panels.type.call(this);

        this.bind();
        if (window.lucide) lucide.createIcons();

        // "Already have an account? Sign in" belongs to the steps where
        // it is still a choice. Once both codes are proven the session is
        // half an account, and following that link abandons a
        // verification the person has just done twice.
        const card = this.root.closest(".auth-card");
        if (card) {
            card.classList.toggle("is-past-verification", PAST_VERIFICATION.has(panel));
        }

        const focusTarget = this.root.querySelector("[data-autofocus]");
        if (focusTarget) focusTarget.focus();
    },

    setError(message) {
        const box = document.getElementById("signup-error");
        if (!box) return;
        box.textContent = message || "";
        box.style.display = message ? "block" : "none";
        if (message) Store.toast(message, "error");
    },

    setBusy(button, busy) {
        if (!button) return;
        button.disabled = busy;
        button.dataset.idle = button.dataset.idle || button.innerHTML;
        button.innerHTML = busy
            ? `<span class="auth-btn-spinner"></span><span>${this.esc(this.t(button.dataset.busyKey || "su_sending"))}</span>`
            : button.dataset.idle;
        if (!busy && window.lucide) lucide.createIcons({ nodes: [button] });
    },

    /** A vernier-style tick scale, not a progress bar.
     *  The signup is a measured sequence of five known steps, and this shop
     *  sells measuring and cutting tools - so the step indicator is drawn
     *  from that world: hairline ticks, filled as they are passed, with the
     *  current one marked. It is the one deliberately expressive element on
     *  the page; everything around it stays quiet. */
    rail(step) {
        if (!step) return "";
        const ticks = [1, 2, 3, 4, 5].map(n => {
            const state = n < step ? "done" : n === step ? "now" : "";
            return `<span class="rail-tick ${state}"></span>`;
        }).join("");
        return `
            <div class="signup-rail" role="progressbar"
                 aria-valuenow="${step}" aria-valuemin="1" aria-valuemax="5"
                 aria-label="${this.esc(this.t("su_step", { n: step, total: 5 }))}">
                <div class="rail-scale">${ticks}</div>
                <span class="rail-count" dir="ltr">${step}<span class="rail-of">/5</span></span>
            </div>`;
    },

    header(titleKey, subKey, step) {
        return `
            ${this.rail(step)}
            <div class="auth-header">
                <h2 class="auth-title">${this.esc(this.t(titleKey))}</h2>
                ${subKey ? `<p class="auth-subtitle">${this.esc(this.t(subKey))}</p>` : ""}
            </div>
            <div class="auth-status error" id="signup-error" style="display:none;"></div>`;
    },

    /** One labelled field. Wrapped so the form's own gap separates fields
     *  from each other, not a label from the input it belongs to. */
    field(id, labelKey, type, value, placeholderKey, extra) {
        return `
            <div class="field">
                <label class="signup-label" for="${id}">${this.esc(this.t(labelKey))}</label>
                <div class="input-group">
                    <input type="${type}" id="${id}" value="${this.esc(value || "")}"
                           placeholder="${this.esc(placeholderKey ? this.t(placeholderKey) : "")}"
                           ${extra || ""}>
                </div>
            </div>`;
    },

    panels: {
        /* Local step 1 — who is this account for */
        type() {
            const option = (value, labelKey, icon) => `
                <button type="button" class="signup-choice${this.accountType === value ? " selected" : ""}"
                        data-type="${value}" aria-pressed="${this.accountType === value}">
                    <i data-lucide="${icon}" class="signup-choice-icon"></i>
                    <span class="signup-choice-label">${this.esc(this.t(labelKey))}</span>
                    <i data-lucide="check" class="signup-choice-check"></i>
                </button>`;

            return `
                ${this.header("su_type_title", "su_type_sub", 1)}
                <div class="signup-choices">
                    ${option.call(this, "Individual", "su_type_individual", "user")}
                    ${option.call(this, "Company", "su_type_company", "building-2")}
                </div>
                <button type="button" class="auth-submit-btn" id="type-next">
                    <span>${this.esc(this.t("su_continue"))}</span><i data-lucide="arrow-right"></i>
                </button>`;
        },

        /* Local step 2 — the details, validated again on the server */
        details() {
            const isCompany = this.accountType === "Company";
            return `
                ${this.header("su_details_title", "su_details_sub", 2)}
                <form id="details-form" class="auth-form" novalidate>
                    ${isCompany ? this.field("su-company", "su_company_name", "text", this.details.company_name, "su_company_name_ph", "data-autofocus") : ""}
                    ${this.field("su-name", isCompany ? "su_contact_person" : "su_full_name", "text",
                        this.details.full_name, "su_full_name_ph", isCompany ? "" : "data-autofocus")}
                    ${this.field("su-email", "su_email", "email", this.details.email, "su_email_ph", 'autocomplete="username" dir="ltr"')}
                    ${this.phoneField()}
                    ${this.otpChannelField()}
                    <div class="signup-actions">
                        <button type="button" class="auth-secondary-btn" id="details-back">${this.esc(this.t("su_back"))}</button>
                        <button type="submit" class="auth-submit-btn" id="details-next" data-busy-key="su_sending">
                            <span>${this.esc(this.t("su_continue"))}</span><i data-lucide="arrow-right"></i>
                        </button>
                    </div>
                </form>`;
        },

        EMAIL_PENDING() { return this.otpPanel("email"); },
        PHONE_PENDING() { return this.otpPanel("phone"); },

        /* Transient states — the controller advances through these. */
        EMAIL_VERIFIED() { return this.spinnerPanel("su_verifying"); },
        PHONE_VERIFIED() { return this.spinnerPanel("su_verifying"); },

        MATCH_REVIEW() {
            // Two cards share this state. The second one only appears
            // after "yes", and only when the stored name differs from the
            // one just typed - saying yes to a record and saying yes to
            // its spelling are different answers.
            const choice = (this.envelope.data || {}).name_choice;
            if (choice) return this.namePanel(choice);

            // Everything hidden arrives already replaced with block
            // glyphs, so the blur below is presentation and nothing more
            // — there is no hidden text in the page to read back out of
            // it. `blurred` only says which rows should look hidden
            // rather than printing a literal row of blocks.
            const card = (this.envelope.data && this.envelope.data.recognition) || {};
            const hidden = new Set(card.blurred || []);
            // Two questions share this panel. One asks whether a record we
            // found might be theirs; the other tells them the details they
            // just proved already belong to an account of their own, and
            // offers it back. Same card, same yes/no, different words.
            const own = card.kind === "own_account";
            const row = (labelKey, key) => {
                const value = card[key];
                if (!value) return "";
                const cls = hidden.has(key) ? " is-redacted" : "";
                return `<div class="signup-match-row">
                       <span class="signup-match-label">${this.esc(this.t(labelKey))}</span>
                       <span class="signup-match-value${cls}" dir="auto" aria-hidden="${hidden.has(key)}">${this.esc(value)}</span>
                   </div>`;
            };

            return `
                ${this.header(own ? "su_own_title" : "su_match_title",
                              own ? "su_own_sub" : "su_match_sub", 4)}
                <div class="signup-match-card">
                    ${row.call(this, "su_match_name", "name")}
                    ${row.call(this, "su_match_company", "company")}
                    ${row.call(this, "su_match_phone", "phone")}
                    ${row.call(this, "su_match_address", "address")}
                    ${row.call(this, "su_match_governorate", "governorate")}
                    ${row.call(this, "su_match_country", "country")}
                </div>
                ${card.company_on_record
                    ? `<p class="signup-match-company">${this.esc(this.t("su_match_company_note"))}</p>`
                    : ""}
                <p class="signup-match-note">${this.esc(this.t("su_match_hidden"))}</p>
                <div class="signup-actions">
                    <button type="button" class="auth-secondary-btn" id="match-no">${this.esc(this.t(own ? "su_own_no" : "su_match_no"))}</button>
                    <button type="button" class="auth-submit-btn" id="match-yes">
                        <span>${this.esc(this.t(own ? "su_own_yes" : "su_match_yes"))}</span><i data-lucide="check"></i>
                    </button>
                </div>`;
        },

        READY() {
            const data = this.envelope.data || {};
            const notice = data.notice;
            // Every route reaches this step, and it is not the same step
            // each time. Somebody being handed a brand-new account is
            // choosing their first password; somebody signing back into an
            // account they already have is replacing the one they could
            // not remember. Calling the second "create a password" is what
            // made it read as being given a second account.
            const titles = {
                accepted: ["su_recover_title", "su_recover_sub"],
                disputed: ["su_disputed_title", "su_disputed_sub"],
            }[data.recovering] || ["su_password_title", "su_password_sub"];
            return `
                ${this.header(titles[0], titles[1], 5)}
                ${notice ? `<p class="signup-notice">${this.esc(notice)}</p>` : ""}
                <form id="password-form" class="auth-form" novalidate>
                    ${this.field("su-password", "su_password", "password", "", null, 'autocomplete="new-password" data-autofocus')}
                    ${this.passwordGuide()}
                    ${this.field("su-password2", "su_confirm_password", "password", "", null, 'autocomplete="new-password"')}
                    <button type="submit" class="auth-submit-btn" id="password-next" data-busy-key="su_finishing">
                        <span>${this.esc(this.t("su_finish"))}</span><i data-lucide="check-circle"></i>
                    </button>
                </form>
                ${this.backButton()}`;
        },

        COMPLETED() {
            return `
                ${this.header("su_done_title", "su_done_sub")}
                <div class="signup-centered"><span class="auth-btn-spinner"></span></div>`;
        },

        BLOCKED() {
            // The third action is the way out. Being blocked is terminal
            // for this signup, and the two buttons above it both assume
            // the account we found is yours - but the ordinary way to
            // arrive here is mistyping one of your own addresses, or
            // using a colleague's, and without this there is nothing on
            // the panel that starts a new signup. The session is also
            // remembered, so it came back on every reload: a dead end
            // that followed you.
            // Which detail was taken. Sent only here, where the person
            // has already proved control of both of them.
            const on = (this.envelope.data || {}).blocked_on;
            const detail = {
                email: this.t("su_blocked_email", { email: this.envelope.email || "" }),
                phone: this.t("su_blocked_phone", { phone: this.envelope.phone || "" }),
                customer: this.t("su_blocked_customer"),
            }[on];

            return `
                ${this.header("su_blocked_title", "su_blocked_sub")}
                ${detail ? `<p class="signup-blocked-detail" dir="auto">${this.esc(detail)}</p>` : ""}
                <div class="signup-actions">
                    <a class="auth-secondary-btn" href="#forgot">${this.esc(this.t("su_goto_forgot"))}</a>
                    <a class="auth-submit-btn" href="#login">
                        <span>${this.esc(this.t("su_goto_login"))}</span><i data-lucide="log-in"></i>
                    </a>
                </div>
                <div class="signup-restart">
                    <button type="button" class="auth-link-btn" id="restart">
                        ${this.esc(this.t("su_blocked_restart"))}
                    </button>
                </div>`;
        },

        EXPIRED() { return this.restartPanel(); },
        CANCELLED() { return this.restartPanel(); },

        /* Change-detail sub-panels, entered from an OTP step. */
        change_email() { return this.changePanel("email"); },
        change_phone() { return this.changePanel("phone"); },
    },

    /* ── Shared panel builders ─────────────────────────────────────── */
    otpPanel(channel) {
        const data = this.envelope.data || {};
        const isEmail = channel === "email";
        const target = isEmail ? this.envelope.email : this.envelope.phone;
        const length = data.otp_length || 6;
        const remaining = data.sends_remaining;
        // Only the phone panel has a delivery channel to switch, and only
        // when the site offers WhatsApp at all.
        const canSwitchChannel = !isEmail && (window.LOGIN_CONTEXT || {}).whatsapp_otp_enabled;
        const otherChannel = this.envelope.phone_otp_channel === "WhatsApp" ? "SMS" : "WhatsApp";
        const switchLabel = otherChannel === "SMS" ? "su_switch_to_sms" : "su_switch_to_whatsapp";

        return `
            ${this.header(isEmail ? "su_email_otp_title" : "su_phone_otp_title", null, isEmail ? 3 : 4)}
            <p class="auth-subtitle" dir="auto">${this.esc(
                this.t(isEmail ? "su_email_otp_sub" : "su_phone_otp_sub", { n: length, target: target || "" })
            )}</p>
            <form id="otp-form" class="auth-form" novalidate>
                <div class="field">
                <label class="signup-label" for="su-code">${this.esc(this.t("su_code"))}</label>
                <div class="input-group">
                    <input type="text" id="su-code" class="signup-code" dir="ltr"
                           inputmode="numeric" autocomplete="one-time-code"
                           maxlength="${length}" pattern="[0-9]*" data-autofocus>
                </div>
                </div>
                <button type="submit" class="auth-submit-btn" id="otp-verify" data-busy-key="su_verifying">
                    <span>${this.esc(this.t("su_verify"))}</span><i data-lucide="arrow-right"></i>
                </button>
            </form>
            <div class="signup-links">
                <button type="button" class="auth-link-btn" id="otp-resend"
                        data-channel="${channel}" ${data.resend_in ? "disabled" : ""}>
                    ${this.esc(data.resend_in ? this.t("su_resend_in", { n: data.resend_in }) : this.t("su_resend"))}
                </button>
                <button type="button" class="auth-link-btn" id="otp-change" data-channel="${channel}">
                    ${this.esc(this.t(isEmail ? "su_change_email" : "su_change_phone"))}
                </button>
                ${canSwitchChannel ? `
                <button type="button" class="auth-link-btn" id="otp-channel-switch" data-channel="${otherChannel}">
                    ${this.esc(this.t(switchLabel))}
                </button>` : ""}
            </div>
            ${remaining != null ? `<p class="signup-hint">${this.esc(this.t("su_sends_left", { n: remaining }))}</p>` : ""}`;
    },

    changePanel(channel) {
        const isEmail = channel === "email";
        return `
            ${this.header(isEmail ? "su_change_email_title" : "su_change_phone_title")}
            <form id="change-form" class="auth-form" novalidate data-channel="${channel}">
                ${isEmail
                    ? this.field("su-change-value", "su_email", "email", "", "su_email_ph",
                                 'dir="ltr" data-autofocus')
                    : this.phoneField()}
                <div class="signup-actions">
                    <button type="button" class="auth-secondary-btn" id="change-back">${this.esc(this.t("su_back"))}</button>
                    <button type="submit" class="auth-submit-btn" id="change-save" data-busy-key="su_sending">
                        <span>${this.esc(this.t("su_save_and_send"))}</span><i data-lucide="send"></i>
                    </button>
                </div>
            </form>`;
    },

    spinnerPanel(labelKey) {
        return `<div class="signup-centered">
                    <span class="auth-btn-spinner"></span>
                    <p class="auth-subtitle">${this.esc(this.t(labelKey))}</p>
                </div>`;
    },

    restartPanel() {
        return `
            ${this.header("su_expired_title", "su_expired_sub")}
            <button type="button" class="auth-submit-btn" id="restart">
                <span>${this.esc(this.t("su_restart"))}</span><i data-lucide="rotate-ccw"></i>
            </button>`;
    },

    /* ── Event wiring ──────────────────────────────────────────────── */
    bind() {
        const on = (id, event, handler) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener(event, handler);
        };

        this.root.querySelectorAll(".signup-choice").forEach(button => {
            button.addEventListener("click", () => {
                this.accountType = button.dataset.type;
                this.render();
            });
        });

        this.root.querySelectorAll(".otp-channel-choice").forEach(button => {
            button.addEventListener("click", () => {
                this.details.phone_otp_channel = button.dataset.channel;
                this.render();
            });
        });

        on("type-next", "click", () => { this.localStep = "details"; this.render(); });
        on("details-back", "click", () => { this.localStep = "type"; this.render(); });
        on("details-form", "submit", e => this.submitDetails(e));
        on("otp-form", "submit", e => this.submitOtp(e));
        on("otp-resend", "click", e => this.resend(e));
        on("otp-channel-switch", "click", e => this.switchChannel(e));
        on("otp-change", "click", e => {
            this.state = e.currentTarget.dataset.channel === "email" ? "change_email" : "change_phone";
            this.render();
        });
        on("change-back", "click", () => { this.state = this.envelope.state; this.render(); });
        on("change-form", "submit", e => this.submitChange(e));
        on("match-yes", "click", e => this.run("decide", { accept: true }, e.currentTarget));
        on("match-no", "click", e => this.run("decide", { accept: false }, e.currentTarget));
        on("name-keep", "click", e =>
            this.run("choose_name", { use_submitted: false }, e.currentTarget));
        on("name-use", "click", e =>
            this.run("choose_name", { use_submitted: true }, e.currentTarget));
        on("go-back", "click", e => this.run("go_back", {}, e.currentTarget));
        on("password-form", "submit", e => this.submitPassword(e));
        on("restart", "click", () => { this.forget(); this.render(); });

        this.bindCountry();
        this.bindPhone();

        const passwordInput = document.getElementById("su-password");
        if (passwordInput) {
            passwordInput.addEventListener("input", () => this.paintPasswordGuide());
            this.paintPasswordGuide();
        }
        this.startResendCountdown();
    },

    /* ── Handlers ──────────────────────────────────────────────────── */
    submitDetails(event) {
        event.preventDefault();
        const value = id => (document.getElementById(id)?.value || "").trim();

        this.details = {
            full_name: value("su-name"),
            company_name: value("su-company"),
            email: value("su-email"),
            phone: value("su-phone"),
            // Untouched by the fields read above: set by the channel
            // picker's own click handler, and defaults to "SMS".
            phone_otp_channel: this.details.phone_otp_channel || "SMS",
        };

        // Mirrors of the server's rules, for instant feedback only. The
        // backend re-checks all of them and is the authority.
        if (this.accountType === "Company" && !this.details.company_name) {
            return this.setError(this.t("su_err_company"));
        }
        // Counted on the name as typed, and only tokens carrying a
        // letter — the same rule as the server's `name_components`.
        // Counting the *repaired* name instead would let punctuation
        // decide: "Anne-Marie Dupont" is two names that become three
        // words once the hyphen goes, and it would sail through a rule
        // it should fail.
        if (this.nameComponents(this.details.full_name) < 3) {
            return this.setError(this.t("su_err_name"));
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.details.email)) {
            return this.setError(this.t("su_err_email"));
        }
        // Judged against the selected country's real lengths rather than
        // a loose floor. Still only feedback - to_e164 on the server is
        // the authority - but a number that is the wrong length for the
        // country cannot be right, so there is no reason to spend a round
        // trip discovering it.
        if (this.phoneVerdict(this.details.phone) !== "ok") {
            this.paintPhoneState();
            return this.setError(this.phoneError());
        }

        this.run("start", {
            account_type: this.accountType,
            full_name: this.details.full_name,
            company_name: this.details.company_name || null,
            email: this.details.email,
            phone: this.details.phone,
            phone_country: this.countryCode,
            phone_otp_channel: this.details.phone_otp_channel,
        }, document.getElementById("details-next"));
    },

    submitOtp(event) {
        event.preventDefault();
        const code = (document.getElementById("su-code")?.value || "").trim();
        if (!code) return this.setError(this.t("su_err_code"));

        const method = this.envelope.state === "EMAIL_PENDING" ? "verify_email" : "verify_phone";
        this.run(method, { code: code }, document.getElementById("otp-verify"));
    },

    resend(event) {
        const channel = event.currentTarget.dataset.channel;
        this.run(channel === "email" ? "send_email_otp" : "send_phone_otp", {});
    },

    /** Switch the phone OTP delivery channel and resend on the new one.
     * `data-channel` on the link already carries the *other* channel -
     * this only ever moves to the one not currently in use. */
    switchChannel(event) {
        const channel = event.currentTarget.dataset.channel;
        this.run("switch_phone_otp_channel", { channel: channel });
    },

    submitChange(event) {
        event.preventDefault();
        const channel = event.currentTarget.dataset.channel;
        const isEmail = channel === "email";
        const field = isEmail ? "su-change-value" : "su-phone";
        const value = (document.getElementById(field)?.value || "").trim();
        if (isEmail) {
            if (!value) return this.setError(this.t("su_err_email"));
        } else if (this.phoneVerdict(value) !== "ok") {
            // The replacement number is held to the same country rules as
            // the original; this panel renders the very same phoneField.
            this.paintPhoneState();
            return this.setError(this.phoneError());
        }

        const args = isEmail
            ? { email: value }
            : { phone: value, phone_country: this.countryCode };
        this.run(isEmail ? "change_email" : "change_phone", args,
            document.getElementById("change-save"));
    },

    /** What actually makes a password hard to guess, said plainly.
     *
     *  Shown before anything is submitted and ticked off as they type, so
     *  the rules are visible while they are being followed rather than
     *  reported afterwards as a rejection. The server still decides - these
     *  are the same rules it applies, mirrored so that in practice nobody
     *  meets the error at all. */
    passwordChecks(value) {
        const pw = String(value || "");
        // Each word separately, not the whole field: "Ahmed123" contains the
        // name of someone called "Ahmed Sabry Amin" even though neither string
        // contains the other.
        const own = [];
        const add = part => { if (part) own.push(String(part)); };
        add(this.details.email);
        add((this.details.email || "").split("@")[0]);
        add(this.details.phone);
        String(this.details.full_name || "").split(/\s+/).forEach(add);
        String(this.details.company_name || "").split(/\s+/).forEach(add);

        const lower = pw.toLowerCase();
        const digits = pw.replace(/\D/g, "");
        const usesOwnDetails = own
            .filter(part => part.length >= 3)
            .some(part => {
                const piece = part.toLowerCase();
                if (lower.includes(piece)) return true;
                // The number counts however either side wrote it, so this
                // has to run both ways — the stored form carries +20 and
                // is longer than what somebody types. Mirrors
                // signup/passwords.py, which is what actually enforces it.
                const partDigits = part.replace(/\D/g, "");
                return (
                    Math.min(partDigits.length, digits.length) >= 4 &&
                    (digits.includes(partDigits) || partDigits.includes(digits))
                );
            });

        return {
            length: pw.length >= this.MIN_PASSWORD_LENGTH,
            mix: /[A-Za-z\u0600-\u06FF]/.test(pw) && /\d/.test(pw),
            personal: pw.length > 0 && !usesOwnDetails,
            common: pw.length > 0 && !this.COMMON_PASSWORDS.some(
                bad => lower === bad || lower.startsWith(bad)
            ),
        };
    },

    /* Both of these come from signup/passwords.py via LOGIN_CONTEXT, so
     * what the guide checks as you type is what the server checks on
     * submit. The fallbacks are only for a page rendered before that
     * context existed - they are not a second opinion. */
    get COMMON_PASSWORDS() {
        const rules = (window.LOGIN_CONTEXT || {}).password_rules || {};
        return rules.common || [
            "password", "123456", "12345678", "qwerty", "111111", "abc123",
            "letmein", "welcome", "admin", "iloveyou", "monkey", "dragon",
        ];
    },

    get MIN_PASSWORD_LENGTH() {
        return ((window.LOGIN_CONTEXT || {}).password_rules || {}).min_length || 8;
    },

    /** "Which of these two names should your account carry?"
     *
     *  Lives out here rather than inside `panels` because panels are called
     *  with `builder.call(this)` — `this` is the wizard, so anything a panel
     *  reaches for through `this.` has to be a wizard method.
     */
    /** A way back out of the answers given after the codes.
     *  Never rendered from the page's own guess - the server decides
     *  whether there is an answer to take back and says so in
     *  allowed_actions, so this cannot offer to undo something that was
     *  never done. The verified email and phone are not reachable from
     *  here; only the card's answer is. */
    backButton() {
        const allowed = (this.envelope && this.envelope.allowed_actions) || [];
        if (!allowed.includes("go_back")) return "";
        return `
            <button type="button" class="signup-back-link" id="go-back">
                <i data-lucide="arrow-left"></i><span>${this.esc(this.t("su_back_to_record"))}</span>
            </button>`;
    },

    namePanel(choice) {
        // Two spellings of one person, and the question is only
        // answerable if you can see where each one lives. So an option
        // carries three things in a fixed order: the source, straddling
        // the border like a label on a file; the name itself, which is
        // the content; and what picking it does.
        //
        // Colour marks the source, never a recommended answer. Styling
        // one as the safe default would be steering a decision that is
        // the person's to make.
        const option = (id, source, icon, labelKey, hintKey, value) => `
            <button type="button" class="signup-name-option" id="${id}" data-source="${source}">
                <span class="name-source">${this.esc(this.t(labelKey))}</span>
                <span class="name-body">
                    <span class="signup-name-value">${this.esc(value)}</span>
                    <span class="name-action">${this.esc(this.t(hintKey))}</span>
                </span>
                <i data-lucide="${icon}" class="name-mark"></i>
            </button>`;

        return `
            ${this.header("su_name_title", "su_name_sub", 4)}
            <div class="signup-name-options">
                ${option("name-keep", "record", "file-badge",
                         "su_name_keep_label", "su_name_keep_hint", choice.stored)}
                ${option("name-use", "typed", "user-pen",
                         "su_name_use_label", "su_name_use_hint", choice.submitted)}
            </div>
            <p class="signup-match-note">
                <i data-lucide="info"></i><span>${this.esc(this.t("su_name_note"))}</span>
            </p>
            ${this.backButton()}`;
    },

    /** How many name components somebody supplied — mirrors
     *  signup/identity.py `name_components`, which is the authority. */
    nameComponents(raw) {
        return String(raw || "")
            .replace(/\s+/g, " ")
            .trim()
            .split(" ")
            // \p{L}, not [^\W\d_]: JavaScript's \W is ASCII-only even under
            // the `u` flag, so that class counted Arabic, Chinese and
            // Cyrillic names as zero components and refused them at the
            // first step - on a shop whose customers are mostly Arabic.
            .filter(token => /\p{L}/u.test(token)).length;
    },

    passwordGuide() {
        const row = key => `
            <li class="pw-check" data-check="${key}">
                <span class="pw-check-mark" aria-hidden="true"></span>
                <span>${this.esc(this.t("su_pw_" + key))}</span>
            </li>`;
        return `
            <div class="pw-guide" id="pw-guide">
                <p class="pw-guide-title">${this.esc(this.t("su_pw_title"))}</p>
                <ul class="pw-checks">
                    ${row("length")}${row("mix")}${row("personal")}${row("common")}
                </ul>
            </div>`;
    },

    paintPasswordGuide() {
        const input = document.getElementById("su-password");
        const guide = document.getElementById("pw-guide");
        if (!input || !guide) return;

        const checks = this.passwordChecks(input.value);
        guide.querySelectorAll(".pw-check").forEach(item => {
            item.classList.toggle("is-met", !!checks[item.dataset.check]);
        });
    },

    submitPassword(event) {
        event.preventDefault();
        const password = document.getElementById("su-password")?.value || "";
        const confirmation = document.getElementById("su-password2")?.value || "";

        if (!password || !confirmation) return this.setError(this.t("su_err_password"));
        if (password !== confirmation) return this.setError(this.t("su_err_password_match"));

        // The same four rules the guide shows and the server enforces. Checked
        // here so the answer arrives in the page's own language, next to the
        // list that explains it, rather than as a server message in English.
        const checks = this.passwordChecks(password);
        if (!Object.keys(checks).every(key => checks[key])) {
            this.paintPasswordGuide();
            return this.setError(this.t("su_err_password_weak"));
        }

        const params = new URLSearchParams(window.location.search);
        this.run("complete", {
            password: password,
            confirm_password: confirmation,
            redirect_to: params.get("redirect-to") || "",
        }, document.getElementById("password-next"));
    },

    /* ── Resend cooldown ───────────────────────────────────────────── */
    startResendCountdown() {
        clearInterval(this.resendTimer);
        const button = document.getElementById("otp-resend");
        if (!button) return;

        let remaining = (this.envelope && this.envelope.data && this.envelope.data.resend_in) || 0;
        if (!remaining) return;

        const tick = () => {
            remaining -= 1;
            if (remaining <= 0) {
                clearInterval(this.resendTimer);
                button.disabled = false;
                button.textContent = this.t("su_resend");
                return;
            }
            button.textContent = this.t("su_resend_in", { n: remaining });
        };

        button.disabled = true;
        button.textContent = this.t("su_resend_in", { n: remaining });
        this.resendTimer = setInterval(tick, 1000);
    },
};

window.Signup = Signup;
