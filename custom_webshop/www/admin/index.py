no_cache = 1

import frappe


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False

	# Redirect guests to login
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/admin"
		raise frappe.Redirect

	# Restrict to System Manager / Website Manager only
	roles = frappe.get_roles()
	if "System Manager" not in roles and "Website Manager" not in roles:
		frappe.local.flags.redirect_location = "/shop"
		raise frappe.Redirect

	context.session_user = frappe.session.user
	context.is_guest = False
	context.csrf_token = frappe.sessions.get_csrf_token()

	return context
