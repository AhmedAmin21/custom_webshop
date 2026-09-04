import contextlib

import frappe
from frappe import _, throw
from frappe.utils import cint, flt, get_fullname

from webshop.webshop.shopping_cart.cart import (
	_get_cart_quotation,
	get_party,
	get_cart_quotation,
	apply_cart_settings,
	set_cart_count,
)
from frappe.contacts.doctype.contact.contact import get_contact_name
from webshop.webshop.doctype.webshop_settings.webshop_settings import (
	get_shopping_cart_settings,
)
from webshop.webshop.utils.product import get_web_item_qty_in_stock
from erpnext.selling.doctype.quotation.quotation import _make_sales_order
from custom_webshop.shopping_cart.shipping_api import (
	_get_cart_weight_info,
	apply_cart_settings_for_webshop,
)



@contextlib.contextmanager
def shopping_as_customer():
	"""Let a shopper's own cart operation read the items it is buying.

	ERPNext resolves item details on every save of a Quotation, and
	`erpnext.stock.get_item_details.get_item_details` calls
	`item.check_permission()` unconditionally. The Customer role has no
	read permission on Item - ERPNext does not ship one, and this site
	adds none - so a Website User adding anything to their basket got a
	bare 403 the moment the quotation was saved. Every account created by
	the verified signup flow was affected: the shop looked finished and
	nothing could be bought.

	The alternative was granting the Customer role blanket read on Item,
	which would expose valuation and cost fields to every portal account
	for the sake of a name and a price they can already see. This is the
	narrower trade: the flag is raised only around one save, only inside
	this app's own cart endpoints, and only after the caller has been
	shown to be operating on their own cart.

	Yields:
		None.
	"""
	previous = frappe.flags.ignore_permissions
	frappe.flags.ignore_permissions = True
	try:
		yield
	finally:
		frappe.flags.ignore_permissions = previous


def assert_purchasable(item_code):
	"""Refuse an item the shop does not actually offer.

	The permission bypass above is only defensible because of this: a
	shopper may put a *published Website Item* in their basket and
	nothing else, so an unpublished or non-existent code is rejected
	before any check is relaxed.

	Args:
		item_code: the code the browser asked for.

	Raises:
		frappe.PermissionError: if the item is not on sale.
	"""
	if not frappe.db.exists("Website Item", {"item_code": item_code, "published": 1}):
		frappe.throw(_("This product is not available."), frappe.PermissionError)


