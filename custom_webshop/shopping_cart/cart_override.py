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
	quotation.submit()

	if quotation.quotation_to == "Lead" and quotation.party_name:
		frappe.defaults.set_user_default("company", quotation.company)

	if not (quotation.shipping_address_name or quotation.customer_address):
		frappe.throw(_("Set Shipping Address or Billing Address"))

	sales_order = frappe.get_doc(
		_make_sales_order(quotation.name, ignore_permissions=True)
	)
	sales_order.payment_schedule = []

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

	# Find existing contact by email first (handles signup-created contacts
	# that may not yet be linked to the customer via Dynamic Link)
	contact_name = get_contact_name(frappe.session.user)
	existing_contacts = []

	if contact_name:
		existing_contacts.append(contact_name)
	else:
		# Fallback: search by Dynamic Link
		existing_contacts = frappe.get_all(
			"Contact",
			filters=[
				["Dynamic Link", "link_doctype", "=", "Customer"],
				["Dynamic Link", "link_name", "=", party.name]
			],
			pluck="name"
		)

	if existing_contacts:
		# Use existing contact and add mobile
		contact = frappe.get_doc("Contact", existing_contacts[0])

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

		# Unset existing primary mobile
		for phone in contact.get("phone_nos", []):
			if phone.is_primary_mobile_no:
				phone.is_primary_mobile_no = 0

		# Add or update mobile number
		if contact_data.get("mobile_no"):
			contact.append("phone_nos", {
				"phone": contact_data.get("mobile_no"),
				"is_primary_mobile_no": 1
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

	# Update primary mobile
	if contact_data.get("mobile_no"):
		phone_rows = contact.get("phone_nos")
		if phone_rows:
			phone_rows[0].phone = contact_data.get("mobile_no")
			phone_rows[0].is_primary_mobile_no = 1
		else:
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
	"""
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

	apply_cart_settings(quotation=quotation)

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

	set_cart_count(quotation)

	if cint(with_items):
		context = get_cart_quotation(quotation)
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
		return {"name": quotation.name}


def get_customer_for_user(user=None):
	"""
	Get the Customer doc linked to the current user via Portal User.
	This is a reliable alternative to get_party() which may return a Lead
	or a different contact link depending on contact.link ordering.
	"""
	if not user:
		user = frappe.session.user

	customers = frappe.get_all(
		"Portal User",
		filters={"user": user, "parenttype": "Customer"},
		pluck="parent"
	)
	if customers:
		return frappe.get_doc("Customer", customers[0])
	return None


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

	frappe.sendmail(
		recipients=[user.email],
		subject=subject,
		message=message,
		reference_doctype="Sales Order",
		reference_name=sales_order.name,
		now=True,
	)
