# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class WebshopIdentityConflict(Document):
	def before_insert(self):
		if not self.opened_on:
			self.opened_on = now_datetime()

	def validate(self):
		"""Stamp who closed a conflict and when, the moment its status
		moves to a terminal value - so the queue carries its own audit
		trail without staff having to fill anything in by hand."""
		if self.status in ("Resolved", "Dismissed"):
			if not self.resolved_on:
				self.resolved_on = now_datetime()
			if not self.resolved_by:
				self.resolved_by = frappe.session.user
		else:
			self.resolved_on = None
			self.resolved_by = None
