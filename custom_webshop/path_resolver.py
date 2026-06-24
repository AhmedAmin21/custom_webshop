from frappe.website.path_resolver import resolve_path


def custom_resolve_path(path):
	"""Legacy list routes use their own redirect controllers."""
	return resolve_path(path)
