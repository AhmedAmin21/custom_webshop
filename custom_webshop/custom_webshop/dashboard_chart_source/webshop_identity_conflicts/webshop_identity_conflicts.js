// Copyright (c) 2026, ahmedamin and contributors
// For license information, please see license.txt

// No filters: the chart is "what is waiting right now", and every
// narrowing a manager might want - by age, by status - is a click away in
// the list the chart links to.
frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Webshop Identity Conflicts"] = {
    method: "custom_webshop.custom_webshop.dashboard_chart_source.webshop_identity_conflicts.webshop_identity_conflicts.get",
    filters: [],
};
