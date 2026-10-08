import json
import math

import frappe

from custom_webshop.api.item_parser import (
	ALL_TOOL_FAMILIES,
	MATERIAL_LABELS,
	build_material_like_pattern,
	build_tool_family_like_pattern,
	get_material_label,
	parse_item_name,
)


def clear_catalog_caches(doc=None, method=None):
	frappe.cache().delete_value("custom_webshop:tool_families")
	frappe.cache().delete_value("custom_webshop:materials")
	frappe.cache().delete_value("custom_webshop:item_attributes")

@frappe.whitelist(allow_guest=True)
def get_item_master_details(item_code):
	"""Return image and description directly from Item master for a given item_code."""
	if not item_code:
		return {}
	return frappe.db.get_value(
		"Item",
		item_code,
		["name", "item_code", "item_name", "image", "description"],
		as_dict=True,
	) or {}


@frappe.whitelist(allow_guest=True)
def get_brands():
	"""Return brand names from the 'Brand - الماركة' Item Attribute values."""
	brand_attr = frappe.db.get_value(
		"Item Attribute",
		{"name": ["like", "%Brand%"]},
		"name",
	) or "Brand - الماركة"

	rows = frappe.db.sql(
		"""
		SELECT 
			iav.attribute_value AS brand,
			iav.abbr AS abbr,
			iav.parent AS attribute
		FROM `tabItem Attribute Value` iav
		WHERE iav.parent = %s
		ORDER BY iav.idx ASC, iav.attribute_value ASC
		""",
		[brand_attr],
		as_dict=True,
	)

	if not rows:
		rows = frappe.db.sql(
			"""
			SELECT 
				iav.attribute_value AS brand,
				iav.abbr AS abbr,
				iav.parent AS attribute
			FROM `tabItem Attribute Value` iav
			WHERE iav.parent LIKE %s
			ORDER BY iav.idx ASC, iav.attribute_value ASC
			""",
			["%Brand%"],
			as_dict=True,
		)

	return rows


