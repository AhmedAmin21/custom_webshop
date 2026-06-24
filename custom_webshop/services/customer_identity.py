"""Portal customer resolution and document ownership helpers."""

import frappe
from frappe import _


def get_portal_customer_names(user=None):
	"""Return Customer names linked to the user via Portal User."""
	if not user:
		user = frappe.session.user
	if user == "Guest":
		return []
	return frappe.get_all(
		"Portal User",
		filters={"user": user, "parenttype": "Customer"},
		pluck="parent",
	)


def get_customer_for_user(user=None):
	"""Return the Customer doc for the current portal user."""
	names = get_portal_customer_names(user)
	if not names:
		return None
	return frappe.get_doc("Customer", names[0])


def require_customer_for_user(user=None):
	customer = get_customer_for_user(user)
	if not customer:
		frappe.throw(_("Customer not found."), frappe.DoesNotExistError)
	return customer


def get_party_for_user(user=None):
	"""Preferred party resolver for custom_webshop — Portal User first."""
	customer = get_customer_for_user(user)
	if customer:
		return customer

	# Fall back to webshop get_party for guest cart / legacy paths only
	from webshop.webshop.shopping_cart.cart import get_party

	return get_party(user)


def verify_address_belongs_to_customer(address_name, customer_name):
	if not address_name or not customer_name:
		frappe.throw(_("Address not found."), frappe.DoesNotExistError)
	if not frappe.db.exists(
		"Dynamic Link",
		{
			"parenttype": "Address",
			"parent": address_name,
			"link_doctype": "Customer",
			"link_name": customer_name,
		},
	):
		frappe.throw(_("Address not found."), frappe.DoesNotExistError)


def verify_contact_belongs_to_customer(contact_name, customer_name):
	if not contact_name or not customer_name:
		frappe.throw(_("Contact not found."), frappe.DoesNotExistError)
	if not frappe.db.exists(
		"Dynamic Link",
		{
			"parenttype": "Contact",
			"parent": contact_name,
			"link_doctype": "Customer",
			"link_name": customer_name,
		},
	):
		frappe.throw(_("Contact not found."), frappe.DoesNotExistError)


def verify_sales_order_belongs_to_user(sales_order, user=None):
	customers = get_portal_customer_names(user)
	if not customers or sales_order.customer not in customers:
		frappe.throw(_("Order not found."), frappe.DoesNotExistError)
