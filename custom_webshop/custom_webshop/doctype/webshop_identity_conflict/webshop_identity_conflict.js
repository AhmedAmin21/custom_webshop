// Copyright (c) 2026, ahmedamin and contributors
// For license information, please see license.txt

/**
 * The identity queue, made readable.
 *
 * What this replaces: a form whose first field was a screaming-snake constant,
 * whose "records involved" was a JSON blob in a text box, and whose only
 * affordance was a button labelled "Review and Resolve". Somebody who did not
 * write this app had no way to tell what had happened or what they were being
 * asked to decide.
 *
 * So the form opens with a briefing instead — what happened, in words; who it
 * is about; the records side by side with what each is worth in submitted
 * documents; and the choices as buttons that say what they do. The stored
 * fields are still there, collapsed, for when somebody wants the raw values.
 *
 * Only the merge keeps a dialog. `rename_doc(..., merge=True)` cannot be
 * undone, so that one still makes you pick a survivor and type its name.
 */

/**
 * A language switch for this document only.
 *
 * Deliberately not `frappe.local.lang`, a User's `language` field, or
 * anything else that is shared with another page or another person: this
 * is a plain object this file owns, a state flag this file owns, and one
 * `localStorage` key namespaced to this doctype so the choice survives a
 * reload without becoming a site setting. Toggling it changes what one
 * staff member sees on one document. Nothing else - not the list view,
 * not another doctype, not the next person who opens this same record -
 * is touched by it.
 *
 * Covers the strings this file itself renders. The panel's prose
 * (headline, what-happened, what-to-do, per-problem text) comes from the
 * server instead, via `get_resolution_options`'s own `lang` argument -
 * same reasoning, same scope, kept in step by hand with this table and
 * with translations/ar.csv.
 */
