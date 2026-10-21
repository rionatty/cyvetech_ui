# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""The desk home's rules: whose figures, which panels, and how each is worked out.

No Frappe import, so tests/test_home_rules.py runs without a bench. home.py reads
the site and public/js/cyvetech_ui_home.js draws the page.

The home is ERPNext's: a greeting, the figures that matter today, what waits for
the user, what needs attention in the business, and the panels behind the
figures. It takes its look from HRMS Addon's desk home; what is on it is the
business's, not HR's (22 Oct 2026: "the Home dashboard should be for the ERP
next").

WHOSE DESK

What a user's home shows follows what their roles are about (DESKS):

	finance    Accounts Manager, Accounts User, Auditor
	sales      Sales Manager, Sales User, Sales Master Manager
	buying     Purchase Manager, Purchase User, Purchase Master Manager
	stock      Stock Manager, Stock User, Item Manager
	making     Manufacturing Manager, Manufacturing User
	projects   Projects Manager, Projects User
	support    Support Team

Someone with several gets them in that order, so an administrator's home opens
on the money, and a sales clerk who also keeps the store sees the orders first
and the stock after. Every figure is checked against what the user may read too
(home.py), so it shows only where they could open the documents behind it. A
user whose roles are none of these gets the desks of what they may read; one who
may read none of it gets their own work: what waits for them, and their drafts.
"""

import calendar
import datetime

from cyvetech_ui.cyvetech_ui import alerts_rules

OVERDUE, TODAY, SOON, LATER, NONE = (
	alerts_rules.OVERDUE,
	alerts_rules.TODAY,
	alerts_rules.SOON,
	alerts_rules.LATER,
	alerts_rules.NONE,
)
# a band of its own for what is fine: paid on time, in stock, ahead of its date
GOOD = "good"
# most urgent first, the order rows of mixed bands are listed in
SEVERITY = (OVERDUE, TODAY, SOON, LATER, NONE, GOOD)

# how many rows a panel lists; the list behind it has the rest
SHOWN = 6

# ── Whose desk ───────────────────────────────────────────────────────────────

FINANCE, SALES, BUYING, STOCK, MAKING, PROJECTS, SUPPORT = (
	"finance",
	"sales",
	"buying",
	"stock",
	"making",
	"projects",
	"support",
)

# (desk, the roles it is for, the doctype that stands for it where no role says so)
DESKS = (
	(FINANCE, ("Accounts Manager", "Accounts User", "Auditor"), "Sales Invoice"),
	(SALES, ("Sales Manager", "Sales User", "Sales Master Manager"), "Sales Order"),
	(BUYING, ("Purchase Manager", "Purchase User", "Purchase Master Manager"), "Purchase Order"),
	(STOCK, ("Stock Manager", "Stock User", "Item Manager"), "Bin"),
	(MAKING, ("Manufacturing Manager", "Manufacturing User"), "Work Order"),
	(PROJECTS, ("Projects Manager", "Projects User"), "Task"),
	(SUPPORT, ("Support Team",), "Issue"),
)


def desks_of(roles, readable=()):
	"""The desks a user has, in DESKS order: those their roles are for, else
	those whose documents they may read."""
	roles = set(roles or ())
	mine = [desk for desk, allowed, _anchor in DESKS if roles & set(allowed)]
	if mine:
		return mine
	readable = set(readable or ())
	return [desk for desk, _allowed, anchor in DESKS if anchor in readable]


# ── The figures across the top ───────────────────────────────────────────────

MONEY, COUNT = "money", "count"

# card: (label, what its figure is, the doctypes it is read from)
CARDS = {
	"sales": ("Sales This Month", MONEY, ("Sales Invoice",)),
	"receivable": ("To Collect", MONEY, ("Sales Invoice",)),
	"payable": ("To Pay", MONEY, ("Purchase Invoice",)),
	"cash": ("Cash and Bank", MONEY, ("GL Entry", "Account")),
	"orders": ("Orders This Month", MONEY, ("Sales Order",)),
	"to_deliver": ("To Deliver", COUNT, ("Sales Order",)),
	"quotations": ("Open Quotations", COUNT, ("Quotation",)),
	"purchases": ("Purchases This Month", MONEY, ("Purchase Order",)),
	"to_receive": ("To Receive", COUNT, ("Purchase Order",)),
	"stock_value": ("Stock Value", MONEY, ("Bin", "Warehouse")),
	"reorder": ("To Reorder", COUNT, ("Bin", "Item", "Warehouse")),
	"work_orders": ("Open Work Orders", COUNT, ("Work Order",)),
	"tasks": ("Open Tasks", COUNT, ("Task",)),
	"issues": ("Open Issues", COUNT, ("Issue",)),
}

# each desk's figures, most telling first
DESK_CARDS = {
	FINANCE: ("sales", "receivable", "payable", "cash"),
	SALES: ("orders", "to_deliver", "quotations", "receivable"),
	BUYING: ("purchases", "to_receive", "payable"),
	STOCK: ("stock_value", "reorder", "to_deliver", "to_receive"),
	MAKING: ("work_orders", "reorder"),
	PROJECTS: ("tasks",),
	SUPPORT: ("issues",),
}
SHOWN_CARDS = 4


def cards_for(desks, readable, shown=SHOWN_CARDS):
	"""The business figures across the top: each desk's in turn, each once, and
	only those whose documents the user may read."""
	readable = set(readable or ())
	out = []
	for desk in desks or ():
		for key in DESK_CARDS.get(desk, ()):
			if key not in out and all(doctype in readable for doctype in CARDS[key][2]):
				out.append(key)
	return out[:shown]


def frame(key):
	"""A business figure before it is read: what the card is called, to draw it
	while its figure is on the way."""
	label, kind, _doctypes = CARDS[key]
	return {"key": key, "label": label, "kind": kind, "frame": 1}


def home_cards(keys, waits, shown=SHOWN_CARDS):
	"""What the top of the home starts with: the business figures' frames, and the
	user's own work after them where there is room. A desk with no business
	figures has the user's own work only."""
	cards = [frame(key) for key in keys][:shown]
	own = own_cards(waits)
	if not cards:
		return own
	if len(cards) < shown:
		cards.append(own[0])
	return cards


def own_cards(waits):
	"""The user's own work as two figures: what is assigned to them, and what
	they have not read."""
	waits = waits or {}
	return [
		{
			"key": "waiting",
			"label": "Waiting for You",
			"kind": COUNT,
			"value": int(waits.get("tasks") or 0),
			"note": waiting_note(waits),
			"tone": "rose" if waits.get("overdue") else "blue",
			"route": ["List", "ToDo"],
			"mine": 1,
		},
		{
			"key": "unread",
			"label": "Unread Notifications",
			"kind": COUNT,
			"value": int(waits.get("unread") or 0),
			"note": "Since you last looked",
			"tone": "navy",
			"route": ["List", "Notification Log"],
			"mine": 1,
		},
	]


def card(key, value, note="", tone="navy", change=None, route=None, filters=None, options=None):
	"""A business figure, read: {"key", "label", "kind", "value", "note", "tone",
	"change", "route", "filters", "options"}."""
	label, kind, _doctypes = CARDS[key]
	out = {"key": key, "label": label, "kind": kind, "value": _number(value), "note": note, "tone": tone}
	if change:
		out["change"] = change
	if route:
		out["route"] = list(route)
	if filters:
		out["filters"] = dict(filters)
	if options:
		out["options"] = dict(options)
	return out


# ── What waits for the user ──────────────────────────────────────────────────

ASSIGNMENT, NOTIFICATION = alerts_rules.ASSIGNMENT, alerts_rules.NOTIFICATION


def _row(alert):
	return {
		"title": alert.get("title") or "",
		"doctype": alert.get("doctype"),
		"docname": alert.get("docname"),
		"when": alert.get("when") or "",
		"band": alert.get("urgency") or NONE,
		"key": alert.get("key"),
	}


def waiting(alerts, shown=SHOWN):
	"""The user's own work, from My Alerts' rows (most urgent first): how much is
	assigned to them, how much of it is late or due today, how many
	notifications they have not read, and the first rows of each."""
	tasks = [alert for alert in alerts or () if alert.get("kind") == ASSIGNMENT]
	notes = [alert for alert in alerts or () if alert.get("kind") == NOTIFICATION and alert.get("unread")]
	return {
		"tasks": len(tasks),
		"overdue": sum(1 for alert in tasks if alert.get("urgency") == OVERDUE),
		"today": sum(1 for alert in tasks if alert.get("urgency") == TODAY),
		"unread": len(notes),
		"items": [_row(alert) for alert in tasks[:shown]],
		"notes": [_row(alert) for alert in notes[:shown]],
	}


def waiting_note(waits):
	"""What is said under the count of what waits for somebody."""
	if not waits.get("tasks"):
		return "Nothing waiting"
	if waits.get("overdue"):
		return "%d overdue" % waits["overdue"]
	if waits.get("today"):
		return "%d due today" % waits["today"]
	return "None overdue"


def greeting(hour):
	return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"


# ── The panels under what waits ──────────────────────────────────────────────

# where a panel goes: beside what waits for the user, across the page, or in the grid below
BESIDE, WIDE, GRID = "beside", "wide", "grid"

# what each user's drafts are looked for in: the documents a day's work leaves half done
DRAFT_DOCTYPES = (
	"Sales Invoice",
	"Sales Order",
	"Quotation",
	"Delivery Note",
	"Payment Entry",
	"Journal Entry",
	"Purchase Order",
	"Purchase Invoice",
	"Purchase Receipt",
	"Material Request",
	"Stock Entry",
	"Stock Reconciliation",
	"Work Order",
)

# panel: (title, the settings switch, where it goes, the doctypes it is read from:
# any one of the sets will do, and none at all means it decides for itself)
PANELS = {
	"attention": ("Needs Attention", "home_attention", BESIDE, ()),
	"trend": ("Sales and Collections", "home_trend", WIDE, (("Sales Invoice",), ("Sales Order",))),
	"aging": ("Receivables Aging", "home_aging", GRID, (("Sales Invoice",),)),
	"cash": ("Cash and Bank", "home_cash", GRID, (("GL Entry", "Account"),)),
	"customers": ("Top Customers This Month", "home_customers", GRID, (("Sales Invoice",), ("Sales Order",))),
	"deliver": ("Orders to Deliver", "home_deliver", GRID, (("Sales Order",),)),
	"receive": ("Purchases to Receive", "home_receive", GRID, (("Purchase Order",),)),
	"reorder": ("Stock to Reorder", "home_reorder", GRID, (("Bin", "Item", "Warehouse"),)),
	"production": ("Work Orders Due", "home_production", GRID, (("Work Order",),)),
	"tasks": ("Tasks Due", "home_tasks", GRID, (("Task",),)),
	"drafts": ("Your Drafts", "home_drafts", GRID, tuple((doctype,) for doctype in DRAFT_DOCTYPES)),
}
SWITCHES = tuple(switch for _title, switch, _place, _needs in PANELS.values())

# each desk's panels; Needs Attention is on every desk that has one, Your Drafts on every home
DESK_PANELS = {
	FINANCE: ("trend", "aging", "cash", "customers"),
	SALES: ("trend", "deliver", "customers"),
	BUYING: ("receive", "reorder"),
	STOCK: ("reorder", "deliver", "receive"),
	MAKING: ("production", "reorder"),
	PROJECTS: ("tasks",),
	SUPPORT: (),
}


def switched_on(stored):
	"""Each panel's switch as on or off. stored: the settings as saved; a switch
	never saved is on, as its field's default says."""
	stored = stored or {}
	out = {}
	for switch in SWITCHES:
		value = stored.get(switch)
		if value is None or value == "":
			out[switch] = True
		else:
			try:
				out[switch] = bool(int(value))
			except (TypeError, ValueError):
				out[switch] = True
	return out


def available(needs, readable):
	"""Whether the user may read one of the sets of doctypes a part is read from."""
	readable = set(readable or ())
	return not needs or any(all(doctype in readable for doctype in group) for group in needs)


def panels_for(desks, readable, switches=None):
	"""The panels a user's home has, in the home's order: {"key", "title",
	"place"} for each their desks have, the settings show, and they may read."""
	switches = switches if switches is not None else switched_on({})
	wanted = {"drafts"}
	if desks:
		wanted.add("attention")
	for desk in desks or ():
		wanted.update(DESK_PANELS.get(desk, ()))
	out = []
	for key, (title, switch, place, needs) in PANELS.items():
		if key in wanted and switches.get(switch, True) and available(needs, readable):
			out.append({"key": key, "title": title, "place": place})
	return out


# ── Dates ────────────────────────────────────────────────────────────────────

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
TREND_MONTHS = 6


def this_month(today):
	"""From the first of this month to today."""
	return today.replace(day=1), today


def same_days_last_month(today):
	"""The same days of last month, to compare this month with: the 1st to
	today's date, or to the month's end where it is shorter."""
	start = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
	last = calendar.monthrange(start.year, start.month)[1]
	return start, start.replace(day=min(today.day, last))


def change(now, before):
	"""How a figure moved against the one before: {"percent", "direction"}, or
	None where there is nothing before to compare it with."""
	now, before = _number(now), _number(before)
	if not before:
		return None
	percent = round(100.0 * (now - before) / abs(before))
	direction = "up" if percent > 0 else "down" if percent < 0 else "same"
	return {"percent": abs(percent), "direction": direction}


def months(today, count=TREND_MONTHS):
	"""The last `count` months to today, the oldest first, this one running to
	today: [{"label", "from", "to"}]."""
	year, month = today.year, today.month
	out = []
	for _ in range(count):
		start = datetime.date(year, month, 1)
		end = min(datetime.date(year, month, calendar.monthrange(year, month)[1]), today)
		out.append({"label": MONTHS[month - 1], "from": str(start), "to": str(end)})
		year, month = (year, month - 1) if month > 1 else (year - 1, 12)
	return list(reversed(out))


def by_month(rows, months_, day="day", value="total"):
	"""Each month's total of rows that are one per day ({day: date, value: x})."""
	sums = [0.0] * len(months_)
	for row in rows or ():
		on = _day(row.get(day))
		if not on:
			continue
		for index, month in enumerate(months_):
			if month["from"] <= str(on) <= month["to"]:
				sums[index] += _number(row.get(value))
				break
	return [round(total, 2) for total in sums]


# ── Receivables aging ────────────────────────────────────────────────────────

# (key, label, the first and last day overdue it holds, band)
AGING = (
	("current", "Not due yet", None, 0, GOOD),
	("d30", "1 to 30 days", 1, 30, SOON),
	("d60", "31 to 60 days", 31, 60, TODAY),
	("d90", "61 to 90 days", 61, 90, OVERDUE),
	("older", "Over 90 days", 91, None, OVERDUE),
)


def aging(rows, today):
	"""What customers owe by how long it is overdue. rows: [{"due_date",
	"total"}], the outstanding in the company's currency; an invoice without a
	due date counts as not due. Each bucket comes with the due dates it holds,
	which open its invoices: [{"key", "label", "value", "band", "filters"}]."""
	totals = {key: 0.0 for key, *_rest in AGING}
	for row in rows or ():
		due = _day(row.get("due_date")) or today
		late = (today - due).days
		totals[_bucket(late)] += _number(row.get("total"))
	out = []
	for key, label, first, last, band in AGING:
		out.append(
			{
				"key": key,
				"label": label,
				"value": round(totals[key], 2),
				"band": band,
				"filters": {"due_date": _due_between(today, first, last)},
			}
		)
	return out


def _bucket(late):
	for key, _label, first, last, _band in AGING:
		if (first is None or late >= first) and (last is None or late <= last):
			return key
	return AGING[-1][0]


def _due_between(today, first, last):
	"""The due dates of invoices overdue by `first` to `last` days, as a filter."""
	if first is None:
		return [">=", str(today - datetime.timedelta(days=last))]
	if last is None:
		return ["<=", str(today - datetime.timedelta(days=first))]
	return ["between", [str(today - datetime.timedelta(days=last)), str(today - datetime.timedelta(days=first))]]


def most_overdue(rows, today, shown=5):
	"""The customers who owe the most past its due date, the largest first.
	rows: [{"customer", "customer_name", "total", "oldest"}], in the company's
	currency, overdue only."""
	ordered = sorted(
		(row for row in rows or () if _number(row.get("total")) > 0),
		key=lambda row: (-_number(row.get("total")), str(row.get("customer") or "")),
	)
	out = []
	for row in ordered[:shown]:
		oldest = _day(row.get("oldest"))
		late = (today - oldest).days if oldest else 0
		out.append(
			{
				"title": row.get("customer_name") or row.get("customer") or "",
				"doctype": "Customer",
				"docname": row.get("customer"),
				"value": round(_number(row.get("total")), 2),
				"when": "oldest %d %s overdue" % (late, "day" if late == 1 else "days") if late > 0 else "",
				"band": OVERDUE if late > 60 else TODAY if late > 30 else SOON,
			}
		)
	return out


# ── The panels' lists ────────────────────────────────────────────────────────


def due_rows(rows, today, doctype, title, due, shown=SHOWN, value=None, done=None, total=None):
	"""Open documents the soonest due first, those without a date last: rows the
	home lists, each opening its document. title and due name the fields;
	value is a money field shown with it; done and total, the fields of how far
	along it is ("per_delivered", or "produced_qty" of "qty")."""
	ordered = sorted(
		rows or (),
		key=lambda row: (_day(row.get(due)) or datetime.date.max, str(row.get("name") or "")),
	)
	out = []
	for row in ordered[:shown]:
		on = _day(row.get(due))
		item = {
			"title": row.get(title) or row.get("name") or "",
			"doctype": doctype,
			"docname": row.get("name"),
			"when": alerts_rules.when(on, today) if on else "no date set",
			"band": alerts_rules.urgency(on, today) if on else NONE,
		}
		if value:
			item["value"] = round(_number(row.get(value)), 2)
		if done and total:
			whole = _number(row.get(total))
			item["progress"] = round(100.0 * _number(row.get(done)) / whole) if whole else 0
		elif done:
			item["progress"] = round(_number(row.get(done)))
		out.append(item)
	return out


def to_reorder(levels, bins, shown=SHOWN):
	"""Stock at or under its reorder level, and any going below zero.

	levels: [{"item_code", "warehouse", "level"}], from each item's reorder
	table; bins: [{"item_code", "warehouse", "projected_qty"}]. Projected is
	what ERPNext expects to have once what is ordered arrives and what is sold
	goes out. Below zero is listed first, the most short at the top, then the
	furthest under its level. {"count", "short", "rows"}."""
	level_of = {}
	for row in levels or ():
		level = _number(row.get("level"))
		if level > 0:
			level_of[(row.get("item_code"), row.get("warehouse"))] = level
	found = []
	for row in bins or ():
		projected = _number(row.get("projected_qty"))
		level = level_of.get((row.get("item_code"), row.get("warehouse")))
		if projected < 0 or (level is not None and projected <= level):
			found.append((row, projected, level))
	found.sort(
		key=lambda hit: (
			0 if hit[1] < 0 else 1,
			hit[1] if hit[1] < 0 else (hit[1] / hit[2] if hit[2] else 0),
			str(hit[0].get("item_code") or ""),
		)
	)
	rows = []
	for row, projected, level in found[:shown]:
		rows.append(
			{
				"title": row.get("item_name") or row.get("item_code") or "",
				"doctype": "Item",
				"docname": row.get("item_code"),
				"warehouse": short_name(row.get("warehouse")),
				"projected": _tidy(projected),
				"level": _tidy(level) if level is not None else None,
				"band": OVERDUE if projected < 0 else TODAY,
			}
		)
	return {"count": len(found), "short": sum(1 for _row, projected, _level in found if projected < 0), "rows": rows}


def drafts(found, today, shown=SHOWN):
	"""The user's own drafts, the oldest first. found: [(doctype, {"name",
	"modified", "title"})]. A draft untouched for a week is late; for three days,
	due today. {"count", "rows"}."""
	ordered = sorted(found or (), key=lambda hit: (str(hit[1].get("modified") or ""), hit[0]))
	rows = []
	for doctype, row in ordered[:shown]:
		touched = _day(row.get("modified")) or today
		age = max(0, (today - touched).days)
		title = row.get("title") or ""
		rows.append(
			{
				"title": title if title and title != row.get("name") else doctype,
				"doctype": doctype,
				"docname": row.get("name"),
				"when": "untouched today" if age == 0 else "untouched for %d %s" % (age, "day" if age == 1 else "days"),
				"band": OVERDUE if age >= 7 else TODAY if age >= 3 else NONE,
			}
		)
	return {"count": len(ordered), "rows": rows}


def ranked(rows, label, value, shown=5, name=None, doctype=None):
	"""The largest first, as bars: [{"label", "value", "doctype", "docname"}]."""
	ordered = sorted(
		(row for row in rows or () if _number(row.get(value)) > 0),
		key=lambda row: (-_number(row.get(value)), str(row.get(label) or "")),
	)
	out = []
	for row in ordered[:shown]:
		item = {"label": row.get(label) or row.get(name) or "", "value": round(_number(row.get(value)), 2)}
		if doctype and name:
			item.update({"doctype": doctype, "docname": row.get(name)})
		out.append(item)
	return out


# ── What needs attention ─────────────────────────────────────────────────────

SALES_OPEN = ("To Deliver and Bill", "To Deliver")
PURCHASES_OPEN = ("To Receive and Bill", "To Receive")
WORK_ORDERS_OPEN = ("Not Started", "In Process", "Stock Reserved", "Stock Partially Reserved")
TASKS_OPEN = ("Open", "Working", "Pending Review", "Overdue")
REQUESTS_OPEN = ("Pending", "Partially Ordered")
QUOTATIONS_OPEN = ("Open", "Replied")
WEEK = 7

# (key, what one is called, what several are, the doctype counted, the desks it is for, band),
# the most pressing first
ATTENTION = (
	("invoices_overdue", "Sales invoice overdue", "Sales invoices overdue", "Sales Invoice", (FINANCE, SALES), OVERDUE),
	("orders_late", "Sales order late to deliver", "Sales orders late to deliver", "Sales Order", (SALES, STOCK, FINANCE), OVERDUE),
	("purchases_late", "Purchase order late to arrive", "Purchase orders late to arrive", "Purchase Order", (BUYING, STOCK), OVERDUE),
	("negative_stock", "Item with stock below zero", "Items with stock below zero", "Bin", (STOCK, FINANCE), OVERDUE),
	("work_orders_late", "Work order past its planned end", "Work orders past their planned end", "Work Order", (MAKING,), OVERDUE),
	("tasks_overdue", "Task overdue", "Tasks overdue", "Task", (PROJECTS,), OVERDUE),
	("bills_due", "Supplier bill due this week", "Supplier bills due this week", "Purchase Invoice", (FINANCE, BUYING), TODAY),
	("orders_to_bill", "Delivered order not billed yet", "Delivered orders not billed yet", "Sales Order", (FINANCE, SALES), TODAY),
	("requests_late", "Material request past its date", "Material requests past their date", "Material Request", (BUYING, STOCK), TODAY),
	("receipts_to_bill", "Receipt waiting for its bill", "Receipts waiting for their bill", "Purchase Receipt", (FINANCE, BUYING), SOON),
	("quotations_expiring", "Quotation expiring this week", "Quotations expiring this week", "Quotation", (SALES,), SOON),
	("issues_open", "Support issue open", "Support issues open", "Issue", (SUPPORT,), SOON),
)
ATTENTION_DOCTYPE = {key: doctype for key, _one, _many, doctype, _desks, _band in ATTENTION}


def attention_for(desks, readable):
	"""The checks a user's desks have, whose doctype they may read, in order."""
	desks = set(desks or ())
	readable = set(readable or ())
	return [key for key, _one, _many, doctype, for_desks, _band in ATTENTION if desks & set(for_desks) and doctype in readable]


def attention_filters(key, today, company=None):
	"""What each check counts, as a list filter: the same filter opens the list."""
	day = str(today)
	week = str(today + datetime.timedelta(days=WEEK))
	mine = {"company": company} if company else {}
	filters = {
		"invoices_overdue": {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<", day], **mine},
		"orders_late": {"docstatus": 1, "status": ["in", list(SALES_OPEN)], "delivery_date": ["<", day], **mine},
		"purchases_late": {"docstatus": 1, "status": ["in", list(PURCHASES_OPEN)], "schedule_date": ["<", day], **mine},
		# stock below zero is wrong in any company: not narrowed to one
		"negative_stock": {"actual_qty": ["<", 0]},
		"work_orders_late": {"docstatus": 1, "status": ["in", list(WORK_ORDERS_OPEN)], "planned_end_date": ["<", day], **mine},
		"tasks_overdue": {"status": ["in", list(TASKS_OPEN)], "exp_end_date": ["<", day]},
		"bills_due": {"docstatus": 1, "outstanding_amount": [">", 0], "due_date": ["<=", week], **mine},
		"orders_to_bill": {"docstatus": 1, "status": "To Bill", **mine},
		"requests_late": {"docstatus": 1, "status": ["in", list(REQUESTS_OPEN)], "schedule_date": ["<", day], **mine},
		"receipts_to_bill": {"docstatus": 1, "status": ["in", ["To Bill", "Partly Billed"]], **mine},
		"quotations_expiring": {"docstatus": 1, "status": ["in", list(QUOTATIONS_OPEN)], "valid_till": ["between", [day, week]], **mine},
		"issues_open": {"status": "Open"},
	}
	return filters[key]


def attention_rows(counts, today, company=None):
	"""What needs attention, the most pressing first: only what there is some
	of. counts: {key: how many}. Each row opens the list of them:
	{"key", "label", "value", "band", "route", "filters"}."""
	order = {key: index for index, (key, *_rest) in enumerate(ATTENTION)}
	rows = []
	for key, one, many, doctype, _desks, band in ATTENTION:
		value = int(_number((counts or {}).get(key)))
		if value <= 0:
			continue
		rows.append(
			{
				"key": key,
				"label": one if value == 1 else many,
				"value": value,
				"band": band,
				"route": ["List", doctype],
				"filters": attention_filters(key, today, company),
			}
		)
	rows.sort(key=lambda row: (SEVERITY.index(row["band"]), order[row["key"]]))
	return rows


# ── What the user makes most ─────────────────────────────────────────────────

# the documents a user's own recent work is counted in
CREATE = (
	"Sales Invoice",
	"Sales Order",
	"Quotation",
	"Delivery Note",
	"Payment Entry",
	"Journal Entry",
	"Purchase Order",
	"Purchase Invoice",
	"Purchase Receipt",
	"Material Request",
	"Stock Entry",
	"Work Order",
	"Lead",
	"Opportunity",
	"Customer",
	"Item",
	"Task",
	"Timesheet",
	"Issue",
)
# what each desk usually makes, for a user with no recent work of their own
DESK_CREATE = {
	FINANCE: ("Sales Invoice", "Payment Entry", "Journal Entry"),
	SALES: ("Sales Order", "Quotation", "Customer"),
	BUYING: ("Purchase Order", "Material Request", "Supplier"),
	STOCK: ("Stock Entry", "Delivery Note", "Purchase Receipt"),
	MAKING: ("Work Order",),
	PROJECTS: ("Task", "Timesheet"),
	SUPPORT: ("Issue",),
}
# how far back a user's own documents are counted
MADE_DAYS = 60
SHOWN_CREATE = 4


def most_made(counts, desks, creatable, shown=SHOWN_CREATE):
	"""The documents a user makes, the most made first: those they made in the
	last MADE_DAYS, then what their desks usually make, each once and only
	where they may make it. counts: {doctype: how many they made}."""
	creatable = set(creatable or ())
	counts = counts or {}
	made = sorted(
		(doctype for doctype, number in counts.items() if number and doctype in creatable),
		key=lambda doctype: (-counts[doctype], CREATE.index(doctype) if doctype in CREATE else len(CREATE)),
	)
	out = list(made)
	for desk in desks or ():
		for doctype in DESK_CREATE.get(desk, ()):
			if doctype in creatable and doctype not in out:
				out.append(doctype)
	return out[:shown]


# ── Quick access, where Frappe has no visits to go by ────────────────────────

# (label, route, the doctype a user must read for it)
DESK_LINKS = {
	FINANCE: (
		("Accounts Receivable", ["query-report", "Accounts Receivable"], "Sales Invoice"),
		("Accounts Payable", ["query-report", "Accounts Payable"], "Purchase Invoice"),
		("General Ledger", ["query-report", "General Ledger"], "GL Entry"),
		("Profit and Loss", ["query-report", "Profit and Loss Statement"], "GL Entry"),
	),
	SALES: (
		("Sales Orders", ["List", "Sales Order"], "Sales Order"),
		("Quotations", ["List", "Quotation"], "Quotation"),
		("Customers", ["List", "Customer"], "Customer"),
	),
	BUYING: (
		("Purchase Orders", ["List", "Purchase Order"], "Purchase Order"),
		("Material Requests", ["List", "Material Request"], "Material Request"),
		("Suppliers", ["List", "Supplier"], "Supplier"),
	),
	STOCK: (
		("Stock Balance", ["query-report", "Stock Balance"], "Stock Ledger Entry"),
		("Stock Ledger", ["query-report", "Stock Ledger"], "Stock Ledger Entry"),
		("Items", ["List", "Item"], "Item"),
	),
	MAKING: (
		("Work Orders", ["List", "Work Order"], "Work Order"),
		("Bills of Materials", ["List", "BOM"], "BOM"),
	),
	PROJECTS: (
		("Projects", ["List", "Project"], "Project"),
		("Tasks", ["List", "Task"], "Task"),
	),
	SUPPORT: (("Issues", ["List", "Issue"], "Issue"),),
}
SHOWN_LINKS = 6


def links_for(desks, readable, shown=SHOWN_LINKS):
	"""The pages offered where Frappe has no record of what the user opens most:
	each desk's, each once, only those the user may read."""
	readable = set(readable or ())
	out, seen = [], set()
	for desk in desks or ():
		for label, route, doctype in DESK_LINKS.get(desk, ()):
			key = "/".join(route)
			if doctype in readable and key not in seen:
				seen.add(key)
				out.append({"label": label, "route": list(route)})
	return out[:shown]


# ── The modules down the left ────────────────────────────────────────────────

# The modules down the left of the home, by their tile's label, in the order work
# flows through ERPNext: from the first contact with a customer, through the order,
# the buying, the stock and the making, to the books; then the modules beside that
# flow, and the setup last. A tile not named here keeps Frappe's place after them.
MODULES = (
	"CRM",
	"Selling",
	"Buying",
	"Stock",
	"Manufacturing",
	"Subcontracting",
	"Accounting",
	"Projects",
	"Assets",
	"Quality",
	"Support",
	"Organization",
	"ERPNext Settings",
)
# The flow itself, from a lead to the money: a module page in it shows its place
# (public/js/cyvetech_ui_module_pages.js).
FLOW = ("CRM", "Selling", "Buying", "Stock", "Manufacturing", "Accounting")


# ── Small helpers ────────────────────────────────────────────────────────────


def short_name(name):
	"""A warehouse's or account's name without the company's abbreviation:
	"Stores - AC" is "Stores"."""
	name = str(name or "")
	return name.rsplit(" - ", 1)[0] if " - " in name else name


def _tidy(value):
	"""A quantity as a whole number where it is one."""
	value = _number(value)
	return int(value) if value == int(value) else round(value, 3)


def _number(value):
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0


def _day(value):
	if not value:
		return None
	if isinstance(value, datetime.datetime):
		return value.date()
	if isinstance(value, datetime.date):
		return value
	try:
		return datetime.date.fromisoformat(str(value)[:10])
	except ValueError:
		return None
