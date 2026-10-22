# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""The desk home's dashboards: a tab for each module, and what is on it.

No Frappe import, so tests/test_home_rules.py checks it without a bench.
home_rules.py says whose figures are whose and works them out; this says what
each module's tab holds: its figures across the top, its dashboards, and the
reports a decision is made from. home.py reads the site for them, and
public/js/cyvetech_ui_home.js draws the tabs (the user, 22 Oct 2026: "add more
dashboard and report for every module, and add navigation tab on the desk for
someone to view the dashboards quickly for decision making").

A TAB IS THERE WHERE ITS MODULE IS ASSIGNED

A module's tab is on a user's desk only where the module is theirs, not
blocked by their Module Profile or the Modules on their user, and only with
the figures and dashboards whose documents they may read: a tab left with
nothing is not shown. Its reports are those the user may open. Overview is
on every desk.

MOST FIGURES ARE DECLARED, NOT WRITTEN

A figure, a breakdown, six months of something or a list of what is due is
declared here (FIGURES, GROUPS, MONTHLY, LISTS) and read by one reader for
each kind in home.py. Their filters may name the day: "{today}", "{month}"
(the 1st of this month), "{week}" (a week from today) and "{since90}" (90 days
ago); fill() puts in the dates. "company": True narrows one to the user's
company, and "warehouses": True to its warehouses. The figures that need more
than that (the aging, the cash, the profit) are home_rules.py's own.
"""

import datetime

MONEY, COUNT, HOURS = "money", "count", "hours"
WIDE, NORMAL = "wide", "normal"

# ── The tabs ─────────────────────────────────────────────────────────────────

OVERVIEW = "overview"

# Each module's tab, in the usual order: what it is called, the module it belongs
# to (Module Def), the documents that make it the module it is (a tab is offered
# only to someone who may read one of them, so a figure two modules share does not
# bring a module's tab along), the picture on it, the workspaces it is the
# dashboard of, its figures, its dashboards, and its reports. A user's own modules
# come first (home_rules.tabs_for).
TABS = (
	{
		"key": "accounts",
		"anchors": ("Sales Invoice", "Purchase Invoice", "GL Entry"),
		"title": "Accounts",
		"module": "Accounts",
		"icon": "cash",
		"workspaces": ("Invoicing", "Payments", "Financial Reports", "Accounts Setup", "Banking", "Taxes", "Budget",
			"Share Management", "Subscription"),
		"cards": ("sales", "receivable", "payable", "cash"),
		"panels": ("attention", "trend", "profit", "cash", "expenses", "aging", "payables"),
		"reports": (
			"Profit and Loss Statement",
			"Balance Sheet",
			"Cash Flow",
			"Trial Balance",
			"General Ledger",
			"Accounts Receivable",
			"Accounts Payable",
			"Gross Profit",
			"Sales Register",
			"Purchase Register",
		),
	},
	{
		"key": "selling",
		"anchors": ("Sales Order", "Quotation"),
		"title": "Sales",
		"module": "Selling",
		"icon": "sales",
		"workspaces": ("Selling",),
		"cards": ("orders", "to_deliver", "quotations", "sales"),
		"panels": ("attention", "sales_trend", "customers", "items", "territories", "quotations", "deliver"),
		"reports": (
			"Sales Analytics",
			"Sales Order Analysis",
			"Item-wise Sales History",
			"Sales Person-wise Transaction Summary",
			"Customer Acquisition and Loyalty",
			"Inactive Customers",
			"Quotation Trends",
			"Lost Quotations",
		),
	},
	{
		"key": "buying",
		"anchors": ("Purchase Order", "Supplier Quotation"),
		"title": "Purchasing",
		"module": "Buying",
		"icon": "purchases",
		"workspaces": ("Buying",),
		"cards": ("purchases", "to_receive", "requests", "payable"),
		"panels": ("attention", "purchase_trend", "receive", "suppliers", "requests_list", "payables"),
		"reports": (
			"Purchase Analytics",
			"Purchase Order Analysis",
			"Procurement Tracker",
			"Item-wise Purchase History",
			"Supplier Quotation Comparison",
			"Requested Items to Order and Receive",
		),
	},
	{
		"key": "stock",
		"anchors": ("Bin", "Stock Ledger Entry"),
		"title": "Stock",
		"module": "Stock",
		"icon": "stock_value",
		"workspaces": ("Stock",),
		"cards": ("stock_value", "reorder", "negative", "to_deliver"),
		"panels": ("attention", "stock_moves", "warehouses", "reorder", "deliver", "receive"),
		"reports": (
			"Stock Balance",
			"Stock Ledger",
			"Stock Projected Qty",
			"Stock Ageing",
			"Warehouse wise Item Balance Age and Value",
			"Itemwise Recommended Reorder Level",
			"Stock Analytics",
			"Delayed Order Report",
		),
	},
	{
		"key": "manufacturing",
		"anchors": ("Work Order", "Job Card"),
		"title": "Manufacturing",
		"module": "Manufacturing",
		"icon": "work_orders",
		"workspaces": ("Manufacturing", "Subcontracting"),
		"cards": ("work_orders", "job_cards", "completed", "reorder"),
		"panels": ("attention", "production_trend", "production", "work_order_status", "job_cards_list"),
		"reports": (
			"Production Planning Report",
			"Work Order Summary",
			"Open Work Orders",
			"Work Orders in Progress",
			"Completed Work Orders",
			"Job Card Summary",
			"BOM Stock Analysis",
			"Production Analytics",
		),
	},
	{
		"key": "projects",
		"anchors": ("Project", "Task", "Timesheet"),
		"title": "Projects",
		"module": "Projects",
		"icon": "tasks",
		"workspaces": ("Projects",),
		"cards": ("projects_open", "tasks", "hours"),
		"panels": ("attention", "projects", "tasks", "hours_by_project"),
		"reports": (
			"Project Summary",
			"Delayed Tasks Summary",
			"Daily Timesheet Summary",
			"Timesheet Billing Summary",
			"Project wise Stock Tracking",
		),
	},
	{
		"key": "crm",
		"anchors": ("Lead", "Opportunity"),
		"title": "CRM",
		"module": "CRM",
		"icon": "customers",
		"workspaces": ("CRM",),
		"cards": ("leads", "opportunities", "pipeline"),
		"panels": ("opportunities_closing", "opportunity_stages", "lead_sources"),
		"reports": (
			"Sales Pipeline Analytics",
			"Opportunity Summary by Sales Stage",
			"Lead Details",
			"Lost Opportunity",
			"Lead Owner Efficiency",
			"Campaign Efficiency",
			"Prospects Engaged But Not Converted",
		),
	},
	{
		"key": "support",
		"anchors": ("Issue",),
		"title": "Support",
		"module": "Support",
		"icon": "issues",
		"workspaces": ("Support",),
		"cards": ("issues", "issues_replied", "issues_on_hold"),
		"panels": ("attention", "issues", "issue_priorities"),
		"reports": ("Issue Analytics", "Issue Summary", "First Response Time for Issues", "Support Hour Distribution"),
	},
	{
		"key": "assets",
		"anchors": ("Asset",),
		"title": "Assets",
		"module": "Assets",
		"icon": "assets",
		"workspaces": ("Assets",),
		"cards": ("asset_value", "assets", "maintenance_due"),
		"panels": ("asset_categories", "maintenance"),
		"reports": (
			"Fixed Asset Register",
			"Asset Depreciation Ledger",
			"Asset Depreciations and Balances",
			"Asset Maintenance",
			"Asset Activity",
		),
	},
	{
		"key": "quality",
		"anchors": ("Quality Inspection", "Non Conformance"),
		"title": "Quality",
		"module": "Quality Management",
		"icon": "quality",
		"workspaces": ("Quality",),
		"cards": ("inspections", "rejected", "non_conformances"),
		"panels": ("inspection_results", "non_conformance_list"),
		"reports": ("Quality Inspection Summary", "Review"),
	},
)
TAB_KEYS = tuple(tab["key"] for tab in TABS)
TAB_TITLES = {OVERVIEW: "Overview", **{tab["key"]: tab["title"] for tab in TABS}}
# the settings switch of each module's tab
SWITCHES = tuple("dash_" + key for key in TAB_KEYS)

# Each report a tab offers, and the doctype it reports on: where Frappe cannot say
# which reports a user may open, one is offered to those who may read its doctype.
REPORT_DOCTYPES = {
	"Profit and Loss Statement": "GL Entry",
	"Balance Sheet": "GL Entry",
	"Cash Flow": "GL Entry",
	"Trial Balance": "GL Entry",
	"General Ledger": "GL Entry",
	"Accounts Receivable": "Sales Invoice",
	"Accounts Payable": "Purchase Invoice",
	"Gross Profit": "Sales Invoice",
	"Sales Register": "Sales Invoice",
	"Purchase Register": "Purchase Invoice",
	"Sales Analytics": "Sales Order",
	"Sales Order Analysis": "Sales Order",
	"Item-wise Sales History": "Sales Order",
	"Sales Person-wise Transaction Summary": "Sales Order",
	"Customer Acquisition and Loyalty": "Customer",
	"Inactive Customers": "Sales Order",
	"Quotation Trends": "Quotation",
	"Lost Quotations": "Quotation",
	"Purchase Analytics": "Purchase Order",
	"Purchase Order Analysis": "Purchase Order",
	"Procurement Tracker": "Purchase Order",
	"Item-wise Purchase History": "Purchase Order",
	"Supplier Quotation Comparison": "Supplier Quotation",
	"Requested Items to Order and Receive": "Material Request",
	"Stock Balance": "Stock Ledger Entry",
	"Stock Ledger": "Stock Ledger Entry",
	"Stock Projected Qty": "Item",
	"Stock Ageing": "Item",
	"Warehouse wise Item Balance Age and Value": "Stock Ledger Entry",
	"Itemwise Recommended Reorder Level": "Item",
	"Stock Analytics": "Stock Entry",
	"Delayed Order Report": "Delivery Note",
	"Production Planning Report": "Work Order",
	"Work Order Summary": "Work Order",
	"Open Work Orders": "Work Order",
	"Work Orders in Progress": "Work Order",
	"Completed Work Orders": "Work Order",
	"Job Card Summary": "Job Card",
	"BOM Stock Analysis": "BOM",
	"Production Analytics": "Work Order",
	"Project Summary": "Project",
	"Delayed Tasks Summary": "Task",
	"Daily Timesheet Summary": "Timesheet",
	"Timesheet Billing Summary": "Timesheet",
	"Project wise Stock Tracking": "Project",
	"Sales Pipeline Analytics": "Opportunity",
	"Opportunity Summary by Sales Stage": "Opportunity",
	"Lead Details": "Lead",
	"Lost Opportunity": "Opportunity",
	"Lead Owner Efficiency": "Lead",
	"Campaign Efficiency": "Lead",
	"Prospects Engaged But Not Converted": "Lead",
	"Issue Analytics": "Issue",
	"Issue Summary": "Issue",
	"First Response Time for Issues": "Issue",
	"Support Hour Distribution": "Issue",
	"Fixed Asset Register": "Asset",
	"Asset Depreciation Ledger": "Asset",
	"Asset Depreciations and Balances": "Asset",
	"Asset Maintenance": "Asset Maintenance",
	"Asset Activity": "Asset Activity",
	"Quality Inspection Summary": "Quality Inspection",
	"Review": "Quality Action",
}

# ── Figures, declared ────────────────────────────────────────────────────────

OPEN_REQUESTS = ("Pending", "Partially Ordered")
OPEN_JOB_CARDS = ("Open", "Work In Progress", "Material Transferred", "On Hold")
OPEN_OPPORTUNITIES = ("Open", "Replied", "Quotation")
ASSETS_GONE = ("Draft", "Sold", "Scrapped", "Cancelled")

# figure: {"label", "kind", "doctype", "function" (COUNT or SUM), "field" (for SUM),
# "filters", "company"/"warehouses", "note" (said under it), "late" (a filter
# added to count how many of it are late, said instead of the note), "tone", "route"}
FIGURES = {
	"requests": {
		"label": "Material Requests Open", "kind": COUNT, "doctype": "Material Request", "function": "COUNT",
		"filters": {"docstatus": 1, "status": ["in", list(OPEN_REQUESTS)]}, "company": True,
		"late": {"schedule_date": ["<", "{today}"]}, "note": "None past their date", "late_words": "past their date",
	},
	"negative": {
		"label": "Items Below Zero", "kind": COUNT, "doctype": "Bin", "function": "COUNT",
		"filters": {"actual_qty": ["<", 0]}, "warehouses": True, "note": "In the company's warehouses", "tone": "rose",
		"quiet": "green",
	},
	"job_cards": {
		"label": "Open Job Cards", "kind": COUNT, "doctype": "Job Card", "function": "COUNT",
		"filters": {"docstatus": 0, "status": ["in", list(OPEN_JOB_CARDS)]}, "company": True,
		"note": "On the shop floor",
	},
	"completed": {
		"label": "Completed This Month", "kind": COUNT, "doctype": "Work Order", "function": "COUNT",
		"filters": {"docstatus": 1, "status": "Completed", "actual_end_date": [">=", "{month}"]}, "company": True,
		"note": "Work orders finished since the 1st", "tone": "green",
	},
	"projects_open": {
		"label": "Open Projects", "kind": COUNT, "doctype": "Project", "function": "COUNT",
		"filters": {"status": "Open"}, "company": True,
		"late": {"expected_end_date": ["<", "{today}"]}, "note": "None past their end date", "late_words": "past their end date",
	},
	"hours": {
		"label": "Hours This Month", "kind": HOURS, "doctype": "Timesheet", "function": "SUM", "field": "total_hours",
		"filters": {"docstatus": 1, "start_date": [">=", "{month}"]}, "company": True,
		"note": "On submitted timesheets", "tone": "blue",
	},
	"leads": {
		"label": "New Leads This Month", "kind": COUNT, "doctype": "Lead", "function": "COUNT",
		"filters": {"creation": [">=", "{month}"]}, "note": "Since the 1st", "tone": "blue",
	},
	"opportunities": {
		"label": "Open Opportunities", "kind": COUNT, "doctype": "Opportunity", "function": "COUNT",
		"filters": {"status": ["in", list(OPEN_OPPORTUNITIES)]}, "company": True,
		"late": {"expected_closing": ["<", "{today}"]}, "note": "None past their closing date", "late_words": "past their closing date",
	},
	"pipeline": {
		"label": "Open Pipeline", "kind": MONEY, "doctype": "Opportunity", "function": "SUM", "field": "base_opportunity_amount",
		"filters": {"status": ["in", list(OPEN_OPPORTUNITIES)]}, "company": True,
		"note": "Expected from open opportunities", "tone": "green",
	},
	"issues_replied": {
		"label": "Replied", "kind": COUNT, "doctype": "Issue", "function": "COUNT",
		"filters": {"status": "Replied"}, "note": "Waiting on the customer",
	},
	"issues_on_hold": {
		"label": "On Hold", "kind": COUNT, "doctype": "Issue", "function": "COUNT",
		"filters": {"status": "On Hold"}, "note": "Paused for now", "tone": "amber",
	},
	"asset_value": {
		"label": "Asset Value", "kind": MONEY, "doctype": "Asset", "function": "SUM", "field": "value_after_depreciation",
		"filters": {"docstatus": 1, "status": ["not in", list(ASSETS_GONE)]}, "company": True,
		"note": "After depreciation", "tone": "green",
	},
	"assets": {
		"label": "Assets in Use", "kind": COUNT, "doctype": "Asset", "function": "COUNT",
		"filters": {"docstatus": 1, "status": ["not in", list(ASSETS_GONE)]}, "company": True,
		"note": "Not sold or scrapped",
	},
	"maintenance_due": {
		"label": "Maintenance Due", "kind": COUNT, "doctype": "Asset Maintenance Log", "function": "COUNT",
		"filters": {"maintenance_status": ["in", ["Planned", "Overdue"]], "due_date": ["<=", "{week}"]},
		"late": {"due_date": ["<", "{today}"]}, "note": "Within the week, none overdue", "late_words": "overdue",
	},
	"inspections": {
		"label": "Inspections This Month", "kind": COUNT, "doctype": "Quality Inspection", "function": "COUNT",
		"filters": {"docstatus": 1, "report_date": [">=", "{month}"]}, "company": True, "note": "Since the 1st", "tone": "blue",
	},
	"rejected": {
		"label": "Rejected This Month", "kind": COUNT, "doctype": "Quality Inspection", "function": "COUNT",
		"filters": {"docstatus": 1, "status": "Rejected", "report_date": [">=", "{month}"]}, "company": True,
		"note": "Inspections that failed", "tone": "rose", "quiet": "green",
	},
	"non_conformances": {
		"label": "Open Non-Conformances", "kind": COUNT, "doctype": "Non Conformance", "function": "COUNT",
		"filters": {"status": "Open"}, "note": "Waiting to be resolved", "tone": "amber", "quiet": "green",
	},
}

# ── Breakdowns, declared ─────────────────────────────────────────────────────

# breakdown: {"title", "doctype", "by" (the field), "function", "field", "filters",
# "company", "draw" ("bars" or "donut"), "money", "none" (what a blank is called),
# "bands" ({value: band}), "empty", "note"}
GROUPS = {
	"work_order_status": {
		"title": "Open Work Orders by Status", "doctype": "Work Order", "by": "status", "function": "COUNT",
		"filters": {"docstatus": 1, "status": ["in", ["Not Started", "In Process", "Stock Reserved", "Stock Partially Reserved", "Stopped"]]},
		"company": True, "draw": "bars", "bands": {"Stopped": "overdue", "In Process": "good", "Not Started": "soon"},
		"empty": "No work orders open", "note": "How many in each",
	},
	"lead_sources": {
		"title": "Leads by Source, Last 90 Days", "doctype": "Lead", "by": "utm_source", "function": "COUNT",
		"filters": {"creation": [">=", "{since90}"]}, "draw": "donut", "none": "No source given",
		"empty": "No leads in the last 90 days", "note": "Where new leads came from",
	},
	"opportunity_stages": {
		"title": "Open Opportunities by Stage", "doctype": "Opportunity", "by": "sales_stage", "function": "SUM",
		"field": "base_opportunity_amount", "filters": {"status": ["in", list(OPEN_OPPORTUNITIES)]}, "company": True,
		"draw": "bars", "money": 1, "none": "No stage set", "empty": "No open opportunities", "note": "Expected value at each stage",
	},
	"issue_priorities": {
		"title": "Open Issues by Priority", "doctype": "Issue", "by": "priority", "function": "COUNT",
		"filters": {"status": ["in", ["Open", "Replied"]]}, "draw": "donut", "none": "No priority set",
		"empty": "No issues open", "note": "How many at each priority",
	},
	"asset_categories": {
		"title": "Assets by Category", "doctype": "Asset", "by": "asset_category", "function": "SUM",
		"field": "value_after_depreciation", "filters": {"docstatus": 1, "status": ["not in", list(ASSETS_GONE)]},
		"company": True, "draw": "donut", "money": 1, "none": "No category", "empty": "No assets in use",
		"note": "Value after depreciation",
	},
	"inspection_results": {
		"title": "Inspections This Month", "doctype": "Quality Inspection", "by": "status", "function": "COUNT",
		"filters": {"docstatus": 1, "report_date": [">=", "{month}"]}, "company": True, "draw": "bars",
		"bands": {"Accepted": "good", "Rejected": "overdue"}, "empty": "No inspections this month", "note": "Accepted and rejected",
	},
}

# ── Six months of something, declared ────────────────────────────────────────

# months: {"title", "series": [{"key", "label", "band", "doctype", "day" (its date
# field), "function", "field", "filters", "negate" (a sum that is below zero, drawn
# as it is above it)}], "company", "note", "route" (opened at a month)}
MONTHLY = {
	"sales_trend": {
		"title": "Orders and Billing by Month",
		"series": (
			{"key": "ordered", "label": "Ordered", "band": "soon", "doctype": "Sales Order", "day": "transaction_date",
				"function": "SUM", "field": "base_net_total", "filters": {"docstatus": 1}},
			{"key": "billed", "label": "Billed", "band": "good", "doctype": "Sales Invoice", "day": "posting_date",
				"function": "SUM", "field": "base_net_total", "filters": {"docstatus": 1}},
		),
		"company": True, "money": 1, "note": "Last 6 months, before tax",
	},
	"purchase_trend": {
		"title": "Purchases by Month",
		"series": (
			{"key": "ordered", "label": "Ordered", "band": "soon", "doctype": "Purchase Order", "day": "transaction_date",
				"function": "SUM", "field": "base_net_total", "filters": {"docstatus": 1}},
			{"key": "billed", "label": "Billed", "band": "today", "doctype": "Purchase Invoice", "day": "posting_date",
				"function": "SUM", "field": "base_net_total", "filters": {"docstatus": 1}},
		),
		"company": True, "money": 1, "note": "Last 6 months, before tax",
	},
	"stock_moves": {
		"title": "Stock In and Out by Month",
		"series": (
			{"key": "in", "label": "In", "band": "good", "doctype": "Stock Ledger Entry", "day": "posting_date",
				"function": "SUM", "field": "stock_value_difference", "filters": {"is_cancelled": 0, "actual_qty": [">", 0]}},
			{"key": "out", "label": "Out", "band": "today", "doctype": "Stock Ledger Entry", "day": "posting_date",
				"function": "SUM", "field": "stock_value_difference", "filters": {"is_cancelled": 0, "actual_qty": ["<", 0]},
				"negate": True},
		),
		"company": True, "money": 1, "note": "Value received and issued",
	},
	"production_trend": {
		"title": "Work Orders Completed by Month",
		"series": (
			{"key": "completed", "label": "Completed", "band": "good", "doctype": "Work Order", "day": "actual_end_date",
				"function": "COUNT", "filters": {"docstatus": 1, "status": "Completed"}},
		),
		"company": True, "money": 0, "note": "Last 6 months",
	},
}

# ── Lists, declared ──────────────────────────────────────────────────────────

# list: {"title", "doctype", "filters", "company", "fields", "title_field", and either
# "due" (the date it is due by, the soonest first) or "opened" (the date it was
# opened, the longest open first), "value" (a money field shown), "done" (how far
# along), "progress" (what the percent says), "empty"}
LISTS = {
	"requests_list": {
		"title": "Material Requests to Order", "doctype": "Material Request",
		"filters": {"docstatus": 1, "status": ["in", list(OPEN_REQUESTS)]}, "company": True,
		"fields": ("name", "title", "schedule_date"), "title_field": "title", "due": "schedule_date",
		"empty": "Nothing waiting to be ordered",
	},
	"job_cards_list": {
		"title": "Job Cards on the Floor", "doctype": "Job Card",
		"filters": {"docstatus": 0, "status": ["in", list(OPEN_JOB_CARDS)]}, "company": True,
		"fields": ("name", "operation", "expected_end_date"), "title_field": "operation", "due": "expected_end_date",
		"empty": "No job cards open",
	},
	"opportunities_closing": {
		"title": "Opportunities Closing Soon", "doctype": "Opportunity",
		"filters": {"status": ["in", list(OPEN_OPPORTUNITIES)]}, "company": True,
		"fields": ("name", "title", "expected_closing", "base_opportunity_amount"), "title_field": "title",
		"due": "expected_closing", "value": "base_opportunity_amount", "empty": "No open opportunities",
	},
	"maintenance": {
		"title": "Maintenance Due", "doctype": "Asset Maintenance Log",
		"filters": {"maintenance_status": ["in", ["Planned", "Overdue"]]},
		"fields": ("name", "asset_name", "task_name", "due_date"), "title_field": "asset_name", "due": "due_date",
		"empty": "No maintenance planned",
	},
	"non_conformance_list": {
		"title": "Open Non-Conformances", "doctype": "Non Conformance", "filters": {"status": "Open"},
		"fields": ("name", "subject", "creation"), "title_field": "subject", "opened": "creation",
		"empty": "Nothing open",
	},
}


# ── Filling in the day ───────────────────────────────────────────────────────


def dates(today):
	"""What the placeholders in the filters stand for, on a given day."""
	return {
		"{today}": str(today),
		"{month}": str(today.replace(day=1)),
		"{week}": str(today + datetime.timedelta(days=7)),
		"{since90}": str(today - datetime.timedelta(days=90)),
	}


def fill(value, day_of):
	"""The filters with their placeholders put in: day_of is dates() for the day."""
	if isinstance(value, str):
		return day_of.get(value, value)
	if isinstance(value, dict):
		return {key: fill(item, day_of) for key, item in value.items()}
	if isinstance(value, (list, tuple)):
		return [fill(item, day_of) for item in value]
	return value


def needs_of(spec):
	"""The doctypes a declared figure or dashboard is read from."""
	if "series" in spec:
		return tuple(dict.fromkeys(series["doctype"] for series in spec["series"]))
	return (spec["doctype"],) + (("Warehouse",) if spec.get("warehouses") else ())
