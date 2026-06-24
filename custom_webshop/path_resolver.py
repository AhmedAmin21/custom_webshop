from frappe.website.path_resolver import resolve_path


def custom_resolve_path(path):
	"""Route shop storefront pages under /shop."""
	if path in ("shop/orders", "orders"):
		return "shop/orders"
	return resolve_path(path)
