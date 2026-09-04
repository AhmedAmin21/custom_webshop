# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Identity normalization and validation primitives for the webshop signup flow.

Everything in this module is a pure function over strings - no database
access, no document writes - so it is cheap to unit test exhaustively and
safe to call from anywhere (a validate hook, a whitelisted endpoint, a
migration patch).

Three canonical forms are defined here, and they are the vocabulary the
rest of the signup package speaks in:

* **phone** -> E.164 (`+201012345678`). Both the matching key *and* the
  stored value: every phone this flow writes - `Contact Phone.phone`,
  `Contact Phone.custom_phone_e164`, `User.mobile_no` and
  `Webshop Account Identity.phone_e164` - is in international form, so a
  number means the same thing in every column that holds it and no reader
  has to know which country row it came from.

  Reading is deliberately more forgiving than writing. Rows written
  before this rule, and rows `contact_enhancements.api.lead_lookup.
  normalize_phone_for_country` writes on its own paths, still hold the
  local form (`01012345678`); `to_local` reproduces that form so
  `matching.phone_variants` can still find them. We canonicalise what we
  write and accept every form when we read.
* **email** -> validated, whitespace-stripped, casefolded.
* **name** -> NFKC, de-diacriticized, orthography-unified token list, used
  *only* for comparison. The name a user typed is stored verbatim.
