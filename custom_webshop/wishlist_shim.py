# Shim for missing webshop.templates.pages.wishlist (upstream gap in this bench)
from webshop.webshop.utils.product import get_web_item_qty_in_stock


def get_stock_availability(item_code, warehouse):
	stock = get_web_item_qty_in_stock(item_code, warehouse)
	return bool(stock.get("in_stock"))
