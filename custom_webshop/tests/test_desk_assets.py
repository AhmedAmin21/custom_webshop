# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Tests for the Desk assets this app ships.

Workspaces, number cards and dashboard charts are JSON files that only
ever run when somebody opens the page, which makes them the easiest thing
in the app to get wrong and not find out. One of them shipped with
`"Today - 7"` as a filter value - a phrase Frappe's query builder has no
idea about, so the card threw `ParserError` the first time the workspace
was opened, and nothing before that had asked it to.

So these tests do what opening the page does: run every card's real
filters through the real endpoint, and every chart through its own. They
also hold two invariants that would have caught that bug on its own terms
- relative dates belong in `dynamic_filters_json` where the client
evaluates them, and `filters_json` may only carry values the server can
read as they stand.
"""

import json
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

APP = "custom_webshop"
MODULE = "Custom Webshop"

#: Operators whose value is a phrase Frappe resolves itself ("this month"),
#: rather than a literal it parses. Everything else in a static filter has
#: to already be a value.
SELF_RESOLVING = {"timespan", "previous", "next"}

#: What a relative date looks like when somebody writes one by hand into a
#: place that cannot evaluate it.
HAND_WRITTEN_RELATIVE = re.compile(
	r"\b(today|now|yesterday|tomorrow)\b\s*[-+]?|\b[-+]\s*\d+\s*(day|week|month|year)", re.I
)


def shipped(kind):
	"""Every JSON document of one kind this app ships, as (name, dict)."""
	root = frappe.get_app_path(APP, APP, kind)
	if not os.path.isdir(root):
		return []

	out = []
	for folder in sorted(os.listdir(root)):
		path = os.path.join(root, folder, f"{folder}.json")
		if os.path.exists(path):
			with open(path, encoding="utf-8") as fh:
				out.append((folder, json.load(fh)))
	return out


class TestShippedDeskAssets(FrappeTestCase):
	def test_this_app_ships_the_assets_these_tests_are_about(self):
		# A guard on the guard: if the folders are renamed, every test
		# below would pass by iterating over nothing.
		self.assertTrue(shipped("number_card"), "no number cards found")
		self.assertTrue(shipped("dashboard_chart"), "no dashboard charts found")
		self.assertTrue(shipped("workspace"), "no workspace found")


class TestNumberCards(FrappeTestCase):
	def test_every_card_is_installed(self):
		for folder, spec in shipped("number_card"):
			with self.subTest(card=folder):
				self.assertTrue(
					frappe.db.exists("Number Card", spec["name"]),
					f"{spec['name']} is on disk but not in the database - "
					"bump its `modified` stamp; sync_dashboards skips a file "
					"that is not newer than the record it already imported",
				)
				self.assertEqual(
					frappe.db.get_value("Number Card", spec["name"], "module"), MODULE
				)

	def test_static_filters_carry_no_relative_dates(self):
		"""`filters_json` is sent to the server exactly as written.

		A phrase like "Today - 7" reaches `frappe.db.format_datetime`,
		which hands it to dateutil, which raises. Relative dates belong in
		`dynamic_filters_json`, where the browser evaluates them into real
		values first.
		"""
		for folder, spec in shipped("number_card"):
			for condition in json.loads(spec.get("filters_json") or "[]"):
				operator, value = condition[2], condition[3]
				if str(operator).lower() in SELF_RESOLVING or not isinstance(value, str):
					continue
				with self.subTest(card=folder, filter=condition):
					self.assertIsNone(
						HAND_WRITTEN_RELATIVE.search(value),
						f"{value!r} is a relative date in a static filter",
					)

	def test_dynamic_filters_are_expressions(self):
		for folder, spec in shipped("number_card"):
			for condition in json.loads(spec.get("dynamic_filters_json") or "[]"):
				with self.subTest(card=folder, filter=condition):
					self.assertEqual(len(condition), 4, "expected [doctype, field, op, expr]")
					self.assertIn(
						"frappe.",
						condition[3],
						"a dynamic filter's value is evaluated as JavaScript; "
						"a plain string here is a literal that never resolves",
					)

	def test_every_card_returns_a_number(self):
		"""What opening the workspace does.

		The dynamic half is evaluated in the browser, so it is stood in
		for here with a real date - the point is that the *server* accepts
		the shape each card produces.
		"""
		from frappe.desk.doctype.number_card.number_card import get_result
		from frappe.utils import add_days, nowdate

		for folder, spec in shipped("number_card"):
			doc = frappe.get_doc("Number Card", spec["name"])
			filters = json.loads(doc.filters_json or "[]")
			for condition in json.loads(doc.dynamic_filters_json or "[]"):
				filters.append(list(condition[:3]) + [add_days(nowdate(), -7)])

			with self.subTest(card=folder):
				result = get_result(frappe.as_json(doc.as_dict()), json.dumps(filters))
				self.assertIsInstance(result, float)


class TestDashboardCharts(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def open_conflict(self):
		"""One row, so a Group By chart has something to group.

		`get_group_by_chart_config` returns None rather than an empty
		shape when nothing matches, so a chart tested against an empty
		queue passes by never being asked anything.
		"""
		doc = frappe.get_doc(
			{
				"doctype": "Webshop Identity Conflict",
				"conflict_type": "PHONE_ALREADY_ASSOCIATED",
				"status": "Open",
				"submitted_name": "Desk Asset Probe",
				"phone_e164": "+201000000001",
				"email_normalized": "desk-asset-probe@example.com",
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		return doc

	def render(self, doc):
		"""Draw a chart the same way the thing that draws it would.

		Frappe's own `dashboard_chart.get` has no branch for a Custom
		chart - the browser reads the source's `.js`, takes the method
		named there and calls it directly. Following the same route means
		this test also proves those two files agree: a `.js` pointing at a
		method that does not exist fails here rather than on the page.
		"""
		if doc.chart_type != "Custom":
			# Passed as JSON rather than by name: Frappe's own
			# `cache_source` turns `chart_name` into a Document and then
			# hands it to a `get` that expects a string, so the name +
			# no_cache combination raises inside Frappe. The client sends
			# JSON for an unsaved chart, and that path works.
			from frappe.desk.doctype.dashboard_chart.dashboard_chart import get

			return get(chart=frappe.as_json(doc.as_dict()), no_cache=True)

		from frappe.desk.doctype.dashboard_chart_source.dashboard_chart_source import get_config

		self.assertTrue(
			frappe.db.exists("Dashboard Chart Source", doc.source),
			f"{doc.name} names a source that is not installed",
		)
		named = re.search(r'method:\s*"([^"]+)"', get_config(doc.source))
		self.assertIsNotNone(named, f"{doc.source}.js names no method")
		return frappe.get_attr(named.group(1))(chart_name=doc.name, no_cache=True)

	def test_every_chart_is_installed_and_renders(self):
		self.open_conflict()

		for folder, spec in shipped("dashboard_chart"):
			with self.subTest(chart=folder):
				name = spec["name"]
				self.assertTrue(frappe.db.exists("Dashboard Chart", name))
				self.assertEqual(frappe.db.get_value("Dashboard Chart", name, "module"), MODULE)

				data = self.render(frappe.get_doc("Dashboard Chart", name))

				self.assertIsNotNone(data, "the chart returned nothing to draw")
				self.assertIn("labels", data)
				self.assertIn("datasets", data)
				self.assertTrue(data["labels"])

	def test_no_chart_axis_is_labelled_with_a_raw_constant(self):
		"""An axis is read by a manager, not by the code that stores it.

		The conflict chart used to plot `conflict_type` straight from the
		column, so it compared PHONE_ALREADY_ASSOCIATED against
		PROFILE_DISCREPANCY in a legend too narrow for either - true, and
		useless to the person deciding what to work on next.
		"""
		self.open_conflict()

		for folder, spec in shipped("dashboard_chart"):
			with self.subTest(chart=folder):
				data = self.render(frappe.get_doc("Dashboard Chart", spec["name"]))
				for label in data["labels"]:
					self.assertFalse(
						re.fullmatch(r"[A-Z][A-Z0-9]*(_[A-Z0-9]+)+", str(label)),
						f"{spec['name']} labels a slice {label!r}",
					)


class TestWorkspace(FrappeTestCase):
	def test_it_is_installed_and_public(self):
		for folder, spec in shipped("workspace"):
			with self.subTest(workspace=folder):
				doc = frappe.get_doc("Workspace", spec["name"])
				self.assertEqual(doc.module, MODULE)
				self.assertTrue(doc.public)

	def test_everything_it_points_at_exists(self):
		"""A workspace happily renders a card or link that is not there.

		It just shows an empty tile, which reads as "nothing to report"
		rather than "this is broken" - so the links are checked here
		instead.
		"""
		for folder, spec in shipped("workspace"):
			doc = frappe.get_doc("Workspace", spec["name"])

			for row in doc.number_cards:
				with self.subTest(workspace=folder, card=row.number_card_name):
					self.assertTrue(frappe.db.exists("Number Card", row.number_card_name))

			for row in doc.charts:
				with self.subTest(workspace=folder, chart=row.chart_name):
					self.assertTrue(frappe.db.exists("Dashboard Chart", row.chart_name))

			for row in doc.links:
				if row.type != "Link" or not row.link_to:
					continue
				with self.subTest(workspace=folder, link=row.link_to):
					self.assertTrue(
						frappe.db.exists(row.link_type, row.link_to),
						f"{row.link_type} {row.link_to} does not exist on this site",
					)

			for row in doc.shortcuts:
				with self.subTest(workspace=folder, shortcut=row.link_to):
					self.assertTrue(frappe.db.exists(row.type, row.link_to))
