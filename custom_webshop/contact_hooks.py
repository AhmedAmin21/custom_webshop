# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Contact doc_events owned by custom_webshop.

One job: keep `Contact Phone.custom_phone_e164` in step with
`Contact Phone.phone`, so identity matching has an indexed canonical
column to query instead of guessing at format variants at runtime.

There used to be a second. `contact_enhancements` rewrote every phone row
to its local national digits on validate, so a number this app had just
verified in international form did not survive its own signup, and a good
deal of machinery here and in `signup.linking` existed to put it back.
That app now stores E.164 in `Contact Phone.phone` itself and keeps the
local form in its own `custom_phone_national` column, so the disagreement
it compensated for no longer exists and the compensation is gone with it.

What is kept is the column, because it is ours and matching queries it,
and `_region_for_row`, because deriving it still needs to know which
numbering plan a local-form row follows - legacy rows, and any site
without that app installed, still hold one.
"""

import frappe

from custom_webshop.signup.identity import DEFAULT_REGION, try_to_e164


def sync_phone_e164(doc, method=None):
	"""Contact validate hook: canonicalise the phone rows.

	Runs on every Contact save in the system, including saves that have
	nothing to do with the webshop, so it is written to be incapable of
	failing one: `try_to_e164` never raises, it touches no other document,
	and a number it cannot parse simply leaves the column empty. Such a
	number is then not matchable by phone, which is strictly better than
	blocking a Contact from being saved at all.

	It only ever writes to this app's own column. Whatever `row.phone`
	holds is left exactly as found, so nothing here can contradict
	contact_enhancements' own normalisation - this app is registered after
	it and so has the last word on every save, and using that to overrule
	another app's deliberate rule would quietly delete its behaviour.

	Args:
		doc: the Contact document being validated.
		method: unused, present for the doc_events hook signature.
	"""
	regions = {}

	for row in doc.get("phone_nos", []):
		row.custom_phone_e164 = try_to_e164(row.phone, _region_for_row(row, regions)) or ""


def _region_for_row(row, cache):
	"""Which numbering plan to read one phone row's local number under.

	A local number means nothing without one: `0512345678` is a valid
	Saudi mobile and not a valid Egyptian one. Reading every row as
	Egyptian - which is what defaulting would do - would leave a foreign
	number written in local form with no canonical form at all, and so
	invisible to phone matching.

	Most rows on this site now arrive already in international form, where
	the region is carried by the number itself and this only has to agree
	with it. It still matters for the ones that do not: rows written
	before contact_enhancements began storing E.164, imported data, and
	any site running this app without that one.

	`Contact Phone.country` is that app's own field and says exactly
	which plan the row follows; it also fills it in itself from any
	number written with a country code. Read with `.get` rather than
	attribute access, so this still works on a site where that field is
	not installed - there the shop's default region stands.

	Args:
		row: a Contact Phone child row.
		cache: dict reused across the rows of one save, so a Contact with
			several numbers does not repeat the same Country lookup.

	Returns:
		A two-letter ISO region code.
	"""
	country = row.get("country")
	if not country:
		return DEFAULT_REGION

	if country not in cache:
		code = frappe.db.get_value("Country", country, "code")
		cache[country] = code.upper() if code else DEFAULT_REGION
	return cache[country]
