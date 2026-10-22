"""The desk home's and the module pages' rules (home_rules.py,
dashboards_rules.py, module_pages_rules.py), and the colors they draw with
(color_rules.py).

The rules import no Frappe. The shipped colors and switches are in settings.py,
which does, so the stand-in in fake_frappe.py is installed for those.
"""

import datetime
import re
import unittest

import fake_frappe

from cyvetech_ui.cyvetech_ui import color_rules, dashboards_rules as dashboards, home_rules as rules, module_pages_rules

fake_frappe.install()
settings = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.settings")
THEME_DEFAULTS = settings.THEME_DEFAULTS

TODAY = datetime.date(2026, 10, 22)
# every doctype any figure, dashboard, tab or report is read from: a user who may read it all
EVERYTHING = (
	{doctype for _label, _kind, doctypes in rules.CARDS.values() for doctype in doctypes}
	| {doctype for _title, _size, needs in rules.PANELS.values() for group in needs for doctype in group}
	| {doctype for tab in dashboards.TABS for doctype in tab["anchors"]}
	| set(dashboards.REPORT_DOCTYPES.values())
	| set(rules.ATTENTION_DOCTYPE.values())
	| {"Payment Entry", "Customer", "Stock Ledger Entry", "Supplier", "Material Request", "Project", "BOM"}
)
ALL_REPORTS = set(dashboards.REPORT_DOCTYPES)


def keys(found):
	return [item["key"] for item in found]


class WhoseDesk(unittest.TestCase):
	def test_roles_say_which_desks_in_the_order_money_first(self):
		roles = ["Stock User", "Accounts User", "Sales User", "Employee"]
		self.assertEqual(rules.desks_of(roles), [rules.FINANCE, rules.SALES, rules.STOCK])

	def test_an_administrator_has_every_desk(self):
		roles = [role for _desk, allowed, _anchor in rules.DESKS for role in allowed]
		self.assertEqual(rules.desks_of(roles), [desk for desk, *_rest in rules.DESKS])

	def test_without_a_role_it_knows_the_desks_follow_what_they_may_read(self):
		self.assertEqual(rules.desks_of(["Cashier"], {"Sales Invoice", "Task"}), [rules.FINANCE, rules.PROJECTS])

	def test_nothing_to_go_by_is_no_desk(self):
		self.assertEqual(rules.desks_of(["Employee"], {"ToDo"}), [])


class Figures(unittest.TestCase):
	def test_an_accountant_sees_the_money(self):
		self.assertEqual(rules.cards_for([rules.FINANCE], EVERYTHING), ["sales", "receivable", "payable", "cash"])

	def test_a_sales_clerk_sees_orders_and_quotes_not_invoices_they_may_not_open(self):
		readable = {"Sales Order", "Quotation", "Bin", "Warehouse", "Item"}
		self.assertEqual(rules.cards_for([rules.SALES], readable), ["orders", "to_deliver", "quotations"])

	def test_an_administrator_gets_two_full_rows(self):
		every = [desk for desk, *_rest in rules.DESKS]
		self.assertEqual(
			rules.cards_for(every, EVERYTHING),
			["sales", "receivable", "payable", "cash", "orders", "to_deliver", "quotations", "purchases"],
		)

	def test_a_figure_is_never_shown_twice(self):
		found = rules.cards_for([rules.STOCK, rules.SALES], EVERYTHING)
		self.assertEqual(len(found), len(set(found)))

	def test_frames_first_then_the_users_own_work_to_fill_the_row(self):
		waits = {"tasks": 3, "overdue": 1, "unread": 2}
		cards = rules.home_cards(["tasks"], waits)
		self.assertEqual(keys(cards), ["tasks", "waiting", "unread"])
		self.assertEqual(cards[0], {"key": "tasks", "label": "Open Tasks", "kind": rules.COUNT, "frame": 1})
		self.assertEqual((cards[1]["value"], cards[1]["note"], cards[1]["tone"]), (3, "1 overdue", "rose"))

	def test_a_row_is_filled_as_far_as_the_users_own_work_goes(self):
		self.assertEqual(keys(rules.home_cards(["sales", "receivable", "payable"], {})), ["sales", "receivable", "payable", "waiting"])
		six = ["sales", "receivable", "payable", "cash", "orders", "to_deliver"]
		self.assertEqual(keys(rules.home_cards(six, {}))[6:], ["waiting", "unread"])
		self.assertEqual(len(rules.home_cards(["sales", "receivable", "payable", "cash"], {})), 4)

	def test_no_business_figures_means_the_users_own_two(self):
		cards = rules.home_cards([], {"tasks": 0, "unread": 4})
		self.assertEqual([(card["key"], card["value"]) for card in cards], [("waiting", 0), ("unread", 4)])
		self.assertEqual(cards[0]["note"], "Nothing waiting")

	def test_a_card_as_read(self):
		card = rules.card("sales", "1250.5", note="x", tone="blue", change={"percent": 12, "direction": "up"},
			route=["List", "Sales Invoice"], filters={"docstatus": 1})
		self.assertEqual((card["value"], card["label"], card["kind"]), (1250.5, "Sales This Month", rules.MONEY))
		self.assertNotIn("options", card)

	def test_a_declared_figure_is_a_card_like_any_other(self):
		self.assertEqual(rules.CARDS["hours"], ("Hours This Month", dashboards.HOURS, ("Timesheet",)))
		self.assertEqual(rules.CARDS["negative"][2], ("Bin", "Warehouse"))


