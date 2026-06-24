no_cache = 1

from custom_webshop.shop.context import get_payment_context


def get_context(context):
	return get_payment_context(context)