"""

import re
import unicodedata

import frappe
from frappe import _

DEFAULT_REGION = "EG"

# Arabic combining marks (tashkeel) U+064B-U+065F, superscript alef U+0670,
# and tatweel/kashida U+0640. Same set contact_enhancements.contact_hooks
# rejects outright on Contact.first_name; here we only strip them, because
# this pipeline feeds *comparison*, not validation - an existing ERPNext
# record written before that app was installed may legitimately carry them
# and must still be comparable against a freshly typed name.
TASHKEEL_AND_TATWEEL_PATTERN = re.compile("[ً-ٰٟـ]")

# Orthography variants that Egyptian users type interchangeably. Folding
# these is what lets "احمد الجويلى" match "احمد الجويلي". Deliberately a
# one-way fold for comparison only - never written back to any record.
ARABIC_FOLDING = {
	"أ": "ا",  # ALEF WITH HAMZA ABOVE  -> ALEF
	"إ": "ا",  # ALEF WITH HAMZA BELOW  -> ALEF
	"آ": "ا",  # ALEF WITH MADDA ABOVE  -> ALEF
	"ٱ": "ا",  # ALEF WASLA            -> ALEF
	"ة": "ه",  # TEH MARBUTA           -> HEH
	"ى": "ي",  # ALEF MAKSURA          -> YEH
	"ـ": "",        # TATWEEL               -> removed
}

WHITESPACE_PATTERN = re.compile(r"\s+")

# ── Name repair ───────────────────────────────────────────────────────────
# contact_enhancements.contact_hooks enforces five rules on Contact.first_name
# and throws on the first violation. Every one of them describes a spelling
# the business does not want stored - not a name the business refuses to
# serve - so signup repairs them instead of turning the person away. The
# repairs below are exactly the corrections that app's own error messages
# ask the user to make by hand.
ALEF_HAMZA_ABOVE = "\u0623"      # أ  banned at the start of a word
ALEF = "\u0627"                  # ا  what it becomes
TEH_MARBUTA = "\u0629"           # ة  banned at the end of a word
HEH = "\u0647"                   # ه  what it becomes
YEH = "\u064A"                   # ي  banned at the end of a word
ALEF_MAKSURA = "\u0649"          # ى  what it becomes




# Egyptian mobile numbers are the only ones this business currently sells
# to, and phonenumbers already knows their shape; this is used purely to
# decide whether a number can be rendered in the local 0-prefixed form.
EGYPT_COUNTRY_CODE = 20


class InvalidPhoneNumber(frappe.ValidationError):
	pass


class InvalidEmail(frappe.ValidationError):
	pass


class InvalidFullName(frappe.ValidationError):
	pass


# ──────────────────────────────────────────────────────────────────────────
# Phone
# ──────────────────────────────────────────────────────────────────────────


def flag_emoji(region):
	"""Return the flag emoji for an ISO-3166 region code.

	Built from the two regional-indicator codepoints rather than shipping
	image assets: it needs no files, scales with the font, and every
	platform the shop runs on renders it.

	Args:
		region: a two-letter ISO region code, any case.

	Returns:
		The flag as a string, or "" for anything that is not two letters.
	"""
	code = (region or "").strip().upper()
	if len(code) != 2 or not code.isalpha():
		return ""
	return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in code)


def dial_code(region):
	"""Return the international dialling code for a region, without the plus.

	Args:
		region: a two-letter ISO region code.

	Returns:
		The country calling code as an int, or None if the region is unknown.
	"""
	import phonenumbers

	code = (region or "").strip().upper()
	if code not in phonenumbers.SUPPORTED_REGIONS:
		return None
	return phonenumbers.country_code_for_region(code)


def example_national_number(region):
	"""Return a realistic local mobile number for a region, for a placeholder.

	Shows the person the shape their own number should take - "010 01234567"
	in Egypt, "(506) 234-5678" in Canada - instead of one hard-coded format
	that is wrong everywhere but home.

	Args:
		region: a two-letter ISO region code.

	Returns:
		A nationally-formatted example, or "" when the library has none.
	"""
	import phonenumbers
	from phonenumbers import PhoneNumberFormat, PhoneNumberType

	code = (region or "").strip().upper()
	if code not in phonenumbers.SUPPORTED_REGIONS:
		return ""

	example = phonenumbers.example_number_for_type(code, PhoneNumberType.MOBILE)
	if not example:
		return ""
	return phonenumbers.format_number(example, PhoneNumberFormat.NATIONAL)


def example_significant_number(region):
	"""Return an example mobile number with no trunk prefix, for a placeholder.

	The same example `example_national_number` gives, in the form the
	signup field actually holds: "10 01234567" for Egypt rather than
	"010 01234567", because the field shows `+20` beside it and the
	leading zero is dropped once a country code is in front.

	Taken from the library's own international formatting - the country
	code is sliced off the front - so the grouping is the one that
	country really uses, not one invented here.

	Args:
		region: a two-letter ISO region code.

	Returns:
		The example without its country code or trunk prefix, or "" when
		the library has none.
	"""
	import phonenumbers
	from phonenumbers import PhoneNumberFormat, PhoneNumberType

	code = (region or "").strip().upper()
	if code not in phonenumbers.SUPPORTED_REGIONS:
		return ""

	example = phonenumbers.example_number_for_type(code, PhoneNumberType.MOBILE)
	if not example:
		return ""

	international = phonenumbers.format_number(example, PhoneNumberFormat.INTERNATIONAL)
	prefix = f"+{example.country_code}"
	if international.startswith(prefix):
		return international[len(prefix):].strip()
	return international


def region_for_e164(e164):
	"""Return the ISO region a canonical number belongs to.

	The signup session records the country someone picked, but rows that
	predate the picker have none, and a number carries its own answer -
	so this recovers the region from the number itself.

	Args:
		e164: a number in E.164 form.

	Returns:
		A two-letter ISO region code, or "" if it cannot be determined.
	"""
	import phonenumbers

	if not e164:
		return ""

	try:
		parsed = phonenumbers.parse(e164, None)
	except phonenumbers.NumberParseException:
		return ""

	return phonenumbers.region_code_for_number(parsed) or ""


def national_number_lengths(region):
	"""Return the digit counts a mobile number may have in a region.

	These are the lengths of the *national significant number* - the part
	that follows the country code, with no trunk prefix. Egypt is 10
	(`1012345678`), not 11: the leading zero people write locally is a
	trunk prefix, and it is not part of the number once a country code is
	in front of it.

	That is what the signup field holds, because the field shows the
	country code beside it and `+20` followed by `01012345678` is not a
	number anyone could dial.

	Drawn from `phonenumbers`' own metadata rather than guessed at. Used
	to bound the input and to say a number is the wrong length before it
	is submitted - a convenience, not the check. `to_e164` remains the
	authority, because a number can be exactly the right length and still
	not be a real one, and it goes on accepting the trunk prefix.

	Args:
		region: a two-letter ISO region code.

	Returns:
		A sorted tuple of digit counts, or () when the region is unknown
		or publishes no mobile metadata.
	"""
	meta = _metadata_for(region)
	if not meta or not meta.mobile:
		return ()

	lengths = set(meta.mobile.possible_length or ())
	if not lengths and meta.general_desc:
		lengths = set(meta.general_desc.possible_length or ())

	return tuple(sorted(lengths))


def national_trunk_prefix(region):
	"""Return the trunk prefix people write before a local number.

	`0` across most of the world, `1` in the North American plan, and
	absent in a few places (Italy keeps its leading zero as part of the
	number). It is dropped once a country code is in front, which is why
	the signup field removes it as you type.

	Args:
		region: a two-letter ISO region code.

	Returns:
		The prefix, or "" when the region has none or is unknown.
	"""
	meta = _metadata_for(region)
	return (meta.national_prefix or "") if meta else ""


def _metadata_for(region):
	"""Return phonenumbers' metadata for a region, or None if unknown."""
	import phonenumbers
	from phonenumbers import phonemetadata

	code = (region or "").strip().upper()
	if code not in phonenumbers.SUPPORTED_REGIONS:
		return None

	return phonemetadata.PhoneMetadata.metadata_for_region(code)


