import json

import frappe

from custom_webshop.api.item_parser import (
	ALL_TOOL_FAMILIES,
	MATERIAL_LABELS,
	build_material_like_pattern,
	build_tool_family_like_pattern,
	get_material_label,
	parse_item_name,
)


@frappe.whitelist(allow_guest=True)
def get_brands():
	"""Return brands that have at least one published Website Item."""
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT wi.brand
		FROM `tabWebsite Item` wi
		WHERE wi.published = 1
		  AND wi.brand IS NOT NULL
		  AND wi.brand != ''
		ORDER BY wi.brand
		""",
		as_dict=True,
	)
	return rows


@frappe.whitelist(allow_guest=True)
def get_item_attributes():
	"""
	Return all Item Attributes with the distinct values actually used on
	published Website Items, grouped so callers get one entry per
	(attribute, attribute_value) pair.
	"""
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


@frappe.whitelist(allow_guest=True)
def get_tool_families():
	"""
	Return distinct Tool Families derived from published item names, sorted.
	Each entry: {"tool_family": "SEM"}
	"""
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
def get_materials():
	"""
	Return distinct Materials derived from published item names, sorted.
	Each entry: {"material": "C", "label_en": "Carbide", "label_ar": "كربيد"}
	"""
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
def get_all_tool_families():
	"""Return the full canonical list of known tool families (static config)."""
	return [{"tool_family": tf} for tf in ALL_TOOL_FAMILIES]


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
	return [family_map[name] for name in selected if name in family_map]


@frappe.whitelist()
def save_display_tool_families(tool_family_names):
	"""
	Persist the ordered list of enabled tool family names.
	Requires System Manager role.
	tool_family_names: JSON list of tool family name strings.
	"""
	frappe.only_for("System Manager")

	if isinstance(tool_family_names, str):
		tool_family_names = json.loads(tool_family_names)

	if not isinstance(tool_family_names, list):
		frappe.throw("tool_family_names must be a list")

	_write_display_tool_family_config(json.dumps(tool_family_names))
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


@frappe.whitelist(allow_guest=True)
def get_catalog_products(
	tool_family=None,
	material=None,
	attribute_filters=None,
	field_filters=None,
	search=None,
	start=0,
	page_length=20,
):
	"""
	Unified catalog product endpoint that combines:
	  - Tool Family filter  (parsed from item_name via LIKE)
	  - Material filter     (parsed from item_name via LIKE)
	  - ERP Attribute filters (delegated to webshop's filter engine)
	  - Brand field filter
	  - Text search

	When tool_family or material is provided, this endpoint handles the full
	query.  When neither is set, callers should use the standard webshop API
	(get_product_filter_data) directly for maximum compatibility.
	"""
	if isinstance(attribute_filters, str):
		attribute_filters = json.loads(attribute_filters) if attribute_filters else {}
	if isinstance(field_filters, str):
		field_filters = json.loads(field_filters) if field_filters else {}

	attribute_filters = attribute_filters or {}
	field_filters = field_filters or {}
	start = int(start)
	page_length = int(page_length)

	# Build WHERE clauses for item_name-based filters
	name_clauses = []
	params = []

	if tool_family:
		name_clauses.append("i.item_name LIKE %s")
		params.append(build_tool_family_like_pattern(tool_family))

	if material:
		name_clauses.append("i.item_name LIKE %s")
		params.append(build_material_like_pattern(material))

	# Brand field filter
	brand_clause = ""
	if field_filters.get("brand"):
		brands = field_filters["brand"]
		if isinstance(brands, str):
			brands = [brands]
		placeholders = ", ".join(["%s"] * len(brands))
		brand_clause = f"AND wi.brand IN ({placeholders})"
		params.extend(brands)

	# Search
	search_clause = ""
	if search:
		search_clause = "AND (i.item_name LIKE %s OR wi.web_item_name LIKE %s OR wi.short_description LIKE %s)"
		like_search = f"%{search}%"
		params.extend([like_search, like_search, like_search])

	name_where = ("AND " + " AND ".join(name_clauses)) if name_clauses else ""

	# First: get candidate item_codes via item_name filter
	item_code_rows = frappe.db.sql(
		f"""
		SELECT wi.item_code
		FROM `tabWebsite Item` wi
		INNER JOIN `tabItem` i ON i.name = wi.item_code
		WHERE wi.published = 1
		  {name_where}
		  {brand_clause}
		  {search_clause}
		""",
		params,
		as_list=True,
	)
	item_codes = [r[0] for r in item_code_rows]

	if not item_codes:
		return {"items": [], "total": 0}

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
			item_codes = [r[0] for r in matching]
			if not item_codes:
				return {"items": [], "total": 0}

	total = len(item_codes)

	# Third: fetch full product data for the final page
	page_codes = item_codes[start : start + page_length]
	if not page_codes:
		return {"items": [], "total": total}

	placeholders = ", ".join(["%s"] * len(page_codes))
	rows = frappe.db.sql(
		f"""
		SELECT
			wi.name,
			wi.item_code,
			i.item_name,
			wi.web_item_name,
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
		ORDER BY wi.web_item_name
		""",
		page_codes,
		as_dict=True,
	)

	for row in rows:
		row["in_stock"] = True

	return {"items": rows, "total": total}