def _generate_item_attributes():
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT iva.attribute, iva.attribute_value
		FROM `tabItem Variant Attribute` iva
		INNER JOIN `tabWebsite Item` wi ON wi.item_code = iva.parent
		WHERE wi.published = 1
		  AND iva.attribute_value IS NOT NULL
		  AND iva.attribute_value != ''
		ORDER BY iva.attribute, iva.attribute_value
		""",
		as_dict=True,
	)

	# Group into { attribute_name: [value, ...] }
	grouped = {}
	for row in rows:
		attr = row["attribute"]
		if attr not in grouped:
			grouped[attr] = []
		grouped[attr].append(row["attribute_value"])

	return [{"attribute": k, "values": v} for k, v in grouped.items()]


@frappe.whitelist(allow_guest=True)
def get_item_attributes():
	"""
	Return all Item Attributes with the distinct values actually used on
	published Website Items, grouped so callers get one entry per
	(attribute, attribute_value) pair.
	"""
	return frappe.cache().get_value(
		"custom_webshop:item_attributes",
		generator=_generate_item_attributes
	)


_SINGLES_DOCTYPE = "Webshop Settings"
_SINGLES_FIELD = "custom_display_attributes"


def _read_display_attribute_config():
	"""Read the raw JSON config from the Singles table, returns None if absent."""
	rows = frappe.db.sql(
		"SELECT `value` FROM `tabSingles` WHERE `doctype`=%s AND `field`=%s",
		(_SINGLES_DOCTYPE, _SINGLES_FIELD),
	)
	if rows and rows[0][0]:
		return rows[0][0]
	return None


def _write_display_attribute_config(value_json):
	"""Upsert the JSON config directly into the Singles table."""
	existing = frappe.db.sql(
		"SELECT `value` FROM `tabSingles` WHERE `doctype`=%s AND `field`=%s",
		(_SINGLES_DOCTYPE, _SINGLES_FIELD),
	)
	if existing:
		frappe.db.sql(
			"UPDATE `tabSingles` SET `value`=%s WHERE `doctype`=%s AND `field`=%s",
			(value_json, _SINGLES_DOCTYPE, _SINGLES_FIELD),
		)
	else:
		frappe.db.sql(
			"INSERT INTO `tabSingles` (`doctype`, `field`, `value`) VALUES (%s, %s, %s)",
			(_SINGLES_DOCTYPE, _SINGLES_FIELD, value_json),
		)
	frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def get_display_attributes():
	"""
	Return attributes for shop page carousels, filtered and ordered by the
	admin config stored in the Singles table.

	If no config is set, falls back to the full get_item_attributes() list.
	"""
	all_attrs = get_item_attributes()

	raw = _read_display_attribute_config()
	if not raw:
		return all_attrs
	try:
		selected = json.loads(raw)
		if not isinstance(selected, list):
			return all_attrs
	except Exception:
		return all_attrs

	# Build a lookup for fast access
	attr_map = {a["attribute"]: a for a in all_attrs}

	# Return only selected attributes in their configured order
	result = []
	for name in selected:
		if name in attr_map:
			result.append(attr_map[name])
	return result


@frappe.whitelist()
def save_display_attributes(attribute_names):
	"""
	Persist the ordered list of enabled attribute names.
	Requires System Manager role.
	attribute_names: JSON list of attribute name strings.
	"""
	frappe.only_for("System Manager")

	if isinstance(attribute_names, str):
		attribute_names = json.loads(attribute_names)

	if not isinstance(attribute_names, list):
		frappe.throw("attribute_names must be a list")

	_write_display_attribute_config(json.dumps(attribute_names))
	return {"success": True}


# ============================================================================
# Tool Family & Material — derived from Item Name (no DB schema changes)
# ============================================================================

_TF_SINGLES_FIELD = "custom_display_tool_families"


def _read_display_tool_family_config():
	"""Read saved tool-family display order from Singles, returns None if absent."""
	rows = frappe.db.sql(
		"SELECT `value` FROM `tabSingles` WHERE `doctype`=%s AND `field`=%s",
		(_SINGLES_DOCTYPE, _TF_SINGLES_FIELD),
	)
	if rows and rows[0][0]:
		return rows[0][0]
	return None


def _write_display_tool_family_config(value_json):
	"""Upsert the tool-family display config directly into the Singles table."""
	existing = frappe.db.sql(
		"SELECT `value` FROM `tabSingles` WHERE `doctype`=%s AND `field`=%s",
		(_SINGLES_DOCTYPE, _TF_SINGLES_FIELD),
	)
	if existing:
		frappe.db.sql(
			"UPDATE `tabSingles` SET `value`=%s WHERE `doctype`=%s AND `field`=%s",
			(value_json, _SINGLES_DOCTYPE, _TF_SINGLES_FIELD),
		)
	else:
		frappe.db.sql(
			"INSERT INTO `tabSingles` (`doctype`, `field`, `value`) VALUES (%s, %s, %s)",
			(_SINGLES_DOCTYPE, _TF_SINGLES_FIELD, value_json),
		)
	frappe.db.commit()


def _get_published_item_names():
	"""Return item_name values for all published Website Items that have one."""
	rows = frappe.db.sql(
		"""
		SELECT i.item_name
		FROM `tabWebsite Item` wi
		INNER JOIN `tabItem` i ON i.name = wi.item_code
		WHERE wi.published = 1
		  AND i.item_name IS NOT NULL
		  AND i.item_name != ''
		""",
		as_list=True,
	)
	return [r[0] for r in rows]


def _generate_tool_families():
	seen = set()
	result = []
	for name in _get_published_item_names():
		parsed = parse_item_name(name)
		if parsed and parsed["tool_family"] and parsed["tool_family"] not in seen:
			seen.add(parsed["tool_family"])
			result.append({"tool_family": parsed["tool_family"]})
	result.sort(key=lambda x: x["tool_family"])
	return result


@frappe.whitelist(allow_guest=True)
def get_tool_families():
	"""
	Return distinct Tool Families derived from published item names, sorted.
	Each entry: {"tool_family": "SEM"}
	"""
	return frappe.cache().get_value(
		"custom_webshop:tool_families",
		generator=_generate_tool_families
	)


def _generate_materials():
	seen = set()
	result = []
	for name in _get_published_item_names():
		parsed = parse_item_name(name)
		if parsed and parsed["material"] and parsed["material"] not in seen:
			seen.add(parsed["material"])
			labels = MATERIAL_LABELS.get(parsed["material"], {})
			result.append({
				"material": parsed["material"],
				"label_en": labels.get("en", parsed["material"]),
				"label_ar": labels.get("ar", parsed["material"]),
			})
	result.sort(key=lambda x: x["material"])
	return result


@frappe.whitelist(allow_guest=True)
def get_materials():
	"""
	Return distinct Materials derived from published item names, sorted.
	Each entry: {"material": "C", "label_en": "Carbide", "label_ar": "كربيد"}
	"""
	return frappe.cache().get_value(
		"custom_webshop:materials",
		generator=_generate_materials
	)


@frappe.whitelist(allow_guest=True)
def get_all_tool_families():
	"""Return the full canonical list of known tool families (static config)."""
	return [{"tool_family": tf, "description": ""} for tf in ALL_TOOL_FAMILIES]


@frappe.whitelist(allow_guest=True)
def get_all_materials():
	"""Return the full canonical list of known materials (static config)."""
	return [
		{"material": code, "label_en": labels["en"], "label_ar": labels["ar"]}
		for code, labels in MATERIAL_LABELS.items()
	]


@frappe.whitelist(allow_guest=True)
def get_display_tool_families():
	"""
	Return tool families for the home page carousels, filtered and ordered by
	the admin config stored in Singles.

	Uses the static canonical list as source of truth so saved selections work
	even before matching products exist in the DB.

	Falls back to the full static list when no config is set.
	"""
	# Static list is source of truth — not DB-derived
	all_families = get_all_tool_families()

	raw = _read_display_tool_family_config()
	if not raw:
		return all_families
	try:
		selected = json.loads(raw)
		if not isinstance(selected, list):
			return all_families
	except Exception:
		return all_families

	family_map = {f["tool_family"]: f for f in all_families}
	result = []
	for item in selected:
		if isinstance(item, str):
			tf_name = item
			desc = ""
		elif isinstance(item, dict):
			tf_name = item.get("tool_family")
			desc = item.get("description", "") or ""
		else:
			continue
		if tf_name in family_map:
			result.append({"tool_family": tf_name, "description": desc})
	return result


@frappe.whitelist()
def save_display_tool_families(tool_family_names):
	"""
	Persist the ordered list of enabled tool family names and optional descriptions.
	Requires System Manager role.
	tool_family_names: JSON list of tool family names (strings) or dicts with {tool_family, description}.
	"""
	frappe.only_for("System Manager")

	if isinstance(tool_family_names, str):
		tool_family_names = json.loads(tool_family_names)

	if not isinstance(tool_family_names, list):
		frappe.throw("tool_family_names must be a list")

	cleaned = []
	for item in tool_family_names:
		if isinstance(item, str):
			cleaned.append({"tool_family": item, "description": ""})
		elif isinstance(item, dict) and "tool_family" in item:
			cleaned.append({
				"tool_family": str(item["tool_family"]),
				"description": str(item.get("description", "") or "")
			})

	_write_display_tool_family_config(json.dumps(cleaned))
	return {"success": True}


@frappe.whitelist(allow_guest=True)
def get_items_by_tool_family(tool_family, material=None, start=0, page_length=20):
	"""
	Return published Website Item data for a given Tool Family (and optionally Material).
	Uses SQL LIKE on item_name — no DB schema change needed.

	Returns the same shape as webshop's get_product_filter_data items list so
	product-card rendering code can reuse the same buildProductCard() helper.
	"""
	tf_pattern = build_tool_family_like_pattern(tool_family)
	params = [tf_pattern]
	material_clause = ""
	if material:
		mat_pattern = build_material_like_pattern(material)
		material_clause = "AND i.item_name LIKE %s"
		params.append(mat_pattern)

	rows = frappe.db.sql(
		f"""
		SELECT
			wi.name,
			wi.item_code,
			i.item_name,
			wi.web_item_name,
			i.image AS image,
			i.description AS description,
			wi.website_image,
			wi.short_description,
			wi.route,
			wi.published,
			wi.brand,
			i.item_group,
			COALESCE(ip.price_list_rate, 0) AS price
		FROM `tabWebsite Item` wi
		INNER JOIN `tabItem` i ON i.name = wi.item_code
		LEFT JOIN `tabItem Price` ip
			ON ip.item_code = wi.item_code
			AND ip.selling = 1
			AND ip.price_list = (
				SELECT value FROM `tabSingles`
				WHERE doctype = 'Webshop Settings'
				  AND field = 'price_list'
				LIMIT 1
			)
		WHERE wi.published = 1
		  AND i.item_name LIKE %s
		  {material_clause}
		ORDER BY wi.web_item_name
		LIMIT %s OFFSET %s
		""",
		params + [int(page_length), int(start)],
		as_dict=True,
	)

	for row in rows:
		row["in_stock"] = True

	return {"items": rows, "total": len(rows)}


CATALOG_PAGE_SIZE = 12
MAX_CATALOG_PAGE_SIZE = 50

_CATALOG_SORT_ORDER = {
	"default": "wi.web_item_name, wi.name",
	"alpha": "wi.web_item_name, wi.name",
	"price-asc": "price ASC, wi.web_item_name, wi.name",
	"price-desc": "price DESC, wi.web_item_name, wi.name",
}


def _catalog_page(items, page, size, total):
	return {
		"items": items,
		"page": page,
		"size": size,
		"total": total,
		"totalPages": math.ceil(total / size),
	}


@frappe.whitelist(allow_guest=True)
def get_catalog_products(
	tool_family=None,
	material=None,
	item_group=None,
	attribute_filters=None,
	field_filters=None,
	search=None,
	sort=None,
	page=1,
	size=CATALOG_PAGE_SIZE,
):
	"""
	Unified catalog product endpoint that returns item master image and description.
	Combines:
	  - Tool Family filter (parsed from item_name via LIKE)
	  - Material filter (parsed from item_name via LIKE)
	  - Item Group filter
	  - ERP Attribute filters
	  - Brand field filter
	  - Text search
	"""
	if isinstance(attribute_filters, str):
		attribute_filters = json.loads(attribute_filters) if attribute_filters else {}
	if isinstance(field_filters, str):
		field_filters = json.loads(field_filters) if field_filters else {}

	attribute_filters = attribute_filters or {}
	field_filters = field_filters or {}
	page = max(1, frappe.utils.cint(page))
	size = frappe.utils.cint(size)
	size = min(size, MAX_CATALOG_PAGE_SIZE) if size > 0 else CATALOG_PAGE_SIZE
	order_by = _CATALOG_SORT_ORDER.get(frappe.utils.cstr(sort), _CATALOG_SORT_ORDER["default"])
	search = frappe.utils.cstr(search).strip()

	# Build WHERE clauses for item_name-based filters.
	name_clauses = []
	params = []

	if tool_family:
		tf_list = [t.strip() for t in str(tool_family).split(",") if t.strip()]
		if tf_list:
			or_parts = " OR ".join(["i.item_name LIKE %s"] * len(tf_list))
			name_clauses.append(f"({or_parts})")
			params.extend([build_tool_family_like_pattern(tf) for tf in tf_list])

	if material:
		mat_list = [m.strip() for m in str(material).split(",") if m.strip()]
		if mat_list:
			or_parts = " OR ".join(["i.item_name LIKE %s"] * len(mat_list))
			name_clauses.append(f"({or_parts})")
			params.extend([build_material_like_pattern(m) for m in mat_list])

	# Brand field filter (mapped to Brand - الماركة Item Attribute)
	if field_filters.get("brand"):
		brands = field_filters["brand"]
		if isinstance(brands, str):
			brands = [brands]
		if "Brand - الماركة" not in attribute_filters:
			attribute_filters["Brand - الماركة"] = brands

	# Item group filter
	ig = item_group or field_filters.get("item_group")
	ig_clause = ""
	if ig:
		if isinstance(ig, str):
			ig = [ig]
		placeholders = ", ".join(["%s"] * len(ig))
		ig_clause = f"AND (i.item_group IN ({placeholders}) OR wi.item_group IN ({placeholders}))"
		params.extend(ig)
		params.extend(ig)

	# Search
	search_clause = ""
	if search:
		search_clause = "AND (wi.item_code LIKE %s OR i.item_name LIKE %s OR wi.web_item_name LIKE %s OR i.description LIKE %s OR wi.short_description LIKE %s)"
		like_search = f"%{search}%"
		params.extend([like_search] * 5)

	name_where = ("AND " + " AND ".join(name_clauses)) if name_clauses else ""

	# First: get candidate item_codes via item_name filter
	item_code_rows = frappe.db.sql(
		f"""
		SELECT wi.item_code, COALESCE(ip.price_list_rate, 0) AS price
		FROM `tabWebsite Item` wi
		INNER JOIN `tabItem` i ON i.name = wi.item_code
		LEFT JOIN `tabItem Price` ip
			ON ip.item_code = wi.item_code
			AND ip.selling = 1
			AND ip.price_list = (
				SELECT value FROM `tabSingles`
				WHERE doctype = 'Webshop Settings' AND field = 'price_list'
				LIMIT 1
			)
		WHERE wi.published = 1
		  {name_where}
		  {ig_clause}
		  {search_clause}
		ORDER BY {order_by}
		""",
		params,
		as_list=True,
	)
	item_codes = list(dict.fromkeys(r[0] for r in item_code_rows))

	if not item_codes:
		return _catalog_page([], 1, size, 0)

	# Second: apply attribute filters on the candidate set
	if attribute_filters:
		for attr_name, values in attribute_filters.items():
			if not values:
				continue
			if isinstance(values, str):
				values = [values]
			placeholders = ", ".join(["%s"] * len(values))
			matching = frappe.db.sql(
				f"""
				SELECT DISTINCT iva.parent
				FROM `tabItem Variant Attribute` iva
				WHERE iva.parent IN ({", ".join(["%s"] * len(item_codes))})
				  AND iva.attribute = %s
				  AND iva.attribute_value IN ({placeholders})
				""",
				item_codes + [attr_name] + list(values),
				as_list=True,
			)
			matched = {r[0] for r in matching}
			item_codes = [code for code in item_codes if code in matched]
			if not item_codes:
				return _catalog_page([], 1, size, 0)

	total = len(item_codes)

	# Third: fetch full product data for the final page
	page = min(page, math.ceil(total / size))
	page_codes = item_codes[(page - 1) * size : page * size]

	placeholders = ", ".join(["%s"] * len(page_codes))
	rows = frappe.db.sql(
		f"""
		SELECT
			wi.name,
			wi.item_code,
			i.item_name,
			wi.web_item_name,
			i.image AS image,
			i.description AS description,
			wi.website_image,
			wi.short_description,
			wi.route,
			wi.brand,
			i.item_group,
			COALESCE(ip.price_list_rate, 0) AS price
		FROM `tabWebsite Item` wi
		INNER JOIN `tabItem` i ON i.name = wi.item_code
		LEFT JOIN `tabItem Price` ip
			ON ip.item_code = wi.item_code
			AND ip.selling = 1
			AND ip.price_list = (
				SELECT value FROM `tabSingles`
				WHERE doctype = 'Webshop Settings' AND field = 'price_list'
				LIMIT 1
			)
		WHERE wi.item_code IN ({placeholders})
		""",
		page_codes,
		as_dict=True,
	)

	by_code = {}
	for row in rows:
		by_code.setdefault(row.item_code, row)
	items = [by_code[code] for code in page_codes if code in by_code]

	for row in items:
		row["in_stock"] = True

	return _catalog_page(items, page, size, total)


# ============================================================================
# Trending products — ranked by qty sold on submitted Sales Invoices.
# Computed once a day by the scheduler (see hooks.py) and stored in Singles,
# so page visits never run the aggregation and `bench clear-cache` does not
# force a recompute.
# ============================================================================

_TRENDING_SINGLES_FIELD = "custom_trending_items"
_TRENDING_STORE_LIMIT = 12  # store a few extra in case some get unpublished


def _compute_trending_item_codes(limit=_TRENDING_STORE_LIMIT):
	"""
	Rank published Website Items by net quantity sold on submitted Sales Invoices.
	Returns (credit notes) have negative qty and are netted out; items whose
	net sold qty is zero or less are excluded.
	"""
	rows = frappe.db.sql(
		"""
		SELECT sii.item_code, SUM(sii.stock_qty) AS sold_qty
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		INNER JOIN `tabWebsite Item` wi
			ON wi.item_code = sii.item_code AND wi.published = 1
		WHERE si.docstatus = 1
		GROUP BY sii.item_code
		HAVING SUM(sii.stock_qty) > 0
		ORDER BY sold_qty DESC
		LIMIT %s
		""",
		(int(limit),),
		as_dict=True,
	)
	return [{"item_code": r.item_code, "sold_qty": float(r.sold_qty)} for r in rows]


def _write_singles_value(field, value):
	"""Upsert a raw value into tabSingles for Webshop Settings."""
	if frappe.db.sql(
		"SELECT 1 FROM `tabSingles` WHERE `doctype`=%s AND `field`=%s",
		(_SINGLES_DOCTYPE, field),
	):
		frappe.db.sql(
			"UPDATE `tabSingles` SET `value`=%s WHERE `doctype`=%s AND `field`=%s",
			(value, _SINGLES_DOCTYPE, field),
		)
	else:
		frappe.db.sql(
			"INSERT INTO `tabSingles` (`doctype`, `field`, `value`) VALUES (%s, %s, %s)",
			(_SINGLES_DOCTYPE, field, value),
		)


def refresh_trending_items():
	"""Daily scheduler job: recompute and persist the trending ranking."""
	ranking = _compute_trending_item_codes()
	payload = {"computed_on": str(frappe.utils.now_datetime()), "items": ranking}
	_write_singles_value(_TRENDING_SINGLES_FIELD, json.dumps(payload))
	frappe.db.commit()
	return payload


def _read_trending_ranking():
	"""Return stored ranking list, or None if it has never been computed."""
	rows = frappe.db.sql(
		"SELECT `value` FROM `tabSingles` WHERE `doctype`=%s AND `field`=%s",
		(_SINGLES_DOCTYPE, _TRENDING_SINGLES_FIELD),
	)
	if not rows or not rows[0][0]:
		return None
	try:
		data = json.loads(rows[0][0])
		return data.get("items", [])
	except Exception:
		return None


@frappe.whitelist(allow_guest=True)
def get_trending_products(limit=6):
	"""
	Return product cards for the home page Trending section, in ranked order.
	Reads the precomputed daily ranking; only computes on the very first call
	ever (before the scheduler has run once).
	"""
	limit = max(1, min(int(limit), _TRENDING_STORE_LIMIT))

	ranking = _read_trending_ranking()
	if ranking is None:
		ranking = refresh_trending_items()["items"]

	codes = [r["item_code"] for r in ranking]
	if not codes:
		return {"items": []}

	sold_map = {r["item_code"]: r["sold_qty"] for r in ranking}
	placeholders = ", ".join(["%s"] * len(codes))
	rows = frappe.db.sql(
		f"""
		SELECT
			wi.name,
			wi.item_code,
			i.item_name,
			wi.web_item_name,
			i.image AS image,
			i.description AS description,
			wi.website_image,
			wi.short_description,
			wi.route,
			wi.brand,
			i.item_group,
			COALESCE(ip.price_list_rate, 0) AS price
		FROM `tabWebsite Item` wi
		INNER JOIN `tabItem` i ON i.name = wi.item_code
		LEFT JOIN `tabItem Price` ip
			ON ip.item_code = wi.item_code
			AND ip.selling = 1
			AND ip.price_list = (
				SELECT value FROM `tabSingles`
				WHERE doctype = 'Webshop Settings' AND field = 'price_list'
				LIMIT 1
			)
		WHERE wi.item_code IN ({placeholders})
		  AND wi.published = 1
		""",
		codes,
		as_dict=True,
	)

	# Preserve ranking order; drop duplicates from multiple price rows
	by_code = {}
	for row in rows:
		by_code.setdefault(row.item_code, row)
	items = []
	for code in codes:
		row = by_code.get(code)
		if row:
			row["in_stock"] = True
			row["sold_qty"] = sold_map.get(code, 0)
			items.append(row)
		if len(items) >= limit:
			break

	return {"items": items}


# Guests keep their basket in the browser, because building one on the
# server would mean creating a Customer for somebody who has not proved
# who they are - the exact thing custom_webshop.signup exists to prevent.
# The browser therefore holds nothing but item codes and quantities, and
# asks for the rest here. Capped so the endpoint cannot be turned into a
# bulk export of the catalogue.
MAX_CART_PREVIEW_ITEMS = 50


@frappe.whitelist(allow_guest=True)
def get_cart_preview(item_codes):
	"""Names, images and prices for the items in a guest's basket.

	Restricted to *published* Website Items, so this cannot be used to
	read anything a visitor could not already see on the shop, and it
	reads the same price list the catalogue does, so the drawer shows a
	guest what the shop shows them.

	Unknown or unpublished codes are simply absent from the result. The
	caller treats a missing code as an item to drop, which is also how a
	basket recovers when something is unpublished while it sits there.

	Args:
		item_codes: a list of item codes, or its JSON string.

	Returns:
		A list of dicts: item_code, item_name, web_item_name, image,
		route and price.
	"""
	if isinstance(item_codes, str):
		item_codes = json.loads(item_codes or "[]")

	codes = [str(code) for code in (item_codes or []) if code][:MAX_CART_PREVIEW_ITEMS]
	if not codes:
		return []

	placeholders = ", ".join(["%s"] * len(codes))
	return frappe.db.sql(
		f"""
		SELECT
			wi.item_code,
			i.item_name,
			wi.web_item_name,
			COALESCE(NULLIF(wi.website_image, ''), i.image) AS image,
			wi.route,
			COALESCE(ip.price_list_rate, 0) AS price
		FROM `tabWebsite Item` wi
		INNER JOIN `tabItem` i ON i.name = wi.item_code
		LEFT JOIN `tabItem Price` ip
			ON ip.item_code = wi.item_code
			AND ip.selling = 1
			AND ip.price_list = (
				SELECT value FROM `tabSingles`
				WHERE doctype = 'Webshop Settings' AND field = 'price_list'
				LIMIT 1
			)
		WHERE wi.published = 1
		  AND wi.item_code IN ({placeholders})
		""",
		codes,
		as_dict=True,
	)