def normalize_region(region, fallback=None):
	"""Return a usable ISO region code, falling back when one is not.

	The region decides which rules a number is judged by, so an unknown or
	missing value must not silently become "no rules at all" - it becomes
	the configured default instead.

	Args:
		region: the region code submitted, if any.
		fallback: what to use when it is missing or unsupported; defaults
			to this module's own default region.

	Returns:
		A supported two-letter region code.
	"""
	import phonenumbers

	code = (region or "").strip().upper()
	if code in phonenumbers.SUPPORTED_REGIONS:
		return code
	return (fallback or DEFAULT_REGION).upper()


def try_to_e164(raw, region=DEFAULT_REGION):
	"""Best-effort E.164 conversion that never raises.

	Used everywhere a failure must not break an unrelated operation - the
	`Contact` validate hook that maintains `custom_phone_e164` on every
	Contact save in the system, and the backfill patch that walks existing
	rows. A number this returns None for is simply not matchable by phone;
	that is a strictly better outcome than blocking a Contact save.

	Accepts every shape Egyptian users actually type, verified by test:
	`01012345678`, `+201012345678`, `00201012345678`, `201012345678`, and
	any of those with spaces, dashes, dots or parentheses.

	Args:
		raw: the phone number as typed, or None.
		region: ISO-3166 region used to interpret a national-format number
			(one without a country code). Defaults to Egypt.

	Returns:
		The number in E.164 form (`+201012345678`), or None if it cannot be
		parsed into a valid number.
	"""
	import phonenumbers

	if not raw:
		return None

	candidate = str(raw).strip()
	if not candidate:
		return None

	# Two parse attempts, in order. The first handles national format
	# ("01012345678" with region EG), a real "+" prefix, and the "00"
	# international prefix, all of which phonenumbers understands natively.
	# The second exists only for a bare country-code prefix like
	# "201012345678", which phonenumbers reads as a 12-digit *national*
	# number and correctly rejects - prepending "+" is what disambiguates
	# it. contact_enhancements deliberately refuses to strip a bare "20"
	# for exactly this ambiguity reason; going through phonenumbers instead
	# of string surgery means we only accept it when the result is a
	# genuinely valid number, so a real local number that happens to start
	# with "20" is never silently mangled.
	attempts = [(candidate, region)]
	digits_only = re.sub(r"[^\d]", "", candidate)
	if digits_only and not candidate.lstrip().startswith("+"):
		attempts.append(("+" + digits_only, None))

	for value, parse_region in attempts:
		try:
			parsed = phonenumbers.parse(value, parse_region)
		except phonenumbers.NumberParseException:
			continue
		if phonenumbers.is_valid_number(parsed):
			return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

	return None


def to_e164(raw, region=DEFAULT_REGION):
	"""Strict E.164 conversion for user-submitted input.

	Args:
		raw: the phone number as typed.
		region: see try_to_e164.

	Returns:
		The number in E.164 form.

	Raises:
		InvalidPhoneNumber: if the number is missing or not a valid number.
	"""
	normalized = try_to_e164(raw, region)
	if not normalized:
		# Show an example from the country the person actually picked. A
		# fixed Egyptian example was actively misleading once the picker
		# existed: someone entering a Canadian number was being told to
		# type "01012345678".
		example = example_national_number(region)
		if example:
			frappe.throw(
				_("That does not look like a valid mobile number. Example: {0}").format(example),
				exc=InvalidPhoneNumber,
				title=_("Invalid Mobile Number"),
			)
		frappe.throw(
			_("Please enter a valid mobile number."),
			exc=InvalidPhoneNumber,
			title=_("Invalid Mobile Number"),
		)
	return normalized


