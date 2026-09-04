"""Run a file inside a booted Frappe context: _run_in_site.py <site> <file>."""
import sys

import frappe

frappe.init(site=sys.argv[1])
frappe.connect()
frappe.set_user("Administrator")
path = sys.argv[2]
try:
	exec(compile(open(path).read(), path, "exec"), {"__name__": "__main__", "__file__": path})
finally:
	frappe.destroy()
