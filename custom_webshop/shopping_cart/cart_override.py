import frappe
from frappe import _, throw
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, get_fullname

from webshop.webshop.shopping_cart.cart import (
	_get_cart_quotation,
	get_cart_quotation,
	set_cart_count,
)
from frappe.contacts.doctype.contact.contact import get_contact_name
from webshop.webshop.utils.product import get_web_item_qty_in_stock

from custom_webshop.services.checkout import build_payment_preview, validate_cart_for_checkout
from custom_webshop.services.customer_identity import (
	get_party_for_user,
	require_customer_for_user,
	verify_address_belongs_to_customer,
	verify_contact_belongs_to_customer,
)
from custom_webshop.shopping_cart.shipping_api import (
	_get_cart_weight_info,
	apply_cart_settings_for_webshop,
)


@frappe.whitelist()
def place_order_from_cart():
	"""
	Validate checkout and prepare for payment.

	Does NOT create a Sales Order — that happens when payment proof is uploaded.
	"""
	quotation = validate_cart_for_checkout()
	preview = build_payment_preview(quotation)
	return {
		"checkout_ready": True,
		"quotation_name": preview["quotation_name"],
		"redirect": "/shop/payment",
	}


@frappe.whitelist()
def add_customer_info(address_data, contact_data):
	"""Create a new Address and Contact for the current customer."""
	party = require_customer_for_user()

	address_data = frappe.parse_json(address_data)
	contact_data = frappe.parse_json(contact_data)

	contact_name = get_contact_name(frappe.session.user)
	existing_contacts = []

	if contact_name:
		existing_contacts.append(contact_name)

	linked_contacts = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", party.name],
		],
		pluck="name",
	)
	for c in linked_contacts:
		if c not in existing_contacts:
			existing_contacts.append(c)

	if existing_contacts:
		contact_doc = None
		for c_name in existing_contacts:
			c = frappe.get_doc("Contact", c_name)
			if c.email_id == frappe.session.user:
				contact_doc = c
				break
		if not contact_doc:
			contact_doc = frappe.get_doc("Contact", existing_contacts[0])
		contact = contact_doc

		has_customer_link = any(
			link.link_doctype == "Customer" and link.link_name == party.name
			for link in contact.get("links", [])
		)
		if not has_customer_link:
			contact.append("links", {"link_doctype": "Customer", "link_name": party.name})

		if not contact.is_primary_contact:
			contact.is_primary_contact = 1

		user_mobile = frappe.db.get_value("User", frappe.session.user, "mobile_no")
		new_mobile = contact_data.get("mobile_no")

		if new_mobile:
			if not user_mobile or new_mobile == user_mobile:
				phone_found = False
				for phone in contact.get("phone_nos", []):
					if phone.phone == new_mobile:
						phone.is_primary_mobile_no = 1
						phone_found = True
						break
				if not phone_found:
					contact.append(
						"phone_nos", {"phone": new_mobile, "is_primary_mobile_no": 1}
					)
			else:
				for phone in contact.get("phone_nos", []):
					if phone.phone == user_mobile:
						phone.is_primary_mobile_no = 1
				if not any(p.phone == new_mobile for p in contact.get("phone_nos", [])):
					contact.append(
						"phone_nos", {"phone": new_mobile, "is_primary_phone": 1}
					)

		contact.flags.ignore_permissions = True
		contact.save()
	else:
		contact = frappe.new_doc("Contact")
		contact.first_name = contact_data.get("first_name") or get_fullname(frappe.session.user)
		contact.is_primary_contact = 1

		if contact_data.get("mobile_no"):
			contact.append(
				"phone_nos",
				{"phone": contact_data.get("mobile_no"), "is_primary_mobile_no": 1},
			)

		user_email = frappe.db.get_value("User", frappe.session.user, "email")
		if user_email:
			contact.append("email_ids", {"email_id": user_email, "is_primary": 1})

		contact.append("links", {"link_doctype": "Customer", "link_name": party.name})
		contact.flags.ignore_permissions = True
		contact.insert()

	quotation = _get_cart_quotation()
	if quotation and contact:
		quotation.contact_person = contact.name
		quotation.contact_email = frappe.session.user
		quotation.flags.ignore_permissions = True
		quotation.save()

	address = frappe.new_doc("Address")
	address.address_title = party.customer_name
	address.address_line1 = address_data.get("address_line1")
	address.city = address_data.get("city")
	address.country = address_data.get("country") or "Egypt"
	address.address_type = "Shipping"
	address.append("links", {"link_doctype": "Customer", "link_name": party.name})
	address.flags.ignore_permissions = True
	address.insert()

	return address.name


