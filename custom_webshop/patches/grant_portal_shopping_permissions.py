# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Give the Customer role the Item read a cart save needs.

See custom_webshop.setup.portal_permissions for why this is a grant and
not a bypass. Runs on migrate as well as install, because this bench's
sites already have the app and would otherwise keep the broken shop.
"""

from custom_webshop.setup.portal_permissions import grant_portal_shopping_permissions


def execute():
	"""Apply the grant to an existing site."""
	granted = grant_portal_shopping_permissions()
	if granted:
		print(f"custom_webshop: portal shopping read granted on {', '.join(granted)}.")
