# Copyright (c) 2026, custom_webshop contributors
# License: MIT

import json

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate

from custom_webshop.shopping_cart.cart_override import _send_order_email


def _require_admin():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	if not (
		"System Manager" in frappe.get_roles() or "Sales Manager" in frappe.get_roles()
	):
		frappe.throw(_("Not permitted."), frappe.PermissionError)


def _order_has_receipt(order_name):
	return bool(
		frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Sales Order", "attached_to_name": order_name},
			limit=1,
		)
	)


@frappe.whitelist()
def get_analytics():
	_require_admin()

	submitted = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1},
		fields=["name", "grand_total", "transaction_date"],
		limit=5000,
	)
	pending_filters = {"docstatus": 0}
	if frappe.db.has_column("Sales Order", "custom_payment_review_status"):
		pending_filters["custom_payment_review_status"] = "Pending Review"
	pending_count = frappe.db.count("Sales Order", pending_filters)
	total_orders = frappe.db.count("Sales Order", {"docstatus": ["<", 2]})

	total_revenue = sum(flt(o.grand_total) for o in submitted)
	conversion = (len(submitted) / total_orders * 100) if total_orders else 0

	chart_points = []
	for i in range(7, -1, -1):
		day = frappe.utils.add_days(nowdate(), -i)
		day_total = sum(
			flt(o.grand_total) for o in submitted if str(o.transaction_date) == str(day)
		)
		chart_points.append(day_total)

	return {
		"total_revenue": total_revenue,
		"order_count": total_orders,
		"submitted_count": len(submitted),
		"pending_count": pending_count,
		"conversion_percent": round(conversion, 1),
		"chart_points": chart_points,
	}


@frappe.whitelist()
def get_inventory():
	_require_admin()

	from webshop.webshop.utils.product import get_web_item_qty_in_stock

	settings = frappe.get_cached_doc("Webshop Settings")
	price_list = settings.price_list

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
		price_filters = {"item_code": item.item_code, "selling": 1}
		if price_list:
			price_filters["price_list"] = price_list
		price = frappe.db.get_value("Item Price", price_filters, "price_list_rate")
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

	filters = {"docstatus": 0}
	if frappe.db.has_column("Sales Order", "custom_payment_review_status"):
		filters["custom_payment_review_status"] = "Pending Review"

	orders = frappe.get_all(
		"Sales Order",
		filters=filters,
		fields=["name", "customer", "grand_total", "currency", "transaction_date", "creation"],
		order_by="creation desc",
		limit=50,
	)

	order_names = [o.name for o in orders]
	files_by_order = {}
	if order_names:
		for f in frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Sales Order", "attached_to_name": ["in", order_names]},
			fields=["attached_to_name", "file_url", "file_name"],
		):
			files_by_order.setdefault(f.attached_to_name, f)

	result = []
	for order in orders:
		file_doc = files_by_order.get(order.name)
		result.append(
			{
				"id": order.name,
				"customer": order.customer,
				"grandTotal": flt(order.grand_total),
				"currency": order.currency,
				"date": str(order.transaction_date or order.creation),
				"status": "pending_review",
				"receipt_url": file_doc.file_url if file_doc else None,
				"has_receipt": bool(file_doc),
			}
		)
	return result


@frappe.whitelist()
def approve_order(order_id):
	_require_admin()

	so = frappe.get_doc("Sales Order", order_id)
	if so.docstatus != 0:
		frappe.throw(_("Order is not in draft state."))

	if not _order_has_receipt(so.name):
		frappe.throw(_("Upload a payment receipt before approving this order."))

	if frappe.db.has_column("Sales Order", "custom_payment_review_status"):
		so.custom_payment_review_status = "Approved"
		so.custom_reviewed_by = frappe.session.user
		so.custom_reviewed_on = now_datetime()

	so.flags.ignore_permissions = True
	so.save()
	so.submit()

	_send_order_email(so, "order_payment_confirmed")
	return {"status": "submitted", "order_id": so.name}


@frappe.whitelist()
def reject_order(order_id, reason=None):
	_require_admin()

	so = frappe.get_doc("Sales Order", order_id)
	if so.docstatus != 0:
		frappe.throw(_("Order is not in draft state."))

	if frappe.db.has_column("Sales Order", "custom_payment_review_status"):
		so.custom_payment_review_status = "Rejected"
		so.custom_rejection_reason = reason or _("Payment proof rejected")
		so.custom_reviewed_by = frappe.session.user
		so.custom_reviewed_on = now_datetime()
		so.flags.ignore_permissions = True
		so.save()

	return {"status": "rejected", "order_id": so.name}


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


def _sanitize_slide(data):
	link = (data.get("link") or "/shop/catalog").strip()
	if link.startswith(("http://", "https://", "/")):
		safe_link = link
	else:
		safe_link = "/shop/catalog"

	image = (data.get("image") or "").strip()
	if image.startswith(("http://", "https://", "/")):
		safe_image = image
	else:
		safe_image = ""

	return {
		"eyebrow": frappe.utils.strip_html(data.get("eyebrow") or "")[:80],
		"title": frappe.utils.strip_html(data.get("title") or "")[:200],
		"subtitle": frappe.utils.strip_html(data.get("subtitle") or "")[:500],
		"link": safe_link,
		"image": safe_image,
	}


@frappe.whitelist()
def get_slides():
	_require_admin()

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

	data = frappe.parse_json(slide_data) if isinstance(slide_data, str) else slide_data
	data = _sanitize_slide(data)
	settings = frappe.get_doc("Webshop Settings")
	slides = _load_slides(settings)

	slide_id = data.get("id")
	if slide_id is not None:
		for slide in slides:
			if slide.get("id") == slide_id:
				slide.update(data)
				break
	else:
		slides.append({**data, "id": frappe.generate_hash(length=10)})

	_save_slides(settings, slides)
	return get_slides()


@frappe.whitelist()
def delete_slide(slide_id):
	_require_admin()

	settings = frappe.get_doc("Webshop Settings")
	slides = [s for s in _load_slides(settings) if s.get("id") != slide_id]
	_save_slides(settings, slides)
	return get_slides()
