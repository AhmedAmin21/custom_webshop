# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WebshopSignupSession(Document):
	"""An in-progress signup.

	Deliberately a dumb container: every rule about what may change and
	when lives in custom_webshop.signup.session, so the state machine is
	one readable table rather than logic smeared across validate hooks that
	would also fire on the migration and test paths that legitimately need
	to set state directly.
	"""

	pass
