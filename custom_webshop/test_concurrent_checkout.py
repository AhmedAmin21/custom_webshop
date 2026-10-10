import frappe
import requests
import threading
import time

def setup_data():
	from custom_webshop.tests.test_phase2_concurrency import setup_test_data
	setup_test_data()
	
	frappe.db.set_value("Webshop Settings", "Webshop Settings", "allow_items_not_in_stock", 0)
	
	# Clear SREs and set stock to 1
	frappe.db.sql("DELETE FROM `tabStock Reservation Entry`")
	frappe.db.sql("DELETE FROM `tabSales Order`")
	frappe.db.sql("DELETE FROM `tabSales Order Item`")
	frappe.db.commit()
	
	# reset stock to exactly 1
	from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
	frappe.db.sql("DELETE FROM `tabStock Ledger Entry`")
	frappe.db.sql("UPDATE `tabBin` SET actual_qty=0, reserved_stock=0, reserved_qty=0")
	frappe.db.commit()
	
	make_stock_entry(item_code="TEST-ITEM-2", target="Stores - _TC", qty=1, basic_rate=100)
	frappe.db.commit()
	
	return frappe.utils.get_url()

def checkout_worker(site_url, email, password, results, index):
	session = requests.Session()
	# Login
	res = session.post(f"{site_url}/api/method/login", data={"usr": email, "pwd": password})
	if res.status_code != 200:
		results.append((index, False, "Login failed"))
		return
		
	# Clear cart
	session.post(f"{site_url}/api/method/custom_webshop.shopping_cart.cart_override.update_cart", data={"item_code": "TEST-ITEM-2", "qty": 0})
	
	# Add 1 item
	session.post(f"{site_url}/api/method/custom_webshop.shopping_cart.cart_override.update_cart", data={"item_code": "TEST-ITEM-2", "qty": 1})
	
	# Place order (we will block here to synchronize)
	time.sleep(1) # wait for other thread to be ready
	res = session.post(f"{site_url}/api/method/custom_webshop.shopping_cart.cart_override.place_order_from_cart", data={"notes": "Concurrent test"})
	
	try:
		data = res.json()
		if "message" in data and isinstance(data["message"], str) and data["message"].startswith("SAL-"):
			results.append((index, True, data["message"]))
		elif "exc_type" in data and data["exc_type"] == "ValidationError":
			results.append((index, False, "Validation Error: Out of stock"))
		else:
			results.append((index, False, str(data)))
	except Exception as e:
		results.append((index, False, str(e)))

def run_test():
	url = setup_data()
	
	# We need passwords for the users to use HTTP
	frappe.set_user("Administrator")
	for i in [1, 2]:
		user = frappe.get_doc("User", f"test_user{i}@example.com")
		user.new_password = "password123"
		user.save(ignore_permissions=True)
	frappe.db.commit()
	
	results = []
	t1 = threading.Thread(target=checkout_worker, args=(url, "test_user1@example.com", "password123", results, 1))
	t2 = threading.Thread(target=checkout_worker, args=(url, "test_user2@example.com", "password123", results, 2))
	
	print("Starting concurrent checkout test...")
	t1.start()
	t2.start()
	t1.join()
	t2.join()
	
	success_count = sum(1 for r in results if r[1])
	print(f"Results: {results}")
	print(f"Successful checkouts: {success_count} (Expected: 1)")
	
	if success_count == 1:
		print("Concurrency test PASSED.")
	else:
		print("Concurrency test FAILED.")

if __name__ == "__main__":
	run_test()
