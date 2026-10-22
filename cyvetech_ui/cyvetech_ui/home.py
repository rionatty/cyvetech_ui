# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""The desk home, read from the site in two calls.

The rules are in home_rules.py, without a Frappe import
(tests/test_home_rules.py); public/js/cyvetech_ui_home.js draws the page.

	summary   what is drawn at once: the greeting, what waits for the user,
	          which figures and panels their desk has, and what they make most
	figures   the figures and the panels, in a call of their own, so the
	          greeting is never held up by them; kept for five minutes per
	          user, and read afresh on request

AS THE USER MAY SEE IT

Every document is read with frappe.get_list, so a user's roles and User
Permissions narrow the figures as they narrow the lists: a sales clerk limited
to one territory sees that territory's orders. A doctype the user may not read
is never asked for. What waits for the user is their own, as My Alerts lists it
(alerts.py).

ONE COMPANY

Money is the user's default company's, in its currency: a figure that added up
two companies would add up two currencies. Invoices owed in another currency
are turned into the company's at today's rate.

NEVER AN ERROR

This is the page everybody lands on. A part that cannot be read is left out and
written to the Error Log (_or), and the rest still comes.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime, nowdate

from cyvetech_ui.cyvetech_ui import alerts, dashboards_rules as dashboards, home_rules as rules
from cyvetech_ui.cyvetech_ui.settings import get_settings

FIGURES_KEY = "cyvetech_ui_home_figures"
MADE_KEY = "cyvetech_ui_home_made"
FIGURES_SECONDS = 5 * 60
MADE_SECONDS = 60 * 60

# every doctype the home may read from, checked once per call
DOCTYPES = sorted(
	{doctype for _label, _kind, doctypes in rules.CARDS.values() for doctype in doctypes}
	| {doctype for *_rest, needs in rules.PANELS.values() for group in needs for doctype in group}
	| {anchor for _desk, _roles, anchor in rules.DESKS}
	| set(rules.ATTENTION_DOCTYPE.values())
	| {doctype for tab in dashboards.TABS for doctype in tab["anchors"]}
	| set(dashboards.REPORT_DOCTYPES.values())
	| {"Payment Entry", "Customer", "Stock Ledger Entry", "Project", "BOM", "Supplier", "Material Request"}
)


@frappe.whitelist()
def summary():
	"""What the home draws at once, for the logged-in user."""
	user = _signed_in()
	today = getdate(nowdate())
	readable = _readable()
	desks = rules.desks_of(frappe.get_roles(user), readable)
	waits = rules.waiting(_or([], _alerts))
	company = _or(None, _company)
	return {
		"greeting": rules.greeting(now_datetime().hour),
		"first_name": _or(None, _first_name, user) or user,
		"today": str(today),
		"company": company,
		"currency": _or(None, _currency, company) if company else None,
		"waiting": waits,
		"desks": desks,
		"cards": rules.home_cards(rules.cards_for(desks, readable), waits),
		"tabs": _tabs(user, desks, readable),
		"create": _or([], _made, user, desks, today),
		"links": rules.links_for(desks, readable),
	}


@frappe.whitelist()
def figures(part=None, fresh=0):
	"""The figures of one part of the logged-in user's home: "cards", the figures
	across the top, or a tab's key, its figures and dashboards (the overview's
	come with how much needs attention on each tab, for the tab bar). None named:
	every part. The home asks for each part on its own, as its tab is opened, so
	no tab waits for another and one never opened is never read. Each part is
	kept five minutes; fresh=1 reads it again now."""
	user = _signed_in()
	today = getdate(nowdate())
	readable = _readable()
	desks = rules.desks_of(frappe.get_roles(user), readable)
	tabs = _tabs(user, desks, readable)
	part = part or ""
	cards = rules.cards_for(desks, readable) if part in ("", "cards") else []
	wanted = [tab for tab in tabs if part in ("", tab["key"])]
	company = _or(None, _company)
	stamp = {
		"day": str(today),
		"company": company,
		"part": part,
		"cards": cards,
		"tabs": [(tab["key"], [card["key"] for card in tab["cards"]], [panel["key"] for panel in tab["panels"]]) for tab in wanted],
		"desks": desks,
	}
	key = "%s:%s" % (FIGURES_KEY, part or "all")
	if not cint(fresh):
		kept = _or(None, _kept, user, key)
		if kept and kept.get("stamp") == stamp:
			return kept
	visible = [tab["key"] for tab in tabs]
	out = {"part": part, "stamp": stamp, "at": str(now_datetime())[:19], "cards": [], "tabs": {}}
	headline = Reader(today, company, readable, desks, dashboards.OVERVIEW, visible)
	out["currency"] = headline.currency
	out["cards"] = [found for found in (_or(None, headline.card, name, title="figure: " + name) for name in cards) if found]
	for tab in wanted:
		reader = Reader(today, company, readable, desks, tab["key"], visible)
		found = {
			"cards": [
				one for one in (_or(None, reader.card, card["key"], title="figure: " + card["key"]) for card in tab["cards"]) if one
			],
			"panels": [
				one
				for one in (_or(None, reader.panel, panel["key"], title="panel: " + panel["key"]) for panel in tab["panels"])
				if one
			],
		}
		if tab["key"] == dashboards.OVERVIEW:
			found["badges"] = _or({}, reader.badges, title="badges")
		out["tabs"][tab["key"]] = found
	_or(None, _keep, user, key, out, FIGURES_SECONDS)
	return out


def _tabs(user, desks, readable):
	"""The tabs of a user's desk, as home_rules.tabs_for says: the modules assigned
	to them, the reports they may open, as the settings show them."""
	return rules.tabs_for(
		desks,
		readable,
		blocked=_or(set(), _blocked_modules, user, title="blocked modules"),
		switches=rules.switched_on(get_settings()),
		reports=_or(None, _allowed_reports, title="allowed reports"),
	)


