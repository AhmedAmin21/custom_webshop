import frappe

from custom_webshop.api.signup import is_available
from custom_webshop.signup import passwords

no_cache = 1


def get_context(context):
	"""Build the login page context.

	`signup_available` comes from the same function the signup API's own
	guard uses, so the "Create one" link is shown exactly when the flow
	behind it will actually work. Reading `Website Settings.disable_signup`
	here on its own used to be enough, but is not any more: this app has
	its own `signup_enabled` switch and needs both OTP channels usable, so
	a page trusting only the site-wide flag would offer a signup that the
	first request then refuses.
	"""
	if frappe.session.user != "Guest":
		frappe.local.flags.redirect_location = _redirect_target() or "/shop"
		raise frappe.Redirect

	context.no_cache = 1
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.redirect_to = _redirect_target()

	try:
		context.signup_available = is_available()
	except Exception:
		# A misconfigured or half-migrated site must still render a
		# working login form; it just will not advertise signup.
		context.signup_available = False

	# Kept for the inline LOGIN_CONTEXT block, which page-login.js reads.
	context.disable_signup = not context.signup_available

	# The password guide is rendered from the server's own rules, so the
	# thing shown as you type and the thing enforced on submit cannot
	# drift apart. `signup.passwords` is the single source.
	context.password_rules = {
		"min_length": passwords.MIN_LENGTH,
		"common": list(passwords.COMMON),
	}



def _redirect_target():
	"""Return the requested post-login path, if any.

	Reads `frappe.form_dict` rather than `frappe.request.args`: both carry
	the query string during a real page render, but `frappe.request` is
	unbound anywhere else, which made this controller impossible to test
	and would raise outright if it were ever called off the request path.

	Returns:
		The raw `redirect-to` value, or "". Sanitising it is the job of
		whoever acts on it - `page-login.js` for login, and
		`custom_webshop.api.signup._safe_redirect` for signup.
	"""
	return frappe.form_dict.get("redirect-to") or ""