def to_local(e164):
	"""Render an E.164 number in the local form other writers may have used.

	For Egyptian numbers that is the familiar leading-zero form
	(`+201012345678` -> `01012345678`); for any other country the E.164
	form is returned unchanged, there being no single "local" convention
	worth guessing at.

	This is a *lookup* helper, not a storage one. Nothing in this app
	writes the string it returns - `linking` stores E.164 everywhere. It
	exists so `matching.phone_variants` can still recognise the rows that
	do hold the local form: everything written before that rule, and
	anything contact_enhancements writes on its own paths. Dropping it
	would make those people invisible to matching, which is the exact
	failure this flow exists to prevent.

	Args:
		e164: a number already in E.164 form.

	Returns:
		The local rendering, for use as a query candidate.
	"""
	import phonenumbers

	if not e164:
		return ""

	try:
		parsed = phonenumbers.parse(e164, None)
	except phonenumbers.NumberParseException:
		return e164

	if parsed.country_code != EGYPT_COUNTRY_CODE:
		return e164

	return "0" + str(parsed.national_number)


def mask_phone(e164):
	"""Mask a phone number for display back to a not-yet-authenticated user.

	Shows enough for the owner to recognise their own number and nothing
	useful to anybody else: country code, first three national digits, then
	asterisks, then the last two. `+201012345678` -> `+20 101 ***** 78`.

	Args:
		e164: a number in E.164 form, or None.

	Returns:
		A masked display string, or "" if there is nothing to show.
	"""
	import phonenumbers

	if not e164:
		return ""

	try:
		parsed = phonenumbers.parse(e164, None)
	except phonenumbers.NumberParseException:
		return "*" * 8

	national = str(parsed.national_number)
	if len(national) <= 5:
		return f"+{parsed.country_code} {'*' * len(national)}"

	return f"+{parsed.country_code} {national[:3]} {'*' * (len(national) - 5)} {national[-2:]}"


# ──────────────────────────────────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────────────────────────────────


def normalize_email(raw):
	"""Validate an email address and reduce it to its canonical form.

	Canonical means: the address part only (a "Name <a@b.com>" string is
	reduced to "a@b.com"), stripped, and casefolded. Deliberately *not*
	Gmail dot-stripping or `+tag` removal: those rules merge addresses that
	their owners consider distinct, and merging two identities is a
	security decision this flow must never make on a heuristic.

	Args:
		raw: the email address as typed.

	Returns:
		The normalized address.

	Raises:
		InvalidEmail: if missing or structurally invalid.
	"""
	from frappe.utils import extract_email_id, validate_email_address

	candidate = (raw or "").strip()
	if not candidate:
		frappe.throw(_("Please enter your email address."), exc=InvalidEmail, title=_("Invalid Email"))

	# validate_email_address splits on commas and would happily accept a
	# list; a signup is exactly one address, so reject anything with a
	# separator before handing it over.
	if "," in candidate or ";" in candidate:
		frappe.throw(
			_("Please enter a single email address."), exc=InvalidEmail, title=_("Invalid Email")
		)

	if not validate_email_address(candidate):
		frappe.throw(
			_("{0} is not a valid email address.").format(candidate),
			exc=InvalidEmail,
			title=_("Invalid Email"),
		)

	address = extract_email_id(candidate)
	if not address:
		frappe.throw(
			_("{0} is not a valid email address.").format(candidate),
			exc=InvalidEmail,
			title=_("Invalid Email"),
		)

	return address.strip().casefold()


def mask_email(email):
	"""Mask an email address for display. `ahmed@example.com` -> `a****@example.com`.

	Args:
		email: an email address, or None.

	Returns:
		A masked display string, or "" if there is nothing to show.
	"""
	if not email or "@" not in email:
		return ""

	local, _sep, domain = email.partition("@")
	if len(local) <= 1:
		return f"*@{domain}"

	return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"


# ──────────────────────────────────────────────────────────────────────────
# Name
# ──────────────────────────────────────────────────────────────────────────


