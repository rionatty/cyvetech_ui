"""The desk home's and the module pages' server side (home.py, module_pages.py)
against the stand-in Frappe in fake_frappe.py, with a small ERPNext company in
it: what each user is shown, read as they may read it, and never an error."""

import datetime
import types
import unittest

import fake_frappe

frappe = fake_frappe.install()
home = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.home")
module_pages = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.module_pages")
settings = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.settings")
boot = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.boot")
settings_controller = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.doctype.cyvetech_ui_settings.cyvetech_ui_settings")

USER = "jane@example.com"
ACME, OTHER = "Acme Ltd", "Other Ltd"
FINANCE_READS = {"Sales Invoice", "Purchase Invoice", "Payment Entry", "GL Entry", "Account", "Customer"}
SALES_READS = {"Sales Order", "Quotation", "Customer", "Bin", "Warehouse", "Item"}


def seed(fake):
	"""Acme in October 2026: sales, what is owed both ways, two bank accounts, stock and orders."""
	fake.today = "2026-10-22"
	fake.now = datetime.datetime(2026, 10, 22, 15, 30)
	fake.user_defaults = {"Company": ACME}
	fake.tables["Company"] = [{"name": ACME, "default_currency": "UGX"}, {"name": OTHER, "default_currency": "KES"}]
	fake.tables["User"] = [{"name": USER, "first_name": "Jane"}]
	fake.tables["Sales Invoice"] = [
		# this month: 1,000 + 500 - 100 (a return)
		{"name": "SI-1", "company": ACME, "docstatus": 1, "posting_date": "2026-10-03", "base_net_total": 1000,
			"customer": "C1", "customer_name": "Alpha", "outstanding_amount": 0, "due_date": "2026-11-02", "party_account_currency": "UGX"},
		{"name": "SI-2", "company": ACME, "docstatus": 1, "posting_date": "2026-10-20", "base_net_total": 500,
			"customer": "C2", "customer_name": "Beta", "outstanding_amount": 500, "due_date": "2026-11-19", "party_account_currency": "UGX"},
		{"name": "SI-3", "company": ACME, "docstatus": 1, "posting_date": "2026-10-21", "base_net_total": -100,
			"customer": "C1", "customer_name": "Alpha", "outstanding_amount": 0, "due_date": "2026-10-21", "party_account_currency": "UGX"},
		# the same days of September: 800
		{"name": "SI-4", "company": ACME, "docstatus": 1, "posting_date": "2026-09-10", "base_net_total": 800,
			"customer": "C2", "customer_name": "Beta", "outstanding_amount": 300, "due_date": "2026-09-25", "party_account_currency": "UGX"},
		# late in September, after the 22nd: not in the comparison
		{"name": "SI-5", "company": ACME, "docstatus": 1, "posting_date": "2026-09-28", "base_net_total": 999,
			"customer": "C3", "customer_name": "Gamma", "outstanding_amount": 0, "due_date": "2026-10-28", "party_account_currency": "UGX"},
		# owed in dollars, long overdue
		{"name": "SI-6", "company": ACME, "docstatus": 1, "posting_date": "2026-06-01", "base_net_total": 7400,
			"customer": "C3", "customer_name": "Gamma", "outstanding_amount": 2, "due_date": "2026-06-30", "party_account_currency": "USD"},
		# a draft, a cancelled one and another company's: none of them count
		{"name": "SI-7", "company": ACME, "docstatus": 0, "posting_date": "2026-10-05", "base_net_total": 5000,
			"customer": "C1", "customer_name": "Alpha", "outstanding_amount": 5000, "due_date": "2026-10-05", "party_account_currency": "UGX",
			"owner": USER, "creation": "2026-10-05 09:00:00", "modified": "2026-10-05 09:00:00", "title": "Alpha"},
		{"name": "SI-8", "company": ACME, "docstatus": 2, "posting_date": "2026-10-06", "base_net_total": 4000,
			"customer": "C1", "customer_name": "Alpha", "outstanding_amount": 4000, "due_date": "2026-10-06", "party_account_currency": "UGX"},
		{"name": "SI-9", "company": OTHER, "docstatus": 1, "posting_date": "2026-10-07", "base_net_total": 3000,
			"customer": "C9", "customer_name": "Other", "outstanding_amount": 3000, "due_date": "2026-10-07", "party_account_currency": "KES"},
	]
	fake.tables["Purchase Invoice"] = [
		{"name": "PI-1", "company": ACME, "docstatus": 1, "outstanding_amount": 700, "due_date": "2026-10-25", "party_account_currency": "UGX"},
		{"name": "PI-2", "company": ACME, "docstatus": 1, "outstanding_amount": 300, "due_date": "2026-12-01", "party_account_currency": "UGX"},
	]
	fake.tables["Payment Entry"] = [
		{"name": "PE-1", "company": ACME, "docstatus": 1, "payment_type": "Receive", "posting_date": "2026-10-04", "base_received_amount": 600},
		{"name": "PE-2", "company": ACME, "docstatus": 1, "payment_type": "Pay", "posting_date": "2026-10-04", "base_received_amount": 900},
	]
	fake.tables["Account"] = [
		{"name": "Cash - AL", "company": ACME, "account_type": "Cash", "is_group": 0, "disabled": 0},
		{"name": "Stanbic - AL", "company": ACME, "account_type": "Bank", "is_group": 0, "disabled": 0},
		{"name": "Debtors - AL", "company": ACME, "account_type": "Receivable", "is_group": 0, "disabled": 0},
	]
	fake.tables["GL Entry"] = [
		{"account": "Cash - AL", "company": ACME, "is_cancelled": 0, "posting_date": "2026-10-01", "debit": 300, "credit": 50},
		{"account": "Stanbic - AL", "company": ACME, "is_cancelled": 0, "posting_date": "2026-10-02", "debit": 5000, "credit": 1000},
		{"account": "Stanbic - AL", "company": ACME, "is_cancelled": 1, "posting_date": "2026-10-02", "debit": 9999, "credit": 0},
		{"account": "Debtors - AL", "company": ACME, "is_cancelled": 0, "posting_date": "2026-10-02", "debit": 777, "credit": 0},
	]
	fake.tables["Sales Order"] = [
		{"name": "SO-1", "company": ACME, "docstatus": 1, "status": "To Deliver and Bill", "delivery_date": "2026-10-20",
			"transaction_date": "2026-10-02", "base_net_total": 2000, "base_grand_total": 2360, "customer": "C1",
			"customer_name": "Alpha", "per_delivered": 0},
		{"name": "SO-2", "company": ACME, "docstatus": 1, "status": "To Deliver", "delivery_date": "2026-10-30",
			"transaction_date": "2026-10-12", "base_net_total": 1000, "base_grand_total": 1180, "customer": "C2",
			"customer_name": "Beta", "per_delivered": 50},
		{"name": "SO-3", "company": ACME, "docstatus": 1, "status": "To Bill", "delivery_date": "2026-10-01",
			"transaction_date": "2026-09-05", "base_net_total": 400, "base_grand_total": 472, "customer": "C2",
			"customer_name": "Beta", "per_delivered": 100},
	]
	fake.tables["Quotation"] = [
		{"name": "QTN-1", "company": ACME, "docstatus": 1, "status": "Open", "valid_till": "2026-10-25", "base_net_total": 900},
	]
	fake.tables["Warehouse"] = [
		{"name": "Stores - AL", "company": ACME, "is_group": 0, "disabled": 0},
		{"name": "Kampala - OL", "company": OTHER, "is_group": 0, "disabled": 0},
	]
	fake.tables["Bin"] = [
		{"item_code": "PAINT", "warehouse": "Stores - AL", "stock_value": 1200, "projected_qty": 5, "actual_qty": 5},
		{"item_code": "BRUSH", "warehouse": "Stores - AL", "stock_value": 300, "projected_qty": -2, "actual_qty": -2},
		{"item_code": "PAINT", "warehouse": "Kampala - OL", "stock_value": 99999, "projected_qty": 1, "actual_qty": 1},
	]
	fake.tables["Item"] = [{"name": "PAINT", "item_name": "Gloss Paint"}, {"name": "BRUSH", "item_name": "Brush"}]
	fake.tables["Item Reorder"] = [
		{"parent": "PAINT", "parenttype": "Item", "warehouse": "Stores - AL", "warehouse_reorder_level": 20},
		{"parent": "PAINT", "parenttype": "Item", "warehouse": "Kampala - OL", "warehouse_reorder_level": 20},
	]
	fake.title_fields = {"Sales Invoice": "title"}
	fake.meta_fields["Sales Invoice"] = {"title"}
	fake.doctypes = set(fake.tables) | {"Sales Invoice", "Purchase Order", "Stock Entry", "Task", "Work Order"}