class Reader:
	"""One user's figures, read once per call. What two parts need (the open
	invoices behind To Collect and the aging) is read once and shared."""

	def __init__(self, today, company, readable, desks, tab=None, tabs=()):
		self.today = today
		self.company = company
		self.readable = set(readable or ())
		self.desks = desks
		self.tab = tab or dashboards.OVERVIEW
		self.tabs = list(tabs or ())
		self.days = dashboards.dates(today)
		self.currency = _or(None, _currency, company) if company else None
		self.memo = {}

	def once(self, key, read, *args):
		if key not in self.memo:
			self.memo[key] = read(*args)
		return self.memo[key]

	def where(self, **filters):
		"""The filters, narrowed to the company where there is one."""
		if self.company:
			filters.setdefault("company", self.company)
		return filters

	def may(self, *doctypes):
		return all(doctype in self.readable for doctype in doctypes)

	# ── The figures ──────────────────────────────────────────────────────

	def card(self, key):
		own = getattr(self, "card_" + key, None)
		return own() if own else self.declared_card(key, dashboards.FIGURES[key])

	def card_sales(self):
		return self._month_card("sales", "Sales Invoice", "posting_date")

	def card_orders(self):
		return self._month_card("orders", "Sales Order", "transaction_date")

	def card_purchases(self):
		return self._month_card("purchases", "Purchase Order", "transaction_date")

	def _month_card(self, key, doctype, day):
		"""What was billed or ordered this month, against the same days of last month."""
		first, today = rules.this_month(self.today)
		before = rules.same_days_last_month(self.today)
		window = self.where(docstatus=1, **{day: ["between", [str(first), str(today)]]})
		now = total(doctype, "base_net_total", window)
		then = total(doctype, "base_net_total", self.where(docstatus=1, **{day: ["between", [str(before[0]), str(before[1])]]}))
		moved = rules.change(now, then)
		return rules.card(
			key,
			now,
			note="Against the same days last month" if moved else "Before tax",
			tone="blue",
			change=moved,
			route=["List", doctype],
			filters=window,
		)

	def card_receivable(self):
		owed = self.owed("Sales Invoice")
		overdue = owed["overdue"]
		return rules.card(
			"receivable",
			owed["total"],
			note={"money": overdue, "words": "overdue"} if overdue else "None overdue",
			tone="rose" if overdue else "green",
			route=["query-report", "Accounts Receivable"],
			options={"company": self.company} if self.company else None,
		)

	def card_payable(self):
		owed = self.owed("Purchase Invoice")
		due = owed["week"]
		return rules.card(
			"payable",
			owed["total"],
			note={"money": due, "words": "due this week"} if due else "Nothing due this week",
			tone="amber" if due else "navy",
			route=["query-report", "Accounts Payable"],
			options={"company": self.company} if self.company else None,
		)

	def card_cash(self):
		accounts = self.cash()
		return rules.card(
			"cash",
			sum(row["value"] for row in accounts),
			note="In %d %s" % (len(accounts), "account" if len(accounts) == 1 else "accounts"),
			tone="green",
			route=["query-report", "General Ledger"],
			options=self._ledger_options([row["account"] for row in accounts]),
		)

	def card_to_deliver(self):
		filters = self.where(docstatus=1, status=["in", list(rules.SALES_OPEN)])
		late = self.attention_count("orders_late")
		return rules.card(
			"to_deliver",
			count("Sales Order", filters),
			note="%d late" % late if late else "None late",
			tone="rose" if late else "navy",
			route=["List", "Sales Order"],
			filters=filters,
		)

	def card_to_receive(self):
		filters = self.where(docstatus=1, status=["in", list(rules.PURCHASES_OPEN)])
		late = self.attention_count("purchases_late")
		return rules.card(
			"to_receive",
			count("Purchase Order", filters),
			note="%d late" % late if late else "None late",
			tone="rose" if late else "navy",
			route=["List", "Purchase Order"],
			filters=filters,
		)

	def card_quotations(self):
		filters = self.where(docstatus=1, status=["in", list(rules.QUOTATIONS_OPEN)])
		worth = total("Quotation", "base_net_total", filters)
		return rules.card(
			"quotations",
			count("Quotation", filters),
			note={"money": worth, "words": "quoted"} if worth else "Nothing quoted",
			tone="navy",
			route=["List", "Quotation"],
			filters=filters,
		)

	def card_stock_value(self):
		warehouses = self.warehouses()
		value = total("Bin", "stock_value", {"warehouse": ["in", warehouses]}) if warehouses else 0
		return rules.card(
			"stock_value",
			value,
			note="In %d %s" % (len(warehouses), "warehouse" if len(warehouses) == 1 else "warehouses"),
			tone="green",
			route=["query-report", "Stock Balance"],
			options={"company": self.company} if self.company else None,
		)

	def card_reorder(self):
		found = self.reorder()
		return rules.card(
			"reorder",
			found["count"],
			note="%d below zero" % found["short"] if found["short"] else "None below zero",
			tone="rose" if found["short"] else "amber" if found["count"] else "green",
			route=["query-report", "Stock Projected Qty"],
			options={"company": self.company} if self.company else None,
		)

	def card_work_orders(self):
		filters = self.where(docstatus=1, status=["in", list(rules.WORK_ORDERS_OPEN)])
		late = self.attention_count("work_orders_late")
		return rules.card(
			"work_orders",
			count("Work Order", filters),
			note="%d past their planned end" % late if late else "All on time",
			tone="rose" if late else "navy",
			route=["List", "Work Order"],
			filters=filters,
		)

	def card_tasks(self):
		filters = {"status": ["in", list(rules.TASKS_OPEN)]}
		late = self.attention_count("tasks_overdue")
		return rules.card(
			"tasks",
			count("Task", filters),
			note="%d overdue" % late if late else "None overdue",
			tone="rose" if late else "navy",
			route=["List", "Task"],
			filters=filters,
		)

	def card_issues(self):
		filters = {"status": "Open"}
		return rules.card("issues", count("Issue", filters), note="Waiting for a reply", tone="amber", route=["List", "Issue"], filters=filters)

	# ── The panels ───────────────────────────────────────────────────────

	def panel(self, key):
		own = getattr(self, "panel_" + key, None)
		if own:
			found = own()
		elif key in dashboards.GROUPS:
			found = self.declared_group(dashboards.GROUPS[key])
		elif key in dashboards.MONTHLY:
			found = self.declared_months(dashboards.MONTHLY[key])
		else:
			found = self.declared_list(dashboards.LISTS[key])
		if not found:
			return None
		return dict(found, key=key, title=found.get("title") or rules.PANELS[key][0])

	def attention_keys(self):
		if self.tab == dashboards.OVERVIEW:
			return rules.attention_overview(self.tabs, self.readable)
		return rules.attention_in(self.tab, self.readable)

	def panel_attention(self):
		keys = self.attention_keys()
		if not keys:
			return None
		counts = {key: self.attention_count(key) for key in keys}
		return {"kind": "attention", "rows": rules.attention_rows(counts, self.today, self.company)}

	def badges(self):
		"""How much needs attention on each tab, for the tab bar: {tab: {"value", "band"}}."""
		keys = rules.attention_overview(self.tabs, self.readable)
		return rules.badges(rules.attention_rows({key: self.attention_count(key) for key in keys}, self.today, self.company))

	def panel_trend(self):
		"""Six months of what was billed and what came in; for someone who may read
		the orders but not the invoices, what was ordered."""
		months = rules.months(self.today)
		window = ["between", [months[0]["from"], months[-1]["to"]]]
		if self.may("Sales Invoice"):
			series = [("billed", "Billed", "soon", self._by_day("Sales Invoice", "posting_date", "base_net_total", window))]
			if self.may("Payment Entry"):
				received = self._by_day(
					"Payment Entry", "posting_date", "base_received_amount", window, payment_type="Receive"
				)
				series.append(("collected", "Collected", "good", received))
			title = "Sales and Collections" if len(series) > 1 else "Sales by Month"
			doctype, day = "Sales Invoice", "posting_date"
		else:
			series = [("ordered", "Ordered", "soon", self._by_day("Sales Order", "transaction_date", "base_net_total", window))]
			title, doctype, day = "Orders by Month", "Sales Order", "transaction_date"
		columns = [rules.by_month(rows, months) for _key, _label, _band, rows in series]
		return {
			"kind": "columns",
			"title": title,
			"note": "Last %d months, before tax" % len(months),
			"series": [{"key": key, "label": label, "band": band} for key, label, band, _rows in series],
			"months": [dict(month, values=[column[index] for column in columns]) for index, month in enumerate(months)],
			"route": ["List", doctype],
			"day": day,
			"filters": self.where(docstatus=1),
		}

	def _by_day(self, doctype, day, field, window, **filters):
		return grouped(doctype, day, field, self.where(docstatus=1, **{day: window}, **filters), alias="day")

	def panel_aging(self):
		owed = self.owed("Sales Invoice")
		if not owed["total"]:
			return {"kind": "aging", "buckets": [], "rows": [], "note": "Nothing owed"}
		return {
			"kind": "aging",
			"note": "Owed by customers, by days overdue",
			"buckets": rules.aging(owed["by_due"], self.today),
			"rows": rules.most_overdue(self.overdue("Sales Invoice", "customer"), self.today),
			"route": ["List", "Sales Invoice"],
			"filters": self.where(docstatus=1, outstanding_amount=[">", 0]),
		}

	def panel_cash(self):
		accounts = self.cash()
		rows = [
			{
				"label": rules.short_name(row["account"]),
				"value": row["value"],
				"band": "overdue" if row["value"] < 0 else "good",
				"route": ["query-report", "General Ledger"],
				"options": self._ledger_options([row["account"]]),
			}
			for row in sorted(accounts, key=lambda row: -row["value"])
		]
		return {"kind": "bars", "money": 1, "rows": rows, "note": "Balance today", "empty": "No bank or cash accounts"}

	def panel_customers(self):
		first, today = rules.this_month(self.today)
		if self.may("Sales Invoice"):
			doctype, day, words = "Sales Invoice", "posting_date", "Billed this month, before tax"
		else:
			doctype, day, words = "Sales Order", "transaction_date", "Ordered this month, before tax"
		rows = grouped(
			doctype,
			"customer",
			"base_net_total",
			self.where(docstatus=1, **{day: ["between", [str(first), str(today)]]}),
			extra=["customer_name"],
		)
		return {
			"kind": "bars",
			"money": 1,
			"note": words,
			"rows": rules.ranked(rows, "customer_name", "total", name="customer", doctype="Customer"),
			"empty": "No sales yet this month",
		}

	def panel_deliver(self):
		filters = self.where(docstatus=1, status=["in", list(rules.SALES_OPEN)])
		rows = frappe.get_list(
			"Sales Order",
			filters=filters,
			fields=["name", "customer", "customer_name", "delivery_date", "base_grand_total", "per_delivered"],
			order_by="delivery_date asc",
			limit=rules.SHOWN,
		)
		return {
			"kind": "list",
			"rows": rules.due_rows(rows, self.today, "Sales Order", "customer_name", "delivery_date",
				value="base_grand_total", done="per_delivered"),
			"total": count("Sales Order", filters),
			"route": ["List", "Sales Order"],
			"filters": filters,
			"empty": "Every order is delivered",
			"progress": "delivered",
		}

	def panel_receive(self):
		filters = self.where(docstatus=1, status=["in", list(rules.PURCHASES_OPEN)])
		rows = frappe.get_list(
			"Purchase Order",
			filters=filters,
			fields=["name", "supplier", "supplier_name", "schedule_date", "base_grand_total", "per_received"],
			order_by="schedule_date asc",
			limit=rules.SHOWN,
		)
		return {
			"kind": "list",
			"rows": rules.due_rows(rows, self.today, "Purchase Order", "supplier_name", "schedule_date",
				value="base_grand_total", done="per_received"),
			"total": count("Purchase Order", filters),
			"route": ["List", "Purchase Order"],
			"filters": filters,
			"empty": "Nothing is on its way",
			"progress": "received",
		}

	def panel_reorder(self):
		found = self.reorder()
		return {
			"kind": "reorder",
			"rows": found["rows"],
			"total": found["count"],
			"route": ["query-report", "Stock Projected Qty"],
			"options": {"company": self.company} if self.company else None,
			"empty": "Everything is above its reorder level",
		}

	def panel_production(self):
		filters = self.where(docstatus=1, status=["in", list(rules.WORK_ORDERS_OPEN)])
		rows = frappe.get_list(
			"Work Order",
			filters=filters,
			fields=["name", "production_item", "item_name", "planned_end_date", "qty", "produced_qty"],
			order_by="planned_end_date asc",
			limit=rules.SHOWN,
		)
		return {
			"kind": "list",
			"rows": rules.due_rows(rows, self.today, "Work Order", "item_name", "planned_end_date",
				done="produced_qty", total="qty"),
			"total": count("Work Order", filters),
			"route": ["List", "Work Order"],
			"filters": filters,
			"empty": "No work orders open",
			"progress": "made",
		}

	def panel_tasks(self):
		filters = {"status": ["in", list(rules.TASKS_OPEN)], "exp_end_date": ["is", "set"]}
		rows = frappe.get_list(
			"Task",
			filters=filters,
			fields=["name", "subject", "project", "exp_end_date", "progress"],
			order_by="exp_end_date asc",
			limit=rules.SHOWN,
		)
		return {
			"kind": "list",
			"rows": rules.due_rows(rows, self.today, "Task", "subject", "exp_end_date", done="progress"),
			"total": count("Task", filters),
			"route": ["List", "Task"],
			"filters": filters,
			"empty": "No open tasks with an end date",
			"progress": "done",
		}

	def panel_drafts(self):
		since = str(add_days(self.today, -rules.MADE_DAYS))
		found = []
		for doctype in rules.DRAFT_DOCTYPES:
			if not self.may(doctype):
				continue
			title = _title_field(doctype)
			fields = ["name", "modified"] + (["%s as title" % title] if title else [])
			for row in frappe.get_list(
				doctype,
				filters={"owner": frappe.session.user, "docstatus": 0, "creation": [">=", since]},
				fields=fields,
				order_by="modified asc",
				limit=rules.SHOWN,
			):
				found.append((doctype, row))
		listed = rules.drafts(found, self.today)
		return {
			"kind": "list",
			"rows": listed["rows"],
			"total": listed["count"],
			"note": "From the last %d days" % rules.MADE_DAYS,
			"empty": "No drafts left open",
		}

	def panel_profit(self):
		"""Six months of income against expenses, from the ledger, and what was left."""
		months = rules.months(self.today)
		window = ["between", [months[0]["from"], months[-1]["to"]]]
		income = rules.signed(self._ledger_by_day(self.accounts("Income"), window), "income")
		expenses = rules.signed(self._ledger_by_day(self.accounts("Expense"), window), "expense")
		rows = rules.profit(income, expenses, months)
		return {
			"kind": "columns",
			"note": "Last %d months, from the ledger" % len(months),
			"series": [
				{"key": "income", "label": "Income", "band": "good"},
				{"key": "expenses", "label": "Expenses", "band": "overdue"},
			],
			"months": rows,
			"net": {"label": "Profit", "margin": rules.margin(rows[-1])},
			"route": ["query-report", "Profit and Loss Statement"],
			"options": {"company": self.company} if self.company else None,
		}

	def _ledger_by_day(self, accounts, window):
		"""The ledger's debits and credits on these accounts, by day. A year's closing
		entry, which empties income and expenses into the balance sheet, is left out."""
		if not accounts:
			return []
		return frappe.get_list(
			"GL Entry",
			filters=self.where(
				account=["in", accounts],
				is_cancelled=0,
				posting_date=window,
				voucher_type=["!=", "Period Closing Voucher"],
			),
			fields=["posting_date as day", aggregate("SUM", "debit", "debit"), aggregate("SUM", "credit", "credit")],
			group_by="posting_date",
			order_by="posting_date asc",
			limit_page_length=0,
		)

	def panel_expenses(self):
		"""This month's expenses by account, the largest as they are and the rest as one."""
		first, today = rules.this_month(self.today)
		accounts = self.accounts("Expense")
		rows = []
		if accounts:
			rows = frappe.get_list(
				"GL Entry",
				filters=self.where(
					account=["in", accounts],
					is_cancelled=0,
					posting_date=["between", [str(first), str(today)]],
					voucher_type=["!=", "Period Closing Voucher"],
				),
				fields=["account", aggregate("SUM", "debit", "debit"), aggregate("SUM", "credit", "credit")],
				group_by="account",
				order_by="account asc",
				limit_page_length=0,
			)
		spent = [
			{
				"label": rules.short_name(row.get("account")),
				"account": row.get("account"),
				"total": rules._number(row.get("debit")) - rules._number(row.get("credit")),
			}
			for row in rows
		]
		parts = rules.slices(spent, "label", "total")
		account_of = {row["label"]: row["account"] for row in spent}
		for part in parts:
			account = account_of.get(part["key"]) if part["key"] else None
			part["route"] = ["query-report", "General Ledger"]
			part["options"] = self._ledger_options([account] if account else accounts, first)
		return {"kind": "donut", "money": 1, "rows": parts, "note": "Since the 1st", "empty": "No expenses booked this month"}

	def panel_payables(self):
		owed = self.owed("Purchase Invoice")
		if not owed["total"]:
			return {"kind": "aging", "buckets": [], "rows": [], "note": "Nothing owed"}
		return {
			"kind": "aging",
			"note": "Owed to suppliers, by days overdue",
			"buckets": rules.aging(owed["by_due"], self.today),
			"rows": rules.most_overdue(
				self.overdue("Purchase Invoice", "supplier"), self.today, doctype="Supplier", party="supplier"
			),
			"owing": "Owed the most past due",
			"route": ["List", "Purchase Invoice"],
			"filters": self.where(docstatus=1, outstanding_amount=[">", 0]),
		}

	def _selling(self):
		"""Where this month's sales are read from: the invoices, or for someone who may
		not read them, the orders. (doctype, its lines, its date, what it says)"""
		if self.may("Sales Invoice"):
			return "Sales Invoice", "Sales Invoice Item", "posting_date", "Billed this month, before tax"
		return "Sales Order", "Sales Order Item", "transaction_date", "Ordered this month, before tax"

	def panel_items(self):
		"""This month's best-selling items by value, from the lines of the documents
		the user may read."""
		doctype, lines, day, words = self._selling()
		first, today = rules.this_month(self.today)
		names = frappe.get_list(
			doctype,
			filters=self.where(docstatus=1, **{day: ["between", [str(first), str(today)]]}),
			pluck="name",
			limit_page_length=0,
		)
		merged = {}
		for start in range(0, len(names), 500):
			for row in grouped(
				lines,
				"item_code",
				"base_net_amount",
				{"parenttype": doctype, "parent": ["in", names[start : start + 500]]},
				extra=["item_name"],
				checked=False,
			):
				found = merged.setdefault(
					row.get("item_code"), {"item_code": row.get("item_code"), "item_name": row.get("item_name"), "total": 0.0}
				)
				found["total"] += rules._number(row.get("total"))
		return {
			"kind": "bars",
			"money": 1,
			"note": words,
			"rows": rules.ranked(list(merged.values()), "item_name", "total", name="item_code", doctype="Item"),
			"empty": "Nothing sold yet this month",
		}

	def panel_territories(self):
		"""This month's sales by territory, as shares of the whole."""
		doctype, _lines, day, words = self._selling()
		first, today = rules.this_month(self.today)
		window = self.where(docstatus=1, **{day: ["between", [str(first), str(today)]]})
		parts = rules.slices(grouped(doctype, "territory", "base_net_total", window), "territory", "total")
		for part in parts:
			part["route"] = ["List", doctype]
			part["filters"] = dict(window, territory=part["key"]) if part["key"] else dict(window)
		return {"kind": "donut", "money": 1, "rows": parts, "note": words, "empty": "No sales yet this month"}

	def panel_quotations(self):
		"""The last 90 days' quotations by where they stand, and how many of those
		decided were won."""
		since = str(add_days(self.today, -rules.QUOTATION_DAYS))
		window = self.where(docstatus=1, transaction_date=[">=", since])
		rows = frappe.get_list(
			"Quotation",
			filters=window,
			fields=["status", aggregate("COUNT", "*", "count"), aggregate("SUM", "base_net_total", "total")],
			group_by="status",
			order_by="status asc",
			limit_page_length=0,
		)
		found = rules.quotation_stages(rows)
		return {
			"kind": "stages",
			"stages": found["stages"],
			"won": found["won"],
			"note": "Quoted since %s" % since,
			"route": ["List", "Quotation"],
			"filters": window,
		}

	def panel_suppliers(self):
		first, today = rules.this_month(self.today)
		if self.may("Purchase Invoice"):
			doctype, day, words = "Purchase Invoice", "posting_date", "Billed this month, before tax"
		else:
			doctype, day, words = "Purchase Order", "transaction_date", "Ordered this month, before tax"
		rows = grouped(
			doctype,
			"supplier",
			"base_net_total",
			self.where(docstatus=1, **{day: ["between", [str(first), str(today)]]}),
			extra=["supplier_name"],
		)
		return {
			"kind": "bars",
			"money": 1,
			"note": words,
			"rows": rules.ranked(rows, "supplier_name", "total", name="supplier", doctype="Supplier"),
			"empty": "No purchases yet this month",
		}

	def panel_warehouses(self):
		"""The stock's value in each of the company's warehouses, as shares of the whole."""
		warehouses = self.warehouses()
		rows = grouped("Bin", "warehouse", "stock_value", {"warehouse": ["in", warehouses]}) if warehouses else []
		values = [
			{"label": rules.short_name(row.get("warehouse")), "warehouse": row.get("warehouse"), "total": row.get("total")}
			for row in rows
		]
		parts = rules.slices(values, "label", "total")
		warehouse_of = {row["label"]: row["warehouse"] for row in values}
		for part in parts:
			options = {"company": self.company} if self.company else {}
			if part["key"]:
				options["warehouse"] = warehouse_of.get(part["key"])
			part["route"] = ["query-report", "Stock Balance"]
			part["options"] = options
		return {"kind": "donut", "money": 1, "rows": parts, "note": "Value in stock today", "empty": "No stock held"}

	def panel_projects(self):
		filters = self.where(status="Open")
		rows = frappe.get_list(
			"Project",
			filters=filters,
			fields=["name", "project_name", "percent_complete", "expected_end_date"],
			order_by="expected_end_date asc",
			limit=rules.SHOWN,
		)
		return {
			"kind": "progress",
			"rows": rules.due_rows(rows, self.today, "Project", "project_name", "expected_end_date", done="percent_complete"),
			"total": count("Project", filters),
			"route": ["List", "Project"],
			"filters": filters,
			"empty": "No projects open",
		}

	def panel_issues(self):
		filters = {"status": "Open"}
		rows = frappe.get_list(
			"Issue",
			filters=filters,
			fields=["name", "subject", "opening_date"],
			order_by="opening_date asc",
			limit=rules.SHOWN,
		)
		return {
			"kind": "list",
			"rows": rules.open_for(rows, self.today, "Issue", "subject", "opening_date"),
			"total": count("Issue", filters),
			"route": ["List", "Issue"],
			"filters": filters,
			"empty": "No issues waiting for a reply",
		}

	# ── Declared in dashboards_rules.py ──────────────────────────────────

	def filled(self, spec, extra=None):
		"""A declared part's filters on this day, narrowed to the company or its
		warehouses where it says so."""
		filters = dashboards.fill(dict(spec.get("filters") or {}, **(extra or {})), self.days)
		if spec.get("company") and self.company:
			filters.setdefault("company", self.company)
		if spec.get("warehouses"):
			filters["warehouse"] = ["in", self.warehouses() or [""]]
		return filters

	def declared_card(self, key, spec):
		"""A figure declared in dashboards_rules.FIGURES: how many, or the sum of a
		field, and how many of them are late where it says how to tell."""
		filters = self.filled(spec)
		if spec["function"] == "COUNT":
			value = count(spec["doctype"], filters)
		else:
			value = total(spec["doctype"], spec["field"], filters)
		note, tone = spec.get("note") or "", spec.get("tone") or "navy"
		if spec.get("late"):
			late = count(spec["doctype"], self.filled(spec, spec["late"]))
			if late:
				note, tone = "%d %s" % (late, spec.get("late_words") or "late"), "rose"
		if not value and spec.get("quiet"):
			tone = spec["quiet"]
		route = spec.get("route") or ["List", spec["doctype"]]
		return rules.card(key, value, note=note, tone=tone, route=route, filters=filters if route[0] == "List" else None)

	def declared_group(self, spec):
		"""A breakdown declared in dashboards_rules.GROUPS: a sum or a count for each
		value of a field, as bars or a ring, each opening its documents."""
		filters = self.filled(spec)
		by = spec["by"]
		if spec["function"] == "COUNT":
			rows = frappe.get_list(
				spec["doctype"],
				filters=filters,
				fields=[by, aggregate("COUNT", "*", "total")],
				group_by=by,
				order_by="%s asc" % by,
				limit_page_length=0,
			)
		else:
			rows = grouped(spec["doctype"], by, spec["field"], filters)
		none = spec.get("none") or "Not set"
		values = [{"label": row.get(by) or none, "value": row.get("total"), "key": row.get(by)} for row in rows]
		bands = spec.get("bands") or {}
		if spec.get("draw") == "donut":
			parts = rules.slices(values, "label", "value")
		else:
			parts = rules.ranked(values, "label", "value", shown=rules.SHOWN)
		key_of = {item["label"]: item["key"] for item in values}
		for part in parts:
			part["route"] = ["List", spec["doctype"]]
			if "key" in part and part["key"] is None:
				# the rest, put together: the whole list
				part["filters"] = dict(filters)
			else:
				value = key_of.get(part["label"])
				part["filters"] = dict(filters, **{by: value if value else ["is", "not set"]})
			if part["label"] in bands:
				part["band"] = bands[part["label"]]
		return {
			"kind": "donut" if spec.get("draw") == "donut" else "bars",
			"money": spec.get("money") or 0,
			"rows": parts,
			"note": spec.get("note") or "",
			"empty": spec.get("empty") or "Nothing to show yet",
		}

	def declared_months(self, spec):
		"""Six months declared in dashboards_rules.MONTHLY: each series a sum or a
		count by its date, a series whose doctype the user may not read left out."""
		months = rules.months(self.today)
		window = ["between", [months[0]["from"], months[-1]["to"]]]
		series, columns = [], []
		for one in spec["series"]:
			if not self.may(one["doctype"]):
				continue
			filters = self.filled(dict(one, company=spec.get("company")), {one["day"]: window})
			if one["function"] == "COUNT":
				rows = frappe.get_list(
					one["doctype"],
					filters=filters,
					fields=["%s as day" % one["day"], aggregate("COUNT", "*", "total")],
					group_by=one["day"],
					order_by="%s asc" % one["day"],
					limit_page_length=0,
				)
			else:
				rows = grouped(one["doctype"], one["day"], one["field"], filters, alias="day")
			column = rules.by_month(rows, months)
			if one.get("negate"):
				column = [-value for value in column]
			series.append({"key": one["key"], "label": one["label"], "band": one["band"]})
			columns.append(column)
		if not series:
			return None
		first = next(one for one in spec["series"] if self.may(one["doctype"]))
		return {
			"kind": "columns",
			"title": spec["title"],
			"note": spec.get("note") or "",
			"money": spec.get("money", 1),
			"series": series,
			"months": [dict(month, values=[column[index] for column in columns]) for index, month in enumerate(months)],
			"route": ["List", first["doctype"]],
			"day": first["day"],
			"filters": self.filled(dict(first, company=spec.get("company"))),
		}

	def declared_list(self, spec):
		"""A list declared in dashboards_rules.LISTS: what is due, the soonest first,
		or what is open, the longest open first."""
		filters = self.filled(spec)
		order = spec.get("due") or spec.get("opened")
		rows = frappe.get_list(
			spec["doctype"], filters=filters, fields=list(spec["fields"]), order_by="%s asc" % order, limit=rules.SHOWN
		)
		if spec.get("due"):
			listed = rules.due_rows(
				rows, self.today, spec["doctype"], spec["title_field"], spec["due"], value=spec.get("value"), done=spec.get("done")
			)
		else:
			listed = rules.open_for(rows, self.today, spec["doctype"], spec["title_field"], spec["opened"])
		return {
			"kind": "list",
			"rows": listed,
			"total": count(spec["doctype"], filters),
			"route": ["List", spec["doctype"]],
			"filters": filters,
			"empty": spec.get("empty") or "Nothing here",
		}

	def panel_hours_by_project(self):
		"""This month's hours on submitted timesheets, by project, from the lines of the
		timesheets the user may read."""
		names = frappe.get_list(
			"Timesheet",
			filters=self.where(docstatus=1, start_date=[">=", self.days["{month}"]]),
			pluck="name",
			limit_page_length=0,
		)
		merged = {}
		for start in range(0, len(names), 500):
			for row in grouped(
				"Timesheet Detail",
				"project",
				"hours",
				{"parenttype": "Timesheet", "parent": ["in", names[start : start + 500]]},
				checked=False,
			):
				label = row.get("project") or "No project"
				found = merged.setdefault(label, {"label": label, "project": row.get("project"), "total": 0.0})
				found["total"] += rules._number(row.get("total"))
		bars = rules.ranked(list(merged.values()), "label", "total", name="project", doctype="Project")
		for bar in bars:
			if not bar.get("docname"):
				bar.pop("doctype", None)
				bar.pop("docname", None)
		return {"kind": "bars", "hours": 1, "rows": bars, "note": "Submitted this month", "empty": "No hours booked this month"}

	# ── Shared reads ─────────────────────────────────────────────────────

	def accounts(self, root_type):
		"""The company's ledger accounts of one kind (Income, Expense), groups left out."""
		return self.once(("accounts", root_type), self._accounts, root_type)

	def _accounts(self, root_type):
		return frappe.get_list("Account", filters=self.where(root_type=root_type, is_group=0), pluck="name", limit_page_length=0)

	def owed(self, doctype):
		return self.once(("owed", doctype), self._owed, doctype)

	def _owed(self, doctype):
		"""What is still owed on the doctype's submitted invoices, in the company's
		currency: in all, overdue, due within the week, and by due date."""
		rows = grouped(
			doctype,
			"due_date, party_account_currency",
			"outstanding_amount",
			self.where(docstatus=1, outstanding_amount=[">", 0]),
			order_by="due_date asc",
		)
		rates = self.rates({row.get("party_account_currency") for row in rows})
		by_due, overdue, week = [], 0.0, 0.0
		soon = add_days(self.today, rules.WEEK)
		for row in rows:
			value = rules._number(row.get("total")) * rates.get(row.get("party_account_currency"), 1.0)
			due = rules._day(row.get("due_date"))
			by_due.append({"due_date": row.get("due_date"), "total": value})
			if due and due < self.today:
				overdue += value
			if due and due <= soon:
				week += value
		return {
			"total": round(sum(row["total"] for row in by_due), 2),
			"overdue": round(overdue, 2),
			"week": round(week, 2),
			"by_due": by_due,
		}

	def overdue(self, doctype, party):
		"""What each party owes, or is owed, past its due date on the doctype's
		invoices, in the company's currency, with the oldest due date among them."""
		rows = grouped(
			doctype,
			"%s, party_account_currency" % party,
			"outstanding_amount",
			self.where(docstatus=1, outstanding_amount=[">", 0], due_date=["<", str(self.today)]),
			extra=[party + "_name", aggregate("MIN", "due_date", "oldest")],
		)
		rates = self.rates({row.get("party_account_currency") for row in rows})
		merged = {}
		for row in rows:
			value = rules._number(row.get("total")) * rates.get(row.get("party_account_currency"), 1.0)
			found = merged.setdefault(
				row.get(party),
				{party: row.get(party), party + "_name": row.get(party + "_name"), "total": 0.0, "oldest": None},
			)
			found["total"] += value
			oldest = rules._day(row.get("oldest"))
			if oldest and (not found["oldest"] or oldest < found["oldest"]):
				found["oldest"] = oldest
		return list(merged.values())

	def rates(self, currencies):
		"""Today's rate into the company's currency for each currency other than
		its own. One with no rate on record counts at 1, and is logged."""
		out = {}
		for currency in currencies:
			if not currency or not self.currency or currency == self.currency:
				continue
			rate = _or(None, _exchange_rate, currency, self.currency, self.today, title="exchange rate " + currency)
			out[currency] = rate or 1.0
		return out

	def cash(self):
		return self.once("cash", self._cash)

	def _cash(self):
		"""Each bank and cash account of the company with its balance today, in the
		company's currency."""
		accounts = frappe.get_list(
			"Account",
			filters=self.where(account_type=["in", ["Bank", "Cash"]], is_group=0, disabled=0),
			pluck="name",
			limit_page_length=0,
		)
		if not accounts:
			return []
		rows = frappe.get_list(
			"GL Entry",
			filters=self.where(account=["in", accounts], is_cancelled=0, posting_date=["<=", str(self.today)]),
			fields=["account", aggregate("SUM", "debit", "debit"), aggregate("SUM", "credit", "credit")],
			group_by="account",
			order_by="account asc",
			limit_page_length=0,
		)
		balance = {row.get("account"): rules._number(row.get("debit")) - rules._number(row.get("credit")) for row in rows}
		return [{"account": account, "value": round(balance.get(account, 0.0), 2)} for account in accounts]

	def _ledger_options(self, accounts, since=None):
		options = {"from_date": str(since or self.today.replace(month=1, day=1)), "to_date": str(self.today)}
		if self.company:
			options["company"] = self.company
		if accounts:
			options["account"] = list(accounts)
		return options

	def warehouses(self):
		return self.once("warehouses", self._warehouses)

	def _warehouses(self):
		return frappe.get_list(
			"Warehouse", filters=self.where(is_group=0, disabled=0), pluck="name", limit_page_length=0
		)

	def reorder(self):
		return self.once("reorder", self._reorder)

	def _reorder(self):
		"""The company's stock at or under its reorder level, or below zero."""
		warehouses = self.warehouses()
		if not warehouses:
			return rules.to_reorder([], [])
		levels = frappe.get_all(
			"Item Reorder",
			filters={"parenttype": "Item", "warehouse": ["in", warehouses]},
			fields=["parent as item_code", "warehouse", "warehouse_reorder_level as level"],
			limit_page_length=0,
		)
		items = sorted({row.get("item_code") for row in levels})
		bins = []
		if items:
			bins += frappe.get_list(
				"Bin",
				filters={"warehouse": ["in", warehouses], "item_code": ["in", items]},
				fields=["item_code", "warehouse", "projected_qty"],
				limit_page_length=0,
			)
		seen = {(row.get("item_code"), row.get("warehouse")) for row in bins}
		bins += [
			row
			for row in frappe.get_list(
				"Bin",
				filters={"warehouse": ["in", warehouses], "projected_qty": ["<", 0]},
				fields=["item_code", "warehouse", "projected_qty"],
				limit_page_length=0,
			)
			if (row.get("item_code"), row.get("warehouse")) not in seen
		]
		found = rules.to_reorder(levels, bins)
		names = {row["docname"] for row in found["rows"]}
		if names:
			titles = {
				row.name: row.item_name
				for row in frappe.get_list(
					"Item", filters={"name": ["in", sorted(names)]}, fields=["name", "item_name"], limit_page_length=0
				)
			}
			for row in found["rows"]:
				row["title"] = titles.get(row["docname"]) or row["title"]
		return found

	def attention_count(self, key):
		doctype = rules.ATTENTION_DOCTYPE[key]
		if not self.may(doctype):
			return 0
		return self.once(("attention", key), count, doctype, rules.attention_filters(key, self.today, self.company))


