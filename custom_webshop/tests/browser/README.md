# Browser walk — the A scenarios

The unit suite proves each rule in isolation. This proves the nine **A**
scenarios end to end in a real browser: a real signup page, real OTP
codes read out of the dev-mode log, real clicks on the recognition card,
and then the records that were actually written.

It is deliberately **not** part of `bench run-tests`. It needs a running
server, a browser, and OTP dev mode — none of which a unit run should
assume — and it commits, because `linking.finalize` must.

## Running it

```bash
bench --site erpnext execute custom_webshop.tests.browser.run.main
# or, from this directory:
./run.sh
```

`run.sh` does the whole cycle: purge anything left from a previous run,
build the nine fixtures, walk them in the browser, check the records,
then purge again. Every step is scoped to the run's own timestamp, so it
can only ever touch records it created itself.

## What each scenario is

| | Setup | Answer | The promise being tested |
|---|---|---|---|
| A1 | nobody in the system | — | no card at all; a new User, Contact and Customer, all linked |
| A2 | same email, phone and name | Yes | linked to the **existing** customer; no second one |
| A3 | same email, phone and name | No | own new customer; the number stays on the old contact; two conflicts |
| A4 | same email and phone, different name | Yes | the name **is** shown — both channels reach this one record — and nothing is queued |
| A5 | phone only, new email, different name | Yes | the name **is** shown — a verified phone is trusted — linked, keeping the record's spelling, nothing queued |
| A6 | phone only, different name | No | own new customer; zero phone rows on the new contact; two conflicts |
| A7 | email only, new phone, same name | Yes | linked; the new number is added to the **existing** contact |
| A8 | email only, new phone, different name | — | no card offered; new customer; `EMAIL_NAME_MISMATCH` |
| A9 | the matched customer is disabled | Yes | never linked silently; staff review either way |

## Prerequisites

* The site is serving on `http://127.0.0.1:8000`.
* `Webshop Signup Settings` has `otp_dev_mode`, `email_otp_enabled`,
  `phone_otp_enabled` and `signup_enabled` all on. Dev mode only changes
  *delivery* — both codes are still typed into the page.
* Nine signups from one address would trip the per-IP hourly cap on
  `start`, so the fixture step clears this app's rate-limit counters
  first (`signup.audit.clear_rate_limits`). Without that, the run reports
  "no code arrived" from roughly the sixth scenario on.
* Playwright's chromium is installed. On a bare container its shared
  libraries may be missing; point `CHROME_LIBS` at a directory holding
  them and `run.sh` puts it on `LD_LIBRARY_PATH`.

## Why fixture names carry no digits

`contact_enhancements` strips digits from a name on every Contact save.
A fixture named `Ahmed Sabry Test1234` reads back as `Ahmed Sabry Test`,
so every "same name" scenario would quietly become a mismatch and test
the wrong branch. The builder makes its unique suffix out of letters.
