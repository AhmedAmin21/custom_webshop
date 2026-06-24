import frappe


def get_context(context):
	frappe.local.flags.redirect_location = "/shop"
	raise frappe.Redirect
