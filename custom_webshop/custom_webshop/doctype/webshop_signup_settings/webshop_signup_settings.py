# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class WebshopSignupSettings(Document):
	def validate(self):
		self.validate_positive_numbers()
		self.validate_otp_length()
		self.validate_group_nodes()

	def validate_positive_numbers(self):
		"""Every tunable here divides, counts down, or bounds a loop; a zero
		or negative value would either disable a safety limit outright (max
		attempts, cooldown) or make sessions expire instantly."""
		for fieldname in (
			"otp_ttl_seconds",
			"otp_max_attempts",
			"otp_max_sends_per_channel",
			"signup_starts_per_hour_per_ip",
			"session_ttl_minutes",
			"session_retention_days",
			"require_name_parts",
		):
			if self.get(fieldname) is not None and self.get(fieldname) < 1:
				frappe.throw(
					_("{0} must be at least 1.").format(_(self.meta.get_label(fieldname))),
					title=_("Invalid Setting"),
				)

		if self.otp_resend_cooldown_seconds is not None and self.otp_resend_cooldown_seconds < 0:
			frappe.throw(_("Resend Cooldown cannot be negative."), title=_("Invalid Setting"))

	def validate_otp_length(self):
		"""Below 6 digits a code is brute-forceable within the attempt limit
		across a handful of re-sends; above 8 it stops being something a
		person can hold in their head between the SMS and the input box."""
		if self.otp_length and not (6 <= self.otp_length <= 8):
			frappe.throw(_("OTP Length must be between 6 and 8."), title=_("Invalid Setting"))

	def validate_group_nodes(self):
		"""A group node cannot be assigned to a Customer - ERPNext's own
		validate_customer_group() rejects it. This site's global default
		Customer Group happens to be the group node "All Customer Groups",
		which is exactly why signup needs its own explicit setting rather
		than reading frappe.db.get_default."""
		if self.default_customer_group and frappe.db.get_value(
			"Customer Group", self.default_customer_group, "is_group"
		):
			frappe.throw(
				_("Default Customer Group must be a leaf group, not a group node."),
				title=_("Invalid Setting"),
			)

		if self.default_territory and frappe.db.get_value(
			"Territory", self.default_territory, "is_group"
		):
			frappe.throw(
				_("Default Territory must be a leaf territory, not a group node."),
				title=_("Invalid Setting"),
			)
