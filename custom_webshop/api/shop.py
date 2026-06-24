# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import json

import frappe
from frappe import _
from frappe.utils import flt, get_fullname

from webshop.webshop.api import get_product_filter_data
from webshop.webshop.shopping_cart.cart import get_cart_quotation
from webshop.webshop.shopping_cart.product_info import get_product_info_for_website
from webshop.webshop.doctype.override_doctype.item_group import get_child_groups_for_website


def _map_product(item):
	"""Map ERPNext Website Item dict to SPA product model."""
	specs = {}
	website_item = frappe.db.get_value(
		"Website Item",
		{"item_code": item.get("item_code")},
		["name"],
		as_dict=True,
	)
	if website_item:
		for row in frappe.get_all(
			"Item Website Specification",
			filters={"parent": website_item.name},
			fields=["label", "description"],
		):
			if row.label:
				specs[row.label] = row.description or ""

	image = item.get("website_image") or ""
	if image and not image.startswith(("http", "/")):
		image = frappe.utils.get_url(image)

	category = item.get("item_group") or "all"
	category_slug = frappe.scrub(category)

	return {
		"id": item.get("item_code"),
		"name": item.get("web_item_name") or item.get("item_name") or item.get("item_code"),
		"category": category_slug,
		"categoryName": category,
		"brand": item.get("brand") or frappe.db.get_value("Item", item.get("item_code"), "brand") or "",
		"description": item.get("short_description") or item.get("web_long_description") or "",
		"price": flt(item.get("price_list_rate") or 0),
		"formatted_price": item.get("formatted_price") or "",
		"image": image or "/assets/webshop/images/cart-empty-state.png",
		"stock": flt(item.get("stock_qty") or (999 if item.get("in_stock") else 0)),
		"in_stock": bool(item.get("in_stock") or item.get("on_backorder")),
		"on_backorder": bool(item.get("on_backorder")),
		"specs": specs,
		"route": item.get("route") or "",
		"ranking": item.get("ranking") or 0,
		"sold": 0,
	}


@frappe.whitelist(allow_guest=True)
def get_shop_context():
	settings = frappe.get_cached_doc("Webshop Settings")
	cart_count = 0
	if settings.enabled and frappe.session.user != "Guest":
		try:
			cart_data = get_cart_quotation()
			doc = cart_data.get("doc") or {}
			cart_count = sum((row.qty or 0) for row in (doc.get("items") or []))
		except Exception:
			pass

	categories = frappe.get_all(
		"Item Group",
		filters={"show_in_website": 1, "is_group": 0},
		fields=["name", "item_group_name", "route"],
		order_by="name asc",
	)

	return {
		"user": frappe.session.user,
		"user_fullname": get_fullname(frappe.session.user) if frappe.session.user != "Guest" else "",
		"is_guest": frappe.session.user == "Guest",
		"is_admin": frappe.session.user != "Guest"
		and ("System Manager" in frappe.get_roles() or "Sales Manager" in frappe.get_roles()),
		"cart_count": cart_count,
		"categories": categories,
		"payment_options": _get_payment_options(settings),
	}


def _get_payment_options(settings):
	return [
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


@frappe.whitelist(allow_guest=True)
def get_products(query_args=None):
	if isinstance(query_args, str):
		query_args = json.loads(query_args or "{}")
	query_args = frappe._dict(query_args or {})

	result = get_product_filter_data(query_args)
	if isinstance(result, dict) and result.get("exc"):
		result = _fallback_product_query(query_args)

	items = [_map_product(item) for item in (result.get("items") or [])]
	return {
		"items": items,
		"items_count": result.get("items_count") or 0,
		"filters": result.get("filters") or {},
		"sub_categories": result.get("sub_categories") or [],
	}


def _fallback_product_query(query_args):
	"""Direct Website Item query when upstream ProductQuery fails."""
	filters = {"published": 1}
	field_filters = query_args.get("field_filters") or {}
	if field_filters.get("item_group"):
		filters["item_group"] = field_filters["item_group"]
	if field_filters.get("brand"):
		filters["brand"] = field_filters["brand"]

	start = int(query_args.get("start") or 0)
	search = query_args.get("search")
	or_filters = None
	if search:
		or_filters = [
			["item_code", "like", f"%{search}%"],
			["item_name", "like", f"%{search}%"],
			["web_item_name", "like", f"%{search}%"],
		]

	items = frappe.get_all(
		"Website Item",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"item_code",
			"web_item_name",
			"item_name",
			"item_group",
			"website_image",
			"short_description",
			"web_long_description",
			"route",
			"on_backorder",
			"ranking",
		],
		order_by="ranking desc, modified desc",
		limit_start=start,
		limit_page_length=20,
	)

	for item in items:
		try:
			info = get_product_info_for_website(item.item_code, skip_quotation_creation=True)
			price = (info.get("product_info") or {}).get("price") or {}
			item.price_list_rate = price.get("price_list_rate")
			item.formatted_price = price.get("formatted_price")
			stock = info.get("product_info") or {}
			item.in_stock = stock.get("in_stock")
			item.stock_qty = stock.get("stock_qty")
		except Exception:
			item.in_stock = True
			item.stock_qty = 0

	count = frappe.db.count("Website Item", filters=filters)
	return {"items": items, "items_count": count, "filters": {}}


