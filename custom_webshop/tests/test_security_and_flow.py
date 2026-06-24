"""Tests for custom_webshop security and checkout services."""

import frappe

from custom_webshop.services.customer_identity import (
	get_customer_for_user,
	verify_address_belongs_to_customer,
)
from custom_webshop.api import shop


def run():
	results = []

	def test(name, fn):
		try:
			out = fn()
			results.append((name, "PASS", out))
		except Exception as e:
			results.append((name, "FAIL", str(e)))

	def test_signup_creates_unique_customer():
		email = f"testuser_{frappe.generate_hash(length=6)}@example.com"
		from custom_webshop.api.auth import custom_sign_up

		code, msg = custom_sign_up(email, "Test User", "/shop", "TestPass123!", "01000000000")
		assert code == 1
		frappe.set_user(email)
		customer = get_customer_for_user()
		assert customer is not None
		return customer.name

	test("signup_creates_unique_customer", test_signup_creates_unique_customer)

	frappe.set_user("Guest")
	test("get_categories_from_erp", lambda: shop.get_categories())
	test("get_payment_options_shape", lambda: shop.get_shop_context().get("payment_options"))

	print("\n=== CUSTOM WEBSHOP TESTS ===")
	for name, status, detail in results:
		print(f"{status}  {name}: {detail}")

	return results


if __name__ == "__main__":
	frappe.connect()
	run()
