# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""My Alerts: which of a user's alerts matters most, and in what order.

No Frappe import, so tests/test_alerts_rules.py runs without a bench.

The panel shows one person their own work: the assignments on their to-do
list, the notifications they have received, and the alerts an administrator
has sent them. Each row is colored by how soon it matters, not by what kind
of thing it is:

    overdue   its due date has passed, or an Urgent alert
    today     due today or tomorrow, a High priority assignment, or an
              Important alert
    soon      due within the week
    later     due after that
    none      nothing is due (most notifications)

A High priority assignment is never quieter than `today`: someone set that
by hand, and it would be odd for it to sit below a task due in a week.
"""

import datetime

OVERDUE, TODAY, SOON, LATER, NONE = "overdue", "today", "soon", "later", "none"
# most urgent first: the order rows are sorted in and the badge is colored by
BANDS = (OVERDUE, TODAY, SOON, LATER, NONE)
SOON_DAYS = 7
HIGH = "High"
ASSIGNMENT, NOTIFICATION = "assignment", "notification"

# Priority of an alert sent from CyveTech User Alert -> its band.
ALERT_PRIORITY_BANDS = {"Urgent": OVERDUE, "Important": TODAY, "Normal": NONE}


def urgency(due, today, priority=None):
	"""Which band an assignment falls in (BANDS)."""
	band = NONE
	if due:
		left = days_left(due, today)
		if left < 0:
			band = OVERDUE
		elif left <= 1:
			band = TODAY
		elif left <= SOON_DAYS:
			band = SOON
		else:
			band = LATER
	return at_least(band, TODAY) if priority == HIGH else band


def alert_band(priority):
	return ALERT_PRIORITY_BANDS.get(priority or "", NONE)


def at_least(band, floor):
	"""The more urgent of the two bands."""
	return band if BANDS.index(band) <= BANDS.index(floor) else floor


def days_left(due, today):
	return (_date(due) - _date(today)).days


def when(due, today):
	"""How soon it is due, as the row's meta line says it ("" when nothing is due)."""
	if not due:
		return ""
	left = days_left(due, today)
	if left < -1:
		return "overdue by %d days" % -left
	if left > 1:
		return "due in %d days" % left
	return {-1: "overdue by 1 day", 0: "due today", 1: "due tomorrow"}[left]


def without_duplicate_assignments(notifications, assignments):
	"""The notifications, less the "Assignment" ones an open to-do already shows.

	Frappe records every assignment twice: a ToDo for the assignee and a
	Notification Log of type "Assignment" pointing at the same document. The
	to-do row is the useful one (it has the due date), so the notification is
	dropped while that to-do is still open. The later "your assignment was
	removed" notice has the same type but no open to-do behind it, so it stays.
	"""
	open_documents = {(a.get("doctype"), a.get("docname")) for a in assignments}
	return [
		n
		for n in notifications
		if not (n.get("type") == "Assignment" and (n.get("doctype"), n.get("docname")) in open_documents)
	]


def order(alerts, today):
	"""The alerts most urgent first: by band, then by the soonest due date,
	and newest first among equals."""

	def key(alert):
		due = alert.get("due")
		return (
			BANDS.index(alert.get("urgency") or NONE),
			days_left(due, today) if due else 10**6,
		)

	newest_first = sorted(alerts, key=lambda alert: _text(alert.get("created")), reverse=True)
	return sorted(newest_first, key=key)  # stable: newest stays first within a band


def outstanding(alerts):
	"""What is still to be dealt with: every assignment, and the unread rest."""
	return [a for a in alerts if a.get("kind") == ASSIGNMENT or a.get("unread")]


def badge_band(alerts):
	"""The most urgent band anything is in, so the badge says at a glance
	whether something is late."""
	worst = NONE
	for alert in alerts:
		worst = at_least(alert.get("urgency") or NONE, worst)
	return worst


def title(text, limit=120):
	"""One line for the row: no runs of blank space, cut on a word when too long."""
	text = " ".join(_text(text).split())
	if len(text) <= limit:
		return text
	return text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"


def _text(value):
	return "" if value is None else str(value)


def _date(value):
	if isinstance(value, datetime.datetime):
		return value.date()
	if isinstance(value, datetime.date):
		return value
	return datetime.date.fromisoformat(str(value)[:10])
