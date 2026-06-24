# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import frappe

from custom_webshop.www.shop.shop_context import get_shop_context


def get_context(context):
	item_code = frappe.form_dict.get("item_code") or ""
	if not item_code:
		frappe.local.flags.redirect_location = "/shop/catalog"
		raise frappe.Redirect

	get_shop_context(context, active_page="detail", item_code=item_code)
