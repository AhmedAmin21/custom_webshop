import traceback

import frappe


def diagnose():
	frappe.init(site="site1.local")
	frappe.connect()
	from webshop.webshop.api import get_product_filter_data
	print("=== get_product_filter_data ===")
	try:
		r = get_product_filter_data({"start": 0})
		print("OK:", r if not isinstance(r, dict) else {k: r[k] for k in list(r)[:5]})
	except Exception:
		traceback.print_exc()

	print("\n=== custom fields ===")
	for field in ("custom_payment_method", "custom_instapay_number", "custom_hero_slides_json"):
		print(field, frappe.db.exists("Custom Field", {"fieldname": field}))

	print("\n=== error log (latest product query) ===")
	err = frappe.db.sql(
		"""SELECT error FROM `tabError Log`
		WHERE method LIKE '%product%' OR error LIKE '%wishlist%'
		ORDER BY creation DESC LIMIT 1""",
		as_dict=True,
	)
	if err:
		print(err[0].error[:500])


if __name__ == "__main__":
	diagnose()
