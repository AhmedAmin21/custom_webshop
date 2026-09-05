# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Turn off ERPNext's "Sent via ERPNext" footer on this already-installed site.

See custom_webshop.setup.email_settings for why this is a site setting
and not something a template can suppress on its own.
"""

from custom_webshop.setup.email_settings import disable_standard_email_footer


def execute():
	"""Apply the setting to an existing site."""
	disable_standard_email_footer()
