import frappe

def get_context(context):
	context.no_cache = 1
	
	items = frappe.get_all(
		"Website Item",
		filters={"published": 1},
		fields=[
			"name",
			"item_name",
			"item_group",
			"description",
			"website_image",
			"website_warehouse"
		]
	)
	
	# Fetch stock and price
	products = []
	for item in items:
		# Get Price
		price = frappe.db.get_value("Item Price", {"item_code": item.name, "price_list": "Standard Selling"}, "price_list_rate") or 0.0
		
		# Get Stock
		stock = 0
		if item.website_warehouse:
			stock_bin = frappe.db.get_value("Bin", {"item_code": item.name, "warehouse": item.website_warehouse}, "actual_qty")
			if stock_bin:
				stock = int(stock_bin)
		
		# specs (using item attributes if available, or just empty for now)
		specs = {}
		
		products.append({
			"id": item.name,
			"name": item.item_name,
			"category": item.item_group.lower().replace(" ", "-"),
			"categoryName": item.item_group,
			"brand": "CNCLeaders",
			"description": item.description or "",
			"price": float(price),
			"image": item.website_image or "/assets/custom_webshop/images/placeholder.jpg",
			"stock": stock,
			"sold": 0,
			"specs": specs
		})
		
	context.products_json = frappe.as_json(products)
	return context
