import frappe

def get_context(context):
	context.no_cache = 1
	item_id = frappe.form_dict.get("id")
	
	if not item_id:
		return context
		
	# Fetch item details
	item = frappe.get_doc("Website Item", {"item_code": item_id})
	if not item:
		return context
		
	price = frappe.db.get_value("Item Price", {"item_code": item.item_code, "price_list": "Standard Selling"}, "price_list_rate") or 0.0
	
	stock = 0
	if item.website_warehouse:
		stock_bin = frappe.db.get_value("Bin", {"item_code": item.item_code, "warehouse": item.website_warehouse}, "actual_qty")
		if stock_bin:
			stock = int(stock_bin)
			
	product = {
		"id": item.item_code,
		"name": item.item_name,
		"category": item.item_group.lower().replace(" ", "-"),
		"categoryName": item.item_group,
		"brand": "CNCLeaders",
		"description": item.description or "",
		"price": float(price),
		"image": item.website_image or "/assets/custom_webshop/images/placeholder.jpg",
		"stock": stock,
		"sold": 0,
		"specs": {}
	}
	
	context.product_json = frappe.as_json(product)
	return context
