import frappe
from custom_webshop.tests.test_phase2_concurrency import setup_test_data

def measure():
	setup_test_data()
	
	frappe.set_user("test_user1@example.com")
	
	from custom_webshop.shopping_cart.cart_override import update_cart
	update_cart("TEST-ITEM-1", 1)
	update_cart("TEST-ITEM-2", 1)
	
	frappe.db.commit()
	
	# Start profiling
	import frappe.utils.profiler
	
	frappe.db.sql("SET profiling = 1")
	frappe.db.queries = []
	
	from webshop.webshop.shopping_cart.cart import get_cart_quotation
	res = get_cart_quotation()
	
	query_count = len(frappe.db.queries)
	print(f"Total queries for get_cart_quotation with 2 items: {query_count}")
	
	for q in frappe.db.queries:
		print(q)
	
	return query_count

if __name__ == "__main__":
	frappe.init(site="erpnext.local")
	frappe.connect()
	measure()