def normalize_name(raw):
	"""Reduce a name to a comparison form. Never stored, never displayed.

	NFKC-normalize, strip Arabic diacritics and tatweel, fold the Arabic
	orthography variants people type interchangeably (see ARABIC_FOLDING),
	casefold, and collapse whitespace.

	Args:
		raw: the name as typed, or None.

	Returns:
		The normalized name, possibly "".
	"""
	if not raw:
		return ""

	value = unicodedata.normalize("NFKC", str(raw))
	value = TASHKEEL_AND_TATWEEL_PATTERN.sub("", value)
	value = "".join(ARABIC_FOLDING.get(char, char) for char in value)
	value = WHITESPACE_PATTERN.sub(" ", value).strip()
	return value.casefold()


def name_tokens(raw):
	"""Return the normalized word list of a name.

	Args:
		raw: the name as typed, or None.

	Returns:
		A list of normalized tokens, possibly empty.
	"""
	normalized = normalize_name(raw)
	return normalized.split() if normalized else []


def names_match(left, right):
	"""Decide whether two names plausibly denote the same person.

	True when the normalized token multisets are identical, or when the
	first tokens agree and at least two tokens are shared - the latter
	covers a record holding "Ahmed Amin Algewily" against a signup of
	"Ahmed Amin Mohamed Algewily", which is the same person writing their
	name at a different length.

	This is deliberately conservative and is never, on its own, permission
	to link anything: a match only *keeps* a phone-based candidate at
	STRONG_MATCH, and a mismatch only ever *downgrades* one. Two unrelated
	people genuinely do share names.

	Args:
		left: first name string.
		right: second name string.

	Returns:
		True if the names plausibly match.
	"""
	left_tokens = name_tokens(left)
	right_tokens = name_tokens(right)

	if not left_tokens or not right_tokens:
		return False

	if sorted(left_tokens) == sorted(right_tokens):
		return True

	if left_tokens[0] != right_tokens[0]:
		return False

	shared = set(left_tokens) & set(right_tokens)
	return len(shared) >= 2


#: Arabic vowel marks and the tatweel stretch character, which are
#: dropped rather than kept - matching contact_enhancements'
#: TASHKEEL_AND_TATWEEL_PATTERN. Every other script's combining marks are
#: kept, because there they carry the vowels rather than decorate them.
TASHKEEL_AND_TATWEEL = re.compile("[\u064b-\u0670\u065f\u0640]")

#: Punctuation that lives *inside* a name component rather than between
#: components. Must agree with contact_enhancements' NAME_PUNCTUATION -
#: it is only used by the fallback, for when that app is not installed.
NAME_PUNCTUATION = frozenset("'\u2019-")


def clean_name(raw):
	"""Whitespace-normalize a name for storage, without altering its content.

	NFKC and whitespace collapsing only - no escaping. The previous signup
	implementation ran `escape_html` before storing, which turned a name
	containing "&" or "'" into "&amp;"/"&#39;" in the database and then
	failed contact_enhancements' "no symbols" rule on the way in. Escaping
	belongs at render time, not in the stored value.

	Args:
		raw: the name as typed, or None.

	Returns:
		The cleaned name, possibly "".
	"""
	if not raw:
		return ""

	value = unicodedata.normalize("NFKC", str(raw))
	return WHITESPACE_PATTERN.sub(" ", value).strip()


def _apply_contact_name_rules(name):
	"""Run the five Arabic first-name rules over a name.

	Delegates to `contact_enhancements`, which owns those rules and, as of
	its own refactor, normalizes rather than rejects - the same conclusion
	this flow reached independently. Calling its function instead of
	re-implementing it means the name signup stores and the name its
	`Contact.validate` hook would produce can never drift apart.

	The fallback below exists only so this app still behaves sensibly if
	that one is not installed; it implements the same five rules.

	Args:
		name: an already whitespace-normalized name.

	Returns:
		The corrected name.
	"""
	try:
		from contact_enhancements.contact_hooks import normalize_arabic_first_name
	except ImportError:
		return _fallback_contact_name_rules(name)

	return normalize_arabic_first_name(name)