class Waiting(unittest.TestCase):
	def test_assignments_and_unread_notifications_counted_apart(self):
		alerts = [
			{"kind": "assignment", "urgency": "overdue", "title": "A", "key": "1"},
			{"kind": "assignment", "urgency": "today", "title": "B", "key": "2"},
			{"kind": "notification", "unread": 1, "title": "C", "key": "3"},
			{"kind": "notification", "unread": 0, "title": "D", "key": "4"},
		]
		waits = rules.waiting(alerts)
		self.assertEqual((waits["tasks"], waits["overdue"], waits["today"], waits["unread"]), (2, 1, 1, 1))
		self.assertEqual([row["title"] for row in waits["items"]], ["A", "B"])
		self.assertEqual([row["title"] for row in waits["notes"]], ["C"])

	def test_the_greeting_follows_the_hour(self):
		self.assertEqual([rules.greeting(hour) for hour in (6, 11, 12, 16, 17, 23)],
			["Good morning", "Good morning", "Good afternoon", "Good afternoon", "Good evening", "Good evening"])


class Tabs(unittest.TestCase):
	def tabs(self, desks=(), readable=EVERYTHING, blocked=(), switches=None, reports=ALL_REPORTS):
		return rules.tabs_for(list(desks), readable, blocked=blocked, switches=switches, reports=reports)

	def test_overview_first_then_the_users_own_modules_then_the_rest(self):
		found = keys(self.tabs([rules.SALES, rules.FINANCE]))
		self.assertEqual(found[:3], ["overview", "selling", "accounts"])
		self.assertEqual(sorted(found), sorted(["overview", *dashboards.TAB_KEYS]))

	def test_a_module_blocked_for_the_user_has_no_tab(self):
		self.assertNotIn("selling", keys(self.tabs([rules.SALES], blocked={"Selling"})))

	def test_a_module_switched_off_in_the_settings_has_no_tab(self):
		switches = rules.switched_on({"dash_crm": "0"})
		self.assertNotIn("crm", keys(self.tabs(switches=switches)))
		self.assertIn("support", keys(self.tabs(switches=switches)))

	def test_a_tab_comes_with_its_own_documents_not_a_figure_it_shares(self):
		storekeeper = {"Bin", "Warehouse", "Item", "Sales Order", "Purchase Order", "Stock Ledger Entry"}
		# stock to reorder is a Manufacturing figure too, and the orders a Sales one
		self.assertEqual(keys(self.tabs([rules.STOCK], storekeeper, blocked={"Selling"})), ["overview", "stock", "buying"])

	def test_a_tab_shows_only_what_the_user_may_read(self):
		stock = next(tab for tab in self.tabs([rules.STOCK], {"Bin", "Warehouse", "Item"}) if tab["key"] == "stock")
		self.assertEqual(keys(stock["cards"]), ["stock_value", "reorder", "negative"])
		self.assertEqual(keys(stock["panels"]), ["attention", "warehouses", "reorder"])

	def test_needs_attention_on_a_tab_only_where_it_has_checks_of_its_own(self):
		found = {tab["key"]: keys(tab["panels"]) for tab in self.tabs([rules.FINANCE])}
		self.assertEqual(found["accounts"][0], "attention")
		self.assertNotIn("attention", found["crm"])  # no check is CRM's
		self.assertEqual(found["overview"], ["attention", "drafts"])

	def test_needs_attention_on_a_tab_only_where_the_user_may_read_a_check(self):
		# someone who books hours but may read no task: none of the projects' checks are theirs
		projects = next(tab for tab in self.tabs([], {"Timesheet"}) if tab["key"] == "projects")
		self.assertEqual(keys(projects["panels"]), ["hours_by_project"])

	def test_the_overview_counts_only_the_tabs_the_user_has(self):
		self.assertEqual(rules.attention_overview(["stock"], EVERYTHING), ["negative_stock"])
		overview = self.tabs([rules.PROJECTS], {"Project", "Task"})[0]
		self.assertEqual(keys(overview["panels"]), ["attention"])  # tasks overdue; no drafts to look for

	def test_a_tabs_figures_are_frames_until_read(self):
		accounts = next(tab for tab in self.tabs([rules.FINANCE]) if tab["key"] == "accounts")
		self.assertTrue(all(card["frame"] for card in accounts["cards"]))
		self.assertEqual(accounts["panels"][1], {"key": "trend", "title": "Sales and Collections", "size": rules.WIDE})

	def test_only_the_reports_the_user_may_open(self):
		accounts = next(tab for tab in self.tabs([rules.FINANCE], reports={"Balance Sheet", "General Ledger"}) if tab["key"] == "accounts")
		self.assertEqual(accounts["reports"], [
			{"label": "Balance Sheet", "route": ["query-report", "Balance Sheet"]},
			{"label": "General Ledger", "route": ["query-report", "General Ledger"]},
		])

	def test_where_frappe_cannot_say_a_report_goes_to_whoever_may_read_what_it_reports_on(self):
		selling = next(tab for tab in self.tabs([rules.SALES], {"Sales Order", "Quotation"}, reports=None) if tab["key"] == "selling")
		self.assertIn("Sales Analytics", [report["label"] for report in selling["reports"]])
		self.assertNotIn("Customer Acquisition and Loyalty", [report["label"] for report in selling["reports"]])

	def test_the_tab_a_module_page_belongs_to(self):
		tabs = self.tabs([rules.FINANCE])
		self.assertEqual(rules.tab_of_workspace(tabs, "Payments"), "accounts")
		self.assertEqual(rules.tab_of_workspace(tabs, "Selling"), "selling")
		self.assertIsNone(rules.tab_of_workspace(tabs, "ERPNext Settings"))

	def test_a_switch_never_saved_is_on(self):
		self.assertTrue(all(rules.switched_on({}).values()))
		self.assertTrue(rules.switched_on({"dash_stock": ""})["dash_stock"])
		self.assertFalse(rules.switched_on({"dash_stock": 0})["dash_stock"])

	def test_every_tab_has_a_switch_in_the_settings_defaults(self):
		for switch in dashboards.SWITCHES:
			self.assertEqual(settings.DEFAULTS[switch], 1, switch)
			self.assertIn(switch, settings.CHECKS)


