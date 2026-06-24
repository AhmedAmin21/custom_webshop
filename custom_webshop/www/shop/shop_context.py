# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import json

import frappe
from frappe import _


def get_shop_context(context, active_page="home", **extra):
	context.no_cache = 1
	context.no_header = 1
	context.no_footer = 1
	context.no_breadcrumbs = 1
	context.show_sidebar = 0
	context.active_page = active_page
	context.title = _("Shop")

	settings = frappe.get_cached_doc("Webshop Settings")
	context.payment_options = [
		{
			"key": "instapay",
			"label": _("InstaPay"),
			"number": settings.get("custom_instapay_number") or "",
		},
		{
			"key": "vodafone_cash",
			"label": _("Vodafone Cash"),
			"number": settings.get("custom_vodafone_cash_number") or "",
		},
		{
			"key": "etisalat_cash",
			"label": _("Etisalat Cash"),
			"number": settings.get("custom_etisalat_cash_number") or "",
		},
	]
	context.is_admin = (
		frappe.session.user != "Guest"
		and (
			"System Manager" in frappe.get_roles()
			or "Sales Manager" in frappe.get_roles()
		)
	)
	context.user = frappe.session.user
	context.user_fullname = (
		frappe.utils.get_fullname(frappe.session.user) if frappe.session.user != "Guest" else ""
	)
	context.is_guest = frappe.session.user == "Guest"

	context.item_code = extra.get("item_code") or ""
	context.order_id = extra.get("order_id") or frappe.form_dict.get("order_id") or ""
	context.redirect_to = extra.get("redirect_to") or frappe.form_dict.get("redirect-to") or ""

	shop_boot = {
		"active_page": active_page,
		"payment_options": context.payment_options,
		"is_admin": context.is_admin,
		"is_guest": context.is_guest,
		"user": context.user,
		"user_fullname": context.user_fullname,
		"item_code": context.item_code,
		"order_id": context.order_id,
		"redirect_to": context.redirect_to,
	}
	context.shop_boot_json = json.dumps(shop_boot)
	context.payment_options_json = json.dumps(context.payment_options)
