import json

import frappe
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False
	context.session_user = frappe.session.user
	context.is_guest = frappe.session.user == "Guest"
	context.csrf_token = frappe.sessions.get_csrf_token()

	item_slug = (frappe.form_dict.get("item") or "").strip()
	context.item_name = item_slug
	context.product_bootstrap = "null"

	if not item_slug:
		return context

	doc = _get_published_website_item(item_slug)
	if not doc:
		return context

	bootstrap = _build_product_bootstrap(doc)
	context.product_bootstrap = json.dumps(bootstrap)
	return context


def _get_published_website_item(item_slug):
	"""Resolve a published Website Item by route or item_code."""
	clean_slug = (item_slug or "").strip().strip("/")
	name = frappe.db.get_value(
		"Website Item",
		{"route": clean_slug, "published": 1},
		"name",
	)
	if not name:
		name = frappe.db.get_value(
			"Website Item",
			{"route": "/" + clean_slug, "published": 1},
			"name",
		)
	if not name:
		name = frappe.db.get_value(
			"Website Item",
			{"item_code": item_slug, "published": 1},
			"name",
		)
	if not name:
		name = frappe.db.get_value(
			"Website Item",
			{"name": item_slug, "published": 1},
			"name",
		)
	if not name:
		rows = frappe.db.sql(
			"""
			SELECT name FROM `tabWebsite Item`
			WHERE published = 1 AND (route = %s OR item_code = %s OR name = %s)
			LIMIT 1
			""",
			(clean_slug, item_slug, item_slug),
			as_dict=True,
		)
		if rows:
			name = rows[0].name

	if not name:
		return None

	return frappe.get_doc("Website Item", name)


def _get_live_recommended_items_data(item_codes):
	"""Batch-fetch live image and description from Item master for recommended item codes."""
	if not item_codes:
		return {}
	rows = frappe.get_all(
		"Item",
		filters={"name": ["in", item_codes]},
		fields=["name", "image", "description"],
	)
	return {row.name: row for row in rows}


def _build_product_bootstrap(doc):
	web_item = frappe.get_doc("Website Item", doc.name)
	settings = frappe.get_cached_doc("Webshop Settings")

	item_master = frappe.db.get_value("Item", web_item.item_code, ["image", "description"], as_dict=True) or {}
	item_image = item_master.get("image") or ""
	item_description = item_master.get("description") or ""

	specifications = [
		{"label": row.label, "description": row.description}
		for row in web_item.get("website_specifications", [])
	]

	slides = []
	if item_image:
		slides.append({"image": item_image, "heading": ""})

	if web_item.slideshow:
		slideshow_data = get_slideshow(web_item)
		for slide in slideshow_data.get("slides") or []:
			img = slide.get("image")
			if img and img != item_image:
				slides.append({"image": img, "heading": slide.get("heading") or ""})

	recommended_items = []
	if settings.enable_recommendations:
		rows = web_item.get_recommended_items(settings)
		item_codes = [r.get("item_code") for r in rows if r.get("item_code")]
		item_master_data = _get_live_recommended_items_data(item_codes)

		for row in rows:
			price_info = row.get("price_info") or {}
			master = item_master_data.get(row.get("item_code")) or {}
			recommended_items.append(
				{
					"item_code": row.get("item_code"),
					"route": row.get("route"),
					"website_item_name": row.get("website_item_name"),
					"image": master.get("image") or "",
					"description": master.get("description") or "",
					"formatted_price": price_info.get("formatted_price")
					or price_info.get("formatted_price_sales_uom"),
				}
			)

	wished = False
	if frappe.session.user != "Guest":
		wished = bool(
			frappe.db.exists(
				"Wishlist Item",
				{"item_code": web_item.item_code, "parent": frappe.session.user},
			)
		)

	return {
		"item_code": web_item.item_code,
		"route": web_item.route,
		"item_image": item_image,
		"item_description": item_description,
		"specifications": specifications,
		"slides": slides,
		"recommended_items": recommended_items,
		"wished": wished,
		"settings": {
			"enable_wishlist": bool(settings.enable_wishlist),
			"enable_recommendations": bool(settings.enable_recommendations),
			"show_price": bool(settings.show_price),
			"show_stock_availability": bool(settings.show_stock_availability),
			"enabled": bool(settings.enabled),
		},
	}