class Declared(unittest.TestCase):
	"""What dashboards_rules.py declares holds together."""

	def test_every_tab_names_figures_and_dashboards_there_are(self):
		for tab in dashboards.TABS:
			for key in tab["cards"]:
				self.assertIn(key, rules.CARDS, (tab["key"], key))
			for key in tab["panels"]:
				self.assertIn(key, rules.PANELS, (tab["key"], key))
			for report in tab["reports"]:
				self.assertIn(report, dashboards.REPORT_DOCTYPES, (tab["key"], report))
			self.assertTrue(tab["anchors"], tab["key"])

	def test_a_declared_figure_is_complete(self):
		for key, spec in dashboards.FIGURES.items():
			self.assertIn(spec["function"], ("COUNT", "SUM"), key)
			self.assertEqual("field" in spec, spec["function"] == "SUM", key)
			self.assertIn(spec["kind"], (dashboards.MONEY, dashboards.COUNT, dashboards.HOURS), key)

	def test_every_placeholder_is_one_there_is(self):
		known = set(dashboards.dates(TODAY))
		specs = list(dashboards.FIGURES.values()) + list(dashboards.GROUPS.values()) + list(dashboards.LISTS.values())
		specs += [series for spec in dashboards.MONTHLY.values() for series in spec["series"]]
		for spec in specs:
			for found in re.findall(r"\{\w+\}", str(spec.get("filters")) + str(spec.get("late"))):
				self.assertIn(found, known, spec)

	def test_the_day_is_filled_in(self):
		filled = dashboards.fill({"a": ["<", "{today}"], "b": [">=", "{month}"], "c": ["between", ["{since90}", "{week}"]], "d": 1}, dashboards.dates(TODAY))
		self.assertEqual(filled, {"a": ["<", "2026-10-22"], "b": [">=", "2026-10-01"], "c": ["between", ["2026-07-24", "2026-10-29"]], "d": 1})

	def test_a_list_says_how_it_is_ordered(self):
		for key, spec in dashboards.LISTS.items():
			self.assertTrue(spec.get("due") or spec.get("opened"), key)
			self.assertIn(spec["title_field"], spec["fields"], key)


