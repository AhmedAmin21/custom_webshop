import re

import frappe
from frappe import _
from frappe.utils import escape_html, get_url
from frappe.utils.data import cint
from frappe.website.utils import is_signup_disabled
from frappe.core.doctype.user.user import test_password_strength, handle_password_test_fail


def _log_match_attempt(message: str, data: dict | None = None):
    """Write a structured log so we can debug why a match failed."""
    title = "[custom_webshop] Customer Match Attempt"
    if data:
        message += "\nData: " + str(data)
    frappe.log_error(title=title, message=message)


@frappe.whitelist(allow_guest=True)
def custom_sign_up(
    email: str, full_name: str, redirect_to: str, pwd: str,
    has_past_transactions: int = 0, mobile: str = ""
):
    """Custom sign up that validates input, optionally matches an existing customer
    BEFORE creating the user, then creates the user and handles follow-up."""

    if is_signup_disabled():
        frappe.throw(_("Sign Up is disabled"), title=_("Not Allowed"))

    user = frappe.db.get("User", {"email": email})
    if user:
        if user.enabled:
            return 0, _("Already Registered")
        else:
            return 0, _("Registered but disabled")

    # Rate limit check
    max_signups = cint(frappe.get_system_settings("max_signups_allowed_per_hour") or 300)
    if frappe.db.get_creation_count("User", 60) >= max_signups:
        frappe.respond_as_web_page(
            _("Temporarily Disabled"),
            _("Too many users signed up recently. Please try back in an hour"),
            http_status_code=429,
        )

    # Validate password strength server-side if policy is enabled
    enable_password_policy = cint(frappe.get_system_settings("enable_password_policy") or 0)
    if enable_password_policy:
        result = test_password_strength(pwd, user_data=(full_name, None, None, email, None))
        feedback = result.get("feedback", {})
        if not feedback.get("password_policy_validation_passed", False):
            handle_password_test_fail(feedback)

    # ── Match existing customer BEFORE creating the user ──
    if cint(has_past_transactions):
        match_result = _find_and_match_old_customer(full_name, mobile)
        if not match_result:
            return 0, _(
                "No matching customer record found. "
                "Please ensure the full name and mobile number match our records exactly, "
                "or uncheck 'I have purchased before' to create a new account."
            )
        # Match found – proceed to create user below
    else:
        match_result = None

    # Create user with the real password
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": escape_html(full_name),
            "enabled": 1,
            "new_password": pwd,
            "user_type": "Website User",
        }
    )
    user.flags.ignore_permissions = True
    # Block the default "Complete Registration" email with password-reset link
    user.flags.no_welcome_mail = True
    user.insert()

    # Assign default portal role (kept as-is per custom_webshop pattern)
    default_role = frappe.get_single_value("Portal Settings", "default_role")
    if default_role:
        user.add_roles(default_role)

    # Cache redirect
    if redirect_to:
        from frappe.www.login import sanitize_redirect

        frappe.cache.hset("redirect_after_login", user.name, sanitize_redirect(redirect_to))

    # Send custom welcome email (no password reset link)
    site_name = (
        frappe.db.get_default("site_name")
        or frappe.get_conf().get("site_name")
        or _("ERPNext")
    )
    subject = _("Welcome to {0}").format(site_name)

    frappe.sendmail(
        recipients=user.email,
        subject=subject,
        template="custom_welcome_email",
        args={
            "first_name": user.first_name,
            "site_url": get_url(),
            "site_name": site_name,
        },
        now=True,
    )

    # ── Handle customer linkage after user creation ──
    if match_result:
        # Return the match result so the front-end can show confirmation
        return 1, match_result
    else:
        _create_new_customer_for_user(user)

    return 1, {"status": "created", "message": _("Account created successfully! Please log in.")}


def _normalize_phone(phone: str) -> str:
    """Strip all non-digit characters for consistent matching."""
    return re.sub(r"\D", "", phone or "")


def _normalize_name(name: str) -> str:
    """Lowercase, strip, and collapse whitespace for fuzzy name matching."""
    return re.sub(r"\s+", " ", (name or "").lower().strip())


