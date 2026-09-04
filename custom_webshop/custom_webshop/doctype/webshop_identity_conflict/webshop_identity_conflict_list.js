// Copyright (c) 2026, ahmedamin and contributors
// For license information, please see license.txt

// Plain-language names for the list, so the queue reads as a list of
// problems rather than a column of constants. A copy of
// signup/conflicts.py SHORT_LABELS, which is the source of truth - the
// chart's axis reads from that one, and JavaScript cannot import it.
// Change them together, or the same situation ends up with two names.
const WIC_LABELS = {
    PHONE_NAME_MISMATCH: __("Linked, name never shown"),
    EMAIL_NAME_MISMATCH: __("Same email, different name"),
    MULTIPLE_PHONE_MATCHES: __("One number, many customers"),
    PHONE_ALREADY_ASSOCIATED: __("Two records want one number"),
    USER_REJECTED_MATCH: __("They declined the match"),
    PROFILE_DISCREPANCY: __("Disputes stored details"),
    CUSTOMER_ALREADY_LINKED: __("Customer already has an account"),
    EMAIL_ACCOUNT_EXISTS: __("Stopped: email registered"),
    PHONE_ACCOUNT_EXISTS: __("Stopped: number registered"),
    STALE_LINK_DECISION: __("Answer no longer fitted"),
    INCOMPLETE_PROFILE: __("Customer has no address"),
    LEAD_PREFILL_DIVERGENCE: __("Lead details disagree"),
    MATCHED_CUSTOMER_DISABLED: __("Matched record is disabled"),
    ACCOUNT_TYPE_MISMATCH: __("Person/business disagree"),
};

frappe.listview_settings["Webshop Identity Conflict"] = {
    add_fields: ["status", "conflict_type", "opened_on", "submitted_name"],

    formatters: {
        conflict_type(value) {
            return WIC_LABELS[value] || value;
        },
    },


    // Age matters more than type here. A queue is worked by "what has
    // been waiting", so anything untouched for a week turns red whatever
    // it is about - the point of the colour is to be noticed, not to
    // classify.
    get_indicator(doc) {
        if (doc.status === "Resolved") return [__("Resolved"), "green", "status,=,Resolved"];
        if (doc.status === "Dismissed") return [__("Dismissed"), "gray", "status,=,Dismissed"];

        const waiting = frappe.datetime.get_day_diff(
            frappe.datetime.now_datetime(),
            doc.opened_on || doc.creation
        );
        if (waiting >= 7) {
            return [__("Waiting {0} days", [waiting]), "red", "status,in,Open,In Review"];
        }
        if (doc.status === "In Review") return [__("In Review"), "blue", "status,=,In Review"];
        return [__("Open"), "orange", "status,=,Open"];
    },
};
