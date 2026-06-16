from frappe.website.path_resolver import resolve_path


def custom_resolve_path(path):
	"""
	Intercept /orders and route to the custom custom_webshop orders list page
	instead of letting ERPNext's website_route_rules rewrite it to "Sales Order".
	For all other paths, fall back to normal route resolution.
	"""
	if path == "orders":
		return "orders"
	return resolve_path(path)
