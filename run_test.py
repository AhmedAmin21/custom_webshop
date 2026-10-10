import frappe
import sys
import os

frappe.init(site="erpnext.local")
frappe.connect()

from custom_webshop.test_concurrent_checkout import run_test
run_test()
