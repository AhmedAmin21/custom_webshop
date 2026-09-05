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

frappe.ui.form.on("Webshop Identity Conflict", {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.disable_save();
        render_briefing(frm);
    },
});

function render_briefing(frm) {
    const wrapper = frm.get_field("briefing").$wrapper;
    wrapper.html(`<div class="wic-loading">${__("Reading the records…")}</div>`);

    frappe.call({
        method: "custom_webshop.api.conflicts.get_resolution_options",
        args: { conflict: frm.doc.name },
        callback: ({ message }) => {
            if (!message) return;
            wrapper.html(build(message));
            wire(frm, wrapper, message);
        },
        error: () => {
            wrapper.html(
                `<div class="wic-panel wic-stop">${__("Could not read this conflict.")}</div>`
            );
        },
    });
}

/* ── The panel ──────────────────────────────────────────────────────── */

function build(o) {
    const closed = o.is_closed;
    const esc = frappe.utils.escape_html;

    return `
        ${styles()}
        <div class="wic">
            <div class="wic-head">
                <div>
                    <div class="wic-eyebrow">${esc(o.conflict_type)}</div>
                    <h3 class="wic-title">${esc(o.headline)}</h3>
                </div>
                <span class="wic-status wic-${closed ? "done" : "open"}">${esc(o.status)}</span>
            </div>

            <p class="wic-lede">${esc(o.what_happened)}</p>

            ${comparison(o)}

            ${closed
                ? `<div class="wic-panel wic-done-panel">
                       ${__("Already {0}. Nothing further to do here.", [o.status.toLowerCase()])}
                   </div>`
                : ""}
            ${problems(o, closed)}
            ${closed ? "" : `<div class="wic-case-actions">
                    <div class="wic-k">${__("Or, for the whole case")}</div>
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
                            ? `<span class="wic-settled-tag">${__("settled")}</span>`
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
        row(__("Name"), o.submitted_name, differs.name),
        row(__("Signed up as"), o.account_type, differs.type),
        row(__("Company given"), o.claimed_company_name, true),
        row(__("Verified email"), o.email_normalized),
        row(__("Verified phone"), o.phone_e164),
    ].join("");

    const stored = (o.parties || []).length
        ? o.parties.map((p) => storedCard(p, o, differs, esc)).join("")
        : `<div class="wic-empty">${__("No customer records are attached to this conflict.")}</div>`;

    return `
        <div class="wic-compare">
            <section class="wic-side">
                <div class="wic-k">${__("What they submitted")}</div>
                <div class="wic-rows">${submitted}</div>
            </section>
            <section class="wic-side wic-side-stored">
                <div class="wic-k">${__("Already in the system")}</div>
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
        [__("Sales Orders"), f["Sales Order"]],
        [__("Invoices"), f["Sales Invoice"]],
        [__("Deliveries"), f["Delivery Note"]],
        [__("Payments"), f["Payment Entry"]],
    ]
        .filter(([, n]) => n)
        .map(([l, n]) => `<span>${l} <b>${n}</b></span>`)
        .join("");

    const tags = [];
    if (p.is_signup_customer) tags.push(__("made by this signup"));
    if (p.holds_verified_phone) tags.push(__("holds the number"));
    if (p.pending_phone) tags.push(__("number pending"));
    if (p.disabled) tags.push(__("disabled"));

    const flagged = (v) => (differs.name && v ? " wic-differs" : "");
    return `
        <div class="wic-card${p.customer === o.suggested_survivor ? " wic-suggested" : ""}">
            <div class="wic-row${flagged(p.customer_name)}">
                <span>${__("Customer")}</span>
                <a class="wic-card-name" dir="auto"
                   href="/app/customer/${encodeURIComponent(p.customer)}">${esc(
                       p.customer_name || p.customer
                   )}</a>
            </div>
            <div class="wic-row${flagged(p.contact_name)}">
                <span>${__("Contact")}</span>
                <b dir="auto">${esc(p.contact_name || p.contact || "—")}</b>
            </div>
            <div class="wic-row${
                p.customer_type && o.account_type && p.customer_type !== o.account_type
                    ? " wic-differs"
                    : ""
            }">
                <span>${__("Record type")}</span><b>${esc(p.customer_type || "—")}</b>
            </div>
            <div class="wic-row"><span>${__("Account")}</span><b>${esc(p.user || "—")}</b></div>
            <div class="wic-card-history">
                ${history || `<i>${__("nothing submitted yet")}</i>`}</div>
            ${tags.length
                ? `<div class="wic-tags">${tags.map((t) => `<span>${t}</span>`).join("")}</div>`
                : ""}
        </div>`;
}

// Which verified channels reached the record, in words. Named at the
// point of deciding rather than used to hide the button: staff asked for
// it on any match, and a phone-only match is the one worth reading twice.
function matched_on(o) {
    const names = { phone: __("the phone"), email: __("the email") };
    const channels = (o.foreign_name_channels || []).map((c) => names[c] || c);
    if (channels.length > 1) return __("both channels");
    return channels[0] || __("nothing verified");
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
            label: __("Switch it to a company"),
            hint: __("Renames this customer to {0} and sets its type to Company — the person stays as its contact",
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
                ? __("Keep it as {0}", [__(recordType.toLowerCase())])
                : __("Keep the record as it is"),
            hint: __("Nothing changes — a person being the contact on a company account is the ordinary shape of one"),
        });
    }
    if (o.individual_conversion) {
        buttons.push({
            action: "make_individual",
            label: __("Switch it to an individual"),
            hint: __("Renames this customer to {0} and sets its type to Individual — for a person entered as a business",
                     [o.individual_conversion]),
        });
    }
    if (o.foreign_name) {
        buttons.push({
            action: "add_foreign_name",
            // Named after the field it writes, not after the situation it
            // describes. "Same person, other script" told a reader what
            // the case was and left them to guess what pressing it did.
            label: __("Add to Foreign Name"),
            hint: __("Keeps {0} as the contact's name and saves {1} in its Foreign Name field — matched on {2}",
                     [o.stored_name || __("the stored name"), o.foreign_name, matched_on(o)]),
        });
    }
    if (o.nameable && o.submitted_name !== o.stored_name) {
        buttons.push({
            action: "apply_name",
            label: __("Their name is right"),
            // "login" read as though signing in itself changed. It is the
            // name on the account - and the customer is only renamed when
            // it is an individual, never a company renamed to whoever
            // happens to be its contact.
            hint: __("Renames the contact and their account to {0}, and the customer too when it is an individual",
                     [o.submitted_name]),
        });
    }
    if (o.mergeable) {
        buttons.push({
            action: "merge",
            label: __("Same person — merge"),
            hint: __("One record survives; this cannot be undone"),
            danger: true,
        });
        buttons.push({
            action: "keep_separate",
            label: __("Different people"),
            hint: __("Change nothing and stop it resurfacing"),
        });
    }
    // Dismiss answers the whole case rather than any one question - it
    // means none of this was a real problem - so it is built in here but
    // never listed in a section's ANSWERS, and reached only by asking for
    // it directly.
    buttons.push({
        action: "dismiss",
        label: __("Dismiss the whole case"),
        hint: __("None of this was a real problem"),
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
            label: __("Nothing to change here"),
            hint: __("Marks this one looked at and leaves every record as it is"),
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
            <summary>${__("History")}</summary>
            <pre>${frappe.utils.escape_html(text)}</pre>
        </details>`;
}

