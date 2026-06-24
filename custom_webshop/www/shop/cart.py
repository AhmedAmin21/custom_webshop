no_cache = 1

from custom_webshop.shop.context import add_shop_context
from custom_webshop.templates.pages import cart as cart_page


def get_context(context):
	cart_page.get_context(context)
	return add_shop_context(context)