const WIC_AR = {
    "A merge cannot be undone.": "لا يمكن التراجع عن الدمج.",
    "Account": "الحساب",
    "Add to Foreign Name": "إضافة إلى الاسم الأجنبي",
    "Add {0} to the contact's Foreign Name field?": "إضافة {0} إلى حقل \"الاسم الأجنبي\" الخاص بجهة الاتصال؟",
    "Already in the system": "موجود بالفعل في النظام",
    "Already {0}. Nothing further to do here.": "تم بالفعل {0}. لا يوجد ما يُتخذ هنا بعد الآن.",
    "Applying…": "جارٍ التطبيق…",
    "Change nothing and stop it resurfacing": "عدم تغيير أي شيء ووقف ظهوره مجددًا",
    "Company given": "اسم الشركة المقدَّم",
    "Confirm": "تأكيد",
    "Contact": "جهة الاتصال",
    "Convert this customer to the company {0}?": "تحويل هذا العميل إلى الشركة {0}؟",
    "Convert this customer to the individual {0}?": "تحويل هذا العميل إلى الفرد {0}؟",
    "Could not read this conflict.": "تعذّرت قراءة بيانات هذا التعارض.",
    "Customer": "العميل",
    "Deliveries": "مذكرات التسليم",
    "Different people": "أشخاص مختلفون",
    "Dismiss the whole case": "تجاهل الحالة بالكامل",
    "Dismiss this conflict?": "تجاهل هذا التعارض؟",
    "Dismissed": "تم التجاهل",
    // Values interpolated into templates above, rather than literal
    // __() strings - the customer_type/account_type field values as
    // they arrive from the server, in both the case Frappe stores them
    // and the lowercase form this file's own .toLowerCase() calls use.
    "Company": "شركة",
    "Individual": "فرد",
    "Partnership": "شراكة",
    "company": "شركة",
    "individual": "فرد",
    "partnership": "شراكة",
    "resolved": "حلّه",
    "dismissed": "تجاهله",
    "Done.": "تم.",
    "History": "السجل التاريخي",
    "In Review": "قيد المراجعة",
    "Invoices": "الفواتير",
    "Keep both records as they are?": "الإبقاء على كلا السجلين كما هما؟",
    "Keep it as {0}": "الإبقاء عليه كـ {0}",
    "Keep the record as it is": "الإبقاء على السجل كما هو",
    "Keeps {0} as the contact's name and saves {1} in its Foreign Name field — matched on {2}": "يُبقي {0} اسمًا لجهة الاتصال، ويحفظ {1} في حقل \"الاسم الأجنبي\" الخاص بها — تمت المطابقة عبر {2}",
    "Leave this customer's type as it is?": "الإبقاء على نوع هذا العميل كما هو؟",
    "Mark this one settled with nothing changed?": "وضع علامة على هذه المشكلة كمحلولة دون تغيير أي شيء؟",
    "Marks this one looked at and leaves every record as it is": "يضع علامة على أنه تمت مراجعة هذه المشكلة، ويُبقي كل سجل كما هو",
    "Merge Permanently": "الدمج بشكل نهائي",
    "Merge these records": "دمج هذين السجلين",
    "Name": "الاسم",
    "Neither record has submitted documents, so nothing is at risk beyond the record itself.": "لا يحتوي أيّ من السجلين على مستندات مُرسَلة، لذا لا يوجد ما هو معرَّض للخطر سوى السجل نفسه.",
    "No customer records are attached to this conflict.": "لا توجد سجلات عملاء مرتبطة بهذا التعارض.",
    "None of this was a real problem": "لم يكن أيٌّ من هذا مشكلة حقيقية",
    "Not Merged": "لم يتم الدمج",
    "Note (optional)": "ملاحظة (اختياري)",
    "Note for the record (optional)": "ملاحظة للسجل (اختياري)",
    "Nothing changes — a person being the contact on a company account is the ordinary shape of one": "لا شيء يتغيّر — كون الشخص هو جهة الاتصال لحساب شركة هو الشكل المعتاد لهذا النوع من الحسابات",
    "Nothing to change here": "لا شيء يتطلب التغيير هنا",
    "One record survives; this cannot be undone": "يبقى سجل واحد فقط بعد الدمج؛ ولا يمكن التراجع عن ذلك",
    "Only the phone matched this record — the email did not. If that number was reassigned, these are two people and this would put one person's name on the other's contact. Check before confirming.": "رقم الهاتف فقط هو ما طابق هذا السجل — أما البريد الإلكتروني فلم يطابقه. إذا كان هذا الرقم قد أُعيد تخصيصه لشخص آخر، فهذان شخصان مختلفان، وهذا الإجراء سيضع اسم أحدهما على جهة اتصال الآخر. تحقّق قبل التأكيد.",
    "Open": "مفتوح",
    "Or, for the whole case": "أو، بالنسبة للحالة بأكملها",
    "Payments": "الدفعات",
    "Reading the records…": "جارٍ قراءة السجلات…",
    "Record to keep": "السجل الذي سيتم الإبقاء عليه",
    "Record type": "نوع السجل",
    "Rename the contact and account to {0}?": "إعادة تسمية جهة الاتصال والحساب إلى {0}؟",
    "Renames the contact and their account to {0}, and the customer too when it is an individual": "يعيد تسمية جهة الاتصال وحسابهم إلى {0}، وكذلك العميل عندما يكون فردًا",
    "Renames this customer to {0} and sets its type to Company — the person stays as its contact": "يعيد تسمية هذا العميل إلى {0} ويضبط نوعه على \"شركة\" — ويبقى الشخص جهة الاتصال الخاصة بها",
    "Renames this customer to {0} and sets its type to Individual — for a person entered as a business": "يعيد تسمية هذا العميل إلى {0} ويضبط نوعه على \"فرد\" — لشخص تم إدخاله سابقًا كشركة",
    "Resolved": "تم الحل",
    "Sales Orders": "أوامر البيع",
    "Same person — merge": "نفس الشخص — دمج",
    "Signed up as": "سجّل باعتباره",
    "Switch it to a company": "تحويله إلى شركة",
    "Switch it to an individual": "تحويله إلى فرد",
    "Their name is right": "اسمهم صحيح",
    "Type <b>{0}</b> exactly to confirm.": "اكتب <b>{0}</b> بالضبط للتأكيد.",
    "Type the name of the record you are keeping": "اكتب اسم السجل الذي ستبقي عليه",
    "Typed rather than clicked, because it cannot be undone.": "يُكتب بدلاً من النقر عليه، لأنه لا يمكن التراجع عنه.",
    "Verified email": "البريد الإلكتروني الموثّق",
    "Verified phone": "رقم الهاتف الموثّق",
    "What they submitted": "ما قدّموه",
    "both channels": "كلا القناتين",
    "disabled": "مُعطَّل",
    "holds the number": "يحمل هذا الرقم",
    "made by this signup": "أنشأه هذا التسجيل",
    "nothing submitted yet": "لم يُقدَّم شيء بعد",
    "nothing verified": "لا شيء تم التحقق منه",
    "number pending": "الرقم قيد الانتظار",
    "settled": "تمت التسوية",
    "the email": "البريد الإلكتروني",
    "the phone": "رقم الهاتف",
    "the stored name": "الاسم المخزَّن",
    "{0} has submitted documents. Whichever you keep, the other's history moves onto it — but the record itself is deleted.": "لدى {0} مستندات مُرسَلة. أيًّا كان السجل الذي ستبقي عليه، سينتقل إليه سجل الآخر التاريخي — لكن السجل نفسه سيُحذف.",
};