/* ── Acting on it ───────────────────────────────────────────────────── */

function wire(frm, wrapper, options) {
    wrapper.find(".wic-choice").on("click", function () {
        const action = this.dataset.action;
        if (action === "merge") return merge_dialog(frm, options);
        confirm_simple(frm, options, action, this.dataset.problem);
    });
}

function confirm_simple(frm, options, action, problem) {
    const label = {
        add_foreign_name: __("Add {0} to the contact's Foreign Name field?", [options.foreign_name]),
        make_company: __("Convert this customer to the company {0}?", [options.company_conversion]),
        make_individual: __("Convert this customer to the individual {0}?", [options.individual_conversion]),
        apply_name: __("Rename the contact and account to {0}?", [options.submitted_name]),
        keep_separate: __("Keep both records as they are?"),
        keep_type: __("Leave this customer's type as it is?"),
        settle_one: __("Mark this one settled with nothing changed?"),
        dismiss: __("Dismiss this conflict?"),
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
            options: `<div class="alert alert-warning" style="margin-bottom:12px">${__(
                "Only the phone matched this record — the email did not. If that number was reassigned, these are two people and this would put one person's name on the other's contact. Check before confirming."
            )}</div>`,
        });
    }
    fields.push({
        fieldtype: "Small Text",
        fieldname: "note",
        label: __("Note for the record (optional)"),
    });

    const d = new frappe.ui.Dialog({
        title: label,
        fields: fields,
        primary_action_label: __("Confirm"),
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
        ? __(
              "{0} has submitted documents. Whichever you keep, the other's history moves onto it — but the record itself is deleted.",
              [withHistory.map((p) => p.customer).join(", ")]
          )
        : __("Neither record has submitted documents, so nothing is at risk beyond the record itself.");

    const d = new frappe.ui.Dialog({
        title: __("Merge these records"),
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "warn",
                options: `<div class="alert alert-warning" style="font-size:var(--text-sm)">
                    <b>${__("A merge cannot be undone.")}</b><br>${warning}</div>`,
            },
            {
                fieldtype: "Select",
                fieldname: "survivor",
                label: __("Record to keep"),
                reqd: 1,
                options: options.parties.map((p) => p.customer),
                default: options.suggested_survivor || "",
                description: options.suggestion_reason,
            },
            {
                fieldtype: "Data",
                fieldname: "confirm",
                label: __("Type the name of the record you are keeping"),
                reqd: 1,
                description: __("Typed rather than clicked, because it cannot be undone."),
            },
            { fieldtype: "Small Text", fieldname: "note", label: __("Note (optional)") },
        ],
        primary_action_label: __("Merge Permanently"),
        primary_action: (values) => {
            if (values.confirm !== values.survivor) {
                frappe.msgprint({
                    title: __("Not Merged"),
                    message: __("Type <b>{0}</b> exactly to confirm.", [
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
        freeze_message: __("Applying…"),
        callback: ({ message }) => {
            if (!message) return;
            const steps = message.steps || [];
            frappe.show_alert(
                { message: steps[0] || __("Done."), indicator: "green" },
                7
            );
            frm.reload_doc();
        },
    });
}

/* ── Styles ─────────────────────────────────────────────────────────── */

function styles() {
    return `<style>
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
