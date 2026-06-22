import frappe
from frappe import _
from frappe.utils import escape_html, get_url
from frappe.utils.data import cint
from frappe.website.utils import is_signup_disabled
from frappe.core.doctype.user.user import test_password_strength, handle_password_test_fail


@frappe.whitelist(allow_guest=True)
def custom_sign_up(
    email: str, full_name: str, redirect_to: str, pwd: str, mobile_no: str = None
):
    """Custom sign up that validates input, creates the user, and auto-creates
    a Customer, Contact, and Portal User for the new account."""

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

    # Create user with the real password
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": escape_html(full_name),
            "enabled": 1,
            "new_password": pwd,
            "user_type": "Website User",
            "mobile_no": mobile_no,
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

    # Auto-create Customer, Contact, and Portal User for the new signup
    _create_new_customer_for_user(user)

    return 1, {"status": "created", "message": _("Account created successfully! Please log in.")}


def _create_new_customer_for_user(user):
    """Create a new Customer, Contact, and Portal User for a fresh signup.
    If a Customer with the same name already exists, link to it instead."""

    customer_name = user.first_name or user.name

    # Check if Customer already exists with this name
    existing_customer = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")

    if existing_customer:
        customer = frappe.get_doc("Customer", existing_customer)
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

    # Reuse the Contact auto-created by Customer.create_primary_contact
    # instead of creating a duplicate.
    contact_name = customer.customer_primary_contact
    if not contact_name:
        contact_name = frappe.db.get_value(
            "Dynamic Link",
            {"link_doctype": "Customer", "link_name": customer.name, "parenttype": "Contact"},
            "parent"
        )

    if contact_name:
        contact = frappe.get_doc("Contact", contact_name)
    else:
        contact = frappe.new_doc("Contact")

    contact.first_name = user.first_name or user.name
    contact.email_id = user.email
    contact.user = user.name
    contact.is_primary_contact = 1

    if not any(e.email_id == user.email for e in contact.get("email_ids", [])):
        contact.append("email_ids", {"email_id": user.email, "is_primary": 1})

    if user.mobile_no:
        if not any(p.phone == user.mobile_no for p in contact.get("phone_nos", [])):
            contact.append("phone_nos", {"phone": user.mobile_no, "is_primary_mobile_no": 1})

    has_customer_link = any(
        l.link_doctype == "Customer" and l.link_name == customer.name
        for l in contact.get("links", [])
    )
    if not has_customer_link:
        contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})

    contact.flags.ignore_mandatory = True
    contact.flags.ignore_permissions = True
    if contact.is_new():
        contact.insert()
    else:
        contact.save()

    # Set customer_primary_contact so Customer.create_primary_contact never fires later
    if not customer.customer_primary_contact:
        customer.db_set("customer_primary_contact", contact.name)
    if not customer.email_id:
        customer.db_set("email_id", user.email)
    if not customer.mobile_no:
        customer.db_set("mobile_no", user.mobile_no)

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