const WIC_LANG_KEY = "custom_webshop:wic_lang";
let WIC_LANG = (() => {
    try {
        return localStorage.getItem(WIC_LANG_KEY) === "ar" ? "ar" : "en";
    } catch (e) {
        return "en";
    }
})();

function wicText(source, args) {
    let value = WIC_LANG === "ar" && WIC_AR[source] ? WIC_AR[source] : source;
    (args || []).forEach((a, i) => {
        value = value.replace(new RegExp("\\{" + i + "\\}", "g"), a);
    });
    return value;
}

frappe.ui.form.on("Webshop Identity Conflict", {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.disable_save();
        render_briefing(frm);
    },
});

function render_briefing(frm) {
    const wrapper = frm.get_field("briefing").$wrapper;
    wrapper.html(`<div class="wic-loading">${wicText("Reading the records…")}</div>`);

    frappe.call({
        method: "custom_webshop.api.conflicts.get_resolution_options",
        // `lang` asks the server to render this one call's text in the
        // toggle's chosen language, independently of the caller's own
        // session - see `wicText` above and `_with_language` server-side.
        // Sent only when Arabic: the endpoint's own session-language
        // default already covers "en" and everyone who never touches
        // the toggle.
        args: { conflict: frm.doc.name, lang: WIC_LANG === "ar" ? "ar" : undefined },
        callback: ({ message }) => {
            if (!message) return;
            wrapper.html(build(message));
            wire(frm, wrapper, message);
        },
        error: () => {
            wrapper.html(
                `<div class="wic-panel wic-stop">${wicText("Could not read this conflict.")}</div>`
            );
        },
    });
}

function toggle_language(frm) {
    WIC_LANG = WIC_LANG === "ar" ? "en" : "ar";
    try {
        localStorage.setItem(WIC_LANG_KEY, WIC_LANG);
    } catch (e) {
        // Private-browsing/storage-blocked: the toggle still works for
        // this page view, it just will not be remembered next time.
    }
    render_briefing(frm);
}

/* ── The panel ──────────────────────────────────────────────────────── */

function build(o) {
    const closed = o.is_closed;
    const esc = frappe.utils.escape_html;

    return `
        ${styles()}
        <div class="wic" dir="${WIC_LANG === "ar" ? "rtl" : "ltr"}">
            <div class="wic-head">
                <div>
                    <div class="wic-eyebrow">${esc(o.conflict_type)}</div>
                    <h3 class="wic-title">${esc(o.headline)}</h3>
                </div>
                <div class="wic-head-right">
                    <button type="button" class="wic-lang-toggle" title="${esc(
                        WIC_LANG === "ar" ? "Show this document in English" : "عرض هذا المستند بالعربية"
                    )}">${WIC_LANG === "ar" ? "EN" : "AR"}</button>
                    <span class="wic-status wic-${closed ? "done" : "open"}">${esc(wicText(o.status))}</span>
                </div>
            </div>

            <p class="wic-lede">${esc(o.what_happened)}</p>

            ${comparison(o)}

            ${closed
                ? `<div class="wic-panel wic-done-panel">
                       ${wicText("Already {0}. Nothing further to do here.", [wicText(o.status.toLowerCase())])}
                   </div>`
                : ""}
            ${problems(o, closed)}
            ${closed ? "" : `<div class="wic-case-actions">
                    <div class="wic-k">${wicText("Or, for the whole case")}</div>
                    ${choices(o, ["dismiss"])}
                </div>`}

            ${o.resolution_notes ? notes(o.resolution_notes) : ""}
        </div>`;
}

// The whole job of this panel is one comparison: what the person typed
// against what the records already hold. It used to be two stacked
// blocks - "the person", then "the records" - which made the reader hold
// three values in their head while scrolling to find the other three.
// Side by side, the disagreement is the thing you see first, and the
// rows that actually differ are marked so the eye lands on them.
//: Which actions answer which question. A problem's section offers only
//: the buttons that settle it - the whole point of splitting the case
//: into sections rather than showing every action against every row.
const ANSWERS = {
    PROFILE_DISCREPANCY: ["add_foreign_name", "apply_name"],
    PHONE_NAME_MISMATCH: ["add_foreign_name", "apply_name"],
    EMAIL_NAME_MISMATCH: ["add_foreign_name", "apply_name"],
    ACCOUNT_TYPE_MISMATCH: ["make_company", "make_individual", "keep_type"],
    MULTIPLE_PHONE_MATCHES: ["merge", "keep_separate"],
    PHONE_ALREADY_ASSOCIATED: ["merge", "keep_separate"],
    CUSTOMER_ALREADY_LINKED: ["merge", "keep_separate"],
    USER_REJECTED_MATCH: ["keep_separate"],
    MATCHED_CUSTOMER_DISABLED: [],
};

