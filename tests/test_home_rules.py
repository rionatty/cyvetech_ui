"""The desk home's and the module pages' rules (home_rules.py,
module_pages_rules.py), and the colors they draw with (color_rules.py).

The rules import no Frappe. The shipped colors and switches are in settings.py,
which does, so the stand-in in fake_frappe.py is installed for those.
"""

import datetime
import unittest

import fake_frappe

from cyvetech_ui.cyvetech_ui import color_rules, home_rules as rules, module_pages_rules

fake_frappe.install()
settings = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.settings")
THEME_DEFAULTS = settings.THEME_DEFAULTS

TODAY = datetime.date(2026, 10, 22)
EVERYTHING = {
	doctype
	for _label, _kind, doctypes in rules.CARDS.values()
	for doctype in doctypes
} | {"Payment Entry", "Customer", "Stock Ledger Entry", "Supplier", "Material Request", "Project", "BOM",
	"Purchase Receipt", "Quotation"} | set(rules.DRAFT_DOCTYPES)


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
		keys = rules.cards_for([rules.FINANCE], EVERYTHING)
		self.assertEqual(keys, ["sales", "receivable", "payable", "cash"])

	def test_a_sales_clerk_sees_orders_and_quotes_not_invoices_they_may_not_open(self):
		readable = {"Sales Order", "Quotation", "Bin", "Warehouse", "Item"}
		self.assertEqual(rules.cards_for([rules.SALES], readable), ["orders", "to_deliver", "quotations"])

	def test_a_sales_clerk_who_also_keeps_the_store(self):
		readable = {"Sales Order", "Quotation", "Bin", "Warehouse", "Item", "Purchase Order"}
		self.assertEqual(
			rules.cards_for([rules.SALES, rules.STOCK], readable), ["orders", "to_deliver", "quotations", "stock_value"]
		)

	def test_a_figure_is_never_shown_twice(self):
		keys = rules.cards_for([rules.STOCK, rules.SALES], EVERYTHING)
		self.assertEqual(len(keys), len(set(keys)))

	def test_frames_first_then_the_users_own_work_where_there_is_room(self):
		waits = {"tasks": 3, "overdue": 1, "unread": 2}
		cards = rules.home_cards(["tasks"], waits)
		self.assertEqual([card["key"] for card in cards], ["tasks", "waiting"])
		self.assertEqual(cards[0], {"key": "tasks", "label": "Open Tasks", "kind": rules.COUNT, "frame": 1})
		self.assertEqual(cards[1]["value"], 3)
		self.assertEqual(cards[1]["note"], "1 overdue")
		self.assertEqual(cards[1]["tone"], "rose")

	def test_no_business_figures_means_the_users_own_two(self):
		cards = rules.home_cards([], {"tasks": 0, "unread": 4})
		self.assertEqual([(card["key"], card["value"]) for card in cards], [("waiting", 0), ("unread", 4)])
		self.assertEqual(cards[0]["note"], "Nothing waiting")

	def test_a_full_row_has_no_room_for_more(self):
		self.assertEqual(len(rules.home_cards(["sales", "receivable", "payable", "cash"], {})), 4)

	def test_a_card_as_read(self):
		card = rules.card("sales", "1250.5", note="x", tone="blue", change={"percent": 12, "direction": "up"},
			route=["List", "Sales Invoice"], filters={"docstatus": 1})
		self.assertEqual(card["value"], 1250.5)
		self.assertEqual(card["label"], "Sales This Month")
		self.assertEqual(card["kind"], rules.MONEY)
		self.assertNotIn("options", card)


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
		self.assertEqual(waits["items"][0]["band"], "overdue")

	def test_the_greeting_follows_the_hour(self):
		self.assertEqual([rules.greeting(hour) for hour in (6, 11, 12, 16, 17, 23)],
			["Good morning", "Good morning", "Good afternoon", "Good afternoon", "Good evening", "Good evening"])


