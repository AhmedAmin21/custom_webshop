import contextlib

import frappe
from frappe import _, throw
from frappe.utils import cint, flt, get_fullname

from webshop.webshop.shopping_cart.cart import (
	_get_cart_quotation,
	apply_cart_settings,
	set_cart_count,
)
from custom_webshop.shopping_cart.party import safe_get_party as get_party
from frappe.contacts.doctype.contact.contact import get_contact_name
from webshop.webshop.doctype.webshop_settings.webshop_settings import (
	get_shopping_cart_settings,
)
from custom_webshop.shopping_cart.stock import get_web_item_qty_in_stock
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


@contextlib.contextmanager
def run_as_system_admin():
	"""Temporarily execute internal server operations under Administrator context.

	Used strictly for internal routines (e.g. ERPNext stock availability calculation
	and Stock Reservation Entry generation) where ERPNext internal functions call
	`frappe.has_permission('Item', 'read')`. The Customer role intentionally does not
	have read permission on Item to prevent API data leaks.

	The session user is unconditionally restored in the finally block.
	"""
	orig_user = frappe.session.user
	frappe.session.user = "Administrator"
	try:
		yield
	finally:
		frappe.session.user = orig_user


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
def place_order_from_cart(notes=None):
	"""
	Override for 'Place Order' and 'Request for Quotation'.
	In the Quotation-first assisted sales workflow:
	1. Save shipping address, notes, and contact person onto the cart Quotation.
	2. Submit the cart Quotation (docstatus = 1) so it is finalized and ready for sales agent review.
	3. Determine threshold:
	   - > 10,000 EGP: does not proceed to payment page; support agents contact customer.
	   - <= 10,000 EGP: customer proceeds to payment page to upload payment proof.
	4. Send order/quotation confirmation email to the customer.
	5. Clear the shopping cart session.
	6. Return routing metadata to the frontend.
	"""
	quotation = _get_cart_quotation()
	cart_settings = frappe.get_cached_doc("Webshop Settings")
	quotation.company = cart_settings.company

	if not (quotation.shipping_address_name or quotation.customer_address):
		frappe.throw(_("Set Shipping Address or Billing Address"))

	# Save customer delivery notes if provided
	if notes and str(notes).strip():
		quotation.custom_order_notes = str(notes).strip()

	# Set contact info on Quotation from customer's primary contact
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
			quotation.contact_person = contact_doc.name
			quotation.contact_mobile = contact_doc.mobile_no
			quotation.contact_email = frappe.session.user
			quotation.contact_display = f"{contact_doc.first_name or ''} {contact_doc.last_name or ''}".strip()

	grand_total = flt(quotation.grand_total)
	requires_payment = grand_total <= 10000.0

	quotation.custom_agent_contact_status = "Pending Agent Contact"
	quotation.flags.ignore_permissions = True
	with shopping_as_customer():
		quotation.submit()
		if notes and str(notes).strip():
			quotation.add_comment("Comment", text=f"Customer Order Notes / Delivery Instructions: {str(notes).strip()}")

	if quotation.quotation_to == "Lead" and quotation.party_name:
		frappe.defaults.set_user_default("company", quotation.company)

	# Send quotation confirmation email
	_send_order_email(quotation, "order_created")

	if hasattr(frappe.local, "cookie_manager"):
		frappe.local.cookie_manager.delete_cookie("cart_count")

	return {
		"name": quotation.name,
		"order_name": quotation.name,
		"quotation_name": quotation.name,
		"grand_total": grand_total,
		"requires_payment": requires_payment,
		"currency": quotation.currency or "EGP",
		"message": _("Customer support agents will contact you to confirm your order.")
	}



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
				# Ensure it is safe to use: either already linked to us, or has no links to other Customers/Suppliers
				has_other_links = any(link.link_doctype in ("Customer", "Supplier") and link.link_name != party.name for link in c.get("links", []))
				if not has_other_links:
					contact_doc = c
					break

		if not contact_doc:
			# Fallback to the first safely linked contact
			for c_name in existing_contacts:
				c = frappe.get_doc("Contact", c_name)
				has_other_links = any(link.link_doctype in ("Customer", "Supplier") and link.link_name != party.name for link in c.get("links", []))
				if not has_other_links:
					contact_doc = c
					break

		if contact_doc:
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
		else:
			# If no safe existing contact is found, clear existing_contacts to trigger creation of a new one
			existing_contacts = []

	if existing_contacts:

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
	party = get_party()
	if not party:
		frappe.throw(_("Customer not found"), frappe.PermissionError)

	def verify_ownership(doc):
		has_link = any(
			link.link_doctype == "Customer" and link.link_name == party.name
			for link in doc.get("links", [])
		)
		if not has_link:
			frappe.throw(_("Not permitted to modify this record"), frappe.PermissionError)

	address_data = frappe.parse_json(address_data)
	contact_data = frappe.parse_json(contact_data)

	# Update Address
	address = frappe.get_doc("Address", address_name)
	verify_ownership(address)
	address.address_line1 = address_data.get("address_line1")
	address.city = address_data.get("city")
	address.country = address_data.get("country")
	address.flags.ignore_permissions = True
	address.save()

	# Update Contact
	contact = frappe.get_doc("Contact", contact_name)
	verify_ownership(contact)
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

	if qty < 0:
		frappe.throw(_("Quantity cannot be negative."))

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
	party = get_party()
	if not party:
		frappe.throw(_("Customer not found"), frappe.PermissionError)

	address_doc = frappe.get_doc("Address", address_name).as_dict()
	
	# Verify ownership to prevent IDOR
	has_link = any(
		link.link_doctype == "Customer" and link.link_name == party.name
		for link in address_doc.get("links", [])
	)
	if not has_link:
		frappe.throw(_("Not permitted to use this address"), frappe.PermissionError)

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