// One section per thing wrong with the signup, each asking its own
// question and offering only what answers it. A case that is wrong in
// three ways is one row with three sections - it used to be three rows,
// each showing every action.
function problems(o, closed) {
    const esc = frappe.utils.escape_html;
    const all = o.problems && o.problems.length
        ? o.problems
        : [{problem_type: o.conflict_type, headline: o.headline,
            what_to_do: o.what_to_do, resolved: closed}];

    return all
        .map((p) => {
            const buttons = closed || p.resolved
                ? ""
                : choices(o, ANSWERS[p.problem_type], p.problem_type);
            return `
                <section class="wic-problem${p.resolved ? " wic-settled" : ""}">
                    <div class="wic-problem-head">
                        <span class="wic-problem-k">${esc(p.headline || p.problem_type)}</span>
                        ${p.resolved
                            ? `<span class="wic-settled-tag">${wicText("settled")}</span>`
                            : ""}
                    </div>
                    <p class="wic-problem-v">${esc(p.what_to_do || "")}</p>
                    ${buttons}
                </section>`;
        })
        .join("");
}

function comparison(o) {
    const esc = frappe.utils.escape_html;

    const differs = {
        name: Boolean(o.stored_name && o.submitted_name && o.stored_name !== o.submitted_name),
        type: Boolean(
            o.account_type &&
                (o.parties || []).some((p) => p.customer_type && p.customer_type !== o.account_type)
        ),
    };

    const row = (label, value, flagged) =>
        value
            ? `<div class="wic-row${flagged ? " wic-differs" : ""}">
                   <span>${label}</span><b dir="auto">${esc(value)}</b>
               </div>`
            : "";

    const submitted = [
        row(wicText("Name"), o.submitted_name, differs.name),
        row(wicText("Signed up as"), wicText(o.account_type), differs.type),
        row(wicText("Company given"), o.claimed_company_name, true),
        row(wicText("Verified email"), o.email_normalized),
        row(wicText("Verified phone"), o.phone_e164),
    ].join("");

    const stored = (o.parties || []).length
        ? o.parties.map((p) => storedCard(p, o, differs, esc)).join("")
        : `<div class="wic-empty">${wicText("No customer records are attached to this conflict.")}</div>`;

    return `
        <div class="wic-compare">
            <section class="wic-side">
                <div class="wic-k">${wicText("What they submitted")}</div>
                <div class="wic-rows">${submitted}</div>
            </section>
            <section class="wic-side wic-side-stored">
                <div class="wic-k">${wicText("Already in the system")}</div>
                ${stored}
            </section>
        </div>
        ${o.mergeable && o.suggestion_reason
            ? `<p class="wic-hint">${esc(o.suggestion_reason)}</p>`
            : ""}`;
}

function storedCard(p, o, differs, esc) {
    const f = p.footprint || {};
    const history = [
        [wicText("Sales Orders"), f["Sales Order"]],
        [wicText("Invoices"), f["Sales Invoice"]],
        [wicText("Deliveries"), f["Delivery Note"]],
        [wicText("Payments"), f["Payment Entry"]],
    ]
        .filter(([, n]) => n)
        .map(([l, n]) => `<span>${l} <b>${n}</b></span>`)
        .join("");

    const tags = [];
    if (p.is_signup_customer) tags.push(wicText("made by this signup"));
    if (p.holds_verified_phone) tags.push(wicText("holds the number"));
    if (p.pending_phone) tags.push(wicText("number pending"));
    if (p.disabled) tags.push(wicText("disabled"));

    const flagged = (v) => (differs.name && v ? " wic-differs" : "");
    return `
        <div class="wic-card${p.customer === o.suggested_survivor ? " wic-suggested" : ""}">
            <div class="wic-row${flagged(p.customer_name)}">
                <span>${wicText("Customer")}</span>
                <a class="wic-card-name" dir="auto"
                   href="/app/customer/${encodeURIComponent(p.customer)}">${esc(
                       p.customer_name || p.customer
                   )}</a>
            </div>
            <div class="wic-row${flagged(p.contact_name)}">
                <span>${wicText("Contact")}</span>
                <b dir="auto">${esc(p.contact_name || p.contact || "—")}</b>
            </div>
            <div class="wic-row${
                p.customer_type && o.account_type && p.customer_type !== o.account_type
                    ? " wic-differs"
                    : ""
            }">
                <span>${wicText("Record type")}</span><b>${esc(wicText(p.customer_type) || "—")}</b>
            </div>
            <div class="wic-row"><span>${wicText("Account")}</span><b>${esc(p.user || "—")}</b></div>
            <div class="wic-card-history">
                ${history || `<i>${wicText("nothing submitted yet")}</i>`}</div>
            ${tags.length
                ? `<div class="wic-tags">${tags.map((t) => `<span>${t}</span>`).join("")}</div>`
                : ""}
        </div>`;
}

