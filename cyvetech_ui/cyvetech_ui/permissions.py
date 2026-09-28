# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""Who may read a CyveTech User Alert.

The DocType lets every role read (and print) alerts; these two hooks narrow
that to the alerts sent to you. A System Manager sees them all. Frappe's
has_permission hooks can only take access away, never grant it, which is
why the DocType itself has to allow reading in the first place.
"""

import frappe

ALERT = "CyveTech User Alert"


def _manages_alerts(user):
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def alert_query(user=None, doctype=None):
	"""permission_query_conditions: list views and reports."""
	user = user or frappe.session.user
	if _manages_alerts(user):
		return ""
	return (
		"(`tabCyveTech User Alert`.docstatus = 1 and `tabCyveTech User Alert`.name in ("
		"select parent from `tabCyveTech Alert Recipient` "
		f"where parenttype = 'CyveTech User Alert' and user = {frappe.db.escape(user)}))"
	)


def alert_has_permission(doc, ptype=None, user=None, debug=False):
	"""has_permission: a single alert."""
	user = user or frappe.session.user
	if _manages_alerts(user):
		return True
	if ptype not in ("read", "print") or doc.docstatus != 1:
		return False
	return any(row.user == user for row in doc.get("recipients") or [])