class Dates(unittest.TestCase):
	def test_this_month_runs_to_today(self):
		self.assertEqual(rules.this_month(TODAY), (datetime.date(2026, 10, 1), TODAY))

	def test_the_same_days_of_last_month(self):
		self.assertEqual(rules.same_days_last_month(TODAY), (datetime.date(2026, 9, 1), datetime.date(2026, 9, 22)))

	def test_a_longer_month_compares_with_the_whole_of_a_shorter_one(self):
		self.assertEqual(rules.same_days_last_month(datetime.date(2026, 3, 31)), (datetime.date(2026, 2, 1), datetime.date(2026, 2, 28)))
		self.assertEqual(rules.same_days_last_month(datetime.date(2026, 1, 15)), (datetime.date(2025, 12, 1), datetime.date(2025, 12, 15)))

	def test_how_a_figure_moved(self):
		self.assertEqual(rules.change(112, 100), {"percent": 12, "direction": "up"})
		self.assertEqual(rules.change(50, 200), {"percent": 75, "direction": "down"})
		self.assertEqual(rules.change(100, 100), {"percent": 0, "direction": "same"})
		self.assertIsNone(rules.change(100, 0))

	def test_six_months_to_today_oldest_first(self):
		months = rules.months(TODAY)
		self.assertEqual([month["label"] for month in months], ["May", "Jun", "Jul", "Aug", "Sep", "Oct"])
		self.assertEqual((months[0]["from"], months[1]["to"], months[-1]["to"]), ("2026-05-01", "2026-06-30", "2026-10-22"))

	def test_months_across_a_new_year(self):
		self.assertEqual([month["from"] for month in rules.months(datetime.date(2026, 2, 3), 3)], ["2025-12-01", "2026-01-01", "2026-02-01"])

	def test_days_add_up_into_their_months(self):
		months = rules.months(TODAY, 2)
		rows = [{"day": "2026-09-05", "total": 100}, {"day": datetime.date(2026, 9, 30), "total": 50.5},
			{"day": "2026-10-01 17:00:00", "total": 7}, {"day": "2026-08-31", "total": 999}, {"day": None, "total": 1}]
		self.assertEqual(rules.by_month(rows, months), [150.5, 7.0])