// Which verified channels reached the record, in words. Named at the
// point of deciding rather than used to hide the button: staff asked for
// it on any match, and a phone-only match is the one worth reading twice.
function matched_on(o) {
    const names = { phone: wicText("the phone"), email: wicText("the email") };
    const channels = (o.foreign_name_channels || []).map((c) => names[c] || c);
    if (channels.length > 1) return wicText("both channels");
    return channels[0] || wicText("nothing verified");
}

function choices(o, allowed, problem) {
    const buttons = [];

    // One person, two scripts, before the "which name wins" question —
    // because when this applies, nothing has to win. An Arabic record and
    // an English signup are one name written twice.
    // Offered before the name questions: if this record is about to
    // become a company, that is the bigger fact about it.
    if (o.company_conversion) {
        buttons.push({
            action: "make_company",
            label: wicText("Switch it to a company"),
            hint: wicText("Renames this customer to {0} and sets its type to Company — the person stays as its contact",
                     [o.company_conversion]),
        });
    }
    // The two answers to "what kind of record is this?", named after what
    // they do to *this* record rather than in the abstract - "leave it as
    // it is" does not tell you what it is being left as.
    const recordType = ((o.parties || [])[0] || {}).customer_type;
    if (o.account_type) {
        buttons.push({
            action: "keep_type",
            label: recordType
                ? wicText("Keep it as {0}", [wicText(recordType.toLowerCase())])
                : wicText("Keep the record as it is"),
            hint: wicText("Nothing changes — a person being the contact on a company account is the ordinary shape of one"),
        });
    }
    if (o.individual_conversion) {
        buttons.push({
            action: "make_individual",
            label: wicText("Switch it to an individual"),
            hint: wicText("Renames this customer to {0} and sets its type to Individual — for a person entered as a business",
                     [o.individual_conversion]),
        });
    }
    if (o.foreign_name) {
        buttons.push({
            action: "add_foreign_name",
            // Named after the field it writes, not after the situation it
            // describes. "Same person, other script" told a reader what
            // the case was and left them to guess what pressing it did.
            label: wicText("Add to Foreign Name"),
            hint: wicText("Keeps {0} as the contact's name and saves {1} in its Foreign Name field — matched on {2}",
                     [o.stored_name || wicText("the stored name"), o.foreign_name, matched_on(o)]),
        });
    }
    if (o.nameable && o.submitted_name !== o.stored_name) {
        buttons.push({
            action: "apply_name",
            label: wicText("Their name is right"),
            // "login" read as though signing in itself changed. It is the
            // name on the account - and the customer is only renamed when
            // it is an individual, never a company renamed to whoever
            // happens to be its contact.
            hint: wicText("Renames the contact and their account to {0}, and the customer too when it is an individual",
                     [o.submitted_name]),
        });
    }
    if (o.mergeable) {
        buttons.push({
            action: "merge",
            label: wicText("Same person — merge"),
            hint: wicText("One record survives; this cannot be undone"),
            danger: true,
        });
        buttons.push({
            action: "keep_separate",
            label: wicText("Different people"),
            hint: wicText("Change nothing and stop it resurfacing"),
        });
    }
    // Dismiss answers the whole case rather than any one question - it
    // means none of this was a real problem - so it is built in here but
    // never listed in a section's ANSWERS, and reached only by asking for
    // it directly.
    buttons.push({
        action: "dismiss",
        label: wicText("Dismiss the whole case"),
        hint: wicText("None of this was a real problem"),
    });

    // A section offers only what answers its own question - plus, always,
    // a way to say there is nothing to do. Some questions have no button
    // of their own: a dispute about an address has no name to apply, and
    // a record already of the right kind has nothing to convert. Without
    // this the section sat there unanswerable and the case could never
    // close.
    const offered = allowed ? buttons.filter((b) => allowed.includes(b.action)) : buttons;
    if (problem) {
        offered.push({
            action: "settle_one",
            problem: problem,
            label: wicText("Nothing to change here"),
            hint: wicText("Marks this one looked at and leaves every record as it is"),
        });
    }
    if (!offered.length) return "";

    return `
        <div class="wic-choices">
            ${offered
                .map(
                    (b) => `
                <button type="button" class="wic-choice${b.danger ? " wic-danger" : ""}"
                        data-action="${b.action}"${b.problem ? ` data-problem="${b.problem}"` : ""}>
                    <span class="wic-choice-label">${b.label}</span>
                    <span class="wic-choice-hint">${b.hint}</span>
                </button>`
                )
                .join("")}
        </div>`;
}

