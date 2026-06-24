no_cache = 1

import frappe
from frappe.utils import cint

from webshop.webshop.product_data_engine.filters import ProductFiltersBuilder
from custom_webshop.shop.context import add_shop_context


def get_context(context):
	context.body_class = "product-page"
	context.parents = [{"name": frappe._("Shop"), "route": "/shop"}]
	filter_engine = ProductFiltersBuilder()
	context.field_filters = filter_engine.get_field_filters()
	context.attribute_filters = filter_engine.get_attribute_filters()
	context.page_length = cint(frappe.db.get_single_value("Webshop Settings", "products_per_page")) or 20
	context.no_cache = 1
	context.show_sidebar = False
	return add_shop_context(context)
