no_cache = 1

import frappe


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False

    # Session info injected into page for JS consumption
    context.session_user = frappe.session.user
    context.is_guest = frappe.session.user == "Guest"
    context.csrf_token = frappe.session.csrf_token

    # Redirect guests to login if needed — shop page is guest-accessible
    # (products are public), so no redirect here

    # Company name for display
    try:
        settings = frappe.get_cached_doc("Webshop Settings")
        context.company = settings.company or ""
    except Exception:
        context.company = ""

    return context