@frappe.whitelist()
def place_order_from_cart():
	"""
	Override for 'Place Order' and 'Request for Quotation'.
	Instead of submitting the Sales Order immediately, we:
	1. Submit the cart Quotation
	2. Create a Sales Order from it and keep it in Draft
	3. Send an order-created email to the customer
	4. Clear the cart
	5. Return the Sales Order name
	The customer must upload payment proof before the SO is submitted.
	"""
	quotation = _get_cart_quotation()
	cart_settings = frappe.get_cached_doc("Webshop Settings")
	quotation.company = cart_settings.company

	quotation.flags.ignore_permissions = True
	# Same reason as update_cart: submitting the quotation and building the
	# Sales Order from it both re-resolve item details, which check Item
	# read permission the Customer role does not have.
	with shopping_as_customer():
		quotation.submit()

	if quotation.quotation_to == "Lead" and quotation.party_name:
		frappe.defaults.set_user_default("company", quotation.company)

	if not (quotation.shipping_address_name or quotation.customer_address):
		frappe.throw(_("Set Shipping Address or Billing Address"))

	sales_order = frappe.get_doc(
		_make_sales_order(quotation.name, ignore_permissions=True)
	)
	sales_order.payment_schedule = []

	# Copy Governorate shipping fields from Quotation to Sales Order
	for field in ("shipping_rule", "shipping_destination", "shipping_district", "custom_manual_shipping_amount"):
		if quotation.get(field):
			sales_order.set(field, quotation.get(field))

	# Reserve stock for this Sales Order
	sales_order.reserve_stock = 1

	if not cint(cart_settings.allow_items_not_in_stock):
		for item in sales_order.get("items"):
			item.warehouse = frappe.db.get_value(
				"Website Item", {"item_code": item.item_code}, "website_warehouse"
			)
			is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")

			if is_stock_item:
				item_stock = get_web_item_qty_in_stock(
					item.item_code, "website_warehouse"
				)
				if not cint(item_stock.in_stock):
					frappe.throw(_("{0} Not in Stock").format(item.item_code))
				if item.qty > item_stock.stock_qty:
					frappe.throw(
						_(
							"Only {0} in Stock for item {1}"
						).format(item_stock.stock_qty, item.item_code)
					)

	# Set contact info on Sales Order from customer's primary contact
	party = get_party()
	if party:
		contact = frappe.db.sql("""
			SELECT c.name, c.first_name, c.last_name, c.mobile_no
			FROM `tabContact` c
			JOIN `tabDynamic Link` dl ON dl.parent = c.name
			WHERE dl.link_doctype = 'Customer'
			AND dl.link_name = %s
			ORDER BY c.is_primary_contact DESC
			LIMIT 1
		""", party.name, as_dict=True)

		if contact:
			contact_doc = contact[0]
			sales_order.contact_person = contact_doc.name
			sales_order.contact_mobile = contact_doc.mobile_no
			sales_order.contact_email = frappe.session.user
			sales_order.contact_display = f"{contact_doc.first_name or ''} {contact_doc.last_name or ''}".strip()

	sales_order.flags.ignore_permissions = True
	with shopping_as_customer():
		sales_order.insert()
	# Keep Sales Order in Draft until customer uploads payment proof
	# sales_order.submit()

	# Send draft order confirmation email
	_send_order_email(sales_order, "order_created")

	if hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.delete_cookie("cart_count")

	return sales_order.name



@frappe.whitelist()
def add_customer_info(address_data, contact_data):
	"""
	Create a new Address and Contact for the current customer.
	Returns the created address name for cart linking.
	"""
	party = get_party()
	if not party:
		frappe.throw(_("Customer not found"))

	address_data = frappe.parse_json(address_data)
	contact_data = frappe.parse_json(contact_data)

	# Find existing contact by email first (handles signup-created contacts)
	contact_name = get_contact_name(frappe.session.user)
	existing_contacts = []

	if contact_name:
		existing_contacts.append(contact_name)

	# Fallback: search by Dynamic Link
	linked_contacts = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", party.name]
		],
		pluck="name"
	)
	for c in linked_contacts:
		if c not in existing_contacts:
			existing_contacts.append(c)

	if existing_contacts:
		# Prefer the contact that has the user's email (signup contact)
		contact_doc = None
		for c_name in existing_contacts:
			c = frappe.get_doc("Contact", c_name)
			if c.email_id == frappe.session.user:
				contact_doc = c
				break
		if not contact_doc:
			contact_doc = frappe.get_doc("Contact", existing_contacts[0])
		contact = contact_doc

		# Ensure link to customer exists (add if missing)
		has_customer_link = any(
			link.link_doctype == "Customer" and link.link_name == party.name
			for link in contact.get("links", [])
		)
		if not has_customer_link:
			contact.append("links", {
				"link_doctype": "Customer",
				"link_name": party.name
			})

		# Ensure is_primary_contact is set
		if not contact.is_primary_contact:
			contact.is_primary_contact = 1

		# Handle mobile number logic
		user_mobile = frappe.db.get_value("User", frappe.session.user, "mobile_no")
		new_mobile = contact_data.get("mobile_no")

		if new_mobile:
			if not user_mobile or new_mobile == user_mobile:
				# Signup mobile is empty or matches: this is the primary mobile
				phone_found = False
				for phone in contact.get("phone_nos", []):
					if phone.phone == new_mobile:
						phone.is_primary_mobile_no = 1
						phone_found = True
						break
				if not phone_found:
					contact.append("phone_nos", {
						"phone": new_mobile,
						"is_primary_mobile_no": 1
					})
			else:
				# Different from signup mobile: keep signup row as primary mobile
				for phone in contact.get("phone_nos", []):
					if phone.phone == user_mobile:
						phone.is_primary_mobile_no = 1

				# Append new number as primary phone if not already present
				if not any(p.phone == new_mobile for p in contact.get("phone_nos", [])):
					contact.append("phone_nos", {
						"phone": new_mobile,
						"is_primary_phone": 1
					})

		contact.flags.ignore_permissions = True
		contact.save()
	else:
		# Create new Contact
		contact = frappe.new_doc("Contact")
		contact.first_name = contact_data.get("first_name") or get_fullname(frappe.session.user)
		contact.is_primary_contact = 1

		if contact_data.get("mobile_no"):
			contact.append("phone_nos", {
				"phone": contact_data.get("mobile_no"),
				"is_primary_mobile_no": 1
			})

		# Add email from user account
		user_email = frappe.db.get_value("User", frappe.session.user, "email")
		if user_email:
			contact.append("email_ids", {
				"email_id": user_email,
				"is_primary": 1
			})

		contact.append("links", {
			"link_doctype": "Customer",
			"link_name": party.name
		})
		contact.flags.ignore_permissions = True
		contact.insert()

	# Update the current quotation's contact_person to this contact
	# This ensures ERPNext validation passes
	quotation = _get_cart_quotation()
	if quotation and contact:
		quotation.contact_person = contact.name
		quotation.contact_email = frappe.session.user
		quotation.flags.ignore_permissions = True
		quotation.save()

	# Create Address
	address = frappe.new_doc("Address")
	address.address_title = party.customer_name
	address.address_line1 = address_data.get("address_line1")
	address.city = address_data.get("city")
	address.country = address_data.get("country")
	address.address_type = "Shipping"
	address.append("links", {
		"link_doctype": "Customer",
		"link_name": party.name
	})
	address.flags.ignore_permissions = True
	address.insert()

	return address.name


