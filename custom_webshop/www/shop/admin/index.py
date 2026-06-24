# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import frappe

from custom_webshop.www.shop.shop_context import get_shop_context


def get_context(context):
	is_admin = (
		frappe.session.user != "Guest"
		and (
			"System Manager" in frappe.get_roles()
			or "Sales Manager" in frappe.get_roles()
		)
	)
	if not is_admin:
		frappe.local.flags.redirect_location = "/shop"
		raise frappe.Redirect

	get_shop_context(context, active_page="admin")