class Money(unittest.TestCase):
	def test_each_invoice_falls_in_its_aging_bucket(self):
		rows = [
			{"due_date": "2026-10-30", "total": 100}, {"due_date": "2026-10-22", "total": 10}, {"due_date": None, "total": 5},
			{"due_date": "2026-10-21", "total": 20}, {"due_date": "2026-09-22", "total": 30}, {"due_date": "2026-09-21", "total": 40},
			{"due_date": "2026-07-24", "total": 50}, {"due_date": "2026-07-23", "total": 60},
		]
		buckets = {bucket["key"]: bucket["value"] for bucket in rules.aging(rows, TODAY)}
		self.assertEqual(buckets, {"current": 115, "d30": 50, "d60": 40, "d90": 50, "older": 60})

	def test_each_bucket_opens_the_invoices_it_holds(self):
		filters = {bucket["key"]: bucket["filters"]["due_date"] for bucket in rules.aging([], TODAY)}
		self.assertEqual(filters["current"], [">=", "2026-10-22"])
		self.assertEqual(filters["d30"], ["between", ["2026-09-22", "2026-10-21"]])
		self.assertEqual(filters["older"], ["<=", "2026-07-23"])

	def test_who_owes_the_most_past_due(self):
		rows = [
			{"customer": "C1", "customer_name": "Alpha", "total": 500, "oldest": "2026-10-12"},
			{"customer": "C2", "customer_name": "Beta", "total": 900, "oldest": "2026-07-01"},
			{"customer": "C3", "customer_name": "Gamma", "total": 0, "oldest": "2026-10-01"},
		]
		owing = rules.most_overdue(rows, TODAY)
		self.assertEqual([row["title"] for row in owing], ["Beta", "Alpha"])
		self.assertEqual((owing[0]["when"], owing[0]["band"], owing[1]["band"]), ("oldest 113 days overdue", "overdue", "soon"))

	def test_and_the_suppliers_owed_the_most(self):
		owed = rules.most_overdue([{"supplier": "S1", "supplier_name": "Paint Co", "total": 70, "oldest": "2026-10-02"}],
			TODAY, doctype="Supplier", party="supplier")
		self.assertEqual((owed[0]["title"], owed[0]["doctype"], owed[0]["docname"]), ("Paint Co", "Supplier", "S1"))

	def test_profit_month_by_month(self):
		months = rules.months(TODAY, 2)
		income = rules.signed([{"day": "2026-10-03", "debit": 50, "credit": 1050}, {"day": "2026-09-09", "debit": 0, "credit": 400}], "income")
		expenses = rules.signed([{"day": "2026-10-04", "debit": 700, "credit": 100}], "expense")
		rows = rules.profit(income, expenses, months)
		self.assertEqual([(row["values"], row["net"]) for row in rows], [([400.0, 0.0], 400.0), ([1000.0, 600.0], 400.0)])
		self.assertEqual(rules.margin(rows[-1]), 40)
		self.assertIsNone(rules.margin({"values": [0, 10], "net": -10}))

	def test_the_largest_parts_of_a_whole_and_the_rest_as_one(self):
		rows = [{"label": name, "value": value} for name, value in (("A", 50), ("B", 30), ("C", 0), ("D", 10), ("E", 6), ("F", 3), ("G", 1))]
		parts = rules.slices(rows, "label", "value", shown=3)
		self.assertEqual([(part["label"], part["value"]) for part in parts], [("A", 50), ("B", 30), ("D", 10), ("Everything else", 10)])
		self.assertIsNone(parts[-1]["key"])

	def test_quotations_by_stage_and_how_many_were_won(self):
		found = rules.quotation_stages([
			{"status": "Open", "count": 4, "total": 400}, {"status": "Replied", "count": 1, "total": 50},
			{"status": "Ordered", "count": 3, "total": 900}, {"status": "Lost", "count": 2, "total": 70}, {"status": "Expired", "count": 1, "total": 5},
		])
		self.assertEqual([(stage["key"], stage["value"], stage["amount"]) for stage in found["stages"]],
			[("open", 5, 450), ("won", 3, 900), ("lost", 2, 70), ("expired", 1, 5)])
		self.assertEqual(found["won"], 50)  # 3 of the 6 decided
		self.assertIsNone(rules.quotation_stages([{"status": "Open", "count": 2, "total": 1}])["won"])