@frappe.whitelist()
def update_customer_info(address_name, address_data, contact_name, contact_data):
	"""
	Update an existing Address and Contact.
	"""
	address_data = frappe.parse_json(address_data)
	contact_data = frappe.parse_json(contact_data)

	# Update Address
	address = frappe.get_doc("Address", address_name)
	address.address_line1 = address_data.get("address_line1")
	address.city = address_data.get("city")
	address.country = address_data.get("country")
	address.flags.ignore_permissions = True
	address.save()

	# Update Contact
	contact = frappe.get_doc("Contact", contact_name)
	contact.first_name = contact_data.get("first_name") or contact.first_name

	# Replace mobile number: clear all and set new one as primary mobile
	if contact_data.get("mobile_no"):
		contact.set("phone_nos", [])
		contact.append("phone_nos", {
			"phone": contact_data.get("mobile_no"),
			"is_primary_mobile_no": 1
		})

	contact.flags.ignore_permissions = True
	contact.save()

	return address.name


@frappe.whitelist()
def get_customer_addresses_with_contacts():
	"""
	Get all addresses for current customer with associated contact info.
	"""
	party = get_party()
	if not party:
		return []

	addresses = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", party.name]
		],
		fields=["name", "address_title", "address_line1", "city", "country", "address_type"]
	)

	# Get primary contact
	contacts = frappe.get_all(
		"Contact",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Customer"],
			["Dynamic Link", "link_name", "=", party.name]
		],
		fields=["name", "first_name", "mobile_no"],
		limit=1
	)

	primary_contact = contacts[0] if contacts else None

	return {
		"addresses": addresses,
		"primary_contact": primary_contact
	}


@frappe.whitelist()
def update_cart(item_code, qty, additional_notes=None, with_items=False):
	"""
	Override update_cart to clear contact_person from quotation before saving.
	This prevents "Contact Person does not belong to Customer" validation errors.
	Contact info is added to the Sales Order when placing the order.

	What the shopper is allowed to buy is settled first, under their own
	permissions. Only then is the cart itself rebuilt, which re-resolves
	item details and prices from end to end and checks an Item permission
	no portal account has - see `shopping_as_customer`.
	"""
	if flt(qty) > 0:
		assert_purchasable(item_code)

	with shopping_as_customer():
		return _update_cart(item_code, qty, additional_notes, with_items)


