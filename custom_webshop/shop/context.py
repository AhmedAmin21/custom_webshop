import frappe
from frappe import _
from frappe.utils import cint, flt

from custom_webshop.shop.routes import SHOP_BASE, shop_url


def add_shop_context(context):
	"""Inject shared storefront URL helpers into every shop page context."""
	context.shop_base = SHOP_BASE
	context.shop_url = shop_url
	context.pathname = "/" + (getattr(frappe.local, "path", "") or "")
	context.body_class = (context.get("body_class") or "") + " cnc-shop"
	return context


def get_home_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = _("Shop")

	settings = frappe.get_cached_doc("Webshop Settings")
	context.featured_item_groups = frappe.get_all(
		"Item Group",
		filters={"is_group": 0, "show_in_website": 1},
		fields=["name", "item_group_name", "route"],
		limit=8,
		order_by="name asc",
	)

	context.trending_items = frappe.get_all(
		"Website Item",
		filters={"published": 1},
		fields=["name", "item_code", "web_item_name", "route", "website_image"],
		limit=6,
		order_by="modified desc",
	)

	return add_shop_context(context)


def get_orders_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = _("Orders")
	context.parents = [{"route": shop_url(), "title": _("Shop")}]

	customers = frappe.get_all(
		"Portal User",
		filters={"user": frappe.session.user, "parenttype": "Customer"},
		pluck="parent",
	)
	if not customers:
		context.orders = []
		return add_shop_context(context)

	orders = frappe.get_all(
		"Sales Order",
		filters={"customer": ["in", customers], "docstatus": ["<", 2]},
		fields=[
			"name", "transaction_date", "status", "docstatus",
			"grand_total", "currency", "per_delivered", "per_billed",
		],
		order_by="transaction_date desc, creation desc",
		ignore_permissions=True,
	)

	for order in orders:
		order.grand_total_formatted = frappe.format_value(
			order.grand_total, {"fieldtype": "Currency", "options": order.currency}
		)

	context.orders = orders
	return add_shop_context(context)


def get_payment_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.title = _("Payment")
	context.parents = [{"route": shop_url("orders"), "title": _("Orders")}]

	order_id = frappe.form_dict.get("order_id")
	context.order_id = order_id

	if frappe.session.user == "Guest":
		target = shop_url(f"payment?order_id={order_id}") if order_id else shop_url("login")
		frappe.local.flags.redirect_location = f"/login?redirect-to={target}"
		raise frappe.Redirect

	customers = frappe.get_all(
		"Portal User",
		filters={"user": frappe.session.user, "parenttype": "Customer"},
		pluck="parent",
	)

	if not order_id:
		context.invalid = True
		context.error = _("No order specified.")
		return add_shop_context(context)

	sales_order = frappe.get_doc("Sales Order", order_id)
	if not sales_order or sales_order.customer not in customers:
		context.invalid = True
		context.error = _("Order not found.")
		return add_shop_context(context)

	if sales_order.docstatus != 0:
		context.invalid = True
		context.error = _("This order does not require payment.")
		return add_shop_context(context)

	context.sales_order = sales_order
	context.grand_total_formatted = frappe.format_value(
		sales_order.grand_total,
		{"fieldtype": "Currency", "options": sales_order.currency},
	)
	context.total_weight = flt(sales_order.total_net_weight)

	weight_uom = sales_order.get("weight_uom")
	if not weight_uom:
		for item in sales_order.get("items", []):
			if item.get("weight_uom"):
				weight_uom = item.weight_uom
				break
	context.weight_uom = weight_uom or ""

	if sales_order.get("shipping_destination"):
		context.shipping_destination = (
			frappe.db.get_value("Governorate", sales_order.shipping_destination, "governorate_name")
			or sales_order.shipping_destination
		)
	else:
		context.shipping_destination = None

	context.shipping_amount = 0
	for tax in sales_order.get("taxes", []):
		if "shipping" in (tax.get("description") or "").lower():
			context.shipping_amount += flt(tax.tax_amount)

	context.shipping_amount_formatted = frappe.format_value(
		context.shipping_amount,
		{"fieldtype": "Currency", "options": sales_order.currency},
	)

	settings = frappe.get_cached_doc("Webshop Settings")
	context.payment_options = [
		{"key": "instapay", "label": _("InstaPay"), "number": settings.get("custom_instapay_number") or ""},
		{"key": "vodafone_cash", "label": _("Vodafone Cash"), "number": settings.get("custom_vodafone_cash_number") or ""},
		{"key": "etisalat_cash", "label": _("Etisalat Cash"), "number": settings.get("custom_etisalat_cash_number") or ""},
	]

	return add_shop_context(context)