class Lists(unittest.TestCase):
	def test_the_soonest_due_first_and_no_date_last(self):
		rows = [
			{"name": "SO-3", "customer_name": "C", "delivery_date": None, "base_grand_total": 3, "per_delivered": 0},
			{"name": "SO-2", "customer_name": "B", "delivery_date": "2026-10-30", "base_grand_total": 2, "per_delivered": 40},
			{"name": "SO-1", "customer_name": "A", "delivery_date": "2026-10-19", "base_grand_total": 1, "per_delivered": 0},
		]
		listed = rules.due_rows(rows, TODAY, "Sales Order", "customer_name", "delivery_date", value="base_grand_total", done="per_delivered")
		self.assertEqual([row["docname"] for row in listed], ["SO-1", "SO-2", "SO-3"])
		self.assertEqual([row["band"] for row in listed], ["overdue", "later", "none"])
		self.assertEqual((listed[0]["when"], listed[2]["when"], listed[1]["progress"]), ("overdue by 3 days", "no date set", 40))

	def test_the_longest_open_first(self):
		rows = [{"name": "ISS-2", "subject": "Login", "opening_date": "2026-10-21"}, {"name": "ISS-1", "subject": "Invoice", "opening_date": "2026-10-10"},
			{"name": "ISS-3", "subject": "New", "opening_date": "2026-10-22"}]
		listed = rules.open_for(rows, TODAY, "Issue", "subject", "opening_date")
		self.assertEqual([(row["docname"], row["when"], row["band"]) for row in listed],
			[("ISS-1", "open for 12 days", "overdue"), ("ISS-2", "open for 1 day", "soon"), ("ISS-3", "opened today", "soon")])

	def test_stock_below_zero_first_then_the_furthest_under_its_level(self):
		levels = [{"item_code": code, "warehouse": "Stores - AC", "level": level} for code, level in (("A", 100), ("B", 10), ("C", 10), ("D", 0))]
		bins = [
			{"item_code": "A", "warehouse": "Stores - AC", "projected_qty": 50}, {"item_code": "B", "warehouse": "Stores - AC", "projected_qty": 1},
			{"item_code": "C", "warehouse": "Stores - AC", "projected_qty": 11}, {"item_code": "D", "warehouse": "Stores - AC", "projected_qty": 5},
			{"item_code": "E", "warehouse": "Shop - AC", "projected_qty": -4}, {"item_code": "F", "warehouse": "Shop - AC", "projected_qty": -1},
		]
		found = rules.to_reorder(levels, bins)
		self.assertEqual([row["docname"] for row in found["rows"]], ["E", "F", "B", "A"])
		self.assertEqual((found["count"], found["short"], found["rows"][0]["warehouse"]), (4, 2, "Shop"))

	def test_drafts_the_oldest_first_and_how_long_untouched(self):
		found = [
			("Sales Invoice", {"name": "SINV-2", "modified": "2026-10-21 10:00:00", "title": "Acme"}),
			("Stock Entry", {"name": "STE-9", "modified": "2026-10-10 08:00:00", "title": "STE-9"}),
			("Payment Entry", {"name": "PE-1", "modified": "2026-10-22 08:00:00"}),
		]
		listed = rules.drafts(found, TODAY)
		self.assertEqual([row["docname"] for row in listed["rows"]], ["STE-9", "SINV-2", "PE-1"])
		self.assertEqual([row["when"] for row in listed["rows"]], ["untouched for 12 days", "untouched for 1 day", "untouched today"])
		self.assertEqual([row["title"] for row in listed["rows"]], ["Stock Entry", "Acme", "Payment Entry"])

	def test_the_largest_first_as_bars(self):
		rows = [{"customer": "C1", "customer_name": "Alpha", "total": 10}, {"customer": "C2", "customer_name": "Beta", "total": 30},
			{"customer": "C3", "customer_name": "", "total": 20}, {"customer": "C4", "customer_name": "Zero", "total": 0}]
		bars = rules.ranked(rows, "customer_name", "total", name="customer", doctype="Customer")
		self.assertEqual([bar["label"] for bar in bars], ["Beta", "C3", "Alpha"])
		self.assertEqual(bars[0], {"label": "Beta", "value": 30.0, "doctype": "Customer", "docname": "C2"})

	def test_names_without_the_company_abbreviation(self):
		self.assertEqual([rules.short_name(name) for name in ("Stores - AC", "Cash", "Bank - Main - AC")], ["Stores", "Cash", "Bank - Main"])


