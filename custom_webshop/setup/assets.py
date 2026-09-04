# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Making a rebuild actually reach the browser.

This app's pages load their CSS and JS by plain path -
`/assets/custom_webshop/js/store.js` - and Frappe serves those with
`Cache-Control: max-age=43200`. A browser that has the file keeps it for
twelve hours, so a deployed fix does not reach anyone already carrying
the old copy: the page keeps running yesterday's logic against today's
server, which reads as "the change did not work" rather than as a stale
file.

Stamping the build on every asset URL makes each build a different URL,
so the cache header goes back to being a help instead of a trap.
"""

import frappe
from frappe.utils import get_build_version


def add_build_version(context):
	"""Give every website page the current build stamp.

	Registered as `update_website_context`, so pages get it without each
	one remembering to ask.

	Args:
		context: the website context being built.
	"""
	context.build_version = get_build_version()
