# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""What is waiting in the identity queue, by kind.

A plain Group By chart can only plot the column, and the column holds
constants - so the queue's own chart read `PHONE_ALREADY_ASSOCIATED`
against `PROFILE_DISCREPANCY` in a legend too narrow for either, which
told a manager nothing they could act on. This turns each constant into
the words the rest of the app already uses for it.
"""

import frappe
from frappe import _
from frappe.utils.dashboard import cache_source

from custom_webshop.signup.conflicts import short_label

OPEN_STATUSES = ("Open", "In Review")


@frappe.whitelist()
@cache_source
def get(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	"""Count the unresolved conflicts of each type, biggest first.

	Only the statuses somebody still has to work. A resolved conflict is
	history, and counting it here would keep a problem that was dealt with
	weeks ago at the top of the chart forever.

	Returns:
		A labels/datasets dict for frappe-charts, or an empty list when
		the queue is clear - which is what the framework renders as "no
		data" rather than an empty axis.
	"""
	rows = frappe.get_all(
		"Webshop Identity Conflict",
		filters={"status": ["in", OPEN_STATUSES]},
		fields=["conflict_type", "count(name) as total"],
		group_by="conflict_type",
		order_by="total desc",
	)
	if not rows:
		return []

	return {
		"labels": [_(short_label(row.conflict_type)) for row in rows],
		"datasets": [{"name": _("Waiting"), "values": [row.total for row in rows]}],
		# One series of counts across categories with long names. A donut
		# spent five colours saying what the axis already says, and
		# truncated every label to do it.
		"type": "bar",
	}
