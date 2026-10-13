# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

import time
import frappe
from custom_webshop.api.items import publish_items_to_website


def run_benchmark():
	print("==================================================")
	print("STARTING 50-ITEM BULK PUBLISH & TEMPLATE SKIP TEST")
	print("==================================================")

	# 1. Clean up test items
	cleanup_codes = [f"TEST-BENCH-PUB-{i:02d}" for i in range(1, 51)] + [
		"TEST-TEMPLATE-ITEM",
		"TEST-STANDARD-ITEM",
	]
	for code in cleanup_codes:
		if frappe.db.exists("Website Item", {"item_code": code}):
			frappe.delete_doc(
				"Website Item",
				frappe.db.get_value(
					"Website Item", {"item_code": code}, "name"
				),
				force=True,
			)
		if frappe.db.exists("Item", code):
			frappe.delete_doc("Item", code, force=True)
	frappe.db.commit()

	# 2. Test template skipping & reason reporting
	print("\n[Step 1] Testing Template Skip and Detailed Reasons...")
	# Create 1 template item (has_variants = 1 with attribute)
	tpl = frappe.get_doc({
		"doctype": "Item",
		"item_code": "TEST-TEMPLATE-ITEM",
		"item_name": "Test Template Product",
		"item_group": "Consumable",
		"stock_uom": "Nos",
		"has_variants": 1,
		"published_in_website": 0,
		"attributes": [{"attribute": "Colour"}],
	}).insert(ignore_permissions=True)

	# Create 1 standard item
	std = frappe.get_doc({
		"doctype": "Item",
		"item_code": "TEST-STANDARD-ITEM",
		"item_name": "Test Standard Product",
		"item_group": "Consumable",
		"stock_uom": "Nos",
		"has_variants": 0,
		"published_in_website": 0,
	}).insert(ignore_permissions=True)
	frappe.db.commit()

	# Test batch containing: 1 standard, 1 template, 1 non-existent
	test_batch = [
		"TEST-STANDARD-ITEM",
		"TEST-TEMPLATE-ITEM",
		"NON-EXISTENT-ITEM-999",
	]
	batch_res = publish_items_to_website(test_batch)
	print(f"-> Batch Result: {batch_res['message']}")
	print(f"-> Details: {batch_res['details']}")

	# Assertions
	assert (
		batch_res["published"] == 1
	), f"Expected 1 published, got {batch_res['published']}"
	assert (
		batch_res["skipped"] == 1
	), f"Expected 1 skipped, got {batch_res['skipped']}"
	assert (
		batch_res["failed"] == 1
	), f"Expected 1 failed, got {batch_res['failed']}"

	# Check reasons
	reasons = {d["item_code"]: (d["status"], d["reason"]) for d in batch_res["details"]}
	assert "TEST-TEMPLATE-ITEM" in reasons, "Template item missing in details"
	assert reasons["TEST-TEMPLATE-ITEM"][0] == "Skipped"
	assert "Template item" in reasons["TEST-TEMPLATE-ITEM"][1]

	assert "NON-EXISTENT-ITEM-999" in reasons, "Non-existent item missing in details"
	assert reasons["NON-EXISTENT-ITEM-999"][0] == "Failed"

	# Verify Website Item was NOT created for template
	assert not frappe.db.exists(
		"Website Item", {"item_code": "TEST-TEMPLATE-ITEM"}
	), "Website Item should NOT be created for template"
	# Verify Website Item WAS created for standard item
	assert frappe.db.exists(
		"Website Item", {"item_code": "TEST-STANDARD-ITEM"}
	), "Website Item SHOULD be created for standard item"
	print("-> PASS: Template was skipped cleanly, reasons verified!")

	# Clean up initial test items
	for code in ["TEST-TEMPLATE-ITEM", "TEST-STANDARD-ITEM"]:
		web_name = frappe.db.get_value(
			"Website Item", {"item_code": code}, "name"
		)
		if web_name:
			frappe.delete_doc("Website Item", web_name, force=True)
		if frappe.db.exists("Item", code):
			frappe.delete_doc("Item", code, force=True)
	frappe.db.commit()

	# 3. Create 50 test items (45 standard items, 5 template items)
	print("\n[Step 2] Creating 50 test items (45 standard + 5 templates)...")
	item_codes = [f"TEST-BENCH-PUB-{i:02d}" for i in range(1, 51)]
	create_start = time.time()
	for i, code in enumerate(item_codes, 1):
		is_template = 1 if i <= 5 else 0
		doc_dict = {
			"doctype": "Item",
			"item_code": code,
			"item_name": f"Test Benchmark Product {code}",
			"item_group": "Consumable",
			"stock_uom": "Nos",
			"has_variants": is_template,
			"published_in_website": 0,
		}
		if is_template:
			doc_dict["attributes"] = [{"attribute": "Colour"}]
		item = frappe.get_doc(doc_dict)
		item.insert(ignore_permissions=True)
	frappe.db.commit()
	print(f"-> 50 items created in {round(time.time() - create_start, 2)}s.")

	# 4. Measure publishing 50 items
	print("\n[Step 3] Publishing the 50 items...")
	t0 = time.time()
	result = publish_items_to_website(item_codes)
	total_time = round(time.time() - t0, 3)

	print(f"-> Result: {result['message']}")
	print(f"-> Published: {result['published']} (expected 45)")
	print(f"-> Skipped: {result['skipped']} (expected 5 templates)")
	print(f"-> Failed: {result['failed']} (expected 0)")
	print(f"-> Time Taken: {total_time}s")
	print(f"-> Skipped Reasons in details: {len(result['details'])}")
	for d in result["details"]:
		print(f"    - {d['item_code']}: {d['status']} ({d['reason']})")

	assert result["published"] == 45, f"Expected 45, got {result['published']}"
	assert result["skipped"] == 5, f"Expected 5, got {result['skipped']}"
	assert result["failed"] == 0, f"Expected 0, got {result['failed']}"

	# 5. Clean up
	print("\n[Step 4] Cleaning up test records...")
	for code in item_codes:
		web_name = frappe.db.get_value(
			"Website Item", {"item_code": code}, "name"
		)
		if web_name:
			frappe.delete_doc("Website Item", web_name, force=True)
		if frappe.db.exists("Item", code):
			frappe.delete_doc("Item", code, force=True)
	frappe.db.commit()
	print("-> Cleanup complete. Database is clean.")

	print("\n==================================================")
	print(
		f"ALL TESTS PASSED: 50 items batch processed in {total_time}s"
	)
	print("==================================================")
	return result


