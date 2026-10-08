import time
import threading
import frappe
from erpnext.stock.doctype.item.test_item import make_item
from custom_webshop.shopping_cart.cart_override import place_order_from_cart
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry
from custom_webshop.api.payment import confirm_payment, reject_payment_proof
from custom_webshop.tasks import expire_unpaid_webshop_reservations
from frappe.utils import add_to_date, now_datetime

def create_test_item(item_code, is_stock_item=1):
	if not frappe.db.exists("Item", item_code):
		make_item(item_code, {"is_stock_item": is_stock_item})
	if not frappe.db.exists("Website Item", {"item_code": item_code}):
		doc = frappe.new_doc("Website Item")
		doc.item_code = item_code
		doc.published = 1
		doc.website_warehouse = "Stores - _TC"
		doc.insert(ignore_permissions=True)
	return item_code

def add_stock(item_code, qty, warehouse="Stores - _TC"):
	make_stock_entry(item_code=item_code, target=warehouse, qty=qty, basic_rate=100)

def setup_test_data():
	frappe.set_user("Administrator")
	# Create Company if needed
	if not frappe.db.exists("Company", "_Test Company"):
		frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test Company",
			"default_currency": "EGP",
			"abbr": "_TC"
		}).insert()

	# Create Warehouse if needed
	if not frappe.db.exists("Warehouse", "Stores - _TC"):
		frappe.get_doc({
			"doctype": "Warehouse",
			"warehouse_name": "Stores",
			"company": "_Test Company"
		}).insert()

	create_test_item("TEST-ITEM-1")
	create_test_item("TEST-ITEM-2")
	add_stock("TEST-ITEM-1", 10)
	add_stock("TEST-ITEM-2", 1)
	
	# Setup Webshop Settings
	settings = frappe.get_doc("Webshop Settings")
	settings.company = "_Test Company"
	settings.allow_items_not_in_stock = 0
	settings.save()
	
	# Create test customer and portal user
	if not frappe.db.exists("Customer", "Test Customer Webshop"):
		frappe.get_doc({
			"doctype": "Customer",
			"customer_name": "Test Customer Webshop",
			"customer_group": "Commercial",
			"territory": "All Territories"
		}).insert()
	
	if not frappe.db.exists("Portal User", {"parent": "Test Customer Webshop", "user": "test_webshop@example.com"}):
		cust = frappe.get_doc("Customer", "Test Customer Webshop")
		cust.append("portal_users", {"user": "test_webshop@example.com"})
		cust.save()
		
	# Create User
	if not frappe.db.exists("User", "test_webshop@example.com"):
		frappe.get_doc({
			"doctype": "User",
			"email": "test_webshop@example.com",
			"first_name": "Test Webshop",
			"send_welcome_email": 0
		}).insert()
	
	frappe.db.commit()

def run_tests():
	print("Setting up test data...")
	setup_test_data()
	
	print("Test setup complete.")
	
	# Test 1: Real concurrent checkout test
	import threading
	import time

	# Create a quotation to simulate the cart
	def simulate_checkout(customer_email):
		frappe.set_user(customer_email)
		# clear cart
		from custom_webshop.shopping_cart.cart_override import _get_cart_quotation, update_cart, place_order_from_cart
		quotation = _get_cart_quotation()
		if quotation:
			quotation.delete()
		
		# add item
		update_cart("TEST-ITEM-2", 1)
		
		# place order
		try:
			order_name = place_order_from_cart("Test notes")
			return order_name, None
		except Exception as e:
			frappe.db.rollback()
			return None, str(e)

	print("Running Concurrency Test for Stock=1...")
	results = []
	def worker(email, index):
		res, err = simulate_checkout(email)
		results.append((index, res, err))

	# User 1
	frappe.set_user("Administrator")
	if not frappe.db.exists("User", "test_user1@example.com"):
		frappe.get_doc({"doctype": "User", "email": "test_user1@example.com", "first_name": "User 1", "send_welcome_email": 0}).insert(ignore_permissions=True)
		cust1 = frappe.new_doc("Customer")
		cust1.customer_name = "User 1"
		cust1.append("portal_users", {"user": "test_user1@example.com"})
		cust1.insert(ignore_permissions=True)
		
		frappe.get_doc({"doctype": "User", "email": "test_user2@example.com", "first_name": "User 2", "send_welcome_email": 0}).insert(ignore_permissions=True)
		cust2 = frappe.new_doc("Customer")
		cust2.customer_name = "User 2"
		cust2.append("portal_users", {"user": "test_user2@example.com"})
		cust2.insert(ignore_permissions=True)
		
		frappe.db.commit()

	t1 = threading.Thread(target=worker, args=("test_user1@example.com", 1))
	t2 = threading.Thread(target=worker, args=("test_user2@example.com", 2))
	
	# Need a way to run Frappe in threads properly, Frappe DB connections are thread-local
	# Let's run it serially but with a simulated delay inside the lock?
	# Actually, standard python threads in Frappe test runner might share the same DB connection or fail.
	# Better to use a test case class.
	return "done"
