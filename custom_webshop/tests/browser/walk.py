# Copyright (c) 2026, ahmedamin and contributors
# For license information, please see license.txt

"""Drive the nine A-scenarios through the real signup wizard.

One page per scenario, both OTP codes read out of the dev-mode log and
typed into the page, the recognition card answered where one is offered.

Nothing about the database is asserted here. This file records only what
the browser saw - which state it reached, what the card showed, which of
the two names it was offered - and `verify.py` checks the records
afterwards. Keeping the two apart means an expectation can be corrected
without paying for another ten-minute walk.
"""

import glob
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(line_buffering=True)
from playwright.sync_api import TimeoutError as PlaywrightTimeout  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT") or os.path.join(HERE, ".run")
BENCH = os.environ.get("BENCH", "/home/frappe/frappe-bench")
BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
LOG = f"{BENCH}/logs/custom_webshop.signup.log"
PASSWORD = "Str0ng-Passw0rd!x7"

RUN = json.load(open(os.path.join(OUT, "afix.json")))
PLAN, FIX, LANGS = RUN["plan"], RUN["fixtures"], RUN["langs"]
RESULTS, FAIL = {}, []


def browser_path():
	found = sorted(glob.glob(os.path.expanduser(
		"~/.cache/ms-playwright/chromium*/chrome-*/chrome-headless-shell")))
	if not found:
		raise SystemExit("no playwright chromium found - run `playwright install chromium`")
	return found[-1]


def code_count(channel):
	"""How many codes this channel has logged so far.

	Every rotated file is counted rather than tailing the newest: the
	logger rotates at 100 KB and `*.log*` sorts alphabetically, so
	`.log.10` reads as older than `.log.2`. Waiting for a total to rise is
	immune to which file the next line lands in.
	"""
	total = 0
	for path in glob.glob(LOG + "*"):
		with open(path, errors="replace") as fh:
			total += sum(1 for line in fh
			             if "otp_dev_mode_not_sent" in line and f"'channel': '{channel}'" in line)
	return total


def latest_code(channel, after):
	# Patient on purpose. The first signup of a run pays for a cold site -
	# freshly built assets, an empty cache, a worker that has not sent
	# anything yet - and a ceiling tuned to the warm case reports that as
	# "no code arrived", which reads like a broken OTP rather than a slow
	# first request. Waiting longer costs nothing when things are healthy.
	for _ in range(240):
		hits = []
		for path in sorted(glob.glob(LOG + "*"), key=os.path.getmtime):
			with open(path, errors="replace") as fh:
				hits += [line for line in fh
				         if "otp_dev_mode_not_sent" in line and f"'channel': '{channel}'" in line]
		if len(hits) > after:
			return re.search(r"'code': '(\d+)'", hits[-1]).group(1)
		time.sleep(0.25)
	raise RuntimeError(f"no new {channel} code appeared in the log after 60s")


def shoot(page, path):
	"""Take a screenshot, or don't - but never take the run down with it.

	These are diagnostics. One of them timed out waiting for fonts inside
	the handler that was already reporting a failure, so the exception
	escaped, killed the walk, and left the results file unwritten.
	"""
	try:
		page.screenshot(path=path, timeout=10000, animations="disabled")
	except Exception as exc:
		print(f"    (screenshot skipped: {exc.__class__.__name__})")


