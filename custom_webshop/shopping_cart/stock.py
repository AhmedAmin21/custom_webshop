import frappe
from frappe.utils import cint, flt
from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses
from webshop.webshop.utils.product import adjust_qty_for_expired_items


def get_web_item_qty_in_stock(item_code, item_warehouse_field, warehouse=None):
	"""
	Calculates the available stock quantity for an item on the webshop.
	Unlike the default webshop implementation which only considers actual_qty,
	this factors in stock reservations so that submitted Sales Orders (and Stock Reservation Entries)
	immediately reduce the available quantity displayed and purchasable on the website.

	Available Stock = GREATEST(0, actual_qty - GREATEST(reserved_stock, reserved_qty))
	"""
	in_stock, stock_qty = 0, ""
	item_data = frappe.db.get_value(
		"Item", item_code, ["variant_of", "is_stock_item"], as_dict=True
	)
	if not item_data:
		return frappe._dict({"in_stock": 0, "stock_qty": 0.0, "is_stock_item": 0})

	template_item_code = item_data.get("variant_of")
	is_stock_item = item_data.get("is_stock_item")

	if not warehouse:
		warehouse = frappe.db.get_value("Website Item", {"item_code": item_code}, item_warehouse_field)

	if not warehouse and template_item_code and template_item_code != item_code:
		warehouse = frappe.db.get_value(
			"Website Item", {"item_code": template_item_code}, item_warehouse_field
		)

	if warehouse and frappe.get_cached_value("Warehouse", warehouse, "is_group") == 1:
		warehouses = get_child_warehouses(warehouse)
	else:
		warehouses = [warehouse] if warehouse else []

	total_stock = 0.0
	if warehouses:
		for wh in warehouses:
			stock_qty = frappe.db.sql(
				"""
				SELECT GREATEST(0, (S.actual_qty - GREATEST(IFNULL(S.reserved_stock, 0), IFNULL(S.reserved_qty, 0)))) / IFNULL(C.conversion_factor, 1)
				FROM tabBin S
				INNER JOIN `tabItem` I ON S.item_code = I.item_code
				LEFT JOIN `tabUOM Conversion Detail` C ON I.sales_uom = C.uom AND C.parent = I.item_code
				WHERE S.item_code=%s AND S.warehouse=%s
				""",
				(item_code, wh),
			)

			if stock_qty:
				total_stock += adjust_qty_for_expired_items(item_code, stock_qty, wh)

		in_stock = 1 if total_stock > 0 else 0

	return frappe._dict(
		{"in_stock": in_stock, "stock_qty": flt(total_stock), "is_stock_item": cint(is_stock_item)}
	)


def patch_webshop_stock_resolver():
	"""
	Patches webshop stock calculation functions so that all callers across
	Webshop (product pages, product info API, cart validation, etc.)
	take stock reservations into account.
	"""
	try:
		import webshop.webshop.utils.product
		import webshop.webshop.shopping_cart.product_info
		import webshop.webshop.shopping_cart.cart

		webshop.webshop.utils.product.get_web_item_qty_in_stock = get_web_item_qty_in_stock
		webshop.webshop.shopping_cart.product_info.get_web_item_qty_in_stock = get_web_item_qty_in_stock
		webshop.webshop.shopping_cart.cart.get_web_item_qty_in_stock = get_web_item_qty_in_stock
	except Exception as e:
		frappe.logger("custom_webshop").warning(f"Failed to patch webshop stock resolver: {e}")

