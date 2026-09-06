# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Turning a verified signup into real records, all at once or not at all.

This is the only module in the app that creates a Customer, a Contact, a
Portal User row or a website account. Everything before it is reversible
by doing nothing; everything here is guarded by a savepoint so a late
failure leaves no half-built account behind.

Three defences against two people signing up on one phone at the same
moment, in increasing order of reliability:

1. The matching engine is re-run *inside* the critical section, so a
   decision made a minute ago is re-checked against the database as it is
   now, immediately before anything is written.
2. A Redis lock keyed on the verified phone number serialises the section.
   Best-effort: if Redis is unreachable the flow continues, because it is
   an optimisation for producing a clean error, not the guarantee.
3. The unique indexes on Webshop Account Identity - `user`, `phone_e164`,
   `email_normalized` - are the guarantee. They are checked by the
   database itself, at the end of the transaction, and cannot be raced.
"""

import contextlib

import frappe
from frappe import _
from frappe.utils import now_datetime

from custom_webshop.signup import conflicts, matching, session, settings
from custom_webshop.signup.identity import region_for_e164, try_to_e164
from custom_webshop.signup.telemetry import log_event

LINK_EXISTING = "LINK_EXISTING"
CREATE_NEW = "CREATE_NEW"
CREATE_NEW_WITH_CONFLICT = "CREATE_NEW_WITH_CONFLICT"
RECOVER_EXISTING = "RECOVER_EXISTING"

LOCK_TIMEOUT_SECONDS = 30
LOCK_WAIT_SECONDS = 15


class SignupRaceLost(frappe.ValidationError):
	http_status_code = 409


@contextlib.contextmanager
def _desk_messages_kept_off_the_shopfront():
	"""Stop other apps' Desk warnings reaching a shopper mid-signup.

	Creating an account saves Contacts and Customers, and every app with a
	hook on those gets to `frappe.msgprint` while it happens. Those
	messages are written for staff looking at a form - contact_enhancements'
	"check before saving a duplicate" is a good example, and a signup that
	links to an existing record triggers it twice - and Frappe hands the
	whole `message_log` back to whoever made the request. On this endpoint
	that is a customer, who is shown an internal note about records they
	cannot see and cannot act on.

	Muted here rather than gated in each app that might emit one: this is
	*our* customer-facing endpoint, so it is our business which of another
	app's audiences it speaks to, and a rule written here covers hooks
	nobody has added yet.

	`frappe.throw` is unaffected - `msgprint` raises before it checks this
	flag - so real errors still stop the request and still reach the
	person. Everything this flow means a customer to read travels in the
	envelope, never in the message log.

	Yields:
		None.
	"""
	previous = frappe.flags.mute_messages
	frappe.flags.mute_messages = True
	try:
		yield
	finally:
		frappe.flags.mute_messages = previous


@contextlib.contextmanager
def phone_lock(phone_e164):
	"""Serialise the finalise section for one phone number.

	Degrades to a no-op if Redis is unavailable rather than refusing to
	finish an otherwise valid signup: correctness here rests on the unique
	indexes, and this lock exists to turn a losing race into a tidy
	message instead of a constraint violation.

	Args:
		phone_e164: the verified number in canonical form.
	"""
	lock = None
	acquired = False

	try:
		lock = frappe.cache.lock(
			f"custom_webshop:signup:{phone_e164}",
			timeout=LOCK_TIMEOUT_SECONDS,
			blocking_timeout=LOCK_WAIT_SECONDS,
		)
		acquired = lock.acquire()
	except Exception:
		log_event("signup_lock_unavailable", phone_locked=bool(phone_e164))
		lock = None

	try:
		yield
	finally:
		if lock is not None and acquired:
			with contextlib.suppress(Exception):
				lock.release()


def finalize(doc, password):
	"""Create or link everything for a verified signup, atomically.

	A signup that turns out to be blocked - because somebody claimed the
	same phone or email while this one was in progress - is *returned* as
	blocked rather than raised. Frappe rolls the whole request transaction
	back on an unhandled exception, so throwing here would discard the
	very block record and conflict that staff need to see. Returning lets
	the request commit them and hand the browser a proper BLOCKED state.

	Args:
		doc: the Webshop Signup Session document, in READY.
		password: the chosen password, used immediately and never stored
			by this app.

	Returns:
		A dict. On success: `blocked` False plus the created user,
		customer, contact and identity names. On a lost race: `blocked`
		True and the classification that caused it.

	Raises:
		session.InvalidSignupState: if the session is not genuinely ready.
	"""
	with phone_lock(doc.phone_e164), _desk_messages_kept_off_the_shopfront():
		_assert_ready(doc)

		# Rule 13: never trust a decision taken before now. Re-derive it
		# against the database as it is at this instant.
		verdict = matching.classify(doc)

		if verdict["result"] in matching.BLOCKING_RESULTS:
			return _record_block(doc, verdict["result"], verdict["reason"], verdict["candidates"])

		# Recovering an account creates nothing, so it leaves before any
		# of the machinery below. It is still re-derived first, like every
		# other decision: an approval given a minute ago is not permission
		# to set a password on an account that no longer answers to both
		# of these channels.
		if doc.resolution == RECOVER_EXISTING or verdict["result"] == matching.OWN_ACCOUNT:
			if doc.resolution != RECOVER_EXISTING or verdict["result"] != matching.OWN_ACCOUNT:
				return _record_block(
					doc,
					verdict["result"],
					"Recovery was approved for a different situation than the one that holds now.",
					verdict["candidates"],
				)
			return _recover_existing(doc, verdict, password)

		savepoint = "custom_webshop_finalize"
		frappe.db.savepoint(savepoint)
		try:
			return _finalize_locked(doc, verdict, password)
		except (SignupRaceLost, frappe.UniqueValidationError, frappe.DuplicateEntryError):
			# A uniqueness constraint fired somewhere in the section:
			# another signup claimed part of this identity between the
			# check above and the insert. Which constraint hardly matters
			# - `Webshop Account Identity` guards phone, email and user,
			# and Frappe's own `tabUser.mobile_no` unique index guards the
			# number independently - they all mean the same thing. Undo
			# this attempt, then record the block on the clean
			# transaction.
			frappe.db.rollback(save_point=savepoint)
			return _record_block(
				doc,
				matching.PHONE_ACCOUNT_EXISTS,
				"Lost a concurrent signup race for this phone or email.",
				verdict["candidates"],
			)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			raise


def _record_withheld_phone(doc, contact, customer):
	"""Queue the pair of Contacts that now disagree about one number.

	Reached whenever the verified number could not be written onto this
	signup's Contact because another one already holds it - most often
	after somebody was shown a recognition card and said "no, that is not
	me". Two records now claim the same person by phone: the one that has
	the number, and the one whose owner just proved they control it.

	Only staff can tell which is right, so both are named here rather
	than guessed between. The account is finished either way - a person
	who says no still gets a working login, which is the whole point of
	withholding the row instead of failing the insert.

	Args:
		doc: the Webshop Signup Session document.
		contact: the Contact this signup wrote, without the number.
		customer: the Customer it belongs to.

	Returns:
		The conflict's name, or None if it could not be raised.
	"""
	holders = ", ".join(_phone_holders(doc.phone_e164, exclude=contact.name)) or "another contact"
	return conflicts.open_conflict(
		doc,
		"PHONE_ALREADY_ASSOCIATED",
		(
			"Verified number {0} is already on {1}, so it was left off the new "
			"contact {2} ({3}) and recorded there as pending. Both records claim "
			"the same person by phone; staff decide which survives."
		).format(doc.phone_e164, holders, contact.name, customer),
		created_customer=customer,
	).name


def _phone_holders(phone_e164, exclude=None):
	"""The Contacts already carrying a number, for a staff-facing note."""
	try:
		from contact_enhancements.api.contact_dedupe import find_contacts_by_phone
	except ImportError:
		return []

	return find_contacts_by_phone(phone_e164, exclude=exclude)


def _recover_existing(doc, verdict, password):
	"""Sign somebody back into the account they just proved they own.

	Reached only from OWN_ACCOUNT: the email and the phone on this signup
	both belong to one existing, enabled account, and both were verified
	in this session. That is more proof of ownership than a password reset
	asks for, which needs the mailbox alone.

	Nothing is created either way - no second Customer, no second Contact -
	because nothing is missing but a way in. The password they chose is
	set on the account on both answers: somebody who has just re-proved
	both channels is here because they could not get in, and sending them
	away still unable to would be the same dead end in a politer voice.

	What differs is only what it means about the name:

	* **Accepted.** They recognised the record. Nothing about it is
	  questioned.
	* **Rejected.** They own both channels but say the name on it is not
	  theirs, so the disagreement goes to staff as a PROFILE_DISCREPANCY.
	  The one thing that must not happen here is this app deciding on its
	  own to rewrite a Contact and a Customer to a name typed at a signup
	  form.

	The name they typed is never written to any record on either path.

	Args:
		doc: the Webshop Signup Session document.
		verdict: the freshly computed matching result.
		password: the chosen password.

	Returns:
		The same dict shape a created account returns, plus `recovered`.
	"""
	user = matching.account_for_email(doc.email_normalized)
	customer = verdict["candidate"]
	identity = frappe.db.get_value(
		"Webshop Account Identity", {"user": user}, ["name", "contact"], as_dict=True
	) or frappe._dict()

	from frappe.utils.password import update_password as set_password

	set_password(user, password)

	# Renaming is asked for two ways: outright ("this is not my data") or
	# by choosing their own spelling on the second card. Both mean the same
	# thing about the records - the account follows them, the Contact and
	# the Customer wait for a person.
	rename = bool(doc.rename_account)
	conflict = None
	if rename:
		# The account belongs to a person, so it takes the person's name.
		# A company signup's business name belongs on the Customer and
		# nowhere near a User - `submitted_party_name` returns the
		# business for one, which renamed somebody's login to their
		# employer.
		rename_account_only(user, doc.full_name)
		conflict = _record_name_dispute(doc, user, customer, identity.get("contact"))

	# Somebody coming back to their own account can still have said they
	# are a business against a record entered as an individual, or the
	# other way round. The check used to run only where a signup *linked*
	# to a record, so on this path the disagreement was never recorded -
	# and with the queue asking each question in its own section, a
	# problem that is never raised has no section and therefore no
	# buttons. That is what left a case half-answerable.
	_note_account_type_mismatch(doc)

	doc.update(
		{
			"resolution": RECOVER_EXISTING,
			"created_user": user,
			"created_customer": customer,
			"created_contact": identity.get("contact"),
			"identity_record": identity.get("name"),
		}
	)
	session.transition(doc, session.COMPLETED, save=True)
	log_event("signup_recovered", doc, user=user, customer=customer, renamed=rename)

	return {
		"blocked": False,
		"recovered": True,
		"disputed": rename,
		"user": user,
		"customer": customer,
		"contact": identity.get("contact"),
		"identity": identity.get("name"),
		"conflict": conflict,
		"resolution": RECOVER_EXISTING,
	}


def _record_name_claim(doc, user, customer, contact, submitted):
	"""Queue the name somebody asked their account to carry.

	The account already carries it by the time this runs - that part is
	theirs to decide. What is queued is the rest: whether the Contact and
	the Customer should follow. Those are business records with order
	history behind them, and the person asking is not necessarily the
	person who filled them in.

	Args:
		doc: the Webshop Signup Session document.
		user: the account, already renamed.
		customer: the Customer it is linked to, or None.
		contact: the Contact it is attached to, or None.
		submitted: the name the account now carries.

	Returns:
		The conflict's name.
	"""
	stored = (
		frappe.db.get_value("Contact", contact, "full_name")
		or (customer and frappe.db.get_value("Customer", customer, "customer_name"))
		or ""
	)
	return conflicts.open_conflict(
		doc,
		"PROFILE_DISCREPANCY",
		(
			"Asked for the account to carry {0!r}; the contact and customer still say "
			"{1!r}. The account {2} has been renamed and nothing else has. Apply the "
			"submitted name from this conflict if it is the right one."
		).format(submitted, stored, user),
		created_user=user,
		created_customer=customer,
	).name


def _record_name_dispute(doc, user, customer, contact):
	"""Queue the name the person says is theirs, for staff to apply.

	Not applied here, and that is the whole point. A name typed into a
	signup form is a claim, not a correction: the record it disagrees with
	may be a company account, a family member's, or simply right. Staff
	see both names side by side and one click puts the submitted one on
	the Contact and the Customer if that is what it turns out to be.

	Args:
		doc: the Webshop Signup Session document.
		user: the account being signed into.
		customer: its Customer, or None.
		contact: its Contact, or None.

	Returns:
		The conflict's name.
	"""
	existing = (
		frappe.db.get_value("Contact", contact, "full_name")
		or (customer and frappe.db.get_value("Customer", customer, "customer_name"))
		or frappe.db.get_value("User", user, "full_name")
	)
	return conflicts.open_conflict(
		doc,
		"PROFILE_DISCREPANCY",
		(
			"Signed in to {0} after verifying both channels, but said the details on "
			"it are not theirs. They gave the name {1!r}; the records say {2!r}. "
			"Nothing was changed - check the address and phone too, and apply the "
			"submitted name from this conflict if it is the right one."
		).format(user, doc.full_name, existing),
		created_user=user,
		created_customer=customer,
	).name



def _record_block(doc, result, reason, candidates=None):
	"""Send a signup to BLOCKED and queue it for staff, without raising.

	Args:
		doc: the Webshop Signup Session document.
		result: the classification that caused the block.
		reason: staff-facing explanation.
		candidates: the audit list of candidates considered.

	Returns:
		A dict marking the signup blocked.
	"""
	conflict_type = conflicts.type_for_result(result)
	if conflict_type:
		conflicts.open_conflict(doc, conflict_type, reason, candidates)
	session.block(doc, result, reason)
	log_event("signup_blocked_at_finalize", doc, reason=result)
	return {"blocked": True, "result": result}


def _finalize_locked(doc, verdict, password):
	"""Do the work of finalize, inside the lock and the savepoint.

	Args:
		doc: the Webshop Signup Session document.
		verdict: the freshly computed matching result.
		password: the chosen password.

	Returns:
		A dict of created record names.
	"""
	resolution, candidate, conflict = _reconcile(doc, verdict)

	contact, phone_withheld = _resolve_contact(
		doc, candidate if resolution == LINK_EXISTING else None
	)
	customer = candidate if resolution == LINK_EXISTING else _create_customer(doc, contact)

	if resolution != LINK_EXISTING:
		_link_contact_to_customer(contact, customer)

	# One finalise can raise more than one - a name mismatch queued at
	# `resolve` and, separately, a number that turned out to be on
	# somebody else's Contact. They are different problems with different
	# answers, so both are kept and both learn what the signup produced.
	opened = [conflict] if conflict else []
	if phone_withheld:
		opened.append(_record_withheld_phone(doc, contact, customer))

	user = _create_user(doc, password, contact, phone_withheld=phone_withheld)

	# They asked for their account to carry the name they typed rather than
	# the one already on the record. The account takes it; the Contact and
	# the Customer do not, until somebody in the Desk says so.
	if doc.rename_account:
		# The person's own name, for the reason in `_recover_existing`.
		rename_account_only(user.name, doc.full_name)
		opened.append(
			_record_name_claim(doc, user.name, customer, contact.name, doc.full_name)
		)
	_attach_user_to_contact(contact, user)
	_ensure_portal_user(customer, user)
	identity = _create_identity(doc, user, customer, contact, linked_existing=resolution == LINK_EXISTING)

	doc.update(
		{
			"resolution": resolution,
			"created_user": user.name,
			"created_customer": customer,
			"created_contact": contact.name,
			"identity_record": identity.name,
		}
	)
	session.transition(doc, session.COMPLETED, save=True)

	for name in opened:
		conflicts.attach_outcome(name, user.name, customer)

	log_event(
		"signup_completed",
		doc,
		resolution=resolution,
		linked_existing=resolution == LINK_EXISTING,
		conflict=conflict,
		conflicts=opened,
	)

	return {
		"blocked": False,
		"user": user.name,
		"customer": customer,
		"contact": contact.name,
		"identity": identity.name,
		"resolution": resolution,
	}


def _assert_ready(doc):
	"""Refuse to finalise anything that has not actually been verified.

	The state machine already forbids reaching READY without both
	channels proven; this re-asserts it from the row's own fields, so a
	state value corrupted by any means still cannot produce an account.

	Args:
		doc: the Webshop Signup Session document.
	"""
	if doc.status != session.READY:
		frappe.throw(
			_("This signup is not ready to be completed."), exc=session.InvalidSignupState
		)

	if not doc.email_verified or not doc.phone_verified:
		frappe.throw(
			_("Both your email and phone must be verified first."),
			exc=session.InvalidSignupState,
		)

	if not doc.email_normalized or not doc.phone_e164:
		frappe.throw(_("This signup is incomplete. Please start again."), exc=session.InvalidSignupState)


def _note_account_type_mismatch(doc):
	"""Queue a link where the signup and the record disagree on who this is.

	One rule for both directions, and for Partnership, which the signup
	form cannot even express: whenever `account_type` and `customer_type`
	differ, somebody looks. Neither direction is treated as an error - a
	person really is often the contact on a company account, and somebody
	trading as a business may have been entered as an individual long ago
	- so the link stands and nothing on the customer is touched.

	Raised on the type alone, independent of any name conflict. The names
	can agree perfectly while the types do not, and that case would
	otherwise go through with nobody told.

	Args:
		doc: the Webshop Signup Session document.

	Returns:
		The conflict's name, or None when the two agree.
	"""
	if not doc.candidate_customer:
		return None

	stored = frappe.db.get_value("Customer", doc.candidate_customer, "customer_type")
	if not stored or stored == doc.account_type:
		return None

	claimed = (
		" They gave the business name {0!r}.".format(doc.company_name)
		if doc.account_type == "Company" and doc.company_name
		else ""
	)
	return conflicts.open_conflict(
		doc,
		"ACCOUNT_TYPE_MISMATCH",
		(
			"Signed up as {0}; {1} is {2} {3} record named {4!r}.{5} The account was "
			"linked and nothing on the customer was changed."
		).format(
			doc.account_type,
			doc.candidate_customer,
			"an" if stored[0].upper() in "AEIOU" else "a",
			stored,
			frappe.db.get_value("Customer", doc.candidate_customer, "customer_name"),
			claimed,
		),
		created_customer=doc.candidate_customer,
	).name


def _note_disabled_record(doc):
	"""Queue a link made to a Customer somebody had switched off.

	`matching.classify` refuses to link a disabled record automatically
	and says staff review is required - but that verdict only ever
	reached the person as a question. If they answered yes, the link went
	ahead and the reason for asking was forgotten, so an account could
	attach to a record the business had deliberately turned off with
	nobody told.

	The link itself is left alone. On this path both the email *and* the
	phone matched the record, which is as much proof of ownership as the
	flow ever gets, and turning a real owner away over a flag they cannot
	see would be worse than linking. What was missing is that somebody
	finds out: they cannot place an order against a disabled Customer, so
	the account is useless until a person decides whether the disabling
	still applies.

	Args:
		doc: the Webshop Signup Session document.

	Returns:
		The conflict's name, or None when the record is not disabled.
	"""
	if not doc.candidate_customer:
		return None

	if not frappe.db.get_value("Customer", doc.candidate_customer, "disabled"):
		return None

	return conflicts.open_conflict(
		doc,
		"MATCHED_CUSTOMER_DISABLED",
		(
			"Linked to {0} on the person's own confirmation, but that customer is "
			"disabled. They proved both channels on it, so the account was linked "
			"rather than refused - but no order can be placed against it until "
			"somebody decides whether the disabling still applies."
		).format(doc.candidate_customer),
		created_customer=doc.candidate_customer,
	).name


def _reconcile(doc, verdict):
	"""Check the stored decision against a freshly computed one.

	The person's yes/no was recorded against the candidate the engine
	found earlier. If the database has changed since - somebody else
	linked that Customer, a second matching record appeared - the stored
	resolution is no longer safe to act on and is downgraded here rather
	than honoured.

	Args:
		doc: the Webshop Signup Session document.
		verdict: a fresh matching.classify result.

	Returns:
		A (resolution, candidate, conflict_name) tuple.
	"""
	result = verdict["result"]
	stored = doc.resolution
	conflict = None

	if stored == LINK_EXISTING:
		# Only honour a link if the re-run still says the same thing about
		# the same Customer. Anything else becomes a conflict.
		if result in matching.CONFIRMABLE_RESULTS and verdict["candidate"] == doc.candidate_customer:
			# A disabled record is the stronger reason to involve
			# somebody, so it wins when both would apply.
			return (
				LINK_EXISTING,
				doc.candidate_customer,
				_note_disabled_record(doc) or _note_account_type_mismatch(doc),
			)

		conflict_type = conflicts.type_for_result(result)
		if conflict_type:
			conflict = conflicts.open_conflict(
				doc,
				conflict_type,
				"Link was approved for {0} but re-checking found {1}; created a new customer instead.".format(
					doc.candidate_customer, result
				),
				verdict["candidates"],
			).name
		return CREATE_NEW_WITH_CONFLICT, None, conflict

	if stored == CREATE_NEW_WITH_CONFLICT:
		conflict = frappe.db.get_value(
			"Webshop Identity Conflict",
			{"signup_session": doc.name, "status": ["in", ("Open", "In Review")]},
			"name",
		)
		return CREATE_NEW_WITH_CONFLICT, None, conflict

	# No stored decision, or a plain CREATE_NEW: if the re-run turned up
	# something that needs review, record it before proceeding.
	if result in matching.CONFLICT_RESULTS:
		conflict_type = conflicts.type_for_result(result)
		if conflict_type:
			conflict = conflicts.open_conflict(
				doc, conflict_type, verdict["reason"], verdict["candidates"]
			).name
		return CREATE_NEW_WITH_CONFLICT, None, conflict

	return CREATE_NEW, None, None


# ──────────────────────────────────────────────────────────────────────────
# Record creation
# ──────────────────────────────────────────────────────────────────────────


def _resolve_contact(doc, existing_customer):
	"""Return the Contact this account will use, creating one if needed.

	For a link to an existing Customer this prefers that Customer's own
	primary Contact and only *adds* to it - a verified email or phone it
	does not yet carry. It never rewrites the existing `first_name`: the
	person in front of us has proved they control a phone number, not that
	the name on a years-old business record is wrong.

	If that Contact already belongs to a different website account, a
	fresh Contact is created against the same Customer instead. A Customer
	legitimately has several contacts, and quietly re-pointing one at a
	new user would be exactly the silent overwrite this flow exists to
	avoid.

	Args:
		doc: the Webshop Signup Session document.
		existing_customer: the Customer being linked to, or None.

	Returns:
		A (contact, phone_withheld) tuple. The Contact is saved;
		`phone_withheld` is True when the verified number could not be
		written onto it because another Contact holds it - see
		`_add_verified_details`.
	"""
	if existing_customer:
		primary = frappe.db.get_value("Customer", existing_customer, "customer_primary_contact")
		if primary:
			contact = frappe.get_doc("Contact", primary)
			claimed_by_someone_else = contact.user and contact.user != doc.email_normalized
			if not claimed_by_someone_else:
				# The business name they typed is written nowhere else on
				# this path: `build()` below sets it, but a link reuses
				# the record's own Contact and never reaches it, so the
				# claim was simply dropped. Only filled when empty - what
				# the record already says about their employer is not a
				# signup form's to overwrite.
				if (
					doc.account_type == "Company"
					and doc.company_name
					and not contact.company_name
				):
					contact.company_name = doc.company_name
				return _persist_contact(contact, doc)

	def build():
		contact = frappe.new_doc("Contact")
		contact.first_name = doc.full_name
		contact.is_primary_contact = 1
		if doc.account_type == "Company" and doc.company_name:
			contact.company_name = doc.company_name
		if existing_customer:
			contact.append("links", {"link_doctype": "Customer", "link_name": existing_customer})
		return contact

	return _persist_contact(build(), doc, rebuild=build)


def _persist_contact(contact, doc, rebuild=None):
	"""Write the verified details onto a Contact and save it.

	The phone check in `_add_verified_details` is a read followed by a
	write, and between the two another request can claim the same number -
	so the check is not the guarantee. contact_enhancements is, twice
	over: `enforce_unique_mobile_number` throws on validate, and a unique
	index on a generated column refuses the row underneath it. This is
	where that is admitted. A save that fails while carrying the number is
	rolled back to a savepoint and made once more without it, which is the
	outcome the check would have produced had it seen the row.

	Only the uniqueness failures are caught. contact_enhancements'
	`enforce_unique_mobile_number` raises `frappe.UniqueValidationError`
	specifically - a documented contract of that function - so a name it
	rejects, or a missing mandatory field, surfaces as itself instead of
	being quietly turned into a withheld phone. This used to catch
	`ValidationError` wholesale, because that rule threw a bare one and
	got there before the database's own index; narrowing it back was the
	point of tagging it.

	A savepoint of its own is needed because the failed write has poisoned
	nothing else - the enclosing finalise savepoint covers the whole
	account, and rolling back to *that* would discard work this is trying
	to preserve.

	Args:
		contact: the Contact document to write to.
		doc: the Webshop Signup Session document.
		rebuild: for a new Contact, a callable returning a fresh unsaved
			copy. A document Frappe has failed to insert cannot be
			re-inserted, so the retry needs a new one. Omitted when
			extending a Contact that already exists, where a plain reload
			does the same job.

	Returns:
		A (contact, phone_withheld) tuple.
	"""
	savepoint = "custom_webshop_contact"
	frappe.db.savepoint(savepoint)

	for attempt in (1, 2):
		withheld = _add_verified_details(contact, doc, withhold_phone=attempt == 2)
		contact.flags.ignore_permissions = True
		try:
			# `save` inserts an unsaved document and updates a saved one,
			# so one call covers both the new Contact and the existing one
			# being extended.
			contact.save(ignore_permissions=True)
			return contact, withheld
		except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
			if attempt == 2 or withheld:
				raise
			frappe.db.rollback(save_point=savepoint)
			contact = rebuild() if rebuild else frappe.get_doc("Contact", contact.name)


def _phone_held_elsewhere(phone_e164, exclude=None):
	"""Whether another Contact already carries this number.

	Asked through contact_enhancements' own
	`contact_dedupe.find_contacts_by_phone`, so the question is answered
	by the same query that app's uniqueness rule asks - one place to be
	right, and no second implementation to drift from it.

	Imported inside the function and guarded, because this app does not
	depend on that one. Without it there is no unique index either, and
	the honest answer is "no": a second row is then legal and appending
	the number is the better behaviour.

	Args:
		phone_e164: the verified number.
		exclude: a Contact name to ignore - the one being written to,
			which may legitimately hold the number already.

	Returns:
		True when some other Contact holds it.
	"""
	try:
		from contact_enhancements.api.contact_dedupe import find_contacts_by_phone
	except ImportError:
		return False

	return bool(find_contacts_by_phone(phone_e164, exclude=exclude))


def _add_verified_details(contact, doc, withhold_phone=False):
	"""Add the verified email and phone to a Contact, additively.

	The phone is not always addable. contact_enhancements enforces one
	mobile number per Contact site-wide, through a validate hook and a
	unique index on a generated column - so when somebody looks at a
	recognition card and says "no, that is not me", the new Contact this
	app then creates cannot carry the number that surfaced the match.
	Appending it anyway is what used to make that answer impossible: the
	insert threw, the request rolled back, and a person who had proved
	both channels got nothing at all for saying no.

	So the number is left off, and recorded on the Contact in
	`custom_pending_phone_e164` - this app's own field - so staff can see
	which number the account was actually verified against. Nothing is
	lost by it: `Webshop Account Identity.phone_e164` is the record that
	matters and it is uniquely indexed in its own right.

	Args:
		contact: the Contact document being built or extended.
		doc: the Webshop Signup Session document.
		withhold_phone: skip the phone unconditionally, used by the retry
			in `_persist_contact` after the index has already refused it.

	Returns:
		True when the verified number was withheld.
	"""
	if not any(row.email_id == doc.email_normalized for row in contact.get("email_ids", [])):
		contact.append(
			"email_ids",
			{"email_id": doc.email_normalized, "is_primary": 0 if contact.get("email_ids") else 1},
		)

	# Compared canonically rather than literally, and under the region the
	# verified number itself belongs to rather than the shop's default. An
	# existing Contact being extended may hold this very number in the
	# local form written before either app stored E.164; matching on the
	# raw string would miss it and give one person two rows for one phone.
	# The region is not in doubt - it is the region of the number this
	# signup just verified - and defaulting instead would fail to
	# recognise a foreign number left in local form, since `0512345678`
	# read as Egyptian canonicalises to nothing at all.
	region = region_for_e164(doc.phone_e164)
	if any(try_to_e164(row.phone, region) == doc.phone_e164 for row in contact.get("phone_nos", [])):
		return False

	if withhold_phone or _phone_held_elsewhere(doc.phone_e164, exclude=contact.get("name")):
		contact.custom_pending_phone_e164 = doc.phone_e164
		return True

	contact.append(
		"phone_nos",
		{
			"phone": doc.phone_e164,
			"is_primary_mobile_no": 0 if contact.get("phone_nos") else 1,
		},
	)
	return False


def _create_customer(doc, contact):
	"""Create the Customer for a signup that matched nothing linkable.

	`customer_primary_contact` is set before insert for two reasons: it is
	mandatory (contact_enhancements makes it so), and setting it stops
	ERPNext's own `Customer.create_primary_contact()` from building a
	second Contact, since its guard is `if not
	self.customer_primary_contact`.

	`customer_primary_address` is equally mandatory but a signup has no
	address yet, so this is the one deferred field - `ignore_mandatory`
	covers it and a conflict is raised so staff know the profile is
	incomplete rather than discovering an unsaveable record later.

	Args:
		doc: the Webshop Signup Session document.
		contact: the Contact document to use as primary contact.

	Returns:
		The new Customer's name.
	"""
	customer = frappe.new_doc("Customer")
	customer.update(
		{
			"customer_name": matching.submitted_party_name(doc),
			"customer_type": "Company" if doc.account_type == "Company" else "Individual",
			"customer_group": settings.get_customer_group(),
			"territory": settings.get_territory(),
			"customer_primary_contact": contact.name,
		}
	)
	customer.flags.ignore_mandatory = True
	customer.flags.ignore_permissions = True
	customer.insert(ignore_permissions=True)

	_assert_identity_not_overwritten(doc, customer)

	if not customer.get("customer_primary_address"):
		# Every signup-created Customer lacks one - a signup collects no
		# address; it is captured at first checkout - so this is a logged
		# fact, not a staff decision. It used to open a queue conflict
		# ("INCOMPLETE_PROFILE"), which meant it fired on effectively every
		# signup and taught staff nothing they could act on; the first
		# order fills the field in regardless.
		log_event("signup_customer_missing_address", doc, customer=customer.name)

	return customer.name


def _assert_identity_not_overwritten(doc, customer):
	"""Notice when another app rewrote the Customer we just created.

	`contact_enhancements.customer_hooks.sync_customer_from_primary_contact`
	prefills a Customer's identity fields from a Lead whenever its primary
	Contact happens to be linked to one. That is correct behaviour for its
	own flows, but it means a signup can end up with a Customer named
	after a Lead rather than after the person who just signed up. Rather
	than fight it - it is another app's rule and this one only owns
	custom_webshop - the divergence is recorded for staff.

	Args:
		doc: the Webshop Signup Session document.
		customer: the freshly inserted Customer document.
	"""
	expected = matching.submitted_party_name(doc)
	actual = frappe.db.get_value("Customer", customer.name, "customer_name")

	# ERPNext suffixes " - N" on a name collision, which is expected and
	# not a divergence.
	if actual and actual != expected and not actual.startswith(f"{expected} - "):
		# Logged, not queued: the only remedy is "decide which source is
		# right and correct the record by hand" - a note about a different
		# app's hook, not a decision staff can make from this form.
		log_event(
			"signup_lead_prefill_diverged",
			doc,
			customer=customer.name,
			expected=expected,
			actual=actual,
		)


def _link_contact_to_customer(contact, customer):
	"""Ensure the Dynamic Link from Contact to Customer exists.

	contact_enhancements' own `link_primary_contact` on_update hook
	normally creates this the moment the Customer is saved. This is the
	idempotent backstop for a site where that app is not installed.

	Args:
		contact: the Contact document.
		customer: the Customer's name.
	"""
	contact.reload()
	if contact.has_link("Customer", customer):
		return

	contact.append("links", {"link_doctype": "Customer", "link_name": customer})
	contact.flags.ignore_permissions = True
	contact.save(ignore_permissions=True)


def _create_user(doc, password, contact, phone_withheld=False):
	"""Create the website account.

	The password goes straight into Frappe's own `new_password` handling,
	which hashes it through passlib. This app never stores, caches, or
	logs it - which is why it is collected on the final step rather than
	held for the length of the signup.

	**The account is named after the Contact it attaches to, not after the
	name that was typed.** That looks like a detail and is the opposite:
	Frappe's `User.on_update` enqueues `create_contact`, which finds the
	Contact carrying this account's email - the existing one, when a link
	was just made to it - and does

	    contact.first_name = user.first_name
	    contact.last_name = user.last_name
	    contact.gender = user.gender

	unconditionally. contact_enhancements then propagates that onto the
	linked Customer. So a stranger who proves a phone number and answers
	"yes, that is me" would rename somebody's Contact *and* their Customer
	to whatever they typed - the exact silent overwrite this whole flow
	exists to avoid - and an empty `last_name` or `gender` on the new
	account would blank the existing ones outright.

	It cannot be repaired afterwards. That job is enqueued with
	`enqueue_after_commit=True`, so in production it runs in a worker
	after this request has committed, and anything written back here would
	simply be overwritten again later. The only fix that holds is to make
	the overwrite a no-op, which is what taking the name from the Contact
	does.

	For a new account this changes nothing - that Contact was just built
	from `doc.full_name`. For a linked one the person keeps the name the
	record already had, and the name they submitted is preserved in the
	`PROFILE_DISCREPANCY` conflict for staff to settle.

	`mobile_no` is left empty when the Contact could not take the number,
	and that is not tidiness. Frappe's `User.on_update` calls
	`create_contact`, which looks the Contact up by the account's email -
	finding the one this signup just wrote - and calls `add_phone` with
	`mobile_no` on it. Setting the field would therefore append the very
	row `_add_verified_details` withheld, from inside somebody else's
	hook, and contact_enhancements' unique index would refuse the save and
	roll the whole signup back. Withholding it here is what makes the
	withholding there hold.

	The number is not lost by it: `Webshop Account Identity.phone_e164`
	is the record that vouches for it, `Contact.custom_pending_phone_e164`
	is where staff see it, and both survive the merge that resolves the
	conflict.

	Args:
		doc: the Webshop Signup Session document.
		password: the chosen password.
		contact: the Contact this account will be attached to.
		phone_withheld: True when the verified number is already held by
			another Contact.

	Returns:
		The inserted User document.
	"""
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": doc.email_normalized,
			"first_name": contact.first_name or doc.full_name,
			"last_name": contact.last_name,
			"gender": contact.gender,
			"enabled": 1,
			"new_password": password,
			"user_type": "Website User",
			"mobile_no": None if phone_withheld else doc.phone_e164,
		}
	)

	# The account has to point back at its Contact, not only be pointed at
	# from it: `Contact.user` alone leaves the Desk's own User form showing
	# an empty "User Primary Contact", the field contact_enhancements reads
	# to keep the two in step. Setting it here lets that app's
	# `link_user_contact` hook build the Dynamic Link on the way through.
	#
	# It is set before the insert again. For a while it was not: that hook
	# used to build the link by appending to the Contact and *saving* it,
	# from inside this User insert, while the finalise transaction already
	# held locks on that same Contact - and every deadlock this suite
	# produced ran through that re-entrant save. It inserts the child row
	# directly now, so the nested save is gone and there is nothing left
	# to route around.
	if _has_field("User", "user_primary_contact"):
		user.user_primary_contact = contact.name

	user.flags.ignore_permissions = True
	user.flags.no_welcome_mail = True
	user.insert(ignore_permissions=True)

	default_role = frappe.get_single_value("Portal Settings", "default_role")
	if default_role:
		user.add_roles(default_role)

	return user


def rename_account_only(user, name):
	"""Put a name on the website account and on nothing else.

	Written with `db.set_value` rather than by saving the User, and that
	is the whole trick. Saving a User fires `on_update`, which enqueues
	Frappe's `create_contact`; that finds the Contact carrying this
	account's email - the existing one, after a link - and assigns
	`first_name`, `last_name` and `gender` from the User outright.
	contact_enhancements then propagates the name onto the Customer. So
	renaming the account the ordinary way renames somebody's business
	records with it, which is exactly what this must not do.

	A direct column write fires no hooks, so the account carries the name
	the person asked for and the Contact and Customer keep theirs until a
	person in the Desk decides otherwise.

	`full_name` is set here too because Frappe derives it in `validate`,
	which a direct write skips - leaving it stale everywhere the Desk
	shows an account by its full name.

	Args:
		user: the User's name.
		name: the name to carry.
	"""
	if not user or not name:
		return

	frappe.db.set_value(
		"User",
		user,
		{"first_name": name, "last_name": None, "full_name": name},
		update_modified=False,
	)


def _has_field(doctype, fieldname):
	"""Whether a field another app owns is installed on this site.

	Asked rather than assumed, because this app does not depend on
	contact_enhancements and must keep working where it is absent.
	"""
	return bool(frappe.get_meta(doctype).has_field(fieldname))


def _attach_user_to_contact(contact, user):
	"""Point a Contact at its website account, if it has none.

	Written with `db_set` rather than a full save: this is a single
	derived field, and re-running the whole Contact validate cycle here
	would put contact_enhancements' Arabic rules back in the path of a
	signup that has already passed them.

	Args:
		contact: the Contact document.
		user: the User document.
	"""
	if contact.user:
		return

	frappe.db.set_value("Contact", contact.name, "user", user.name, update_modified=False)
	contact.user = user.name


def _ensure_portal_user(customer, user):
	"""Give the account portal access to its Customer.

	The child row is inserted directly instead of appending to the
	Customer and saving it. Saving an existing Customer would re-run its
	full validation - including the mandatory `customer_primary_address`
	that many historic records do not have - and would let other apps'
	hooks rewrite fields on a record this flow has no business touching.

	Args:
		customer: the Customer's name.
		user: the User document.
	"""
	if frappe.db.exists(
		"Portal User", {"parent": customer, "user": user.name, "parenttype": "Customer"}
	):
		return

	portal_user = frappe.new_doc("Portal User")
	portal_user.update(
		{
			"parenttype": "Customer",
			"parentfield": "portal_users",
			"parent": customer,
			"user": user.name,
		}
	)
	portal_user.insert(ignore_permissions=True)


def _create_identity(doc, user, customer, contact, linked_existing):
	"""Write the authoritative identity row.

	Deliberately last. Its unique indexes are the final arbiter of a race,
	and inserting it here means a signup that lost one fails before it can
	hand anybody an account.

	Args:
		doc: the Webshop Signup Session document.
		user: the User document.
		customer: the Customer's name.
		contact: the Contact document.
		linked_existing: whether the Customer pre-dated this signup.

	Returns:
		The inserted Webshop Account Identity document.

	Raises:
		SignupRaceLost: if a concurrent signup claimed this identity.
			`finalize` catches this alongside the raw uniqueness errors
			and turns all of them into a clean BLOCKED response.
	"""
	identity = frappe.new_doc("Webshop Account Identity")
	identity.update(
		{
			"user": user.name,
			"customer": customer,
			"phone_e164": doc.phone_e164,
			"email_normalized": doc.email_normalized,
			"signup_session": doc.name,
			"contact": contact.name,
			"verified_on": now_datetime(),
			"linked_existing_customer": 1 if linked_existing else 0,
		}
	)
	identity.flags.ignore_permissions = True

	try:
		identity.insert(ignore_permissions=True)
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		log_event("signup_race_lost", doc)
		frappe.throw(
			_("An account was just created with these details. Please sign in instead."),
			exc=SignupRaceLost,
			title=_("Account Already Exists"),
		)

	return identity