class Attention(unittest.TestCase):
	def test_each_check_belongs_to_a_tab_there_is(self):
		for key, *_rest in rules.ATTENTION:
			self.assertIn(rules.ATTENTION_TAB[key], dashboards.TAB_KEYS, key)

	def test_a_tabs_checks_are_its_own_and_readable(self):
		self.assertEqual(rules.attention_in("selling", EVERYTHING), ["orders_late", "orders_to_bill", "quotations_expiring"])
		self.assertEqual(rules.attention_in("selling", {"Quotation"}), ["quotations_expiring"])

	def test_each_tab_badge_counts_its_checks_in_the_color_of_the_most_pressing(self):
		rows = [
			{"key": "quotations_expiring", "value": 2, "band": "soon"},
			{"key": "issues_open", "value": 4, "band": "soon"},
			{"key": "orders_to_bill", "value": 3, "band": "today"},
			{"key": "orders_late", "value": 1, "band": "overdue"},
			{"key": "no_such_check", "value": 9, "band": "overdue"},
		]
		self.assertEqual(rules.badges(rows), {"selling": {"value": 6, "band": "overdue"}, "support": {"value": 4, "band": "soon"}})
		self.assertEqual(rules.badges([]), {})

	def test_only_what_there_is_some_of_the_most_pressing_first(self):
		rows = rules.attention_rows({"quotations_expiring": 4, "bills_due": 2, "orders_late": 1, "invoices_overdue": 0}, TODAY, "Acme")
		self.assertEqual(keys(rows), ["orders_late", "bills_due", "quotations_expiring"])
		self.assertEqual((rows[0]["label"], rows[1]["label"]), ("Sales order late to deliver", "Supplier bills due this week"))
		self.assertEqual((rows[0]["route"], rows[0]["filters"]["delivery_date"], rows[0]["filters"]["company"]),
			(["List", "Sales Order"], ["<", "2026-10-22"], "Acme"))

	def test_what_each_check_counts(self):
		self.assertEqual(rules.attention_filters("bills_due", TODAY)["due_date"], ["<=", "2026-10-29"])
		self.assertNotIn("company", rules.attention_filters("negative_stock", TODAY, "Acme"))


class MostMade(unittest.TestCase):
	def test_the_users_own_work_first_then_their_desks_usual(self):
		counts = {"Payment Entry": 30, "Sales Invoice": 12, "Journal Entry": 0}
		creatable = {"Payment Entry", "Sales Invoice", "Journal Entry", "Sales Order", "Quotation"}
		self.assertEqual(rules.most_made(counts, [rules.FINANCE, rules.SALES], creatable),
			["Payment Entry", "Sales Invoice", "Journal Entry", "Sales Order"])

	def test_only_what_they_may_make(self):
		self.assertEqual(rules.most_made({"Sales Invoice": 5}, [rules.FINANCE], {"Payment Entry"}), ["Payment Entry"])

	def test_links_for_a_desk_without_visits_to_go_by(self):
		links = rules.links_for([rules.FINANCE, rules.STOCK], {"Sales Invoice", "GL Entry", "Item"})
		self.assertEqual([link["label"] for link in links], ["Accounts Receivable", "General Ledger", "Profit and Loss", "Items"])


