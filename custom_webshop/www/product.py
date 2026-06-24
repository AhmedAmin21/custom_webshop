import frappe


def get_context(context):
	item_code = frappe.form_dict.get("item_code")
	if item_code:
		frappe.local.flags.redirect_location = f"/shop/product/{item_code}"
	else:
		frappe.local.flags.redirect_location = "/shop/catalog"
	raise frappe.Redirect