function notes(text) {
    return `
        <details class="wic-notes">
            <summary>${wicText("History")}</summary>
            <pre>${frappe.utils.escape_html(text)}</pre>
        </details>`;
}

/* ── Acting on it ───────────────────────────────────────────────────── */

function wire(frm, wrapper, options) {
    wrapper.find(".wic-lang-toggle").on("click", () => toggle_language(frm));

    wrapper.find(".wic-choice").on("click", function () {
        const action = this.dataset.action;
        if (action === "merge") return merge_dialog(frm, options);
        confirm_simple(frm, options, action, this.dataset.problem);
    });
}

function confirm_simple(frm, options, action, problem) {
    const label = {
        add_foreign_name: wicText("Add {0} to the contact's Foreign Name field?", [options.foreign_name]),
        make_company: wicText("Convert this customer to the company {0}?", [options.company_conversion]),
        make_individual: wicText("Convert this customer to the individual {0}?", [options.individual_conversion]),
        apply_name: wicText("Rename the contact and account to {0}?", [options.submitted_name]),
        keep_separate: wicText("Keep both records as they are?"),
        keep_type: wicText("Leave this customer's type as it is?"),
        settle_one: wicText("Mark this one settled with nothing changed?"),
        dismiss: wicText("Dismiss this conflict?"),
    }[action];

    // Filing a name onto a record reached by the phone alone is the one
    // case worth reading twice: that stored name was withheld from the
    // shopper precisely because Egyptian numbers get reassigned, so the
    // two spellings may belong to two people. Said here rather than by
    // hiding the button, which staff asked to keep on any match.
    const phoneOnly =
        action === "add_foreign_name" &&
        (options.foreign_name_channels || []).join() === "phone";

    const fields = [];
    if (phoneOnly) {
        fields.push({
            fieldtype: "HTML",
            options: `<div class="alert alert-warning" style="margin-bottom:12px">${wicText(
                "Only the phone matched this record — the email did not. If that number was reassigned, these are two people and this would put one person's name on the other's contact. Check before confirming."
            )}</div>`,
        });
    }
    fields.push({
        fieldtype: "Small Text",
        fieldname: "note",
        label: wicText("Note for the record (optional)"),
    });

    const d = new frappe.ui.Dialog({
        title: label,
        fields: fields,
        primary_action_label: wicText("Confirm"),
        primary_action: (values) => {
            d.hide();
            send(frm, {
                conflict: frm.doc.name,
                action: action,
                note: values.note,
                problem: problem,
            });
        },
    });
    d.show();
}

function merge_dialog(frm, options) {
    const withHistory = (options.parties || []).filter((p) => (p.footprint || {}).total);
    const warning = withHistory.length
        ? wicText(
              "{0} has submitted documents. Whichever you keep, the other's history moves onto it — but the record itself is deleted.",
              [withHistory.map((p) => p.customer).join(", ")]
          )
        : wicText("Neither record has submitted documents, so nothing is at risk beyond the record itself.");

    const d = new frappe.ui.Dialog({
        title: wicText("Merge these records"),
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "warn",
                options: `<div class="alert alert-warning" style="font-size:var(--text-sm)">
                    <b>${wicText("A merge cannot be undone.")}</b><br>${warning}</div>`,
            },
            {
                fieldtype: "Select",
                fieldname: "survivor",
                label: wicText("Record to keep"),
                reqd: 1,
                options: options.parties.map((p) => p.customer),
                default: options.suggested_survivor || "",
                description: options.suggestion_reason,
            },
            {
                fieldtype: "Data",
                fieldname: "confirm",
                label: wicText("Type the name of the record you are keeping"),
                reqd: 1,
                description: wicText("Typed rather than clicked, because it cannot be undone."),
            },
            { fieldtype: "Small Text", fieldname: "note", label: wicText("Note (optional)") },
        ],
        primary_action_label: wicText("Merge Permanently"),
        primary_action: (values) => {
            if (values.confirm !== values.survivor) {
                frappe.msgprint({
                    title: wicText("Not Merged"),
                    message: wicText("Type <b>{0}</b> exactly to confirm.", [
                        frappe.utils.escape_html(values.survivor),
                    ]),
                    indicator: "orange",
                });
                return;
            }
            d.hide();
            send(frm, {
                conflict: frm.doc.name,
                action: "merge",
                survivor: values.survivor,
                note: values.note,
            });
        },
    });
    d.get_primary_btn().addClass("btn-danger");
    d.show();
}

