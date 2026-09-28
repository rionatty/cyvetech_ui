# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""My Alerts: the logged-in user's own assignments, notifications and alerts.

The ordering rules are in alerts_rules.py; the panel and the pop-ups are
public/js/cyvetech_ui_alerts.js. Marking notifications read goes through
Frappe's own API (frappe.desk.doctype.notification_log.notification_log
.mark_as_read / .mark_all_as_read), which already works on the session
user's notifications only.

WHOSE ALERTS

Every query here filters on frappe.session.user, set on the server, and
nothing accepts a user from the browser. That filter has to be explicit:
frappe.get_all skips permission rules, and the rules alone would not narrow
things to "mine" anyway — Administrator may read every Notification Log and
a System Manager every ToDo.
"""

import frappe
from frappe import _
from frappe.utils import cint, strip_html, today

from cyvetech_ui.cyvetech_ui import alerts_rules as rules

ALERT = "CyveTech User Alert"

# How many of each to read. The panel is a glance, not a list view; the count
# in its header is the honest total of what is outstanding.
LIMIT = 40


@frappe.whitelist()
def my_alerts(limit=LIMIT):
	"""{"alerts": [...], "total": n, "band": "overdue"} for the session user."""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Log in to see your alerts."), frappe.PermissionError)

	limit = max(1, min(cint(limit) or LIMIT, 100))
	day = today()
	assignments = _assignments(user, day)
	notifications = rules.without_duplicate_assignments(_notifications(user), assignments)
	alerts = rules.order(assignments + notifications, day)
	pending = rules.outstanding(alerts)
	return {
		"alerts": alerts[:limit],
		"total": len(pending),
		"band": rules.badge_band(pending),
	}


def _assignments(user, day):
	"""Open to-dos: what the user has been given to do."""
	rows = frappe.get_all(
		"ToDo",
		filters={"allocated_to": user, "status": "Open"},
		fields=["name", "reference_type", "reference_name", "description", "date", "priority", "creation"],
		order_by="modified desc",
		limit=LIMIT,
	)
	return [
		{
			"kind": rules.ASSIGNMENT,
			"key": row.name,
			"title": rules.title(strip_html(row.description or "")) or _("An assignment"),
			"doctype": row.reference_type or "ToDo",
			"docname": row.reference_name or row.name,
			"due": str(row.date) if row.date else None,
			"created": str(row.creation),
			"urgency": rules.urgency(row.date, day, row.priority),
			"when": rules.when(row.date, day),
		}
		for row in rows
	]


def _notifications(user):
	"""The user's notifications, newest first, read or not: a read one is still
	what happened. The unread are marked and counted on their own."""
	body = _body_field()
	rows = frappe.get_all(
		"Notification Log",
		filters={"for_user": user},
		fields=["name", "subject", "type", "document_type", "document_name", "from_user", "creation", "read"]
		+ ([body] if body else []),
		order_by="creation desc",
		limit=LIMIT,
	)
	sent = _alerts_behind(rows)
	out = []
	for row in rows:
		alert = sent.get(row.document_name) if row.document_type == ALERT else None
		doctype, docname = row.document_type, row.document_name
		if alert and alert.reference_doctype and alert.reference_name:
			# an alert about a document opens that document
			doctype, docname = alert.reference_doctype, alert.reference_name
		out.append(
			{
				"kind": rules.NOTIFICATION,
				"key": row.name,
				"title": rules.title(strip_html(row.subject or "")) or _("A notification"),
				"doctype": doctype,
				"docname": docname,
				"due": None,
				"created": str(row.creation),
				"urgency": rules.alert_band(alert.priority) if alert else rules.NONE,
				"when": "",
				"type": row.type,
				# what the notification says beyond its title: an ERPNext Notification
				# rule's message, the text of a mention or comment
				"message": rules.title(strip_html(row.get(body) or ""), limit=240) if body else "",
				"unread": 0 if row.read else 1,
				"from_user": row.from_user,
				# set only for alerts sent from CyveTech User Alert
				"alert": {"name": row.document_name, "priority": alert.priority, "message": alert.message}
				if alert
				else None,
			}
		)
	return out


def _body_field():
	"""Where a Notification Log keeps its message: `description` on Frappe v16,
	`email_content` before it. On v16 email_content holds a rule's email text,
	which can be its placeholder, and Frappe's own bell shows description only."""
	try:
		meta = frappe.get_meta("Notification Log")
		return next((f for f in ("description", "email_content") if meta.has_field(f)), None)
	except Exception:
		return None


def _alerts_behind(rows):
	"""The CyveTech User Alerts some of these notifications came from, by name."""
	names = [row.document_name for row in rows if row.document_type == ALERT and row.document_name]
	if not names:
		return {}
	return {
		alert.name: alert
		for alert in frappe.get_all(
			ALERT,
			filters={"name": ["in", names]},
			fields=["name", "priority", "message", "reference_doctype", "reference_name"],
		)
	}
