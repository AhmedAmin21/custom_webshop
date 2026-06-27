import frappe
from frappe import _
from frappe.utils import escape_html, get_url
from frappe.utils.data import cint
from frappe.website.utils import is_signup_disabled
from frappe.core.doctype.user.user import test_password_strength, handle_password_test_fail


@frappe.whitelist(allow_guest=True)
def custom_sign_up(
    email: str,
    full_name: str,
    pwd: str,
    redirect_to: str = "",
    mobile_no: str = None,
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


def _default_customer_group():
	"""Return a non-group Customer Group (global default may be a group node)."""
	if frappe.db.exists("Customer Group", "Individual"):
		return "Individual"
	group = frappe.db.get_default("customer_group") or "Individual"
	if frappe.db.get_value("Customer Group", group, "is_group"):
		group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	return group or "Individual"


def _default_territory():
	"""Return a non-group Territory (global default may be a group node)."""
	territory = frappe.db.get_default("territory") or "Egypt"
	if frappe.db.get_value("Territory", territory, "is_group"):
		territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
	return territory or "Egypt"


def _create_new_customer_for_user(user):
    """Create a new Customer, Contact, and Portal User for a fresh signup.
    If a Customer with the same name already exists, link to it instead.

    Strategy to avoid duplicate contacts:
    1. Call Frappe's create_contact() synchronously so the Contact exists
       before the Customer is inserted.
    2. Insert the Customer with customer_primary_contact pre-set to that
       Contact, so ERPNext's on_update → create_primary_contact() sees a
       non-empty value and does NOT create a second Contact.
    3. Add the Customer Dynamic Link back onto the Contact.
    """

    customer_name = user.first_name or user.name

    # ── Existing customer path ──────────────────────────────────────────────
    existing_customer = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")

    if existing_customer:
        customer = frappe.get_doc("Customer", existing_customer)

        # Find or update the existing primary contact
        contact_name = customer.customer_primary_contact or frappe.db.get_value(
            "Dynamic Link",
            {"link_doctype": "Customer", "link_name": customer.name, "parenttype": "Contact"},
            "parent",
        )
        if contact_name:
            contact = frappe.get_doc("Contact", contact_name)
        else:
            contact = frappe.new_doc("Contact")

        _fill_contact(contact, user, customer.name)
        contact.flags.ignore_mandatory = True
        contact.flags.ignore_permissions = True
        if contact.is_new():
            contact.insert()
        else:
            contact.save()

        _update_customer_fields(customer, contact, user)
        _ensure_portal_user(customer, user)
        return

    # ── New customer path ───────────────────────────────────────────────────
    # Frappe enqueues create_contact after user.insert() as a background job.
    # We run it synchronously NOW so the Contact exists before the Customer is
    # created, then pre-set customer_primary_contact to block ERPNext's
    # create_primary_contact() from making a second Contact.

    from frappe.core.doctype.user.user import create_contact as _frappe_create_contact
    _frappe_create_contact(user, ignore_mandatory=True)

    # Retrieve the just-created contact by email
    from frappe.contacts.doctype.contact.contact import get_contact_name
    contact_name = get_contact_name(user.email)

    if not contact_name:
        # Should not happen, but fall back to a manual insert
        contact = frappe.new_doc("Contact")
        contact.first_name = user.first_name or user.name
        contact.email_id = user.email
        contact.user = user.name
        contact.is_primary_contact = 1
        contact.append("email_ids", {"email_id": user.email, "is_primary": 1})
        if user.mobile_no:
            contact.append("phone_nos", {"phone": user.mobile_no, "is_primary_mobile_no": 1})
        contact.flags.ignore_mandatory = True
        contact.flags.ignore_permissions = True
        contact.insert()
        contact_name = contact.name

    # Insert Customer with customer_primary_contact already pointing to the
    # existing Contact — ERPNext's create_primary_contact() guard
    # (`if not self.customer_primary_contact`) will therefore skip creation.
    customer = frappe.new_doc("Customer")
    customer.update(
        {
            "customer_name": customer_name,
            "customer_type": "Individual",
            "customer_group": _default_customer_group(),
            "territory": _default_territory(),
            "customer_primary_contact": contact_name,
            "email_id": user.email,
            "mobile_no": user.mobile_no or "",
        }
    )
    customer.flags.ignore_mandatory = True
    customer.flags.ignore_permissions = True
    customer.insert()
    # Add the Customer Dynamic Link to the existing Contact
    contact = frappe.get_doc("Contact", contact_name)
    if not any(
        l.link_doctype == "Customer" and l.link_name == customer.name
        for l in contact.get("links", [])
    ):
        contact.append("links", {"link_doctype": "Customer", "link_name": customer.name})
        contact.flags.ignore_mandatory = True
        contact.flags.ignore_permissions = True
        contact.save()

    _ensure_portal_user(customer, user)


def _fill_contact(contact, user, customer_name):
    """Populate contact fields without creating duplicates."""
    contact.first_name = user.first_name or user.name
    contact.email_id = user.email
    contact.user = user.name
    contact.is_primary_contact = 1

    if not any(e.email_id == user.email for e in contact.get("email_ids", [])):
        contact.append("email_ids", {"email_id": user.email, "is_primary": 1})

    if user.mobile_no:
        if not any(p.phone == user.mobile_no for p in contact.get("phone_nos", [])):
            contact.append("phone_nos", {"phone": user.mobile_no, "is_primary_mobile_no": 1})

    if not any(
        l.link_doctype == "Customer" and l.link_name == customer_name
        for l in contact.get("links", [])
    ):
        contact.append("links", {"link_doctype": "Customer", "link_name": customer_name})


def _update_customer_fields(customer, contact, user):
    """Sync email, mobile, and primary contact back onto the customer row."""
    if not customer.customer_primary_contact:
        customer.db_set("customer_primary_contact", contact.name)
    if not customer.email_id:
        customer.db_set("email_id", user.email)
    if not customer.mobile_no and user.mobile_no:
        customer.db_set("mobile_no", user.mobile_no)


def _ensure_portal_user(customer, user):
    """Add a Portal User row to the customer if not already present."""
    existing = frappe.db.exists(
        "Portal User", {"parent": customer.name, "user": user.name, "parenttype": "Customer"}
    )
    if not existing:
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