class Base(unittest.TestCase):
	def setUp(self):
		fake_frappe.reset(frappe)
		seed(frappe)

	def as_(self, roles, readable, creatable=()):
		frappe.roles[USER] = list(roles)
		frappe.readable = set(readable)
		frappe.creatable = set(creatable)

	def card(self, found, key):
		return next(card for card in found["cards"] if card["key"] == key)

	def panel(self, found, key):
		return next(panel for panel in found["panels"] if panel["key"] == key)


class Summary(Base):
	def test_a_guest_is_refused(self):
		frappe.session.user = "Guest"
		with self.assertRaises(frappe.PermissionError):
			home.summary()

	def test_the_greeting_and_the_company(self):
		self.as_(["Accounts User"], FINANCE_READS)
		found = home.summary()
		self.assertEqual((found["greeting"], found["first_name"]), ("Good afternoon", "Jane"))
		self.assertEqual((found["today"], found["company"], found["currency"]), ("2026-10-22", ACME, "UGX"))
		self.assertEqual(found["desks"], ["finance"])

	def test_an_accountant_is_drawn_frames_for_the_money(self):
		self.as_(["Accounts User"], FINANCE_READS)
		found = home.summary()
		self.assertEqual([card["key"] for card in found["cards"]], ["sales", "receivable", "payable", "cash"])
		self.assertTrue(all(card.get("frame") for card in found["cards"]))
		self.assertEqual([panel["key"] for panel in found["panels"]], ["attention", "trend", "aging", "cash", "customers", "drafts"])

	def test_someone_with_no_desk_gets_their_own_work(self):
		self.as_(["Employee"], {"ToDo"})
		frappe.tables["ToDo"] = [
			{"name": "T1", "allocated_to": USER, "status": "Open", "description": "Call the bank", "date": "2026-10-20",
				"reference_type": "", "reference_name": "", "creation": "2026-10-01 10:00:00", "priority": "Medium", "modified": "2026-10-01"},
		]
		found = home.summary()
		self.assertEqual([(card["key"], card["value"]) for card in found["cards"]], [("waiting", 1), ("unread", 0)])
		self.assertEqual(found["cards"][0]["note"], "1 overdue")
		self.assertEqual(found["panels"], [])
		self.assertEqual(found["waiting"]["items"][0]["title"], "Call the bank")

	def test_a_panel_switched_off_is_not_offered(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.doctypes.add(settings.DOCTYPE)
		frappe.singles[settings.DOCTYPE] = {"home_trend": "0", "home_aging": "0"}
		self.assertNotIn("trend", [panel["key"] for panel in home.summary()["panels"]])

	def test_what_the_user_makes_most_and_it_is_kept_an_hour(self):
		self.as_(["Accounts User"], FINANCE_READS, creatable={"Sales Invoice", "Payment Entry", "Journal Entry"})
		frappe.doctypes |= {"Payment Entry", "Journal Entry"}
		frappe.tables["Payment Entry"] += [
			{"name": f"PE-{i}", "owner": USER, "creation": "2026-10-1%d 09:00:00" % i, "docstatus": 1} for i in range(3, 6)
		]
		frappe.tables["Sales Invoice"][0].update(owner=USER, creation="2026-10-03 09:00:00")
		self.assertEqual(home.summary()["create"], ["Payment Entry", "Sales Invoice", "Journal Entry"])
		self.assertEqual(frappe.cache_seconds[(home.MADE_KEY, USER)], 3600)
		frappe.tables["Payment Entry"] = []  # read again within the hour: the kept answer
		self.assertEqual(home.summary()["create"][0], "Payment Entry")

	def test_a_document_the_user_may_make_but_not_read_is_offered_never_counted(self):
		self.as_(["Accounts User"], FINANCE_READS, creatable={"Journal Entry"})
		frappe.doctypes.add("Journal Entry")
		self.assertEqual(home.summary()["create"], ["Journal Entry"])
		self.assertFalse([query for query in frappe.queries if query.doctype == "Journal Entry"])
		self.assertEqual(frappe.errors, [])

	def test_a_part_that_fails_is_logged_and_the_rest_comes(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.fail_get_all.add("ToDo")
		found = home.summary()
		self.assertEqual(found["waiting"]["tasks"], 0)
		self.assertTrue(any("CyveTech home" in error for error in frappe.errors))


class FiguresForFinance(Base):
	def setUp(self):
		super().setUp()
		self.as_(["Accounts User"], FINANCE_READS)
		self.found = home.figures()

	def test_sales_this_month_against_the_same_days_last_month(self):
		sales = self.card(self.found, "sales")
		self.assertEqual(sales["value"], 1400)  # 1,000 + 500 - 100: drafts, cancelled and other companies left out
		self.assertEqual(sales["change"], {"percent": 75, "direction": "up"})  # against 800
		self.assertEqual(sales["route"], ["List", "Sales Invoice"])
		self.assertEqual(sales["filters"]["posting_date"], ["between", ["2026-10-01", "2026-10-22"]])
		self.assertEqual(sales["filters"]["company"], ACME)

	def test_what_customers_owe_in_the_companys_currency(self):
		frappe.cached.clear()
		home._exchange_rate = lambda from_currency, to_currency, day: 3700.0 if from_currency == "USD" else None
		found = home.figures()
		owed = self.card(found, "receivable")
		self.assertEqual(owed["value"], 500 + 300 + 2 * 3700)
		self.assertEqual(owed["note"], {"money": 300 + 7400, "words": "overdue"})
		self.assertEqual(owed["tone"], "rose")
		self.assertEqual(owed["route"], ["query-report", "Accounts Receivable"])
		self.assertEqual(owed["options"], {"company": ACME})

	def test_a_currency_with_no_rate_counts_at_one_and_is_logged(self):
		def no_rate(*args):
			raise RuntimeError("no exchange rate")

		frappe.cached.clear()
		home._exchange_rate = no_rate
		self.assertEqual(self.card(home.figures(), "receivable")["value"], 802)
		self.assertIn("CyveTech home: exchange rate USD", frappe.errors)

	def test_what_the_company_owes_and_what_falls_due_this_week(self):
		payable = self.card(self.found, "payable")
		self.assertEqual(payable["value"], 1000)
		self.assertEqual(payable["note"], {"money": 700, "words": "due this week"})

	def test_cash_and_bank_from_the_ledger(self):
		cash = self.card(self.found, "cash")
		self.assertEqual(cash["value"], 250 + 4000)  # a cancelled entry and the debtors account left out
		self.assertEqual(cash["note"], "In 2 accounts")
		self.assertEqual(cash["options"]["account"], ["Cash - AL", "Stanbic - AL"])
		bars = self.panel(self.found, "cash")["rows"]
		self.assertEqual([(bar["label"], bar["value"]) for bar in bars], [("Stanbic", 4000), ("Cash", 250)])

	def test_six_months_of_billing_and_collecting(self):
		trend = self.panel(self.found, "trend")
		self.assertEqual(trend["title"], "Sales and Collections")
		self.assertEqual([series["key"] for series in trend["series"]], ["billed", "collected"])
		self.assertEqual(trend["months"][-1]["values"], [1400, 600])  # a payment out is not collected
		self.assertEqual(trend["months"][-2]["values"], [1799, 0])
		self.assertEqual(trend["months"][0]["from"], "2026-05-01")

	def test_the_aging_and_who_owes_most(self):
		frappe.cached.clear()
		home._exchange_rate = lambda *args: 3700.0
		aging = self.panel(home.figures(), "aging")
		buckets = {bucket["key"]: bucket["value"] for bucket in aging["buckets"]}
		self.assertEqual(buckets, {"current": 500, "d30": 300, "d60": 0, "d90": 0, "older": 7400})
		self.assertEqual([row["docname"] for row in aging["rows"]], ["C3", "C2"])

	def test_top_customers_this_month(self):
		customers = self.panel(self.found, "customers")
		self.assertEqual([(bar["label"], bar["value"]) for bar in customers["rows"]], [("Alpha", 900), ("Beta", 500)])

	def test_what_needs_attention(self):
		attention = self.panel(self.found, "attention")
		self.assertEqual([(row["key"], row["value"]) for row in attention["rows"]], [("invoices_overdue", 2), ("bills_due", 1)])

	def test_the_users_drafts(self):
		drafts = self.panel(self.found, "drafts")
		self.assertEqual([(row["doctype"], row["docname"], row["title"]) for row in drafts["rows"]], [("Sales Invoice", "SI-7", "Alpha")])
		self.assertEqual(drafts["rows"][0]["when"], "untouched for 17 days")

	def test_every_query_was_one_the_user_may_make(self):
		for query in frappe.queries:
			if query.checked:
				self.assertIn(query.doctype, FINANCE_READS)

	def test_totals_go_as_frappe_v16_wants_them(self):
		fields = [field for query in frappe.queries for field in (query.fields or [])]
		self.assertIn({"SUM": "base_net_total", "as": "total"}, fields)
		self.assertFalse([field for field in fields if isinstance(field, str) and "(" in field])

	def test_the_figures_are_kept_five_minutes_and_read_afresh_on_request(self):
		self.assertEqual(frappe.cache_seconds[(home.FIGURES_KEY, USER)], 300)
		frappe.tables["Sales Invoice"][0]["base_net_total"] = 5000
		self.assertEqual(self.card(home.figures(), "sales")["value"], 1400)
		self.assertEqual(self.card(home.figures(fresh=1), "sales")["value"], 5400)

	def test_a_new_day_or_another_desk_reads_them_again(self):
		frappe.tables["Sales Invoice"][0]["base_net_total"] = 5000
		frappe.today = "2026-10-23"
		self.assertEqual(self.card(home.figures(), "sales")["value"], 5400)


class FiguresForOthers(Base):
	def test_a_sales_clerk_gets_orders_never_invoices(self):
		self.as_(["Sales User"], SALES_READS)
		found = home.figures()
		self.assertEqual([card["key"] for card in found["cards"]], ["orders", "to_deliver", "quotations"])
		self.assertEqual(self.card(found, "orders")["value"], 3000)
		self.assertEqual(self.card(found, "to_deliver")["value"], 2)
		self.assertEqual(self.card(found, "to_deliver")["note"], "1 late")
		self.assertEqual(self.card(found, "quotations")["note"], {"money": 900, "words": "quoted"})
		self.assertEqual(self.panel(found, "trend")["title"], "Orders by Month")
		self.assertFalse([query for query in frappe.queries if query.doctype in ("Sales Invoice", "Purchase Invoice")])

	def test_orders_to_deliver_the_soonest_first(self):
		self.as_(["Sales User"], SALES_READS)
		deliver = self.panel(home.figures(), "deliver")
		self.assertEqual([row["docname"] for row in deliver["rows"]], ["SO-1", "SO-2"])
		self.assertEqual(deliver["rows"][0]["band"], "overdue")
		self.assertEqual(deliver["total"], 2)

	def test_a_storekeeper_gets_the_stock(self):
		self.as_(["Stock User"], {"Bin", "Warehouse", "Item", "Sales Order"})
		found = home.figures()
		self.assertEqual(self.card(found, "stock_value")["value"], 1500)  # the other company's warehouse left out
		self.assertEqual(self.card(found, "stock_value")["note"], "In 1 warehouse")
		reorder = self.panel(found, "reorder")
		self.assertEqual([(row["docname"], row["title"]) for row in reorder["rows"]], [("BRUSH", "Brush"), ("PAINT", "Gloss Paint")])
		self.assertEqual(self.card(found, "reorder")["note"], "1 below zero")

	def test_figures_on_frappe_v15_go_as_sql_it_takes(self):
		frappe.__version__ = "15.40.0"
		self.as_(["Accounts User"], FINANCE_READS)
		found = home.figures()
		self.assertEqual(self.card(found, "sales")["value"], 1400)
		fields = [field for query in frappe.queries for field in (query.fields or [])]
		self.assertIn("sum(`base_net_total`) as total", fields)
		self.assertFalse([field for field in fields if isinstance(field, dict)])

	def test_a_figure_that_fails_is_left_out_and_the_rest_come(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.fail_get_all.add("GL Entry")
		found = home.figures()
		self.assertNotIn("cash", [card["key"] for card in found["cards"]])
		self.assertIn("sales", [card["key"] for card in found["cards"]])
		self.assertIn("CyveTech home: figure: cash", frappe.errors)

	def test_nobody_at_all_gets_no_panels(self):
		self.as_(["Employee"], set())
		self.assertEqual((home.figures()["cards"], home.figures()["panels"]), ([], []))


class ModulePages(Base):
	def setUp(self):
		super().setUp()
		frappe.doctypes |= {"Workspace Sidebar", "Workspace"}
		frappe.tables["Workspace Sidebar"] = [{"name": "Selling"}]
		frappe.tables["Workspace"] = [{"name": "Selling"}]
		# documents with attributes, as Frappe's are (a dict's .items is its own method)
		row = types.SimpleNamespace
		frappe.docs[("Workspace Sidebar", "Selling")] = row(items=[
			row(link_type="DocType", link_to="Quotation"), row(link_type="DocType", link_to="Sales Order"),
			row(link_type="Report", link_to="Sales Analytics"),
		])
		frappe.docs[("Workspace", "Selling")] = row(
			links=[row(type="Link", link_type="DocType", link_to="Sales Order"), row(type="Card Break", link_type="", link_to="")],
			shortcuts=[row(type="DocType", link_to="Customer")],
		)
		frappe.tables["ToDo"] = [
			{"name": "T1", "allocated_to": USER, "status": "Open", "description": "Approve SO-1", "date": "2026-10-21",
				"reference_type": "Sales Order", "reference_name": "SO-1", "creation": "2026-10-20", "priority": "Medium", "modified": "2026-10-20"},
			{"name": "T2", "allocated_to": USER, "status": "Open", "description": "Fix an item", "date": None,
				"reference_type": "Item", "reference_name": "PAINT", "creation": "2026-10-20", "priority": "Medium", "modified": "2026-10-20"},
		]
		frappe.tables["Notification Log"] = []

	def test_what_waits_and_what_needs_attention_in_the_module(self):
		self.as_(["Sales User"], SALES_READS, creatable={"Sales Order", "Quotation"})
		found = module_pages.summary("Selling")
		self.assertEqual(found["waiting"]["tasks"], 1)
		self.assertEqual(found["waiting"]["items"][0]["docname"], "SO-1")
		self.assertEqual(found["doctypes"], ["Sales Order"])
		self.assertEqual([(row["key"], row["value"]) for row in found["attention"]],
			[("orders_late", 1), ("orders_to_bill", 1), ("quotations_expiring", 1)])
		self.assertEqual(found["action"], "Sales Order")

	def test_only_the_modules_documents_are_asked_for(self):
		self.as_(["Sales User"], SALES_READS)
		module_pages.summary("Selling")
		todo = next(query for query in frappe.queries if query.doctype == "ToDo")
		self.assertEqual(todo.filters["reference_type"], ["in", ["Quotation", "Sales Order", "Customer"]])

	def test_a_check_the_user_may_not_read_is_not_counted(self):
		self.as_(["Sales User"], {"Quotation", "Customer"})
		found = module_pages.summary("Selling")
		self.assertEqual([row["key"] for row in found["attention"]], ["quotations_expiring"])
		self.assertFalse([query for query in frappe.queries if query.checked and query.doctype == "Sales Order"])

	def test_a_workspace_with_no_menu_still_answers(self):
		self.as_(["Sales User"], SALES_READS)
		found = module_pages.summary("Nowhere")
		self.assertEqual((found["waiting"]["tasks"], found["attention"], found["action"]), (0, [], None))


class SettingsAndBoot(Base):
	def test_an_update_writes_the_defaults_of_settings_never_saved(self):
		frappe.doctypes.add(settings.DOCTYPE)
		frappe.singles[settings.DOCTYPE] = {"sidebar_color": "#222222", "home_trend": "0"}
		written = settings.ensure_defaults()
		self.assertIn("home_enabled", written)
		self.assertEqual(frappe.singles[settings.DOCTYPE]["home_enabled"], 1)
		self.assertEqual(frappe.singles[settings.DOCTYPE]["accent_color"], "#2F64B0")
		# what someone saved is left alone
		self.assertEqual(frappe.singles[settings.DOCTYPE]["sidebar_color"], "#222222")
		self.assertEqual(frappe.singles[settings.DOCTYPE]["home_trend"], "0")
		self.assertEqual(settings.ensure_defaults(), [])

	def test_a_site_that_never_saved_them_is_left_to_frappes_defaults(self):
		frappe.doctypes.add(settings.DOCTYPE)
		self.assertEqual(settings.ensure_defaults(), [])
		self.assertEqual(frappe.singles.get(settings.DOCTYPE), None)

	def test_the_boot_carries_the_home_and_the_module_pages(self):
		payload = boot.payload(settings.merge({}), [])
		self.assertEqual(payload["home"]["enabled"], 1)
		self.assertEqual(payload["home"]["modules"][:3], ["CRM", "Selling", "Buying"])
		self.assertEqual(payload["module_pages"]["flow"], ["CRM", "Selling", "Buying", "Stock", "Manufacturing", "Accounting"])
		self.assertEqual(payload["module_pages"]["actions"]["Selling"], "Sales Order")
		self.assertEqual(payload["theme"]["vars"]["--cvt-band-good"], "#1e7a46")

	def test_switched_off_in_the_settings(self):
		payload = boot.payload(settings.merge({"home_enabled": "0", "module_pages_enabled": "0"}), [])
		self.assertEqual((payload["home"]["enabled"], payload["module_pages"]["enabled"]), (0, 0))

	def test_a_header_too_light_for_white_text_is_saved_with_a_warning(self):
		doc = settings_controller.CyveTechUISettings({"header_color": "#fde68a", "danger_color": "#c53030"})
		doc.validate()
		self.assertEqual(doc.header_color, "#FDE68A")
		self.assertEqual(len(frappe.messages), 1)
		self.assertIn("<b>header_color</b>", frappe.messages[0])

	def test_the_shipped_colors_raise_no_warning(self):
		doc = settings_controller.CyveTechUISettings(dict(settings.DEFAULTS))
		doc.validate()
		self.assertEqual(frappe.messages, [])

	def test_a_malformed_status_color_is_refused(self):
		doc = settings_controller.CyveTechUISettings({"success_color": "green"})
		with self.assertRaises(frappe.ValidationError):
			doc.validate()


if __name__ == "__main__":
	unittest.main()
