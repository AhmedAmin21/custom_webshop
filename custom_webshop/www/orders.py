# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from frappe import _


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/shop/login?redirect-to=/shop/orders"
		raise frappe.Redirect
	frappe.local.flags.redirect_location = "/shop/orders"
	raise frappe.Redirect
