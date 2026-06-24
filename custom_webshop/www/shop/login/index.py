# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import frappe

from custom_webshop.www.shop.shop_context import get_shop_context


def get_context(context):
	if frappe.session.user != "Guest":
		redirect = frappe.form_dict.get("redirect-to") or "/shop"
		frappe.local.flags.redirect_location = redirect
		raise frappe.Redirect

	get_shop_context(context, active_page="login")