function send(frm, args) {
    frappe.call({
        method: "custom_webshop.api.conflicts.resolve_conflict",
        args: args,
        freeze: true,
        freeze_message: wicText("Applying…"),
        callback: ({ message }) => {
            if (!message) return;
            const steps = message.steps || [];
            frappe.show_alert(
                { message: steps[0] || wicText("Done."), indicator: "green" },
                7
            );
            frm.reload_doc();
        },
    });
}

/* ── Styles ─────────────────────────────────────────────────────────── */

function styles() {
    return `<style>
        /* Frappe's own Desk CSS pins several generic tags (p, h3, div text
           runs) to text-align: left directly, not merely as an inherited
           default - so dir="rtl" on the panel below flips character
           ordering (numerals, punctuation) but every block still hugged
           the left edge instead of following it. !important here is
           deliberate and contained to this one panel's own classes: it
           is the only way to out-rank a rule that already used a fixed
           value rather than the logical "start" this panel actually
           wants in both directions. */
        .wic, .wic * { text-align: start !important; }
        .wic { font-size: var(--text-md); }
        .wic-loading { color: var(--text-muted); padding: 1rem 0; }
        .wic-head {
            display: flex; align-items: flex-start; justify-content: space-between;
            gap: 1rem; margin-bottom: .35rem;
        }
        .wic-eyebrow {
            font-family: var(--font-stack-monospace, monospace);
            font-size: var(--text-xs); letter-spacing: .04em;
            color: var(--text-light); margin-bottom: .2rem;
        }
        .wic-title { margin: 0; font-size: var(--text-xl); font-weight: 600; }
        .wic-head-right { display: flex; align-items: center; gap: .5rem; flex: none; }
        .wic-lang-toggle {
            font-size: var(--text-xs); font-weight: 700; letter-spacing: .03em;
            padding: .15rem .5rem; border-radius: 10px; cursor: pointer;
            border: 1px solid var(--border-color); background: var(--fg-color, #fff);
            color: var(--text-muted);
        }
        .wic-lang-toggle:hover { color: var(--text-color); border-color: var(--text-muted); }
        .wic-status {
            flex: none; font-size: var(--text-xs); font-weight: 600;
            padding: .15rem .55rem; border-radius: 10px; white-space: nowrap;
        }
        .wic-open { background: var(--bg-orange); color: var(--text-on-orange, #7a4100); }
        .wic-done { background: var(--bg-green); color: var(--text-on-green, #0a5c36); }
        .wic-lede {
            margin: 0 0 1.1rem; color: var(--text-muted);
            max-width: 46rem; line-height: 1.6;
        }
        .wic-k {
            font-size: var(--text-xs); font-weight: 600; letter-spacing: .06em;
            text-transform: uppercase; color: var(--text-light); margin-bottom: .4rem;
        }
        /* The comparison is the panel. Two columns, the same rows in the
           same order down each, so the eye reads across a line rather
           than holding one side in memory while it scrolls to the other. */
        /* One section per thing wrong with the signup. Each is a
           question with its own answers, so it is boxed as a unit
           rather than run together with the next. */
        .wic-problem {
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius-md);
            padding: .9rem 1rem; margin-bottom: .8rem;
        }
        .wic-problem-head {
            display: flex; align-items: center; gap: .6rem; margin-bottom: .25rem;
        }
        .wic-problem-k { font-size: var(--text-md); font-weight: 600; }
        .wic-problem-v {
            margin: 0 0 .8rem; color: var(--text-muted);
            line-height: 1.6; max-width: 46rem;
        }
        /* A settled question stays visible - the case is one row now, and
           what was already decided is part of reading it - but it steps
           back so the outstanding ones are what you see. */
        .wic-settled { opacity: .62; background: var(--bg-light-gray, #f8f9fa); }
        .wic-settled-tag {
            font-size: var(--text-xs); font-weight: 600;
            background: var(--bg-green, #e8f5e9); color: var(--text-on-green, #0a5c36);
            border-radius: 9px; padding: .05rem .5rem;
        }
        .wic-case-actions { margin-top: 1.2rem; }
        .wic-related {
            margin: 0 0 1rem; padding: .55rem .8rem;
            border-inline-start: 3px solid var(--yellow-300, #f5c518);
            background: var(--bg-yellow, #fffbe6);
            border-radius: 5px; font-size: var(--text-sm);
        }
        .wic-related a { font-weight: 600; }
        .wic-compare {
            display: grid; grid-template-columns: 1fr 1fr;
            gap: .9rem; margin-bottom: 1rem; align-items: start;
        }
        @media (max-width: 60rem) {
            .wic-compare { grid-template-columns: 1fr; }
        }
        .wic-side {
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius-md);
            padding: .85rem .95rem;
            background: var(--card-bg, #fff);
        }
        /* The stored side is the one with consequences, so it carries the
           weight - the submitted side is only what somebody typed. */
        .wic-side-stored { background: var(--bg-light-gray, #f8f9fa); }
        .wic-side .wic-k { margin-bottom: .55rem; }
        .wic-rows { display: grid; gap: .3rem; }
        .wic-row {
            display: grid; grid-template-columns: 8.5rem 1fr;
            gap: .5rem; align-items: baseline;
            padding: .18rem .3rem; border-radius: 5px;
        }
        .wic-row > span { font-size: var(--text-xs); color: var(--text-light); }
        .wic-row > b, .wic-row > a { font-weight: 600; word-break: break-word; }
        /* The rows that disagree are the reason anybody opened this. */
        .wic-differs { background: var(--bg-orange, #fff4e5); }
        .wic-differs > span { color: var(--text-on-orange, #7a4100); }
        .wic-card {
            border: 0; padding: 0; margin-bottom: .7rem;
        }
        .wic-card + .wic-card {
            border-top: 1px solid var(--border-color); padding-top: .7rem;
        }
        .wic-suggested { border-color: var(--primary, #2490ef); }
        .wic-card-name { font-weight: 600; display: block; margin-bottom: .15rem; }
        .wic-card-meta { font-size: var(--text-sm); color: var(--text-muted); }
        .wic-card-history {
            margin-top: .5rem; font-size: var(--text-sm);
            display: flex; flex-wrap: wrap; gap: .15rem .9rem;
        }
        .wic-tags { margin-top: .5rem; display: flex; flex-wrap: wrap; gap: .3rem; }
        .wic-tags span {
            font-size: var(--text-xs); background: var(--bg-light-gray);
            border-radius: 9px; padding: .05rem .5rem;
        }
        .wic-hint {
            font-size: var(--text-sm); color: var(--text-muted);
            margin: 0 0 1.1rem; max-width: 46rem;
        }
        .wic-empty {
            font-size: var(--text-sm); color: var(--text-muted);
            padding: .7rem 0 1.1rem;
        }
        .wic-panel {
            background: var(--bg-light-gray); border-radius: var(--border-radius-md);
            padding: .8rem .95rem; margin-bottom: 1rem;
        }
        .wic-panel-k {
            font-size: var(--text-xs); font-weight: 600; letter-spacing: .06em;
            text-transform: uppercase; color: var(--text-light); margin-bottom: .25rem;
        }
        .wic-panel-v { margin: 0; line-height: 1.6; max-width: 46rem; }
        .wic-done-panel { color: var(--text-muted); }
        .wic-choices {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
            gap: .6rem;
        }
        .wic-choice {
            text-align: start; background: var(--card-bg, #fff);
            border: 1px solid var(--border-color); border-radius: var(--border-radius-md);
            padding: .7rem .85rem; cursor: pointer; display: grid; gap: .15rem;
        }
        .wic-choice:hover { border-color: var(--text-muted); }
        .wic-choice:focus-visible { outline: 2px solid var(--primary, #2490ef); outline-offset: 1px; }
        .wic-choice-label { font-weight: 600; }
        .wic-choice-hint { font-size: var(--text-sm); color: var(--text-muted); line-height: 1.45; }
        .wic-danger .wic-choice-label { color: var(--red-600, #b62b2b); }
        .wic-notes { margin-top: 1.2rem; }
        .wic-notes summary {
            cursor: pointer; font-size: var(--text-sm); color: var(--text-muted);
        }
        .wic-notes pre {
            margin: .5rem 0 0; padding: .7rem .8rem; overflow-x: auto;
            background: var(--bg-light-gray); border-radius: var(--border-radius-md);
            font-size: var(--text-sm); white-space: pre-wrap;
        }
    </style>`;
}
