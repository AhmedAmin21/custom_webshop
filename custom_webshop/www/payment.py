# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

no_cache = 1

import frappe
from frappe import _


def get_context(context):
	order_id = frappe.form_dict.get("order_id")
	if frappe.session.user == "Guest":
		redirect = "/shop/login"
		if order_id:
			redirect = f"/shop/login?redirect-to=/shop/payment%3Forder_id%3D{order_id}"
		frappe.local.flags.redirect_location = redirect
		raise frappe.Redirect

	if order_id:
		frappe.local.flags.redirect_location = f"/shop/payment?order_id={order_id}"
	else:
		frappe.local.flags.redirect_location = "/shop/payment"
	raise frappe.Redirect
