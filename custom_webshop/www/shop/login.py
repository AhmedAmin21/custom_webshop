no_cache = 1

import frappe

from custom_webshop.shop.routes import shop_url


def get_context(context):
	target = frappe.utils.get_url(shop_url())
	frappe.local.flags.redirect_location = f"/login?redirect-to={target}"
	raise frappe.Redirect
