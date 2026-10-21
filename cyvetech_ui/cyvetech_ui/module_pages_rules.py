# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""What a module's page shows above ERPNext's own cards.

No Frappe import, so tests/test_home_rules.py checks it without a bench.
module_pages.py reads the site and public/js/cyvetech_ui_module_pages.js draws
the page.

A module's page opens under a header of its own, in the desk home's look: the
module's picture and name, the groups of its menu, where it falls in the flow
from a lead to the money (home_rules.FLOW), what needs attention in it, what
waits for the user there, and a button to make the document most made there.
ERPNext's own charts, figures and cards follow, drawn as the home draws its
panels.

	ACTIONS       the document each module's header offers to make
	doctypes      the documents a module's page and menu open, each once
	mine_in       the user's own alerts about those documents
	attention_in  the checks of what needs attention that are about them
	action_of     the document the header offers
"""

from cyvetech_ui.cyvetech_ui import home_rules

# how many rows the panel of what waits lists; the rest are in My Alerts
SHOWN = 5
# how many things that need attention the header names
SHOWN_ATTENTION = 3

# Where each module's work usually starts. A user who makes something else
# there more often is offered that instead (action_of).
ACTIONS = {
	"CRM": "Lead",
	"Selling": "Sales Order",
	"Buying": "Purchase Order",
	"Stock": "Stock Entry",
	"Manufacturing": "Work Order",
	"Subcontracting": "Subcontracting Order",
	"Projects": "Task",
	"Invoicing": "Sales Invoice",
	"Payments": "Payment Entry",
	"Budget": "Budget",
	"Assets": "Asset",
	"Quality": "Quality Inspection",
	"Support": "Issue",
	"Share Management": "Share Transfer",
	"Subscription": "Subscription",
}


def doctypes(names):
	"""Each doctype once, in the order first named, blanks left out."""
	seen, found = set(), []
	for name in names or ():
		name = str(name or "").strip()
		if name and name not in seen:
			seen.add(name)
			found.append(name)
	return found


def mine_in(alerts, names):
	"""The user's alerts about documents of the doctypes named, in the order
	given: what waits for them in one module."""
	wanted = set(names or ())
	return [alert for alert in alerts or () if alert.get("doctype") in wanted]


def attention_in(names):
	"""The checks of what needs attention whose doctype the module opens."""
	wanted = set(names or ())
	return [key for key, *_rest in home_rules.ATTENTION if home_rules.ATTENTION_DOCTYPE[key] in wanted]


def action_of(workspace, made, names):
	"""The document a module's header offers to make: the one the user makes
	most among the module's documents, else where the module's work usually
	starts. made: what the user makes most, the most made first
	(home_rules.most_made)."""
	wanted = set(names or ())
	for doctype in made or ():
		if doctype in wanted:
			return doctype
	return ACTIONS.get(workspace)