def _find_and_match_old_customer(full_name: str, mobile: str) -> dict | None:
    """Search for an existing Contact by mobile + full name (case-insensitive,
    whitespace-tolerant), linked to exactly one Customer.
    Return match details or None."""

    normalized_mobile = _normalize_phone(mobile)
    normalized_full_name = _normalize_name(full_name)

    _log_match_attempt(
        "Starting match search",
        {
            "input_full_name": full_name,
            "input_mobile": mobile,
            "normalized_full_name": normalized_full_name,
            "normalized_mobile": normalized_mobile,
        },
    )

    if not normalized_mobile or not normalized_full_name:
        _log_match_attempt(
            "Aborted – missing mobile or full_name",
            {"normalized_mobile": normalized_mobile, "normalized_full_name": normalized_full_name},
        )
        return None

    # 1. Gather candidate contacts by normalized mobile
    candidate_names = set()

    # Via Contact.mobile_no
    contacts = frappe.get_all(
        "Contact",
        filters=[["mobile_no", "!=", ""]],
        fields=["name", "mobile_no"],
        ignore_permissions=True,
    )
    for c in contacts:
        if _normalize_phone(c.mobile_no) == normalized_mobile:
            candidate_names.add(c.name)

    # Via Contact Phone child table
    phones = frappe.get_all(
        "Contact Phone",
        filters=[["phone", "!=", ""]],
        fields=["parent", "phone"],
        ignore_permissions=True,
    )
    for p in phones:
        if _normalize_phone(p.phone) == normalized_mobile:
            candidate_names.add(p.parent)

    _log_match_attempt(
        "Candidates after mobile search",
        {
            "candidate_count": len(candidate_names),
            "candidates": list(candidate_names),
        },
    )

    if not candidate_names:
        _log_match_attempt("No contacts matched the mobile number.")
        return None

    # 2. Filter by normalized full_name match and exactly one Customer link
    matches = []
    rejected_names = []
    for contact_name in candidate_names:
        contact = frappe.get_doc("Contact", contact_name)
        contact_normalized_name = _normalize_name(contact.full_name)

        if contact_normalized_name != normalized_full_name:
            rejected_names.append(
                {
                    "contact": contact.name,
                    "contact_full_name": contact.full_name,
                    "contact_normalized_name": contact_normalized_name,
                    "reason": "name_mismatch",
                }
            )
            continue

        customer_links = [l for l in contact.links if l.link_doctype == "Customer"]
        if len(customer_links) == 1:
            matches.append(
                {
                    "contact": contact.name,
                    "customer": customer_links[0].link_name,
                }
            )
        else:
            rejected_names.append(
                {
                    "contact": contact.name,
                    "contact_full_name": contact.full_name,
                    "reason": f"customer_link_count={len(customer_links)}",
                }
            )

    _log_match_attempt(
        "After name + customer-link filtering",
        {
            "matches": matches,
            "rejected": rejected_names,
        },
    )

    # Skip if 0 or multiple matches
    if len(matches) != 1:
        _log_match_attempt(
            f"Match count != 1 (count={len(matches)}). Aborting.",
            {"matches": matches},
        )
        return None

    customer_name = matches[0]["customer"]

    # 3. Fetch latest submitted Sales Invoice with items
    latest_invoice = frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer_name, "docstatus": 1},
        fields=["name", "posting_date", "grand_total"],
        order_by="posting_date desc, creation desc",
        limit=1,
        ignore_permissions=True,
    )

    if not latest_invoice:
        _log_match_attempt(
            "No submitted Sales Invoice found for customer.",
            {"customer": customer_name},
        )
        return None

    invoice = latest_invoice[0]
    items = frappe.get_all(
        "Sales Invoice Item",
        filters={"parent": invoice.name},
        fields=["item_name", "qty"],
        limit=5,
        ignore_permissions=True,
    )

    customer_docname = frappe.db.get_value("Customer", customer_name, "customer_name")

    _log_match_attempt(
        "Match found successfully.",
        {
            "customer": customer_name,
            "contact": matches[0]["contact"],
            "invoice": invoice.name,
        },
    )

    return {
        "status": "match_found",
        "customer_name": customer_docname or customer_name,
        "contact": matches[0]["contact"],
        "customer": customer_name,
        "invoice": {
            "name": invoice.name,
            "posting_date": str(invoice.posting_date),
            "grand_total": invoice.grand_total,
            "items": items,
        },
    }


