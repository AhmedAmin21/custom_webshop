# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import frappe


def get_context(context):
	frappe.local.flags.redirect_location = "/shop/cart"
	raise frappe.Redirect