class Panels(unittest.TestCase):
	def keys(self, desks, readable=EVERYTHING, switches=None):
		return [panel["key"] for panel in rules.panels_for(desks, readable, switches)]

	def test_an_accountant(self):
		self.assertEqual(self.keys([rules.FINANCE]), ["attention", "trend", "aging", "cash", "customers", "drafts"])

	def test_each_panel_knows_where_it_goes(self):
		places = {panel["key"]: panel["place"] for panel in rules.panels_for([rules.FINANCE], EVERYTHING)}
		self.assertEqual(places["attention"], rules.BESIDE)
		self.assertEqual(places["trend"], rules.WIDE)
		self.assertEqual(places["aging"], rules.GRID)

	def test_a_panel_switched_off_in_the_settings_is_gone_for_everyone(self):
		switches = rules.switched_on({"home_trend": "0", "home_cash": 0})
		self.assertEqual(self.keys([rules.FINANCE], switches=switches), ["attention", "aging", "customers", "drafts"])

	def test_a_switch_never_saved_is_on(self):
		self.assertTrue(all(rules.switched_on({}).values()))
		self.assertTrue(rules.switched_on({"home_trend": ""})["home_trend"])
		self.assertTrue(rules.switched_on({"home_trend": None})["home_trend"])

	def test_the_trend_takes_orders_where_invoices_are_not_open_to_the_user(self):
		self.assertIn("trend", self.keys([rules.SALES], {"Sales Order"}))
		self.assertNotIn("trend", self.keys([rules.SALES], {"Quotation"}))

	def test_cash_needs_the_ledger_and_the_accounts(self):
		self.assertNotIn("cash", self.keys([rules.FINANCE], {"Sales Invoice", "GL Entry"}))
		self.assertIn("cash", self.keys([rules.FINANCE], {"Sales Invoice", "GL Entry", "Account"}))

	def test_someone_with_no_desk_has_their_drafts_and_no_attention(self):
		self.assertEqual(self.keys([], {"Sales Invoice"}), ["drafts"])
		self.assertEqual(self.keys([], set()), [])

	def test_every_panel_has_a_switch_in_the_settings_defaults(self):
		for switch in rules.SWITCHES:
			self.assertEqual(settings.DEFAULTS[switch], 1, switch)
			self.assertIn(switch, settings.CHECKS)


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
		self.assertEqual(rules.change(-50, -100), {"percent": 50, "direction": "up"})

	def test_six_months_to_today_oldest_first(self):
		months = rules.months(TODAY)
		self.assertEqual([month["label"] for month in months], ["May", "Jun", "Jul", "Aug", "Sep", "Oct"])
		self.assertEqual(months[0]["from"], "2026-05-01")
		self.assertEqual(months[1]["to"], "2026-06-30")
		self.assertEqual(months[-1]["to"], "2026-10-22")

	def test_months_across_a_new_year(self):
		self.assertEqual([month["from"] for month in rules.months(datetime.date(2026, 2, 3), 3)],
			["2025-12-01", "2026-01-01", "2026-02-01"])

	def test_days_add_up_into_their_months(self):
		months = rules.months(TODAY, 2)
		rows = [{"day": "2026-09-05", "total": 100}, {"day": datetime.date(2026, 9, 30), "total": 50.5},
			{"day": "2026-10-01", "total": 7}, {"day": "2026-08-31", "total": 999}, {"day": None, "total": 1}]
		self.assertEqual(rules.by_month(rows, months), [150.5, 7.0])


class Aging(unittest.TestCase):
	def test_each_invoice_falls_in_its_bucket(self):
		rows = [
			{"due_date": "2026-10-30", "total": 100},  # not due
			{"due_date": "2026-10-22", "total": 10},  # due today: not overdue yet
			{"due_date": None, "total": 5},  # no due date: counted as not due
			{"due_date": "2026-10-21", "total": 20},  # 1 day
			{"due_date": "2026-09-22", "total": 30},  # 30 days
			{"due_date": "2026-09-21", "total": 40},  # 31 days
			{"due_date": "2026-07-24", "total": 50},  # 90 days
			{"due_date": "2026-07-23", "total": 60},  # 91 days
		]
		buckets = {bucket["key"]: bucket["value"] for bucket in rules.aging(rows, TODAY)}
		self.assertEqual(buckets, {"current": 115, "d30": 50, "d60": 40, "d90": 50, "older": 60})

	def test_each_bucket_opens_the_invoices_it_holds(self):
		filters = {bucket["key"]: bucket["filters"]["due_date"] for bucket in rules.aging([], TODAY)}
		self.assertEqual(filters["current"], [">=", "2026-10-22"])
		self.assertEqual(filters["d30"], ["between", ["2026-09-22", "2026-10-21"]])
		self.assertEqual(filters["d60"], ["between", ["2026-08-23", "2026-09-21"]])
		self.assertEqual(filters["older"], ["<=", "2026-07-23"])

	def test_who_owes_the_most_past_due(self):
		rows = [
			{"customer": "C1", "customer_name": "Alpha", "total": 500, "oldest": "2026-10-12"},
			{"customer": "C2", "customer_name": "Beta", "total": 900, "oldest": "2026-07-01"},
			{"customer": "C3", "customer_name": "Gamma", "total": 0, "oldest": "2026-10-01"},
		]
		owing = rules.most_overdue(rows, TODAY)
		self.assertEqual([row["title"] for row in owing], ["Beta", "Alpha"])
		self.assertEqual(owing[0]["when"], "oldest 113 days overdue")
		self.assertEqual(owing[0]["band"], "overdue")
		self.assertEqual(owing[1]["band"], "soon")
		self.assertEqual((owing[0]["doctype"], owing[0]["docname"]), ("Customer", "C2"))