def _create_new_customer_for_user(user):
    """Create a new Customer, Contact, and Portal User for a fresh signup.
    If a Customer with the same name already exists, link to it instead."""

    customer_name = user.first_name or user.name

    # Check if Customer already exists with this name
    existing_customer = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")

    if existing_customer:
        customer = frappe.get_doc("Customer", existing_customer)
        _log_match_attempt(
            "Existing Customer found during fresh signup; linking user.",
            {"customer": customer.name, "user": user.name},
        )
    else:
        # Create Customer
        customer = frappe.new_doc("Customer")
        customer.update(
            {
                "customer_name": customer_name,
                "customer_type": "Individual",
            }
        )
        customer.flags.ignore_mandatory = True
        customer.flags.ignore_permissions = True
        customer.insert()

    # Check if a Contact already exists for this user email
    existing_contact_name = frappe.db.get_value("Contact", {"email_id": user.email}, "name")

    if existing_contact_name:
        contact = frappe.get_doc("Contact", existing_contact_name)
        contact.user = user.name
        # Ensure Customer link exists
        has_customer_link = any(
            l.link_doctype == "Customer" and l.link_name == customer.name
            for l in contact.get("links", [])
        )
        if not has_customer_link:
            contact.append(
                "links", {"link_doctype": "Customer", "link_name": customer.name}
            )
        contact.flags.ignore_permissions = True
        contact.save()
    else:
        # Create Contact linked to Customer + User
        contact = frappe.new_doc("Contact")
        contact.first_name = user.first_name or user.name
        contact.email_id = user.email
        contact.user = user.name
        contact.is_primary_contact = 1
        contact.append("email_ids", {"email_id": user.email, "is_primary": 1})
        contact.append(
            "links", {"link_doctype": "Customer", "link_name": customer.name}
        )
        contact.flags.ignore_mandatory = True
        contact.flags.ignore_permissions = True
        contact.insert()

    # Add Portal User row manually (avoids triggering automatic Customer role assignment)
    existing_portal_user = frappe.db.exists(
        "Portal User", {"parent": customer.name, "user": user.name, "parenttype": "Customer"}
    )
    if not existing_portal_user:
        portal_user = frappe.new_doc("Portal User")
        portal_user.update(
            {
                "parenttype": "Customer",
                "parentfield": "portal_users",
                "parent": customer.name,
                "user": user.name,
            }
        )
        portal_user.insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def confirm_customer_mapping(customer: str, contact: str, user: str):
    """Link an existing Customer/Contact to a newly created User."""

    # 1. Update Contact
    contact_doc = frappe.get_doc("Contact", contact)
    contact_doc.user = user

    # Ensure user's email is in email_ids, set as primary
    has_email = any(
        e.email_id == user for e in contact_doc.get("email_ids", [])
    )
    if not has_email:
        # Unset existing primary
        for e in contact_doc.get("email_ids", []):
            if e.is_primary:
                e.is_primary = 0
        contact_doc.append("email_ids", {"email_id": user, "is_primary": 1})
        contact_doc.email_id = user

    # Ensure Customer Dynamic Link exists
    has_customer_link = any(
        l.link_doctype == "Customer" and l.link_name == customer
        for l in contact_doc.get("links", [])
    )
    if not has_customer_link:
        contact_doc.append(
            "links", {"link_doctype": "Customer", "link_name": customer}
        )

    contact_doc.flags.ignore_permissions = True
    contact_doc.save()

    # 2. Add Portal User row (manual insert to suppress automatic role assignment)
    existing = frappe.db.exists(
        "Portal User", {"parent": customer, "user": user, "parenttype": "Customer"}
    )
    if not existing:
        portal_user = frappe.new_doc("Portal User")
        portal_user.update(
            {
                "parenttype": "Customer",
                "parentfield": "portal_users",
                "parent": customer,
                "user": user,
            }
        )
        portal_user.insert(ignore_permissions=True)

    return {"status": "mapped"}
