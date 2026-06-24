# Copyright (c) 2026, custom_webshop contributors
# License: MIT

from custom_webshop.www.shop.shop_context import get_shop_context


def get_context(context):
	get_shop_context(context, active_page="catalog")