# ── Reading the site ─────────────────────────────────────────────────────────


def aggregate(function, field, alias):
	"""SUM, COUNT, MIN or MAX as a get_list field. Frappe v16 no longer takes SQL as
	a string in a field and wants it as a dict; v15 takes only the string."""
	if _major() >= 16:
		return {function: field, "as": alias}
	return "%s(%s) as %s" % (function.lower(), field if field == "*" else "`%s`" % field, alias)


def total(doctype, field, filters):
	"""The sum of a field over the documents the user may read."""
	rows = frappe.get_list(doctype, filters=filters, fields=[aggregate("SUM", field, "total")], order_by=None)
	return rules._number(rows[0].get("total")) if rows else 0.0


def count(doctype, filters):
	"""How many documents the user may read match the filters."""
	rows = frappe.get_list(doctype, filters=filters, fields=[aggregate("COUNT", "*", "count")], order_by=None)
	return int(rules._number(rows[0].get("count"))) if rows else 0


def grouped(doctype, by, field, filters, alias=None, extra=None, order_by=None, checked=True):
	"""The sum of a field for each value of `by` (one field, or several separated by
	commas), over the documents the user may read: [{by..., "total"}]. alias
	renames a single `by` field in the rows; extra adds fields to them. checked=False
	reads a child table's rows, whose parents the caller has already read with the
	user's permissions: a child table has no permissions of its own to check."""
	names = [name.strip() for name in by.split(",") if name.strip()]
	fields = ["%s as %s" % (names[0], alias)] if alias and len(names) == 1 else list(names)
	fields += list(extra or ()) + [aggregate("SUM", field, "total")]
	return (frappe.get_list if checked else frappe.get_all)(
		doctype,
		filters=filters,
		fields=fields,
		group_by=", ".join(names),
		order_by=order_by or "%s asc" % names[0],
		limit_page_length=0,
	)


