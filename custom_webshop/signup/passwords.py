# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""The password rules, in one place.

There used to be two sets. The wizard checked four rules as you typed -
length, letters and numbers, not your own details, not a common password -
and the server checked only zxcvbn's score. They overlapped without
agreeing, so `Zx9$q` failed the guide's "8 characters" and sailed past the
server, and switching `enable_password_policy` off left the server
enforcing nothing at all while four green ticks said otherwise. A client
that validates one thing and a server that validates another is a bug
whichever way round it fails.

So the rules live here, the server enforces them, and the page renders
the guide from this module's own word list - injected into
`window.LOGIN_CONTEXT` by `www/login/index.py` - rather than keeping a
second copy in JavaScript. The browser check stays because a rule you
learn about after pressing the button is a bad rule; it is now a preview
of this one rather than a rival to it.

zxcvbn still runs on top when the site's password policy is on. These
four are the floor, not the ceiling: they are the part that can be
explained to a shopper in one line each.
"""

import re

import frappe
from frappe import _

#: Minimum length. Deliberately modest - this is a shop, and a rule
#: nobody can satisfy is a rule people work around with `Passw0rd!`.
MIN_LENGTH = 8

#: The handful that turn up again and again. Not a dictionary: zxcvbn is
#: the real strength estimator and it runs after these. This list exists
#: so the commonest cases fail with a sentence a shopper understands
#: rather than a score.
COMMON = (
	"password",
	"123456",
	"12345678",
	"qwerty",
	"111111",
	"abc123",
	"letmein",
	"welcome",
	"admin",
	"iloveyou",
	"monkey",
	"dragon",
)

#: A fragment shorter than this is too generic to be worth matching -
#: "ali" inside "validate" is not somebody using their own name.
MIN_PERSONAL_FRAGMENT = 3

#: Digit runs shorter than this collide constantly with ordinary numbers.
MIN_PERSONAL_DIGITS = 4

_LETTER = re.compile(r"[A-Za-z؀-ۿ]")
_DIGIT = re.compile(r"\d")
_NON_DIGIT = re.compile(r"\D")


def personal_parts(doc):
	"""Everything about this person a password should not contain.

	Each *word* of the name separately, not the name as one string:
	somebody called Ahmed Sabry Amin picking `Ahmed123` is using their own
	name, and comparing against the whole name would miss it - which is
	exactly what it used to do.

	Args:
		doc: the Webshop Signup Session document.

	Returns:
		A list of strings.
	"""
	parts = []

	def add(value):
		if value:
			parts.append(str(value))

	email = doc.get("email_normalized") or doc.get("email") or ""
	add(email)
	add(email.split("@")[0])
	add(doc.get("phone_e164"))
	add(doc.get("phone_raw"))
	for word in str(doc.get("full_name") or "").split():
		add(word)
	for word in str(doc.get("company_name") or "").split():
		add(word)

	return parts


def check(password, parts=None):
	"""Run the four rules and say which pass.

	Args:
		password: the candidate.
		parts: the person's own details, from `personal_parts`.

	Returns:
		A dict of rule name -> bool, in the order the guide shows them.
	"""
	password = password or ""
	lower = password.lower()
	digits = _NON_DIGIT.sub("", password)

	return {
		"length": len(password) >= MIN_LENGTH,
		"mix": bool(_LETTER.search(password)) and bool(_DIGIT.search(password)),
		"personal": bool(password) and not _uses_own_details(password, lower, digits, parts or []),
		"common": bool(password) and not any(
			lower == bad or lower.startswith(bad) for bad in COMMON
		),
	}


def _uses_own_details(password, lower, digits, parts):
	"""Whether any of the person's own details show up in the password."""
	for part in parts:
		if len(part) < MIN_PERSONAL_FRAGMENT:
			continue
		if part.lower() in lower:
			return True

		# The number counts however either side wrote it. Containment has
		# to run both ways: the stored form is `+201012345678` and
		# somebody typing `x1012345678` has used their number, but the
		# stored digits are *longer* than the password's, so looking only
		# for the whole stored number inside the password misses it.
		part_digits = _NON_DIGIT.sub("", part)
		if min(len(part_digits), len(digits)) >= MIN_PERSONAL_DIGITS and (
			part_digits in digits or digits in part_digits
		):
			return True
	return False


def validate(password, parts=None):
	"""Refuse a password that breaks any of the four rules.

	One rule per message, and the message says what to change. Frappe's
	own handler renders zxcvbn's raw feedback as English HTML - accurate,
	and not something to put in front of a shopper.

	Args:
		password: the candidate.
		parts: the person's own details, from `personal_parts`.

	Raises:
		frappe.ValidationError: naming the first rule that failed.
	"""
	results = check(password, parts)

	if not results["length"]:
		frappe.throw(
			_("Your password needs at least {0} characters.").format(MIN_LENGTH),
			title=_("Password Too Short"),
		)

	if not results["mix"]:
		frappe.throw(
			_("Use both letters and numbers in your password."),
			title=_("Password Too Simple"),
		)

	if not results["common"]:
		frappe.throw(
			_("That is one of the most commonly used passwords. Pick something else."),
			title=_("Password Too Common"),
		)

	if not results["personal"]:
		frappe.throw(
			_("Your password should not contain your own name, email or phone number."),
			title=_("Password Too Easy To Guess"),
		)