def run(page, case, lang):
	plan = PLAN[case]
	print(f"\n== {case}  ({lang})  {plan['name']!r}  {plan['email']}  {plan['phone']}")

	page.goto(f"{BASE}/login?lang={lang}", wait_until="networkidle")
	page.evaluate("(l) => { try { localStorage.setItem('cnc_lang_v2', l); } catch (e) {} }", lang)
	page.reload(wait_until="networkidle")
	page.wait_for_timeout(700)

	page.click("#go-to-signup")
	page.wait_for_timeout(400)
	page.click("#type-next")
	page.wait_for_timeout(500)

	page.fill("#su-name", plan["name"])
	page.fill("#su-email", plan["email"])
	# The field takes national digits without the trunk zero; the fixture
	# holds whatever form the Contact ended up storing.
	page.fill("#su-phone", re.sub(r"^(\+?20|00?20)", "", plan["phone"]).lstrip("0"))
	page.wait_for_timeout(250)

	before = code_count("email")
	page.click("#details-next")
	page.wait_for_timeout(400)
	page.fill("#su-code", latest_code("email", before))
	before = code_count("phone")
	page.click("#otp-verify")
	page.wait_for_timeout(1600)
	page.fill("#su-code", latest_code("phone", before))
	page.click("#otp-verify")
	page.wait_for_timeout(2400)

	verdict = page.evaluate("() => Signup.envelope && Signup.envelope.state")
	print(f"    state after both codes: {verdict}")
	shoot(page, f"{OUT}/shots/{case}-{lang}.png")

	rows, card, names = None, None, None
	if verdict == "MATCH_REVIEW":
		card = page.evaluate("() => Signup.envelope.data.recognition")
		rows = page.evaluate("""() => [...document.querySelectorAll('.signup-match-row')].map(r => ({
			label: r.querySelector('.signup-match-label').textContent.trim(),
			value: r.querySelector('.signup-match-value').textContent.trim(),
			blurred: r.querySelector('.signup-match-value').classList.contains('is-redacted'),
		}))""")
		for row in rows:
			print(f"      {'BLUR' if row['blurred'] else '    '} {row['label']}: {row['value']}")

		if plan["answer"] is None:
			# Clicking either button here would invent a decision the
			# person never made, and hide the real failure.
			FAIL.append(f"{case}: a card was shown but the scenario expects none")
		else:
			page.click("#match-yes" if plan["answer"] else "#match-no")
			page.wait_for_timeout(1800)

			# Saying yes to a record and saying yes to its spelling are
			# different answers, so a second card follows whenever the
			# stored name differs from the one just typed.
			if page.query_selector("#name-keep"):
				names = page.evaluate(
					"""() => [...document.querySelectorAll('.signup-name-option')].map(
						b => ({id: b.id, value: b.querySelector('.signup-name-value').textContent.trim()}))""")
				for option in names:
					print(f"      name option {option['id']}: {option['value']}")
				shoot(page, f"{OUT}/shots/{case}-{lang}-name.png")
				page.click("#name-keep" if plan.get("name_choice", "keep") == "keep" else "#name-use")
				page.wait_for_timeout(1800)
	elif plan["answer"] is not None:
		FAIL.append(f"{case}: expected a recognition card, state was {verdict}")

	# Waited for rather than assumed: answering the card can write a phone
	# row onto an existing Contact, which runs the other app's whole
	# validate chain, and a fixed pause long enough for that on a quiet
	# machine is not long enough on a busy one.
	try:
		page.wait_for_selector("#su-password", timeout=20000)
	except PlaywrightTimeout:
		error = page.query_selector("#signup-error")
		FAIL.append(f"{case}: never reached the password step"
		            + (f" - page said {error.inner_text().strip()!r}" if error else "")
		            + f" (state {page.evaluate('() => Signup.envelope && Signup.envelope.state')})")
		shoot(page, f"{OUT}/shots/stuck-{case}.png")
		return {"case": case, "lang": lang, "state": verdict, "card": card, "rows": rows,
		        "name_options": names, "url": page.url, "email": plan["email"],
		        "phone": plan["phone"], "name": plan["name"], "stuck": True}

	page.fill("#su-password", PASSWORD)
	page.fill("#su-password2", PASSWORD)
	page.click("#password-next")
	page.wait_for_load_state("networkidle")
	page.wait_for_timeout(2600)

	print(f"    landed: {page.url}")
	return {"case": case, "lang": lang, "state": verdict, "card": card, "rows": rows,
	        "name_options": names, "url": page.url, "email": plan["email"],
	        "phone": plan["phone"], "name": plan["name"]}


os.makedirs(f"{OUT}/shots", exist_ok=True)
with sync_playwright() as pw:
	chrome = pw.chromium.launch(executable_path=browser_path(),
	                            args=["--no-sandbox", "--disable-gpu"])
	errors = []
	for case in sorted(PLAN):
		page = chrome.new_page(viewport={"width": 1280, "height": 980})
		page.on("pageerror", lambda exc, case=case: errors.append(f"{case}: {exc}"))
		try:
			RESULTS[case] = run(page, case, LANGS[case])
		except Exception as exc:
			FAIL.append(f"{case}: {exc}")
			shoot(page, f"{OUT}/shots/fail-{case}.png")
			print(f"    !! {exc}")
			RESULTS[case] = {"case": case, "error": str(exc)}
		page.close()
	chrome.close()

if errors:
	FAIL.append(f"page errors: {errors}")
print("\n  page errors:", errors or "none")

with open(f"{OUT}/walk.json", "w") as fh:
	json.dump({"stamp": RUN["stamp"], "cases": RESULTS}, fh, indent=1, ensure_ascii=False)

print("\n" + ("  walk clean" if not FAIL else f"  {len(FAIL)} problems in the walk:"))
for problem in FAIL:
	print("   -", problem)
sys.exit(1 if FAIL else 0)
