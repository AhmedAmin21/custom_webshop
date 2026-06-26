import frappe
from frappe import _


no_cache = 1


def get_context(context):
    # Already logged-in redirect
    if frappe.session.user != "Guest":
        redirect_to = frappe.request.args.get("redirect-to") or "/shop"
        frappe.local.flags.redirect_location = redirect_to
        raise frappe.Redirect

    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
    context.redirect_to = frappe.request.args.get("redirect-to") or ""

    try:
        disable_signup = frappe.db.get_single_value("Website Settings", "disable_signup") or 0
    except Exception:
        disable_signup = 0
    context.disable_signup = bool(disable_signup)
