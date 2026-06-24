# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import frappe

from custom_webshop.www.shop.shop_context import get_shop_context


def get_context(context):
	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = "/shop"
		raise frappe.Redirect

	get_shop_context(context, active_page="signup")