@frappe.whitelist(allow_guest=True)
def get_product_detail(item_code):
	if not item_code:
		frappe.throw(_("Item code is required"))

	info = get_product_info_for_website(item_code)
	product_info = info.get("product_info") or {}

	item = frappe.db.get_value(
		"Website Item",
		{"item_code": item_code, "published": 1},
		[
			"item_code",
			"web_item_name",
			"item_name",
			"item_group",
			"website_image",
			"short_description",
			"web_long_description",
			"route",
			"on_backorder",
		],
		as_dict=True,
	)
	if not item:
		frappe.throw(_("Product not found"), frappe.DoesNotExistError)

	price_data = product_info.get("price") or {}
	item.price_list_rate = price_data.get("price_list_rate")
	item.formatted_price = price_data.get("formatted_price")
	item.in_stock = product_info.get("in_stock")
	item.stock_qty = product_info.get("stock_qty")
	item.on_backorder = item.on_backorder or product_info.get("on_backorder")

	brand = frappe.db.get_value("Item", item_code, "brand")
	item.brand = brand

	mapped = _map_product(item)
	mapped["description"] = item.web_long_description or item.short_description or mapped["description"]
	mapped["qty_in_cart"] = product_info.get("qty") or 0
	return mapped


@frappe.whitelist(allow_guest=True)
def get_cart_json():
	try:
		data = get_cart_quotation()
	except Exception:
		return {"items": [], "subtotal": 0, "shipping": 0, "grand_total": 0, "currency": ""}

	doc = data.get("doc") or {}
	items = []
	for row in doc.get("items") or []:
		items.append(
			{
				"productId": row.item_code,
				"item_code": row.item_code,
				"qty": row.qty,
				"name": row.item_name,
				"price": flt(row.rate),
				"amount": flt(row.amount),
				"image": row.get("thumbnail") or row.get("image"),
			}
		)

	shipping_amount = 0
	for tax in doc.get("taxes") or []:
		desc = (tax.get("description") or "").lower()
		if "shipping" in desc:
			shipping_amount += flt(tax.get("tax_amount"))

	return {
		"items": items,
		"subtotal": flt(doc.get("net_total")),
		"shipping": shipping_amount,
		"grand_total": flt(doc.get("grand_total")),
		"currency": doc.get("currency"),
		"shipping_address_name": doc.get("shipping_address_name"),
		"customer_address": doc.get("customer_address"),
	}


@frappe.whitelist()
def get_orders_json():
	if frappe.session.user == "Guest":
		return []

	customers = frappe.get_all(
		"Portal User",
		filters={"user": frappe.session.user, "parenttype": "Customer"},
		pluck="parent",
	)
	if not customers:
		return []

	orders = frappe.get_all(
		"Sales Order",
		filters={"customer": ["in", customers], "docstatus": ["<", 2]},
		fields=[
			"name",
			"transaction_date",
			"status",
			"docstatus",
			"grand_total",
			"currency",
			"per_delivered",
			"per_billed",
		],
		order_by="transaction_date desc, creation desc",
		ignore_permissions=True,
	)

	has_payment_method = frappe.db.has_column("Sales Order", "custom_payment_method")

	result = []
	for order in orders:
		payment_method = None
		if has_payment_method:
			payment_method = frappe.db.get_value("Sales Order", order.name, "custom_payment_method")
		items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": order.name},
			fields=["item_code", "item_name", "qty", "rate", "amount"],
		)
		status = _map_order_status(order)
		result.append(
			{
				"id": order.name,
				"date": str(order.transaction_date),
				"status": status,
				"docstatus": order.docstatus,
				"subtotal": flt(order.grand_total),
				"shipping": 0,
				"grandTotal": flt(order.grand_total),
				"currency": order.currency,
				"payment_method": payment_method,
				"items": [
					{
						"productId": i.item_code,
						"qty": i.qty,
						"price": flt(i.rate),
						"name": i.item_name,
					}
					for i in items
				],
				"detail_url": f"/orders/{order.name}",
			}
		)
	return result


