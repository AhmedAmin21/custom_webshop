no_cache = 1

from custom_webshop.shop.context import get_home_context


def get_context(context):
	return get_home_context(context)