@frappe.whitelist()
def update_customer_info(address_name, address_data, contact_name, contact_data):
	"""Update an existing Address and Contact owned by the current customer."""
	party = require_customer_for_user()
	verify_address_belongs_to_customer(address_name, party.name)
	verify_contact_belongs_to_customer(contact_name, party.name)

	address_data = frappe.parse_json(address_data)
	contact_data = frappe.parse_json(contact_data)

	address = frappe.get_doc("Address", address_name)
	address.address_line1 = address_data.get("address_line1")
	address.city = address_data.get("city")
	address.country = address_data.get("country") or address.country
	address.flags.ignore_permissions = True
	address.save()

	contact = frappe.get_doc("Contact", contact_name)
	contact.first_name = contact_data.get("first_name") or contact.first_name

	if contact_data.get("mobile_no"):
		contact.set("phone_nos", [])
		contact.append(
			"phone_nos",
			{"phone": contact_data.get("mobile_no"), "is_primary_mobile_no": 1},
		)

	contact.flags.ignore_permissions = True
	contact.save()

	return address.name


@frappe.whitelist()
def get_customer_addresses_with_contacts():
	"""Get all addresses for current customer with associated contact info."""
	party = get_party_for_user()
	if not party:
		return {"addresses": [], "primary_contact": None}

	addresses = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", party.name],
		],
		fields=["name", "address_title", "address_line1", "city", "country", "address_type"],
	)

	contacts = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", party.name],
		],
		fields=["name", "first_name", "mobile_no"],
		limit=1,
	)

	return {"addresses": addresses, "primary_contact": contacts[0] if contacts else None}


@frappe.whitelist(allow_guest=True)
@rate_limit(key="custom_webshop_update_cart", limit=120, seconds=60 * 60)
def update_cart(item_code, qty, additional_notes=None, with_items=False):
	"""Override update_cart with custom shipping settings."""
	quotation = _get_cart_quotation()

	empty_card = False
	qty = flt(qty)
	if qty == 0:
		quotation_items = quotation.get("items", {"item_code": ["!=", item_code]})
		if quotation_items:
			quotation.set("items", quotation_items)
		else:
			empty_card = True
	else:
		warehouse = frappe.get_cached_value(
			"Website Item", {"item_code": item_code}, "website_warehouse"
		)

		quotation_items = quotation.get("items", {"item_code": item_code})
		if not quotation_items:
			quotation.append(
				"items",
				{
					"doctype": "Quotation Item",
					"item_code": item_code,
					"qty": qty,
					"additional_notes": additional_notes,
					"warehouse": warehouse,
				},
			)
		else:
			quotation_items[0].qty = qty
			quotation_items[0].warehouse = warehouse
			quotation_items[0].additional_notes = additional_notes

	apply_cart_settings_for_webshop(quotation=quotation)

	quotation.flags.ignore_permissions = True
	quotation.payment_schedule = []

	# Keep contact on quotation when linked to customer
	party = get_party_for_user()
	if party and not quotation.contact_person:
		contact_name = get_contact_name(frappe.session.user)
		if contact_name:
			try:
				verify_contact_belongs_to_customer(contact_name, party.name)
				quotation.contact_person = contact_name
				quotation.contact_email = frappe.session.user
			except Exception:
				pass

	if not empty_card:
		quotation.save()
	else:
		quotation.delete()
		quotation = None

	set_cart_count(quotation)

	if cint(with_items):
		context = get_cart_quotation(quotation)
		context.update(_get_cart_weight_info(quotation))
		return {
			"items": frappe.render_template(
				"templates/includes/cart/cart_items.html", context
			),
			"total": frappe.render_template(
				"templates/includes/cart/cart_items_total.html", context
			),
			"taxes_and_totals": frappe.render_template(
				"templates/includes/cart/cart_payment_summary.html", context
			),
		}

	return {"name": quotation.name if quotation else None}