def _major():
	try:
		return int(str(frappe.__version__).split(".")[0])
	except (AttributeError, ValueError):
		return 16


def _readable():
	"""Of the doctypes the home reads from, those the site has and the user may read."""
	return _permitted(DOCTYPES, "read")


def _permitted(doctypes, ptype):
	"""Of these doctypes, those the site has (asked in one query) and the user may `ptype`."""
	try:
		present = set(frappe.get_all("DocType", filters={"name": ["in", list(doctypes)]}, pluck="name"))
	except Exception:
		return set()
	out = set()
	for doctype in present:
		try:
			if frappe.has_permission(doctype, ptype):
				out.add(doctype)
		except Exception:
			continue
	return out


def _blocked_modules(user):
	"""The modules a user is kept from: those blocked on their user record (or by
	their Module Profile), and those blocked for everyone on the Administrator's,
	as Frappe's own list of a user's modules has it (utils/modules.py)."""
	blocked = set(frappe.get_cached_doc("User", user).get_blocked_modules() or ())
	if user != "Administrator":
		blocked |= set(frappe.get_cached_doc("User", "Administrator").get_blocked_modules() or ())
	return blocked


def _allowed_reports():
	"""The reports the user may open, as Frappe's search lists them, or None where
	this Frappe cannot say (each report is then offered to whoever may read what
	it reports on)."""
	from frappe.desk.desk_views import DeskViews

	return set(DeskViews.get_allowed_report_names(cache=True))


