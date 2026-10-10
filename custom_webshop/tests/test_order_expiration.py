import frappe
from frappe.tests.utils import FrappeTestCase
from custom_webshop.shopping_cart.cart_override import _send_order_email
from custom_webshop.tasks import expire_unpaid_webshop_reservations
from custom_webshop.www.payment import get_context as get_payment_context
from custom_webshop.api.payment import confirm_payment

class TestOrderExpiration(FrappeTestCase):
	def test_order_expired_email_template_renders(self):
		"""Verify that order_expired.html renders without Jinja syntax errors."""
		# Create a dummy or find an existing Sales Order
		so_name = frappe.db.get_value("Sales Order", {"order_type": "Shopping Cart"}, "name")
		if not so_name:
			so_name = frappe.db.get_value("Sales Order", {}, "name")
		
		so_doc = frappe.get_doc("Sales Order", so_name)
		
		# Test rendering template directly
		context = {
			"site_url": "http://testsite.local",
			"shop_url": "http://testsite.local/shop",
			"site_name": "CNCLeaders Corp",
			"first_name": "Ahmed",
			"sales_order": so_doc,
		}
		html = frappe.render_template("custom_webshop/templates/emails/order_expired.html", context)
		self.assertIn("انتهت مهلة سداد الطلب", html)
		self.assertIn("The inventory reservation for order", html)
		self.assertIn(so_doc.name, html)
		self.assertIn("Visit Shop & Reorder", html)

	def test_payment_page_blocks_cancelled_order(self):
		"""Verify that www/payment.py displays the expiration notice when an order is Cancelled."""
		# Find or mock a sales order
		so_name = frappe.db.get_value("Sales Order", {"order_type": "Shopping Cart"}, "name")
		if not so_name:
			so_name = frappe.db.get_value("Sales Order", {}, "name")
		so = frappe.get_doc("Sales Order", so_name)

		orig_status = so.status
		try:
			so.db_set("status", "Cancelled")
			# Simulate user request context
			frappe.form_dict.order_id = so.name
			frappe.session.user = so.owner or "Administrator"
			
			ctx = frappe._dict({})
			res = get_payment_context(ctx)
			
			self.assertTrue(res.get("invalid"))
			self.assertTrue(res.get("is_expired"))
			self.assertIn("expired", res.get("error").lower())
			self.assertEqual(res.get("action_url"), "/shop")
		finally:
			so.db_set("status", orig_status)
			frappe.form_dict.order_id = None

	def test_confirm_payment_blocks_cancelled_order(self):
		"""Verify that confirm_payment API raises ValidationError when status is Cancelled."""
		so_name = frappe.db.get_value("Sales Order", {"order_type": "Shopping Cart"}, "name")
		if not so_name:
			so_name = frappe.db.get_value("Sales Order", {}, "name")
		so = frappe.get_doc("Sales Order", so_name)

		orig_status = so.status
		try:
			so.db_set("status", "Cancelled")
			# Associate user
			customer = so.customer
			frappe.session.user = so.owner or "Administrator"
			
			# Ensure Portal User link
			if not frappe.db.exists("Portal User", {"user": frappe.session.user, "parent": customer}):
				p_user = frappe.new_doc("Portal User")
				p_user.parent = customer
				p_user.parenttype = "Customer"
				p_user.parentfield = "portal_users"
				p_user.user = frappe.session.user
				p_user.insert(ignore_permissions=True)

			with self.assertRaises(frappe.ValidationError):
				confirm_payment(
					order_id=so.name,
					payment_method="instapay",
					filename="receipt.jpg",
					file_content="aGVsbG8="
				)
		finally:
			so.db_set("status", orig_status)

	def test_payment_page_renders_warning_banner(self):
		"""Verify that payment.html renders the 60-minute warning banner and PAYMENT_DATA with created_at."""
		so_name = frappe.db.get_value("Sales Order", {"order_type": "Shopping Cart", "docstatus": 0, "status": ["!=", "Cancelled"]}, "name")
		if not so_name:
			so_name = frappe.db.get_value("Sales Order", {"docstatus": 0}, "name")
		
		so = frappe.get_doc("Sales Order", so_name)
		orig_status = so.status
		try:
			so.db_set("status", "Draft")
			frappe.form_dict.order_id = so.name
			owner_user = frappe.db.get_value("Webshop Account Identity", {"customer": so.customer}, "user") or so.owner
			frappe.session.user = owner_user

			ctx = frappe._dict({})
			res = get_payment_context(ctx)
			self.assertFalse(res.get("invalid", False))

			# Render HTML with Frappe template renderer
			html = frappe.render_template("custom_webshop/www/payment.html", res)
			self.assertIn("payment-warning-banner", html)
			self.assertIn("payment-countdown-badge", html)
			self.assertIn("payment_warning_title", html)
			self.assertIn("created_at", html)
		finally:
			so.db_set("status", orig_status)
			frappe.form_dict.order_id = None