class Lists(unittest.TestCase):
	def test_the_soonest_due_first_and_no_date_last(self):
		rows = [
			{"name": "SO-3", "customer_name": "C", "delivery_date": None, "base_grand_total": 3, "per_delivered": 0},
			{"name": "SO-2", "customer_name": "B", "delivery_date": "2026-10-30", "base_grand_total": 2, "per_delivered": 40},
			{"name": "SO-1", "customer_name": "A", "delivery_date": "2026-10-19", "base_grand_total": 1, "per_delivered": 0},
		]
		listed = rules.due_rows(rows, TODAY, "Sales Order", "customer_name", "delivery_date",
			value="base_grand_total", done="per_delivered")
		self.assertEqual([row["docname"] for row in listed], ["SO-1", "SO-2", "SO-3"])
		self.assertEqual([row["band"] for row in listed], ["overdue", "later", "none"])
		self.assertEqual(listed[0]["when"], "overdue by 3 days")
		self.assertEqual(listed[2]["when"], "no date set")
		self.assertEqual(listed[1]["progress"], 40)
		self.assertEqual(listed[1]["value"], 2)

	def test_how_far_a_work_order_has_got(self):
		rows = [{"name": "WO-1", "item_name": "Paint", "planned_end_date": "2026-10-23 17:00:00", "qty": 200, "produced_qty": 50}]
		listed = rules.due_rows(rows, TODAY, "Work Order", "item_name", "planned_end_date", done="produced_qty", total="qty")
		self.assertEqual((listed[0]["progress"], listed[0]["band"], listed[0]["when"]), (25, "today", "due tomorrow"))

	def test_stock_below_zero_first_then_the_furthest_under_its_level(self):
		levels = [
			{"item_code": "A", "warehouse": "Stores - AC", "level": 100},
			{"item_code": "B", "warehouse": "Stores - AC", "level": 10},
			{"item_code": "C", "warehouse": "Stores - AC", "level": 10},
			{"item_code": "D", "warehouse": "Stores - AC", "level": 0},  # no level set
		]
		bins = [
			{"item_code": "A", "warehouse": "Stores - AC", "projected_qty": 50},  # half its level
			{"item_code": "B", "warehouse": "Stores - AC", "projected_qty": 1},  # a tenth
			{"item_code": "C", "warehouse": "Stores - AC", "projected_qty": 11},  # above it
			{"item_code": "D", "warehouse": "Stores - AC", "projected_qty": 5},  # no level, above zero
			{"item_code": "E", "warehouse": "Shop - AC", "projected_qty": -4},  # below zero, no level
			{"item_code": "F", "warehouse": "Shop - AC", "projected_qty": -1},
		]
		found = rules.to_reorder(levels, bins)
		self.assertEqual([row["docname"] for row in found["rows"]], ["E", "F", "B", "A"])
		self.assertEqual((found["count"], found["short"]), (4, 2))
		self.assertEqual(found["rows"][0]["warehouse"], "Shop")
		self.assertEqual(found["rows"][0]["band"], "overdue")
		self.assertEqual(found["rows"][2], {"title": "B", "doctype": "Item", "docname": "B", "warehouse": "Stores",
			"projected": 1, "level": 10, "band": "today"})

	def test_a_level_is_for_its_own_warehouse_only(self):
		found = rules.to_reorder([{"item_code": "A", "warehouse": "W1", "level": 10}],
			[{"item_code": "A", "warehouse": "W2", "projected_qty": 1}])
		self.assertEqual(found["count"], 0)

	def test_drafts_the_oldest_first_and_how_long_untouched(self):
		found = [
			("Sales Invoice", {"name": "SINV-2", "modified": "2026-10-21 10:00:00", "title": "Acme"}),
			("Stock Entry", {"name": "STE-9", "modified": "2026-10-10 08:00:00", "title": "STE-9"}),
			("Payment Entry", {"name": "PE-1", "modified": "2026-10-22 08:00:00"}),
		]
		listed = rules.drafts(found, TODAY)
		self.assertEqual([row["docname"] for row in listed["rows"]], ["STE-9", "SINV-2", "PE-1"])
		self.assertEqual([row["when"] for row in listed["rows"]], ["untouched for 12 days", "untouched for 1 day", "untouched today"])
		self.assertEqual([row["band"] for row in listed["rows"]], ["overdue", "none", "none"])
		# a title that is only its name, or none at all, reads as what it is
		self.assertEqual([row["title"] for row in listed["rows"]], ["Stock Entry", "Acme", "Payment Entry"])
		self.assertEqual(listed["count"], 3)

	def test_the_largest_first_as_bars(self):
		rows = [{"customer": "C1", "customer_name": "Alpha", "total": 10}, {"customer": "C2", "customer_name": "Beta", "total": 30},
			{"customer": "C3", "customer_name": "", "total": 20}, {"customer": "C4", "customer_name": "Zero", "total": 0}]
		bars = rules.ranked(rows, "customer_name", "total", name="customer", doctype="Customer")
		self.assertEqual([bar["label"] for bar in bars], ["Beta", "C3", "Alpha"])
		self.assertEqual(bars[0], {"label": "Beta", "value": 30.0, "doctype": "Customer", "docname": "C2"})

	def test_names_without_the_company_abbreviation(self):
		self.assertEqual(rules.short_name("Stores - AC"), "Stores")
		self.assertEqual(rules.short_name("Cash"), "Cash")
		self.assertEqual(rules.short_name("Bank - Main - AC"), "Bank - Main")


