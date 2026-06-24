"""Backend smoke tests for custom_webshop integration."""
import frappe


def run():
	results = []

	def test(name, fn):
		try:
			out = fn()
			results.append((name, "PASS", out))
		except Exception as e:
			frappe.log_error(title=f"Backend test failed: {name}")
			results.append((name, "FAIL", str(e)))

	from custom_webshop.api import shop, admin
	from custom_webshop.shopping_cart import shipping_api
	import webshop.webshop.api as webshop_api
	import webshop.webshop.shopping_cart.product_info as product_info

	# Guest context
	frappe.set_user("Guest")

	test("get_shop_context", shop.get_shop_context)
	test("get_categories", shop.get_categories)
	test("get_products", lambda: shop.get_products({"start": 0}))
	test("get_home_data", shop.get_home_data)
	test("get_cart_json", shop.get_cart_json)
	test("get_product_filter_data", lambda: webshop_api.get_product_filter_data({"start": 0}))
	test("get_governorates", shipping_api.get_governorates)
	test("get_governorate_shipping_rules", shipping_api.get_governorate_shipping_rules)

	item = frappe.db.get_value("Website Item", {"published": 1}, "item_code")
	if item:
		test("get_product_detail", lambda: shop.get_product_detail(item))
		test(
			"get_product_info_for_website",
			lambda: product_info.get_product_info_for_website(item, skip_quotation_creation=True),
		)
	else:
		results.append(("get_product_detail", "SKIP", "No published Website Items"))

	# Admin context
	frappe.set_user("Administrator")
	test("admin.get_analytics", admin.get_analytics)
	test("admin.get_inventory", admin.get_inventory)
	test("admin.get_pending_orders", admin.get_pending_orders)
	test("admin.get_slides", admin.get_slides)
	test("get_orders_json", shop.get_orders_json)

	# Override wiring
	test(
		"hook: place_order override",
		lambda: frappe.get_hooks("override_whitelisted_methods").get(
			"webshop.webshop.shopping_cart.cart.place_order"
		),
	)
	test(
		"import: place_order_from_cart",
		lambda: frappe.get_attr(
			"custom_webshop.shopping_cart.cart_override.place_order_from_cart"
		).__name__,
	)
	test(
		"import: confirm_payment",
		lambda: frappe.get_attr("custom_webshop.api.payment.confirm_payment").__name__,
	)

	# Custom fields (may need sync)
	for field in ("custom_instapay_number", "custom_hero_slides_json"):
		exists = frappe.db.exists(
			"Custom Field", {"fieldname": field, "dt": "Webshop Settings"}
		)
		results.append((f"custom_field:{field}", "PASS" if exists else "WARN", bool(exists)))

	print("\n=== BACKEND TEST RESULTS ===")
	passed = failed = skipped = warned = 0
	for name, status, detail in results:
		if status == "PASS":
			passed += 1
			if isinstance(detail, dict):
				summary = {
					k: (len(v) if isinstance(v, (list, dict)) else v)
					for k, v in list(detail.items())[:8]
				}
			elif isinstance(detail, list):
				summary = f"list[{len(detail)}]"
			else:
				summary = detail
			print(f"PASS  {name}: {summary}")
		elif status == "SKIP":
			skipped += 1
			print(f"SKIP  {name}: {detail}")
		elif status == "WARN":
			warned += 1
			print(f"WARN  {name}: {detail}")
		else:
			failed += 1
			print(f"FAIL  {name}: {detail}")

	pub = frappe.db.count("Website Item", {"published": 1})
	gov = frappe.db.count("Governorate", {"enabled": 1})
	draft_so = frappe.db.count("Sales Order", {"docstatus": 0})
	print(
		f"\nSummary: {passed} passed, {failed} failed, {skipped} skipped, {warned} warnings"
	)
	print(
		f"Data: {pub} published Website Items, {gov} governorates, {draft_so} draft Sales Orders"
	)
	return {"passed": passed, "failed": failed, "skipped": skipped, "warnings": warned}


if __name__ == "__main__":
	frappe.connect()
	run()
