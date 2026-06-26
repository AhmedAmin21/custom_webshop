no_cache = 1

import frappe


def get_context(context):
    context.no_cache = 1
    context.show_sidebar = False
    context.session_user = frappe.session.user
    context.is_guest = frappe.session.user == "Guest"
    context.csrf_token = frappe.session.csrf_token
    return context
