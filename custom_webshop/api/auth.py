# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Closure of the legacy one-step signup.

`hooks.py` still overrides `frappe.core.doctype.user.user.sign_up` so that
no client can reach Frappe's built-in signup either - but the override now
declines instead of creating an account. Verified signup lives in
custom_webshop.api.signup.

What used to be here created a Frappe User, an ERPNext Customer, a Contact
and a Portal User row from a single unauthenticated POST, with no proof
that the person owned either the email address or the phone number they
typed. Two consequences were the reason for replacing it rather than
patching it further:

* It linked a new account to any existing Customer whose `customer_name`
  string equalled the submitted full name, and granted a Portal User row
  on it - so signing up under somebody else's name inherited their order
  history.
* Validation ran after the User row was inserted, so a name that
  contact_enhancements' Arabic rules reject stranded an account that could
  never finish signing up.

Both are gone with the endpoint. Nothing here creates anything.
"""

import frappe
from frappe import _

REPLACEMENT_MESSAGE = "Please create your account using the sign-up form on the login page."


@frappe.whitelist(allow_guest=True)
def custom_sign_up(email=None, full_name=None, pwd=None, redirect_to="", mobile_no=None):
	"""Decline a legacy signup request.

	Keeps Frappe's own `sign_up` contract - a (status, message) tuple with
	status 0 meaning "not created" - so an old client, or Frappe's stock
	login page, shows the message instead of an error page. Arguments are
	accepted and ignored so that no caller fails on a signature mismatch;
	none of them is read, logged, or stored.

	Args:
		email, full_name, pwd, redirect_to, mobile_no: accepted for
			compatibility with the endpoint this replaces. All ignored.

	Returns:
		A (0, message) tuple.
	"""
	return 0, _(REPLACEMENT_MESSAGE)
