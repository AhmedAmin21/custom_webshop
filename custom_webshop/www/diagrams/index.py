import frappe
from frappe import _


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/diagrams"
		raise frappe.Redirect

	frappe.only_for("System Manager")
	context.no_cache = 1
	context.title = _("Internal Architecture Diagrams")
	return context
