# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import frappe

from custom_webshop.www.shop.shop_context import get_shop_context


def get_context(context):
	if frappe.session.user == "Guest":
		order_id = frappe.form_dict.get("order_id") or ""
		redirect = "/shop/login"
		if order_id:
			redirect = f"/shop/login?redirect-to=/shop/payment%3Forder_id%3D{order_id}"
		frappe.local.flags.redirect_location = redirect
		raise frappe.Redirect

	order_id = frappe.form_dict.get("order_id") or ""
	get_shop_context(context, active_page="payment", order_id=order_id)
