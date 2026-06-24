# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import json

import frappe
from frappe import _
from frappe.utils import flt, nowdate


def _require_admin():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if not (
		"System Manager" in frappe.get_roles() or "Sales Manager" in frappe.get_roles()
	):
		frappe.throw(_("Not permitted."), frappe.PermissionError)


@frappe.whitelist()
def get_analytics():
	_require_admin()

	orders = frappe.get_all(
		"Sales Order",
		filters={"docstatus": ["<", 2]},
		fields=["name", "grand_total", "docstatus", "transaction_date", "creation"],
	)

	total_revenue = sum(flt(o.grand_total) for o in orders if o.docstatus == 1)
	submitted = [o for o in orders if o.docstatus == 1]
	pending = [o for o in orders if o.docstatus == 0]

	conversion = (len(submitted) / len(orders) * 100) if orders else 0

	# Daily chart: last 8 days revenue
	chart_points = []
	for i in range(7, -1, -1):
		day = frappe.utils.add_days(nowdate(), -i)
		day_total = sum(
			flt(o.grand_total)
			for o in submitted
			if str(o.transaction_date) == str(day)
		)
		chart_points.append(day_total)

	return {
		"total_revenue": total_revenue,
		"order_count": len(orders),
		"submitted_count": len(submitted),
		"pending_count": len(pending),
		"conversion_percent": round(conversion, 1),
		"chart_points": chart_points,
	}


@frappe.whitelist()
def get_inventory():
	_require_admin()

	from webshop.webshop.utils.product import get_web_item_qty_in_stock

	items = frappe.get_all(
		"Website Item",
		filters={"published": 1},
		fields=["name", "item_code", "web_item_name", "item_name", "item_group", "website_image"],
		order_by="modified desc",
		limit=100,
	)

	result = []
	for item in items:
		stock_info = get_web_item_qty_in_stock(item.item_code, "website_warehouse")
		price = frappe.db.get_value(
			"Item Price",
			{"item_code": item.item_code, "selling": 1},
			"price_list_rate",
		)
		image = item.website_image or ""
		if image and not image.startswith(("http", "/")):
			image = frappe.utils.get_url(image)

		result.append(
			{
				"id": item.item_code,
				"name": item.web_item_name or item.item_name,
				"categoryName": item.item_group,
				"price": flt(price),
				"stock": flt(stock_info.get("stock_qty") or 0),
				"in_stock": bool(stock_info.get("in_stock")),
				"image": image or "/assets/webshop/images/cart-empty-state.png",
			}
		)
	return result


@frappe.whitelist()
def get_pending_orders():
	_require_admin()

	orders = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 0},
		fields=["name", "customer", "grand_total", "currency", "transaction_date", "creation"],
		order_by="creation desc",
		limit=50,
	)

	result = []
	for order in orders:
		files = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Sales Order", "attached_to_name": order.name},
			fields=["file_url", "file_name"],
			limit=1,
		)
		result.append(
			{
				"id": order.name,
				"customer": order.customer,
				"grandTotal": flt(order.grand_total),
				"currency": order.currency,
				"date": str(order.transaction_date or order.creation),
				"status": "pending",
				"receipt_url": files[0].file_url if files else None,
			}
		)
	return result


@frappe.whitelist()
def approve_order(order_id):
	_require_admin()

	so = frappe.get_doc("Sales Order", order_id)
	if so.docstatus != 0:
		frappe.throw(_("Order is not in draft state."))

	so.flags.ignore_permissions = True
	so.submit()
	return {"status": "submitted", "order_id": so.name}


def _load_slides(settings):
	raw = settings.get("custom_hero_slides_json")
	if not raw:
		return []
	try:
		return json.loads(raw) if isinstance(raw, str) else list(raw)
	except Exception:
		return []


def _save_slides(settings, slides):
	settings.custom_hero_slides_json = json.dumps(slides)
	settings.flags.ignore_permissions = True
	settings.save()


@frappe.whitelist()
def get_slides():
	_require_admin()
	import json

	settings = frappe.get_cached_doc("Webshop Settings")
	slides = _load_slides(settings)
	for idx, slide in enumerate(slides):
		slide["idx"] = idx
		image = slide.get("image") or ""
		if image and not image.startswith(("http", "/")):
			slide["image"] = frappe.utils.get_url(image)
	return slides


@frappe.whitelist()
def save_slide(slide_data):
	_require_admin()
	import json

	data = frappe.parse_json(slide_data) if isinstance(slide_data, str) else slide_data
	settings = frappe.get_doc("Webshop Settings")
	slides = _load_slides(settings)

	slide_id = data.get("id")
	if slide_id is not None:
		for slide in slides:
			if slide.get("id") == slide_id:
				slide.update(
					{
						"eyebrow": data.get("eyebrow", slide.get("eyebrow", "")),
						"title": data.get("title", slide.get("title", "")),
						"subtitle": data.get("subtitle", slide.get("subtitle", "")),
						"link": data.get("link", slide.get("link", "/shop/catalog")),
						"image": data.get("image", slide.get("image", "")),
					}
				)
				break
	else:
		import frappe.utils

		slides.append(
			{
				"id": frappe.utils.generate_hash(length=10),
				"eyebrow": data.get("eyebrow") or "",
				"title": data.get("title") or "",
				"subtitle": data.get("subtitle") or "",
				"link": data.get("link") or "/shop/catalog",
				"image": data.get("image") or "",
			}
		)

	_save_slides(settings, slides)
	return get_slides()


@frappe.whitelist()
def delete_slide(slide_id):
	_require_admin()

	settings = frappe.get_doc("Webshop Settings")
	slides = [s for s in _load_slides(settings) if s.get("id") != slide_id]
	_save_slides(settings, slides)
	return get_slides()