def _fallback_contact_name_rules(name):
	"""Stand-in for the whole normalization when contact_enhancements is absent.

	Mirrors the shape of theirs rather than only the Arabic rules, because
	with that app missing this is the only thing standing between a typed
	name and the database: allowed characters first, then letterless
	tokens dropped, then the five rules.

	Args:
		name: an already whitespace-normalized name.

	Returns:
		The corrected name.
	"""
	name = TASHKEEL_AND_TATWEEL.sub("", name)

	# Any letter in any script, whitespace, intra-name punctuation, and
	# combining marks - a mark is not a letter, so spacing it out would
	# split "\u0936\u0930\u094d\u092e\u093e" into pieces and lose its vowels.
	name = "".join(
		char
		if (char.isalpha() or char.isspace() or char in NAME_PUNCTUATION
		    or unicodedata.category(char).startswith("M"))
		else " "
		for char in name
	)

	words = []
	for word in WHITESPACE_PATTERN.sub(" ", name).strip().split(" "):
		if not word or not any(char.isalpha() for char in word):
			# Punctuation belongs inside a component, never as one.
			continue
		if word[0] == ALEF_HAMZA_ABOVE:
			word = ALEF + word[1:]
		if word.endswith(TEH_MARBUTA):
			word = word[:-1] + HEH
		elif word.endswith(YEH):
			word = word[:-1] + ALEF_MAKSURA
		words.append(word)
	return " ".join(words)


def repair_name(raw):
	"""Rewrite a name into the spelling this system stores, never rejecting.

	The rules themselves belong to `contact_enhancements`: which
	characters may appear in a name, and the five Arabic first-name
	corrections. This function normalizes the Unicode form and then hands
	the whole job over - see `_apply_contact_name_rules`.

	It used to filter characters here as well, keeping only letters and
	whitespace. That was a second copy of a rule another app owns, and it
	drifted exactly as duplicated rules do: when that app widened its own
	filter to keep apostrophes, hyphens and combining marks, this stage
	still stripped them first, so the fix never reached signup.
	"O'Brien" was stored as "O Brien" and every mark-based script -
	Devanagari, Tamil, Bengali, Hebrew - came out with its vowels gone.
	There is one filter now, and it is theirs.

	Args:
		raw: the name as typed, or None.

	Returns:
		The repaired name, possibly "" if nothing usable was left.
	"""
	name = clean_name(raw)
	if not name:
		return ""

	name = _apply_contact_name_rules(name)
	return WHITESPACE_PATTERN.sub(" ", name).strip()


def name_components(raw):
	"""Count the name components somebody actually supplied.

	Counted on the name **as typed**, and only tokens carrying a letter.
	Both halves of that matter:

	* Counting the repaired name instead lets punctuation decide the
	  answer. `repair_name` turns anything that is not a letter into a
	  space, so "Anne-Marie Dupont" - two components - becomes three words
	  and passes a rule it should fail, while "O'Brien Sean Murphy" is
	  three components that only look like four. The requirement is about
	  what the person supplied, not about how many gaps survived
	  normalisation.
	* Requiring a letter keeps a stray digit or symbol from counting as a
	  name: "Ahmed 1 Ali Hassan" supplied three names and a typo, not
	  four.

	Args:
		raw: the full name as typed.

	Returns:
		How many name components were given.
	"""
	cleaned = clean_name(raw)
	if not cleaned:
		return 0

	return sum(1 for token in cleaned.split(" ") if any(ch.isalpha() for ch in token))


def validate_full_name(raw, min_parts=3):
	"""Repair a person's full name and return it in storage form.

	The only thing this refuses is a name with too few components. That is
	a **business rule about the customer record**, not a claim about
	language: this shop identifies a person by given name, father's name
	and family name, because that is what its paperwork and its staff
	work from. Plenty of naming systems do not work that way - a Chinese
	name of two characters is complete and correct as it stands - and the
	message says what this shop needs rather than pretending the person
	got their own name wrong.

	It is also the one problem no rewriting can fix: a name that was never
	supplied cannot be invented. Every other irregularity is corrected in
	place by `repair_name`, which is what the Contact's own validate hook
	would do anyway, so the two agree.

	The count is taken from the name as typed - see `name_components` for
	why the repaired form is the wrong thing to count.

	Args:
		raw: the full name as typed.
		min_parts: how many components the business requires.

	Returns:
		The repaired name, safe to store.

	Raises:
		InvalidFullName: if nothing usable is left, or too few components
			were supplied.
	"""
	supplied = name_components(raw)
	name = repair_name(raw)

	if not name:
		frappe.throw(_("Please enter your full name."), exc=InvalidFullName, title=_("Invalid Name"))

	if supplied < min_parts:
		frappe.throw(
			_(
				"We need {0} parts of your name — your first name, your father's name "
				"and your family name. For example: Ahmed Sabry Amin."
			).format(min_parts),
			exc=InvalidFullName,
			title=_("Full Name Required"),
		)

	return name
