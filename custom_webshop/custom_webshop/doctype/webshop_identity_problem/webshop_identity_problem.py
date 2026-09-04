# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WebshopIdentityProblem(Document):
	"""One thing wrong with a signup.

	A signup can be wrong in several ways at once - a name that
	disagrees, a record of the wrong kind, a number already spoken for -
	and each is a separate decision. They used to be separate conflicts,
	which meant staff worked one case as several unrelated rows. They are
	rows on one conflict now, so the queue holds one item per signup and
	the form asks each question in its own section.
	"""

	pass
