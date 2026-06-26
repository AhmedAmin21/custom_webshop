"""Client debug logging — writes NDJSON to session log file for browser-side diagnostics."""

import json
import time

import frappe


LOG_PATH = "/home/erpnext/frappe-bench/.cursor/debug-edf32e.log"


@frappe.whitelist(allow_guest=True)
def log_client_event(location="", message="", data=None, hypothesis_id="", run_id=""):
	"""Append a debug log line from the browser (guest-safe, no secrets)."""
	try:
		payload = data
		if isinstance(payload, str):
			payload = json.loads(payload) if payload else {}
		if not isinstance(payload, dict):
			payload = {"value": payload}

		entry = {
			"sessionId": "edf32e",
			"location": location or "unknown",
			"message": message or "",
			"data": payload,
			"timestamp": int(time.time() * 1000),
			"hypothesisId": hypothesis_id or "",
			"runId": run_id or "",
			"user": frappe.session.user,
		}
		with open(LOG_PATH, "a", encoding="utf-8") as f:
			f.write(json.dumps(entry, default=str) + "\n")
		return True
	except Exception:
		frappe.log_error("debug_log.log_client_event failed")
		return False
