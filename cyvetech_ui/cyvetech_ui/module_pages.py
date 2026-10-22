# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""The module pages: what waits for the user, and what needs attention, among
a module's documents.

public/js/cyvetech_ui_module_pages.js puts a header over each module's
workspace, in the desk home's look; the rest of what it shows comes with the
boot (boot.py), and the cards under it are ERPNext's own. The rules are in
module_pages_rules.py.

	summary   for one workspace: what waits for the logged-in user among the
	          documents its page and menu open, how many of them need
	          attention, the document its header offers to make, and the
	          desk's tab of dashboards for the module, where the user has it

WHOSE ALERTS

The user's own, read as My Alerts reads them (alerts.py): nothing here takes a
user to look at. What needs attention is counted with frappe.get_list, so a
user's permissions narrow it as they narrow the lists. The workspace named
only says which documents to count.

NEVER AN ERROR

A module's page opens whatever happens here: a part that cannot be read is
left out and written to the Error Log, and the header still comes.
"""

import frappe
from frappe.utils import getdate, nowdate, today

from cyvetech_ui.cyvetech_ui import alerts, alerts_rules, home, home_rules, module_pages_rules as rules


@frappe.whitelist()
def summary(workspace: str):
	"""What waits for the logged-in user, and what needs attention, among the
	module's documents."""
	user = home._signed_in()
	day = getdate(nowdate())
	names = home._or([], _doctypes, workspace, title="module doctypes")
	mine = rules.mine_in(home._or([], _alerts, user, names, title="module alerts") if names else [], names)
	readable = home._readable()
	desks = home_rules.desks_of(frappe.get_roles(user), readable)
	company = home._or(None, home._company)
	reader = home.Reader(day, company, readable, desks)
	counts = {key: home._or(0, reader.attention_count, key, title="attention: " + key) for key in rules.attention_in(names)}
	made = home._or([], home._made, user, desks, day)
	tabs = home._or([], home._tabs, user, desks, readable, title="module tabs")
	return {
		"workspace": workspace,
		"waiting": home_rules.waiting(mine, rules.SHOWN),
		# the doctypes of what waits, which the user's own lists are kept to when they open them from here
		"doctypes": rules.doctypes(alert.get("doctype") for alert in mine),
		"attention": home_rules.attention_rows(counts, day, company)[: rules.SHOWN_ATTENTION],
		"action": rules.action_of(workspace, made, names),
		# the desk's tab of dashboards for this module, where the user has it
		"dashboard": home_rules.tab_of_workspace(tabs, workspace),
	}


def _doctypes(workspace):
	"""The doctypes the module opens: its menu (the Workspace Sidebar Frappe draws
	down the left), then its page's cards and shortcuts."""
	names = []
	if frappe.db.exists("DocType", "Workspace Sidebar") and frappe.db.exists("Workspace Sidebar", workspace):
		names += [row.link_to for row in frappe.get_doc("Workspace Sidebar", workspace).items if row.link_type == "DocType"]
	if frappe.db.exists("Workspace", workspace):
		page = frappe.get_doc("Workspace", workspace)
		names += [row.link_to for row in page.links if row.type == "Link" and row.link_type == "DocType"]
		names += [row.link_to for row in page.shortcuts if row.type == "DocType"]
	return rules.doctypes(names)


def _alerts(user, names):
	"""The user's own assignments and notifications about documents of those
	doctypes, most urgent first, as My Alerts orders them."""
	day = today()
	assignments = alerts._assignments(user, day, names)
	notifications = alerts_rules.without_duplicate_assignments(alerts._notifications(user, names), assignments)
	return alerts_rules.order(assignments + notifications, day)