def _signed_in():
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Log in to see your home."), frappe.PermissionError)
	return user


def _alerts():
	"""The user's own assignments and notifications, as My Alerts lists them."""
	return alerts.my_alerts(limit=40)["alerts"]


def _first_name(user):
	return frappe.db.get_value("User", user, "first_name")


def _company():
	return frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")


def _currency(company):
	return frappe.get_cached_value("Company", company, "default_currency")


def _exchange_rate(from_currency, to_currency, day):
	from erpnext.setup.utils import get_exchange_rate

	return get_exchange_rate(from_currency, to_currency, str(day))


def _title_field(doctype):
	"""The field a doctype's documents are titled by, where it has one of its own."""
	meta = frappe.get_meta(doctype)
	field = getattr(meta, "title_field", None)
	return field if field and field != "name" and meta.has_field(field) else None


def _made(user, desks, today):
	"""What the user makes most, kept for an hour: how many of each doctype they
	made in the last MADE_DAYS days, of those they may make."""
	kept = _or(None, _kept, user, MADE_KEY)
	if kept is not None and kept.get("day") == str(today) and kept.get("desks") == desks:
		return kept.get("made") or []
	creatable = _permitted(
		dict.fromkeys(rules.CREATE + tuple(d for desk in desks for d in rules.DESK_CREATE.get(desk, ()))), "create"
	)
	since = str(add_days(today, -rules.MADE_DAYS))
	# counted from the documents themselves, so only where the user may read them too
	countable = creatable & _permitted(rules.CREATE, "read")
	counts = {
		doctype: _or(0, count, doctype, {"owner": user, "creation": [">=", since]}, title="made: " + doctype)
		for doctype in rules.CREATE
		if doctype in countable
	}
	made = rules.most_made(counts, desks, creatable)
	_or(None, _keep, user, MADE_KEY, {"day": str(today), "desks": desks, "made": made}, MADE_SECONDS)
	return made


def _kept(user, key):
	return frappe.cache.get_value(key, user=user)


def _keep(user, key, value, seconds):
	frappe.cache.set_value(key, value, user=user, expires_in_sec=seconds)


def _or(fallback, read, *args, title=None):
	"""What `read` gives, or `fallback` where it cannot be read. Logged with
	defer_insert: a GET is rolled back, and the log has to outlive it."""
	try:
		return read(*args)
	except Exception:
		try:
			frappe.log_error(title="CyveTech home: %s" % (title or getattr(read, "__name__", "read")), defer_insert=True)
		except Exception:
			pass
		return fallback
