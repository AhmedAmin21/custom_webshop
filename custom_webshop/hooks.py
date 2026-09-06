app_name = "custom_webshop"
app_title = "custom_webshop"
app_publisher = "ahmedamin"
app_description = "test"
app_email = "ahmedalgewily@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "custom_webshop",
# 		"logo": "/assets/custom_webshop/logo.png",
# 		"title": "custom_webshop",
# 		"route": "/custom_webshop",
# 		"has_permission": "custom_webshop.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/custom_webshop/css/custom_webshop.css"
# app_include_js = "/assets/custom_webshop/js/custom_webshop.js"

# include js, css files in header of web template
web_include_css = "/assets/custom_webshop/css/cart.css"

# Every page's asset URLs carry the build stamp, so a rebuild is a new URL
# rather than a change a twelve-hour cache header hides - see
# custom_webshop.setup.assets.
update_website_context = "custom_webshop.setup.assets.add_build_version"

# Custom shop pages — assets are loaded directly in each page's HTML,
# not via web_include, to keep the custom pages fully standalone.
#
# Signup is served entirely by the custom /login page (www/login/index.html
# + public/js/page-signup.js). Frappe's own signup form is not themed here
# and not reachable: the sign_up override below declines every request, so
# there is exactly one way to create an account and it is the verified one.

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "custom_webshop/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "custom_webshop/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "custom_webshop.utils.jinja_methods",
# 	"filters": "custom_webshop.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "custom_webshop.install.after_install"
after_migrate = "custom_webshop.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "custom_webshop.uninstall.before_uninstall"
# after_uninstall = "custom_webshop.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "custom_webshop.utils.before_app_install"
# after_app_install = "custom_webshop.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "custom_webshop.utils.before_app_uninstall"
# after_app_uninstall = "custom_webshop.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "custom_webshop.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Contact": {
		# Keeps the canonical E.164 column in step with whatever local
		# format is stored in Contact Phone.phone. Never throws, so it
		# cannot break an unrelated Contact save.
		"validate": "custom_webshop.contact_hooks.sync_phone_e164",
	},
	"Customer": {
		# Strips Portal User rows granting an account access to a Customer
		# it was not verified against - webshop's get_party() adds these
		# silently from contact.links[0].
		"validate": "custom_webshop.customer_hooks.enforce_portal_user_identity",
	},
	"Country": {
		# The signup country picker is assembled from this doctype, then
		# cached; rebuild it when the source changes.
		"on_update": "custom_webshop.signup.countries.clear_cache",
		"on_trash": "custom_webshop.signup.countries.clear_cache",
	},
}

scheduler_events = {
	"daily": [
		"custom_webshop.signup.session.expire_stale_sessions",
	],
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"custom_webshop.tasks.all"
# 	],
# 	"daily": [
# 		"custom_webshop.tasks.daily"
# 	],
# 	"hourly": [
# 		"custom_webshop.tasks.hourly"
# 	],
# 	"weekly": [
# 		"custom_webshop.tasks.weekly"
# 	],
# 	"monthly": [
# 		"custom_webshop.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "custom_webshop.install.before_tests"

# Custom Fields
# -------------
custom_fields = {
	"Webshop Settings": [
		{
			"fieldname": "custom_manual_payment_settings",
			"label": "Manual Payment Settings",
			"fieldtype": "Section Break",
			"insert_after": "payment_gateway_account",
			"collapsible": 1,
		},
		{
			"fieldname": "custom_instapay_number",
			"label": "InstaPay Number",
			"fieldtype": "Data",
			"insert_after": "custom_manual_payment_settings",
		},
		{
			"fieldname": "custom_vodafone_cash_number",
			"label": "Vodafone Cash Number",
			"fieldtype": "Data",
			"insert_after": "custom_instapay_number",
		},
		{
			"fieldname": "custom_etisalat_cash_number",
			"label": "Etisalat Cash Number",
			"fieldtype": "Data",
			"insert_after": "custom_vodafone_cash_number",
		},
		{
			"fieldname": "custom_display_attributes",
			"label": "Display Attributes (JSON)",
			"fieldtype": "Small Text",
			"insert_after": "custom_etisalat_cash_number",
			"description": "JSON list of attribute names to show on the shop page carousels, in order. Managed by the admin panel.",
		},
	],
	"Sales Order": [
		{
			"fieldname": "custom_payment_method",
			"label": "Payment Method",
			"fieldtype": "Select",
			"options": "\nInstaPay\nVodafone Cash\nEtisalat Cash",
			"insert_after": "payment_terms_section",
			"read_only": 1,
		}
	]
}

# Overriding Methods
# ------------------------------
override_whitelisted_methods = {
	"webshop.webshop.shopping_cart.cart.place_order": "custom_webshop.shopping_cart.cart_override.place_order_from_cart",
	"webshop.webshop.shopping_cart.cart.request_for_quotation": "custom_webshop.shopping_cart.cart_override.place_order_from_cart",
	"webshop.webshop.shopping_cart.cart.update_cart": "custom_webshop.shopping_cart.cart_override.update_cart",
	"webshop.webshop.shopping_cart.cart.update_cart_address": "custom_webshop.shopping_cart.cart_override.update_cart_address",
	"frappe.core.doctype.user.user.sign_up": "custom_webshop.api.auth.custom_sign_up"
}

website_path_resolver = "custom_webshop.path_resolver.custom_resolve_path"

role_home_page = {
	"Customer": "/shop"
}

override_doctype_class = {
	"Sales Order": "custom_webshop.overrides.sales_order.CustomSalesOrder"
}

website_route_rules = [
	{"from_route": "/orders", "to_route": "orders"},
	{"from_route": "/orders/<path:name>", "to_route": "order", "defaults": {"doctype": "Sales Order", "parents": [{"label": "Orders", "route": "orders"}]}},
	{"from_route": "/shop", "to_route": "shop"},
	{"from_route": "/catalog", "to_route": "catalog"},
	{"from_route": "/product", "to_route": "product"},
	# Served from www/checkout, not www/cart. Frappe picks a page from the
	# *last* installed app that has one, and webshop - installed after
	# this app - ships its own templates/pages/cart.html, which shadowed
	# ours completely: /cart was rendering webshop's stock cart, whose
	# get_party() sends anyone without a Customer to /contact, a page
	# this site does not have. An endpoint webshop has no file for is
	# the only way to win that lookup without reordering the apps.
	{"from_route": "/cart", "to_route": "checkout"},
	{"from_route": "/admin", "to_route": "admin"},
]

# Default home page for all users
home_page = "shop"
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "custom_webshop.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# Both doctypes are a record of what a signup did, not a business record in
# their own right - a Webshop Signup Session outlives the attempt it logged,
# and a Webshop Account Identity just names which User/Contact/Customer a
# signup ended up as. Neither should be the reason a Contact or Customer
# can't be deleted; a dangling reference in a log is fine, a login nobody
# can clean up because a log still points at it is not.
ignore_links_on_delete = ["Webshop Account Identity", "Webshop Signup Session"]

# Request Events
# ----------------
# before_request = ["custom_webshop.utils.before_request"]
# after_request = ["custom_webshop.utils.after_request"]

# Job Events
# ----------
# before_job = ["custom_webshop.utils.before_job"]
# after_job = ["custom_webshop.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"custom_webshop.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