def _send_order_email(doc, email_type, recipient_email=None):
	"""
	Send order-related email notifications to the customer.
	doc: Quotation or Sales Order document
	email_type: 'order_created' | 'order_payment_confirmed' | 'order_expired'
	"""
	target_email = recipient_email or doc.get("contact_email") or doc.get("owner")
	if not target_email or target_email == "Guest":
		if frappe.session.user != "Guest":
			target_email = frappe.session.user
		else:
			return

	if not target_email or "@" not in str(target_email):
		return

	first_name = ""
	send_to = target_email

	if frappe.db.exists("User", target_email):
		user = frappe.get_doc("User", target_email)
		if user.email:
			send_to = user.email
		first_name = user.first_name or user.full_name or user.name

	if not first_name:
		first_name = doc.get("customer_name") or send_to.split("@")[0]

	site_url = frappe.utils.get_url()
	grand_total = flt(doc.get("grand_total"))
	requires_payment = grand_total <= 10000.0

	context = {
		"site_url": site_url,
		"shop_url": f"{site_url}/shop",
		"site_name": (
			frappe.db.get_default("site_name")
			or frappe.get_conf().get("site_name")
			or "CNCLeaders"
		),
		"first_name": first_name,
		"sales_order": doc,
		"quotation": doc,
		"doc": doc,
		"requires_payment": requires_payment,
		"payment_url": f"{site_url}/payment?order_id={doc.name}",
		"order_url": f"{site_url}/orders/{doc.name}",
	}

	if email_type == "order_created":
		subject = _("Order Confirmation: Your order {0} has been created").format(doc.name)
		template = "custom_webshop/templates/emails/order_created.html"
	elif email_type == "order_payment_confirmed":
		subject = _("Payment Confirmed: We received your payment proof for order {0}").format(doc.name)
		template = "custom_webshop/templates/emails/order_payment_confirmed.html"
	elif email_type == "order_expired":
		subject = _("Stock reservation expired for order {0}").format(doc.name)
		template = "custom_webshop/templates/emails/order_expired.html"
	else:
		return

	message = frappe.render_template(template, context)

	# Failing to notify must never undo the order.
	try:
		frappe.sendmail(
			recipients=[send_to],
			subject=subject,
			message=message,
			reference_doctype=doc.doctype or "Quotation",
			reference_name=doc.name,
			now=True,
		)
	except Exception:
		frappe.log_error(
			title="custom_webshop: could not email {0} {1}".format(doc.doctype or "Quotation", doc.name),
			message=frappe.get_traceback(),
		)


@frappe.whitelist()
def get_cart_quotation(doc=None):
	"""
	Optimized get_cart_quotation to eliminate N+1 queries.
	"""
	from webshop.webshop.shopping_cart.cart import (
		get_address_docs,
		get_shipping_addresses,
		get_billing_addresses,
		get_applicable_shipping_rules,
		set_cart_count
	)

	party = get_party()

	if not doc:
		quotation = _get_cart_quotation(party)
		doc = quotation
		set_cart_count(quotation)

	addresses = get_address_docs(party=party)

	if not doc.customer_address and addresses:
		update_cart_address("billing", addresses[0].name)

	return {
		"doc": optimized_decorate_quotation_doc(doc),
		"shipping_addresses": get_shipping_addresses(party),
		"billing_addresses": get_billing_addresses(party),
		"shipping_rules": get_applicable_shipping_rules(party),
		"cart_settings": frappe.get_cached_doc("Webshop Settings"),
	}


def optimized_decorate_quotation_doc(doc):
	if not doc.get("items"):
		return doc

	item_codes = [d.item_code for d in doc.items]
	
	items_data = frappe.get_all(
		"Item", 
		filters={"name": ["in", item_codes]}, 
		fields=["name", "variant_of", "item_name", "image"]
	)
	item_map = {d.name: d for d in items_data}
	
	web_item_codes = set(item_codes)
	for item in items_data:
		if item.variant_of:
			web_item_codes.add(item.variant_of)
			
	if web_item_codes:
		web_items_data = frappe.get_all(
			"Website Item",
			filters={"item_code": ["in", list(web_item_codes)]},
			fields=["item_code", "web_item_name", "thumbnail", "website_image", "description", "route", "website_warehouse"]
		)
		web_item_map = {d.item_code: d for d in web_items_data}
	else:
		web_item_map = {}
	
	for d in doc.get("items", []):
		item_code = d.item_code
		item_data = item_map.get(item_code)
		
		is_variant = item_data and item_data.variant_of and item_code not in web_item_map
		target_item_code = item_data.variant_of if is_variant else item_code
		web_item = web_item_map.get(target_item_code)
		
		if is_variant and item_data:
			d.web_item_name = item_data.item_name
			if item_data.image:
				d.thumbnail = item_data.image
				
		if web_item:
			if not is_variant:
				d.web_item_name = web_item.web_item_name
				d.thumbnail = web_item.thumbnail
			elif not item_data.image:
				d.thumbnail = web_item.thumbnail
				
			d.website_image = web_item.website_image
			d.description = web_item.description
			d.route = web_item.route
			d.warehouse = web_item.website_warehouse

	return doc
