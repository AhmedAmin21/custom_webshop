# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

from custom_webshop.setup.custom_fields import create_signup_custom_fields, create_signup_indexes
from custom_webshop.setup.portal_permissions import grant_portal_shopping_permissions


def after_install():
	create_signup_custom_fields()
	create_signup_indexes()
	grant_portal_shopping_permissions()


def after_migrate():
	"""Re-assert the schema this app owns on every migrate.

	Both helpers are idempotent. Running them here as well as in
	after_install covers the case this app is already installed on a site
	that predates these fields - the ordinary situation for this bench.
	"""
	create_signup_custom_fields()
	create_signup_indexes()
	grant_portal_shopping_permissions()
