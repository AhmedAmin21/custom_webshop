# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""The country list behind the signup phone field.

Assembled rather than hard-coded. The names come from Frappe's own
`Country` doctype - already installed, already translated, already the
list the rest of ERPNext uses - and the dialling codes and example
numbers come from `phonenumbers`, which ships with Frappe. Neither a
bundled country table nor a third-party picker library is needed, and the
names stay in step with the ones staff see everywhere else in the Desk.

A country with no ISO code, or one `phonenumbers` does not recognise, is
skipped: without a dialling code there is nothing to offer the person.
"""

import frappe

from custom_webshop.signup import settings
from custom_webshop.signup.identity import (
	dial_code,
	example_significant_number,
	flag_emoji,
	national_number_lengths,
	national_trunk_prefix,
)

CACHE_PREFIX = "custom_webshop_signup_countries"


def build():
	"""Assemble the full country list.

	Returns:
		A list of dicts sorted by name, each with:
			code: ISO-3166 alpha-2, upper case. This is what the signup UI
				shows as the country marker.
			name: the country name, as Frappe knows it.
			dial: international dialling code, without the plus.
			flag: flag emoji. Provided for callers that want it, but the
				signup UI deliberately does not use it - Windows renders no
				regional-indicator glyphs at all and many Linux builds ship
				no emoji font, so a flag column silently degrades to bare
				letters. The UI shows `code` instead.
			example: an example mobile number in the form the field
				holds it - grouped the way that country groups numbers,
				but with no trunk prefix, since the dial code sits right
				beside it.
			trunk: the prefix people write before a local number and drop
				once a country code is in front ("0" almost everywhere,
				"1" in North America, absent in a few places). The field
				removes it as you type, so `+20` is never followed by
				`01012345678` - which is not a number anyone can dial.
			lengths: the digit counts the national significant number may
				have here, so the form can bound the field and say "that
				is too short" before anything is submitted. Empty when the
				region publishes no mobile metadata, which the UI reads as
				"impose no length rule" rather than "reject everything".
			max_len: the largest of those, or 0 when unknown.
	"""
	rows = frappe.get_all("Country", filters={"code": ["is", "set"]}, fields=["name", "code"])

	countries = []
	for row in rows:
		region = (row.code or "").strip().upper()
		code = dial_code(region)
		if not code:
			continue

		lengths = list(national_number_lengths(region))

		countries.append(
			{
				"code": region,
				# Frappe ships country-name translations, so an Arabic
				# visitor gets "مصر" rather than "Egypt".
				"name": frappe._(row.name),
				# Kept so the picker's search matches either language: an
				# Arabic reader who types "egypt" or "eg" should still find
				# مصر, and vice versa.
				"name_en": row.name,
				"dial": code,
				"flag": flag_emoji(region),
				"example": example_significant_number(region),
				"trunk": national_trunk_prefix(region),
				"lengths": lengths,
				"max_len": max(lengths) if lengths else 0,
			}
		)

	# Sorted on the translated name, not the English one - an Arabic list
	# ordered by English spelling is no order at all to the person reading
	# it. `sort_key` folds accents so "Åland" files under A rather than
	# after Z, matching how the database collation orders names.
	countries.sort(key=lambda c: _sort_key(c["name"]))
	return countries


def _sort_key(name):
	"""Return an accent-folded, case-folded sort key for a country name."""
	import unicodedata

	decomposed = unicodedata.normalize("NFKD", name)
	return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def get_all(lang=None):
	"""Return the country list for a language, cached.

	The list changes only when the Country doctype does, so it is built
	once per language and kept in Redis rather than reassembled on every
	page load - it costs a query plus 250 `phonenumbers` lookups and 250
	translation lookups.

	Args:
		lang: language code to build the names in; defaults to the
			request's own language.

	Returns:
		See `build`.
	"""
	lang = lang or frappe.local.lang or "en"
	key = f"{CACHE_PREFIX}:{lang}"

	cached = frappe.cache.get_value(key)
	if cached:
		return cached

	countries = build()
	frappe.cache.set_value(key, countries)
	return countries


def clear_cache(doc=None, method=None):
	"""Drop every language's cached list. Wired to Country's doc_events.

	Args:
		doc: the Country document that changed; unused.
		method: unused, present for the doc_events hook signature.
	"""
	frappe.cache.delete_keys(CACHE_PREFIX)


def default_code():
	"""Return the region the picker should start on.

	Args:
		None.

	Returns:
		A two-letter ISO region code.
	"""
	return settings.get_phone_region().upper()


@frappe.whitelist(allow_guest=True)
def for_signup(lang=None):
	"""Country list plus the default selection, for the signup form.

	Guest-readable on purpose: it is the public list of countries this shop
	will accept a phone number from, and carries nothing about anybody.

	Takes the language from the caller rather than the session. The shop's
	own language toggle lives in the browser (`Store.lang`, backed by
	localStorage) and is independent of Frappe's request language, so a
	visitor reading the site in Arabic can arrive here with an English
	request language. Trusting the session would show them English country
	names on an otherwise Arabic form.

	Args:
		lang: "ar", "en", or anything Frappe has translations for.

	Returns:
		A dict with `countries` and `default`.
	"""
	if lang:
		frappe.local.lang = lang

	return {"countries": get_all(lang), "default": default_code()}
