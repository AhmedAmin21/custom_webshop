# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

import time
import frappe
from frappe import _
from webshop.webshop.doctype.website_item.website_item import make_website_item

MAX_BATCH_SIZE = 50


@frappe.whitelist()
def publish_items_to_website(item_codes):
	"""Publish a batch of items to Website Items with a strict 50-item limit.
	Restricted to authorized staff roles.

	Args:
		item_codes: list or JSON list of Item codes.

	Returns:
		dict with published, skipped, failed counts, elapsed time, and summary message.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to continue."), frappe.PermissionError)

	allowed_roles = {"Item Manager", "Stock Manager", "Website Manager", "System Manager"}
	user_roles = set(frappe.get_roles(frappe.session.user))
	if not (user_roles & allowed_roles):
		frappe.throw(_("Not permitted to publish items to website."), frappe.PermissionError)

	if isinstance(item_codes, str):
		item_codes = frappe.parse_json(item_codes)

	if not item_codes:
		frappe.throw(_("No items selected to publish."))

	if len(item_codes) > MAX_BATCH_SIZE:
		frappe.throw(
			_(
				"Cannot publish more than {0} items at a time to prevent system load. "
				"You selected {1} items. Please select 50 or fewer items."
			).format(MAX_BATCH_SIZE, len(item_codes)),
			title=_("Batch Limit Exceeded"),
		)

	start_time = time.time()
	published = 0
	skipped = 0
	failed = 0
	details = []

	for item_code in item_codes:
		try:
			# Verify item exists and check template/status
			item_data = frappe.db.get_value(
				"Item",
				item_code,
				["name", "has_variants", "published_in_website", "disabled", "is_sales_item"],
				as_dict=True,
			)

			if not item_data:
				failed += 1
				details.append({
					"item_code": item_code,
					"status": "Failed",
					"reason": _("Item does not exist"),
				})
				continue

			disabled = item_data.get("disabled") if isinstance(item_data, dict) else getattr(item_data, "disabled", False)
			is_sales = item_data.get("is_sales_item") if isinstance(item_data, dict) else getattr(item_data, "is_sales_item", True)
			has_variants = item_data.get("has_variants") if isinstance(item_data, dict) else getattr(item_data, "has_variants", False)

			# 1. Skip Disabled items
			if disabled:
				skipped += 1
				details.append({
					"item_code": item_code,
					"status": "Skipped",
					"reason": _("Item is disabled"),
				})
				continue

			# 2. Skip Non-sales items
			if not is_sales:
				skipped += 1
				details.append({
					"item_code": item_code,
					"status": "Skipped",
					"reason": _("Item is not marked as a sales item"),
				})
				continue

			# 3. Skip Template items (has_variants = 1)
			if has_variants:
				skipped += 1
				details.append({
					"item_code": item_code,
					"status": "Skipped",
					"reason": _("Template item (has variants)"),
				})
				continue

			# 2. Check if Website Item already exists
			existing_web_item = frappe.db.get_value(
				"Website Item",
				{"item_code": item_code},
				["name", "published"],
				as_dict=True,
			)

			if existing_web_item:
				is_published = (
					existing_web_item.get("published")
					if isinstance(existing_web_item, dict)
					else getattr(existing_web_item, "published", 0)
				)
				web_item_name = (
					existing_web_item.get("name")
					if isinstance(existing_web_item, dict)
					else getattr(existing_web_item, "name", None)
				)
				if not is_published:
					frappe.db.set_value(
						"Website Item", web_item_name, "published", 1
					)
					frappe.db.set_value("Item", item_code, "published_in_website", 1)
					published += 1
				else:
					skipped += 1
					details.append({
						"item_code": item_code,
						"status": "Skipped",
						"reason": _("Already published"),
					})
				continue

			# 3. Create Website Item for standard item or variant
			item_doc = frappe.get_doc("Item", item_code)
			make_website_item(item_doc, save=True)
			published += 1

		except Exception as e:
			failed += 1
			err_msg = str(e)
			details.append({
				"item_code": item_code,
				"status": "Failed",
				"reason": err_msg,
			})
			frappe.log_error(
				f"Failed to publish item {item_code} to website: {err_msg}",
				"Bulk Website Item Publish",
			)

	elapsed = round(time.time() - start_time, 2)

	summary = _(
		"{0} item(s) published, {1} skipped, {2} failed in {3}s."
	).format(published, skipped, failed, elapsed)

	return {
		"published": published,
		"skipped": skipped,
		"failed": failed,
		"time_taken": elapsed,
		"details": details,
		"message": summary,
	}