class Attention(unittest.TestCase):
	def test_each_desk_has_its_checks_and_only_where_they_may_read(self):
		self.assertEqual(rules.attention_for([rules.PROJECTS], {"Task"}), ["tasks_overdue"])
		self.assertEqual(rules.attention_for([rules.PROJECTS], set()), [])
		finance = rules.attention_for([rules.FINANCE], EVERYTHING)
		self.assertIn("invoices_overdue", finance)
		self.assertNotIn("quotations_expiring", finance)

	def test_only_what_there_is_some_of_the_most_pressing_first(self):
		counts = {"quotations_expiring": 4, "bills_due": 2, "orders_late": 1, "invoices_overdue": 0}
		rows = rules.attention_rows(counts, TODAY, "Acme")
		self.assertEqual([row["key"] for row in rows], ["orders_late", "bills_due", "quotations_expiring"])
		self.assertEqual(rows[0]["label"], "Sales order late to deliver")
		self.assertEqual(rows[1]["label"], "Supplier bills due this week")
		self.assertEqual(rows[0]["route"], ["List", "Sales Order"])
		self.assertEqual(rows[0]["filters"]["delivery_date"], ["<", "2026-10-22"])
		self.assertEqual(rows[0]["filters"]["company"], "Acme")

	def test_what_each_check_counts(self):
		self.assertEqual(rules.attention_filters("bills_due", TODAY)["due_date"], ["<=", "2026-10-29"])
		self.assertEqual(rules.attention_filters("quotations_expiring", TODAY)["valid_till"], ["between", ["2026-10-22", "2026-10-29"]])
		# stock below zero is wrong in any company
		self.assertNotIn("company", rules.attention_filters("negative_stock", TODAY, "Acme"))
		for key, *_rest in rules.ATTENTION:
			self.assertIsInstance(rules.attention_filters(key, TODAY, "Acme"), dict, key)


class MostMade(unittest.TestCase):
	def test_the_users_own_work_first_then_their_desks_usual(self):
		counts = {"Payment Entry": 30, "Sales Invoice": 12, "Journal Entry": 0}
		creatable = {"Payment Entry", "Sales Invoice", "Journal Entry", "Sales Order", "Quotation"}
		self.assertEqual(rules.most_made(counts, [rules.FINANCE, rules.SALES], creatable),
			["Payment Entry", "Sales Invoice", "Journal Entry", "Sales Order"])

	def test_only_what_they_may_make(self):
		self.assertEqual(rules.most_made({"Sales Invoice": 5}, [rules.FINANCE], {"Payment Entry"}), ["Payment Entry"])

	def test_ties_go_to_the_usual_order(self):
		self.assertEqual(rules.most_made({"Stock Entry": 2, "Sales Invoice": 2}, [], {"Stock Entry", "Sales Invoice"}),
			["Sales Invoice", "Stock Entry"])

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
		self.assertEqual(module_pages_rules.attention_in(["Sales Order", "Quotation", "Item"]),
			["orders_late", "orders_to_bill", "quotations_expiring"])

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
		self.assertGreaterEqual(color_rules.contrast(self.colors()["--cvt-header-deep"], "#ffffff"), 4.5)

	def test_a_color_too_light_for_white_text_is_named(self):
		self.assertEqual(color_rules.white_text_shortfalls({"Header": "#eaa51a", "Done": "#1e7a46", "Blank": ""}), ["Header"])

	def test_every_value_is_a_hex_color_the_desk_will_take(self):
		import re

		for name, value in self.colors().items():
			self.assertRegex(name, r"^--cvt-[a-z-]+$")
			self.assertTrue(re.fullmatch(r"#[0-9a-f]{6}|\d{1,2}px", value), (name, value))


if __name__ == "__main__":
	unittest.main()