@frappe.whitelist()
def update_cart_address(address_type, address_name):
	"""Override update_cart_address with ownership validation."""
	from frappe.contacts.doctype.address.address import get_address_display

	party = require_customer_for_user()
	verify_address_belongs_to_customer(address_name, party.name)

	quotation = _get_cart_quotation()
	address_doc = frappe.get_doc("Address", address_name).as_dict()
	address_display = get_address_display(address_doc)

	if address_type.lower() == "billing":
		quotation.customer_address = address_name
		quotation.address_display = address_display
		quotation.shipping_address_name = quotation.shipping_address_name or address_name
	elif address_type.lower() == "shipping":
		quotation.shipping_address_name = address_name
		quotation.shipping_address = address_display
		quotation.customer_address = quotation.customer_address or address_name

	apply_cart_settings_for_webshop(quotation=quotation)

	quotation.flags.ignore_permissions = True
	quotation.save()

	context = get_cart_quotation(quotation)
	context.update(_get_cart_weight_info(quotation))
	context["address"] = {"name": address_name, "display": address_display}

	return {
		"taxes": frappe.render_template(
			"templates/includes/order/order_taxes.html", context
		),
		"address": frappe.render_template(
			"templates/includes/cart/address_card.html", context
		),
	}


def get_customer_for_user(user=None):
	"""Backward-compatible import path."""
	from custom_webshop.services.customer_identity import get_customer_for_user as _get

	return _get(user)


def _send_order_email(sales_order, email_type, recipient_user=None):
	"""Send order-related email notifications to the customer."""
	user_email = None
	first_name = sales_order.customer_name or sales_order.customer

	if recipient_user:
		user_email = frappe.db.get_value("User", recipient_user, "email")
		first_name = frappe.db.get_value("User", recipient_user, "first_name") or first_name
	elif sales_order.contact_email:
		user = frappe.db.get_value(
			"User",
			{"email": sales_order.contact_email},
			["email", "first_name", "enabled"],
			as_dict=True,
		)
		if user and user.enabled:
			user_email = user.email
			first_name = user.first_name or first_name
	else:
		portal_users = frappe.get_all(
			"Portal User",
			filters={"parent": sales_order.customer, "parenttype": "Customer"},
			pluck="user",
			limit=1,
		)
		if portal_users:
			user_email = frappe.db.get_value("User", portal_users[0], "email")
			first_name = frappe.db.get_value("User", portal_users[0], "first_name") or first_name

	if not user_email:
		user_email = frappe.db.get_value("Customer", sales_order.customer, "email_id")

	if not user_email:
		return

	site_url = frappe.utils.get_url()
	context = {
		"site_url": site_url,
		"site_name": frappe.db.get_default("site_name")
		or frappe.db.get_default("company")
		or site_url,
		"first_name": first_name,
		"sales_order": sales_order,
		"payment_url": f"{site_url}/shop/payment?order_id={sales_order.name}",
		"order_url": f"{site_url}/orders/{sales_order.name}",
	}

	if email_type == "order_created":
		subject = _("Your order {0} is pending payment review").format(sales_order.name)
		template = "custom_webshop/templates/emails/order_created.html"
	else:
		subject = _("Payment confirmed for order {0}").format(sales_order.name)
		template = "custom_webshop/templates/emails/order_payment_confirmed.html"

	message = frappe.render_template(template, context)

	frappe.sendmail(
		recipients=[user_email],
		subject=subject,
		message=message,
		reference_doctype="Sales Order",
		reference_name=sales_order.name,
		now=True,
	)