def _map_order_status(order):
	if order.docstatus == 0:
		return "pending"
	if order.per_delivered >= 100:
		return "delivered"
	if order.per_delivered > 0:
		return "shipped"
	if order.docstatus == 1:
		return "paid"
	return "pending"


@frappe.whitelist()
def get_order_for_payment(order_id):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	customers = frappe.get_all(
		"Portal User",
		filters={"user": frappe.session.user, "parenttype": "Customer"},
		pluck="parent",
	)
	if not order_id:
		frappe.throw(_("No order specified."))

	sales_order = frappe.get_doc("Sales Order", order_id)
	if sales_order.customer not in customers:
		frappe.throw(_("Order not found."), frappe.DoesNotExistError)

	if sales_order.docstatus != 0:
		frappe.throw(_("This order does not require payment."), frappe.ValidationError)

	shipping_amount = 0
	for tax in sales_order.get("taxes") or []:
		if "shipping" in (tax.get("description") or "").lower():
			shipping_amount += flt(tax.tax_amount)

	return {
		"order_id": sales_order.name,
		"grand_total": flt(sales_order.grand_total),
		"grand_total_formatted": frappe.format_value(
			sales_order.grand_total,
			{"fieldtype": "Currency", "options": sales_order.currency},
		),
		"currency": sales_order.currency,
		"shipping": shipping_amount,
		"items": [
			{
				"productId": i.item_code,
				"qty": i.qty,
				"price": flt(i.rate),
				"name": i.item_name,
			}
			for i in sales_order.get("items") or []
		],
	}


@frappe.whitelist(allow_guest=True)
def get_home_data():
	settings = frappe.get_cached_doc("Webshop Settings")

	# Trending / featured products
	products_result = get_products({"start": 0})
	items = products_result.get("items") or []

	# Categories with show_in_website
	categories = frappe.get_all(
		"Item Group",
		filters={"show_in_website": 1, "is_group": 0},
		fields=["name", "item_group_name"],
		order_by="name asc",
		limit=10,
	)

	category_map = {}
	for cat in categories:
		slug = frappe.scrub(cat.name)
		category_map[slug] = cat.name

	# Hero slides from Webshop Settings child table or defaults
	slides = _get_hero_slides(settings)

	return {
		"products": items[:12],
		"categories": category_map,
		"category_descriptions": {k: v for k, v in category_map.items()},
		"slides": slides,
	}


def _get_hero_slides(settings):
	slides = []
	raw = settings.get("custom_hero_slides_json")
	if raw:
		try:
			slides = json.loads(raw) if isinstance(raw, str) else raw
		except Exception:
			slides = []
	for slide in slides:
		image = slide.get("image") or ""
		if image and not image.startswith(("http", "/")):
			slide["image"] = frappe.utils.get_url(image)
	if not slides:
		slides = [
			{
				"eyebrow": "CNC LEADERS",
				"title": _("Industrial Components for precision machining"),
				"subtitle": _("Browse our certified CNC parts catalog."),
				"link": "/shop/catalog",
				"image": "/assets/webshop/images/cart-empty-state.png",
			}
		]
	return slides


@frappe.whitelist(allow_guest=True)
def get_categories():
	groups = frappe.get_all(
		"Item Group",
		filters={"show_in_website": 1},
		fields=["name", "item_group_name", "parent_item_group", "is_group"],
		order_by="lft asc",
	)
	result = {"all": _("All Components")}
	for g in groups:
		if not g.is_group:
			# slug -> Item Group doc name (used by product filters)
			result[frappe.scrub(g.name)] = g.name
	return result