def _update_cart(item_code, qty, additional_notes, with_items):
	"""Rebuild the cart. Always called inside `shopping_as_customer`."""
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

	# Use custom cart settings that never auto-select non-Governorate shipping rules
	apply_cart_settings_for_webshop(quotation=quotation)

	quotation.flags.ignore_permissions = True
	quotation.payment_schedule = []

	# Clear contact fields to prevent validation errors
	quotation.contact_person = None
	quotation.contact_mobile = None
	quotation.contact_display = None

	if not empty_card:
		quotation.save()
	else:
		quotation.delete()
		quotation = None

	if quotation:
		set_cart_count(quotation)
	elif hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.set_cookie("cart_count", "0")

	if cint(with_items):
		context = get_cart_quotation(quotation)
		# Inject raw weight info so payment summary renders it correctly
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
	else:
		return {"name": quotation.name if quotation else ""}


@frappe.whitelist()
def update_cart_address(address_type, address_name):
	"""
	Override update_cart_address to prevent standard shipping rule auto-selection.
	"""
	from frappe.contacts.doctype.address.address import get_address_display

	quotation = _get_cart_quotation()
	address_doc = frappe.get_doc("Address", address_name).as_dict()
	address_display = get_address_display(address_doc)

	if address_type.lower() == "billing":
		quotation.customer_address = address_name
		quotation.address_display = address_display
		quotation.shipping_address_name = (
			quotation.shipping_address_name or address_name
		)
	elif address_type.lower() == "shipping":
		quotation.shipping_address_name = address_name
		quotation.shipping_address = address_display
		quotation.customer_address = quotation.customer_address or address_name

	# Use custom cart settings that never auto-select non-Governorate shipping rules
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
	"""
	Get the Customer doc for the current user.

	Kept as a thin wrapper so existing callers keep working; the actual
	resolution now goes through the verified identity record - see
	custom_webshop.signup.resolution for why reading Portal User (or
	webshop's get_party) directly is not a safe answer to this question.
	"""
	from custom_webshop.signup.resolution import get_customer

	return get_customer(user)


def _send_order_email(sales_order, email_type):
	"""
	Send order-related email notifications to the customer.
	email_type: 'order_created' | 'order_payment_confirmed'
	"""
	if frappe.session.user == "Guest":
		return

	user = frappe.get_doc("User", frappe.session.user)
	if not user.enabled:
		return

	site_url = frappe.utils.get_url()
	context = {
		"site_url": site_url,
		"site_name": frappe.db.get_default("site_name") or frappe.db.get_default("company") or site_url,
		"first_name": user.first_name or user.full_name or user.name,
		"sales_order": sales_order,
		"payment_url": f"{site_url}/payment?order_id={sales_order.name}",
		"order_url": f"{site_url}/orders/{sales_order.name}",
	}

	if email_type == "order_created":
		subject = _("Your order {0} has been created - payment required").format(sales_order.name)
		template = "custom_webshop/templates/emails/order_created.html"
	else:
		subject = _("Payment confirmed for order {0}").format(sales_order.name)
		template = "custom_webshop/templates/emails/order_payment_confirmed.html"

	message = frappe.render_template(template, context)

	# Failing to notify must never undo the order. `now=True` sends inline,
	# and with no outgoing Email Account configured - the state of this
	# site - it raises `OutgoingEmailError`; Frappe rolls the whole request
	# back on an unhandled exception, so the Sales Order that was just
	# created is destroyed and the customer is told nothing happened. The
	# order is the thing that matters; the email is a courtesy, and a
	# courtesy that cannot be delivered is logged and left there.
	try:
		frappe.sendmail(
			recipients=[user.email],
			subject=subject,
			message=message,
			reference_doctype="Sales Order",
			reference_name=sales_order.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="custom_webshop: could not email order {0}".format(sales_order.name),
			message=frappe.get_traceback(),
		)
