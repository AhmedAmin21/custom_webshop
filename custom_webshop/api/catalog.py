import json

import frappe


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

	try:
		raw = _read_display_attribute_config()
		if not raw:
			return all_attrs
		selected = json.loads(raw)
		if not isinstance(selected, list) or not selected:
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