def create_100_test_items():
	"""Create 100 test items (95 standard + 5 templates) for user testing."""
	print("Creating 100 test items in ERPNext...")

	# 95 standard items
	for i in range(1, 96):
		code = f"TEST-ITEM-{i:03d}"
		if not frappe.db.exists("Item", code):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": code,
				"item_name": f"Test Item {i:03d}",
				"item_group": "Consumable",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"has_variants": 0,
				"published_in_website": 0,
			})
			item.insert(ignore_permissions=True)

	# 5 template items (to test template skipping)
	for i in range(96, 101):
		code = f"TEST-TEMPLATE-{i:03d}"
		if not frappe.db.exists("Item", code):
			item = frappe.get_doc({
				"doctype": "Item",
				"item_code": code,
				"item_name": f"Test Template Item {i:03d}",
				"item_group": "Consumable",
				"stock_uom": "Nos",
				"is_stock_item": 0,
				"has_variants": 1,
				"attributes": [{"attribute": "Colour"}],
				"published_in_website": 0,
			})
			item.insert(ignore_permissions=True)

	frappe.db.commit()
	count = frappe.db.count("Item", {"item_code": ["like", "TEST-%"]})
	print(f"Successfully created 100 test items. Total matching TEST-% in DB: {count}")


def cleanup_100_test_items():
	"""Delete the 100 test items and their Website Items."""
	print("Cleaning up 100 test items...")
	items = frappe.get_all("Item", filters={"item_code": ["like", "TEST-%"]}, pluck="name")
	for code in items:
		web_name = frappe.db.get_value("Website Item", {"item_code": code}, "name")
		if web_name:
			frappe.delete_doc("Website Item", web_name, force=True)
		frappe.delete_doc("Item", code, force=True)
	frappe.db.commit()
	print("Cleanup complete.")