class Modules(unittest.TestCase):
	def test_the_flow_runs_through_the_modules_in_their_order(self):
		positions = [rules.MODULES.index(module) for module in rules.FLOW]
		self.assertEqual(positions, sorted(positions))

	def test_each_doctype_once_in_the_order_named(self):
		self.assertEqual(module_pages_rules.doctypes(["B", "A", "", None, "B", " C "]), ["B", "A", "C"])

	def test_what_waits_in_one_module(self):
		alerts = [{"doctype": "Sales Order", "key": 1}, {"doctype": "Item", "key": 2}, {"doctype": "Quotation", "key": 3}]
		self.assertEqual([alert["key"] for alert in module_pages_rules.mine_in(alerts, ["Quotation", "Sales Order"])], [1, 3])

	def test_the_checks_a_module_has(self):
		self.assertEqual(module_pages_rules.attention_in(["Sales Order", "Quotation", "Item"]), ["orders_late", "orders_to_bill", "quotations_expiring"])

	def test_the_document_offered_is_what_the_user_makes_most_there(self):
		names = ["Quotation", "Sales Order", "Sales Invoice"]
		self.assertEqual(module_pages_rules.action_of("Selling", ["Payment Entry", "Quotation"], names), "Quotation")
		self.assertEqual(module_pages_rules.action_of("Selling", ["Payment Entry"], names), "Sales Order")
		self.assertIsNone(module_pages_rules.action_of("Organization", [], ["Company"]))


class HomeColors(unittest.TestCase):
	def colors(self, **picked):
		return color_rules.theme_variables(dict(THEME_DEFAULTS, **picked), THEME_DEFAULTS, 16)

	def test_the_header_is_the_sidebar_color_until_one_is_picked(self):
		self.assertEqual(self.colors()["--cvt-header"], "#16335e")
		self.assertEqual(self.colors(sidebar="#0b3d2e")["--cvt-header"], "#0b3d2e")
		self.assertEqual(self.colors(header="#3a1f5d")["--cvt-header"], "#3a1f5d")

	def test_the_status_bands_are_the_settings_colors(self):
		found = self.colors(danger="#aa0000", warning="#995500", success="#006633", accent="#224488")
		self.assertEqual(
			(found["--cvt-band-overdue"], found["--cvt-band-today"], found["--cvt-band-good"], found["--cvt-band-soon"], found["--cvt-accent"]),
			("#aa0000", "#995500", "#006633", "#224488", "#224488"),
		)

	def test_a_malformed_color_falls_back_to_its_default(self):
		self.assertEqual(self.colors(danger="red; background: url(x)")["--cvt-band-overdue"], "#c53030")

	def test_text_on_the_header_is_whatever_reads_on_it(self):
		self.assertEqual(self.colors()["--cvt-on-header"], "#ffffff")
		self.assertEqual(self.colors(header="#f5f5f5")["--cvt-on-header"], color_rules.DARK_INK)

	def test_every_shipped_status_color_carries_white_text(self):
		shipped = {key: THEME_DEFAULTS[key] for key in ("accent", "danger", "warning", "success")}
		self.assertEqual(color_rules.white_text_shortfalls(shipped), [])
		self.assertGreaterEqual(color_rules.contrast(self.colors()["--cvt-header-mid"], "#ffffff"), 4.5)

	def test_a_color_too_light_for_white_text_is_named(self):
		self.assertEqual(color_rules.white_text_shortfalls({"Header": "#eaa51a", "Done": "#1e7a46", "Blank": ""}), ["Header"])

	def test_every_value_is_a_hex_color_the_desk_will_take(self):
		for name, value in self.colors().items():
			self.assertRegex(name, r"^--cvt-[a-z-]+$")
			self.assertTrue(re.fullmatch(r"#[0-9a-f]{6}|\d{1,2}px", value), (name, value))


if __name__ == "__main__":
	unittest.main()
