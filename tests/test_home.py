"""The desk home's and the module pages' server side (home.py, module_pages.py)
against the stand-in Frappe in fake_frappe.py, with a small ERPNext company in
it: which tabs each user gets, what is on them, read as they may read it, and
never an error."""

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
FINANCE_READS = {"Sales Invoice", "Purchase Invoice", "Payment Entry", "GL Entry", "Account", "Customer", "Supplier"}
SALES_READS = {"Sales Order", "Quotation", "Customer", "Bin", "Warehouse", "Item"}
STOCK_READS = {"Bin", "Warehouse", "Item", "Stock Ledger Entry"}


def acme(**row):
	return dict(row, company=ACME)


def seed(fake):
	"""Acme in October 2026: its sales, what is owed both ways, its ledger, stock and orders, its projects,
	issues, leads, assets and inspections."""
	fake.today = "2026-10-22"
	fake.now = datetime.datetime(2026, 10, 22, 15, 30)
	fake.user_defaults = {"Company": ACME}
	fake.tables["Company"] = [{"name": ACME, "default_currency": "UGX"}, {"name": OTHER, "default_currency": "KES"}]
	fake.tables["User"] = [{"name": USER, "first_name": "Jane"}]
	invoice = lambda name, day, net, customer, customer_name, owed, due, territory="Kampala", currency="UGX", docstatus=1, company=ACME: {
		"name": name, "company": company, "docstatus": docstatus, "posting_date": day, "base_net_total": net, "customer": customer,
		"customer_name": customer_name, "outstanding_amount": owed, "due_date": due, "party_account_currency": currency, "territory": territory,
	}
	fake.tables["Sales Invoice"] = [
		invoice("SI-1", "2026-10-03", 1000, "C1", "Alpha", 0, "2026-11-02"),  # this month: 1,000 + 500 - 100 (a return)
		invoice("SI-2", "2026-10-20", 500, "C2", "Beta", 500, "2026-11-19", territory="Jinja"),
		invoice("SI-3", "2026-10-21", -100, "C1", "Alpha", 0, "2026-10-21"),
		invoice("SI-4", "2026-09-10", 800, "C2", "Beta", 300, "2026-09-25"),  # the same days of September: 800
		invoice("SI-5", "2026-09-28", 999, "C3", "Gamma", 0, "2026-10-28"),  # after the 22nd: not in the comparison
		invoice("SI-6", "2026-06-01", 7400, "C3", "Gamma", 2, "2026-06-30", currency="USD"),  # owed in dollars, long overdue
		dict(invoice("SI-7", "2026-10-05", 5000, "C1", "Alpha", 5000, "2026-10-05", docstatus=0),  # a draft of the user's
			owner=USER, creation="2026-10-05 09:00:00", modified="2026-10-05 09:00:00", title="Alpha"),
		invoice("SI-8", "2026-10-06", 4000, "C1", "Alpha", 4000, "2026-10-06", docstatus=2),  # cancelled
		invoice("SI-9", "2026-10-07", 3000, "C9", "Other", 3000, "2026-10-07", currency="KES", company=OTHER),
	]
	fake.tables["Sales Invoice Item"] = [
		{"parent": "SI-1", "parenttype": "Sales Invoice", "item_code": "PAINT", "item_name": "Gloss Paint", "base_net_amount": 700},
		{"parent": "SI-1", "parenttype": "Sales Invoice", "item_code": "BRUSH", "item_name": "Brush", "base_net_amount": 300},
		{"parent": "SI-2", "parenttype": "Sales Invoice", "item_code": "PAINT", "item_name": "Gloss Paint", "base_net_amount": 500},
		{"parent": "SI-4", "parenttype": "Sales Invoice", "item_code": "PAINT", "item_name": "Gloss Paint", "base_net_amount": 800},
	]
	bill = lambda name, owed, due, supplier, supplier_name, net=0, day="2026-10-01": acme(
		name=name, docstatus=1, outstanding_amount=owed, due_date=due, party_account_currency="UGX", supplier=supplier,
		supplier_name=supplier_name, base_net_total=net, posting_date=day)
	fake.tables["Purchase Invoice"] = [
		bill("PI-1", 700, "2026-10-25", "S1", "Paint Co", net=700, day="2026-10-02"),
		bill("PI-2", 300, "2026-12-01", "S2", "Tins Ltd", net=300, day="2026-10-09"),
		bill("PI-3", 200, "2026-10-01", "S1", "Paint Co", net=200, day="2026-09-01"),  # overdue
	]
	fake.tables["Payment Entry"] = [
		acme(name="PE-1", docstatus=1, payment_type="Receive", posting_date="2026-10-04", base_received_amount=600),
		acme(name="PE-2", docstatus=1, payment_type="Pay", posting_date="2026-10-04", base_received_amount=900),
	]
	account = lambda name, root, kind="": acme(name=name, root_type=root, account_type=kind, is_group=0, disabled=0)
	fake.tables["Account"] = [
		account("Cash - AL", "Asset", "Cash"), account("Stanbic - AL", "Asset", "Bank"), account("Debtors - AL", "Asset", "Receivable"),
		account("Sales - AL", "Income"), account("Rent - AL", "Expense"), account("Salaries - AL", "Expense"), account("Fuel - AL", "Expense"),
	]
	ledger = lambda account_, day, debit=0, credit=0, cancelled=0, voucher="Journal Entry": acme(
		account=account_, posting_date=day, debit=debit, credit=credit, is_cancelled=cancelled, voucher_type=voucher)
	fake.tables["GL Entry"] = [
		ledger("Cash - AL", "2026-10-01", 300, 50),
		ledger("Stanbic - AL", "2026-10-02", 5000, 1000),
		ledger("Stanbic - AL", "2026-10-02", 9999, 0, cancelled=1),
		ledger("Debtors - AL", "2026-10-02", 777, 0),
		ledger("Sales - AL", "2026-10-03", credit=1000, voucher="Sales Invoice"),
		ledger("Sales - AL", "2026-09-10", credit=800, voucher="Sales Invoice"),
		ledger("Rent - AL", "2026-10-05", debit=300),
		ledger("Salaries - AL", "2026-10-20", debit=400),
		ledger("Fuel - AL", "2026-10-21", debit=50, credit=10),
		ledger("Sales - AL", "2026-10-21", debit=999, voucher="Period Closing Voucher"),  # a year's closing: left out
	]
	order = lambda name, status, delivery, day, net, grand, customer, customer_name, delivered, territory: acme(
		name=name, docstatus=1, status=status, delivery_date=delivery, transaction_date=day, base_net_total=net, base_grand_total=grand,
		customer=customer, customer_name=customer_name, per_delivered=delivered, territory=territory)
	fake.tables["Sales Order"] = [
		order("SO-1", "To Deliver and Bill", "2026-10-20", "2026-10-02", 2000, 2360, "C1", "Alpha", 0, "Kampala"),
		order("SO-2", "To Deliver", "2026-10-30", "2026-10-12", 1000, 1180, "C2", "Beta", 50, "Mbarara"),
		order("SO-3", "To Bill", "2026-10-01", "2026-09-05", 400, 472, "C2", "Beta", 100, "Jinja"),
	]
	fake.tables["Sales Order Item"] = [
		{"parent": "SO-1", "parenttype": "Sales Order", "item_code": "PAINT", "item_name": "Gloss Paint", "base_net_amount": 2000},
		{"parent": "SO-2", "parenttype": "Sales Order", "item_code": "BRUSH", "item_name": "Brush", "base_net_amount": 1000},
	]
	quote = lambda name, status, day, net, valid="2026-10-25": acme(name=name, docstatus=1, status=status, transaction_date=day, base_net_total=net, valid_till=valid)
	fake.tables["Quotation"] = [
		quote("QTN-1", "Open", "2026-10-01", 900),
		quote("QTN-2", "Ordered", "2026-09-15", 1500, valid="2026-09-30"),
		quote("QTN-3", "Lost", "2026-08-30", 300, valid="2026-09-15"),
		quote("QTN-4", "Expired", "2026-06-01", 50, valid="2026-06-30"),  # older than 90 days
	]
	fake.tables["Warehouse"] = [acme(name="Stores - AL", is_group=0, disabled=0), {"name": "Kampala - OL", "company": OTHER, "is_group": 0, "disabled": 0}]
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
	fake.tables["Stock Ledger Entry"] = [
		acme(posting_date="2026-10-05", actual_qty=10, stock_value_difference=1000, is_cancelled=0),
		acme(posting_date="2026-10-06", actual_qty=-4, stock_value_difference=-400, is_cancelled=0),
		acme(posting_date="2026-09-01", actual_qty=5, stock_value_difference=500, is_cancelled=0),
		acme(posting_date="2026-10-07", actual_qty=3, stock_value_difference=300, is_cancelled=1),
	]
	fake.tables["Material Request"] = [
		acme(name="MR-1", docstatus=1, status="Pending", schedule_date="2026-10-20", title="Pigment"),
		acme(name="MR-2", docstatus=1, status="Partially Ordered", schedule_date="2026-10-30", title="Tins"),
		acme(name="MR-3", docstatus=1, status="Ordered", schedule_date="2026-10-01", title="Done"),
	]
	fake.tables["Purchase Order"] = [
		acme(name="PO-1", docstatus=1, status="To Receive and Bill", schedule_date="2026-10-18", transaction_date="2026-10-04",
			base_net_total=600, base_grand_total=708, supplier="S1", supplier_name="Paint Co", per_received=0),
	]
	fake.tables["Project"] = [
		acme(name="PRJ-1", project_name="New Plant", status="Open", percent_complete=40, expected_end_date="2026-10-15"),
		acme(name="PRJ-2", project_name="Shop Fit", status="Open", percent_complete=80, expected_end_date="2026-11-30"),
		acme(name="PRJ-3", project_name="Old", status="Completed", percent_complete=100, expected_end_date="2026-05-01"),
	]
	fake.tables["Task"] = [{"name": "TASK-1", "subject": "Wire it", "status": "Open", "exp_end_date": "2026-10-20", "project": "PRJ-1", "progress": 10}]
	fake.tables["Timesheet"] = [
		acme(name="TS-1", docstatus=1, start_date="2026-10-02", total_hours=12.5),
		acme(name="TS-2", docstatus=0, start_date="2026-10-03", total_hours=5),
		acme(name="TS-3", docstatus=1, start_date="2026-09-28", total_hours=8),
	]
	fake.tables["Timesheet Detail"] = [
		{"parent": "TS-1", "parenttype": "Timesheet", "project": "PRJ-1", "hours": 8},
		{"parent": "TS-1", "parenttype": "Timesheet", "project": None, "hours": 4.5},
		{"parent": "TS-2", "parenttype": "Timesheet", "project": "PRJ-1", "hours": 5},
	]
	fake.tables["Issue"] = [
		{"name": "ISS-1", "subject": "Invoice wrong", "status": "Open", "opening_date": "2026-10-10", "priority": "High"},
		{"name": "ISS-2", "subject": "Login", "status": "Open", "opening_date": "2026-10-21", "priority": "Low"},
		{"name": "ISS-3", "subject": "Color", "status": "Replied", "opening_date": "2026-10-15", "priority": "High"},
		{"name": "ISS-4", "subject": "Delivery", "status": "On Hold", "opening_date": "2026-10-01", "priority": "Medium"},
	]
	fake.tables["Work Order"] = [
		acme(name="WO-1", docstatus=1, status="In Process", planned_end_date="2026-10-18 17:00:00", production_item="PAINT",
			item_name="Gloss Paint", qty=100, produced_qty=40),
		acme(name="WO-2", docstatus=1, status="Completed", actual_end_date="2026-10-02 10:00:00", production_item="PAINT", item_name="Gloss Paint"),
	]
	fake.tables["Job Card"] = [acme(name="JC-1", docstatus=0, status="Open", operation="Mixing", expected_end_date="2026-10-23")]
	fake.tables["Lead"] = [
		acme(name="L-1", creation="2026-10-05 09:00:00", utm_source="Facebook"),
		acme(name="L-2", creation="2026-10-10 09:00:00", utm_source=None),
		acme(name="L-3", creation="2026-07-01 09:00:00", utm_source="Radio"),
	]
	fake.tables["Opportunity"] = [
		acme(name="OPP-1", status="Open", sales_stage="Prospecting", base_opportunity_amount=5000, expected_closing="2026-10-20", title="Big order"),
		acme(name="OPP-2", status="Quotation", sales_stage="Proposal", base_opportunity_amount=3000, expected_closing="2026-11-05", title="Repaint"),
	]
	fake.tables["Asset"] = [
		acme(name="AST-1", docstatus=1, status="Partially Depreciated", asset_category="Vehicles", value_after_depreciation=20000),
		acme(name="AST-2", docstatus=1, status="Sold", asset_category="Vehicles", value_after_depreciation=999),
	]
	fake.tables["Quality Inspection"] = [
		acme(name="QI-1", docstatus=1, status="Accepted", report_date="2026-10-03"),
		acme(name="QI-2", docstatus=1, status="Rejected", report_date="2026-10-04"),
	]
	fake.tables["Non Conformance"] = [{"name": "NC-1", "status": "Open", "subject": "Mix off", "creation": "2026-10-11 08:00:00"}]
	fake.title_fields = {"Sales Invoice": "title"}
	fake.meta_fields["Sales Invoice"] = {"title"}
	fake.doctypes = set(fake.tables) | {"Stock Entry", "Supplier Quotation"}
	fake.allowed_reports = {"Balance Sheet", "General Ledger", "Sales Analytics", "Stock Balance"}


class Base(unittest.TestCase):
	def setUp(self):
		fake_frappe.reset(frappe)
		seed(frappe)

	def as_(self, roles, readable, creatable=()):
		frappe.roles[USER] = list(roles)
		frappe.readable = set(readable)
		frappe.creatable = set(creatable)

	def tab(self, found, key):
		return next(tab for tab in found["tabs"] if tab["key"] == key)

	def read(self, part):
		"""The figures of one part, as the home asks for them."""
		found = home.figures(part=part)
		return found["tabs"].get(part, {"cards": found["cards"], "panels": []}) if part != "cards" else {"cards": found["cards"]}

	def card(self, read, key):
		return next(card for card in read["cards"] if card["key"] == key)

	def panel(self, read, key):
		return next(panel for panel in read["panels"] if panel["key"] == key)


class Summary(Base):
	def test_a_guest_is_refused(self):
		frappe.session.user = "Guest"
		with self.assertRaises(frappe.PermissionError):
			home.summary()

	def test_the_greeting_and_the_company(self):
		self.as_(["Accounts User"], FINANCE_READS)
		found = home.summary()
		self.assertEqual((found["greeting"], found["first_name"], found["company"], found["currency"]), ("Good afternoon", "Jane", ACME, "UGX"))

	def test_an_accountant_has_the_overview_and_the_accounts_tab(self):
		self.as_(["Accounts User"], FINANCE_READS)
		found = home.summary()
		self.assertEqual([card["key"] for card in found["cards"]], ["sales", "receivable", "payable", "cash"])
		self.assertEqual([tab["key"] for tab in found["tabs"]], ["overview", "accounts"])
		accounts = self.tab(found, "accounts")
		self.assertEqual([panel["key"] for panel in accounts["panels"]],
			["attention", "trend", "profit", "cash", "expenses", "aging", "payables"])
		# only the reports Frappe says the user may open
		self.assertEqual([report["label"] for report in accounts["reports"]], ["Balance Sheet", "General Ledger"])

	def test_a_module_blocked_for_the_user_has_no_tab(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.blocked[USER] = ["Accounts"]
		self.assertEqual([tab["key"] for tab in home.summary()["tabs"]], ["overview"])

	def test_or_blocked_for_everyone(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.blocked["Administrator"] = ["Accounts"]
		self.assertEqual([tab["key"] for tab in home.summary()["tabs"]], ["overview"])

	def test_a_tab_switched_off_in_the_settings(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.doctypes.add(settings.DOCTYPE)
		frappe.singles[settings.DOCTYPE] = {"dash_accounts": "0"}
		self.assertEqual([tab["key"] for tab in home.summary()["tabs"]], ["overview"])

	def test_an_administrator_has_every_tab_their_own_modules_first(self):
		every = {doctype for table in frappe.tables for doctype in [table]} | FINANCE_READS | SALES_READS | STOCK_READS
		self.as_(["Accounts Manager", "Sales Manager", "Stock Manager", "Projects Manager"], every)
		keys = [tab["key"] for tab in home.summary()["tabs"]]
		self.assertEqual(keys[:5], ["overview", "accounts", "selling", "stock", "projects"])
		self.assertEqual(sorted(keys[5:]), sorted(["buying", "manufacturing", "crm", "support", "assets", "quality"]))

	def test_someone_with_no_desk_gets_their_own_work(self):
		self.as_(["Employee"], {"ToDo"})
		frappe.tables["ToDo"] = [
			{"name": "T1", "allocated_to": USER, "status": "Open", "description": "Call the bank", "date": "2026-10-20",
				"reference_type": "", "reference_name": "", "creation": "2026-10-01 10:00:00", "priority": "Medium", "modified": "2026-10-01"},
		]
		found = home.summary()
		self.assertEqual([(card["key"], card["value"]) for card in found["cards"]], [("waiting", 1), ("unread", 0)])
		self.assertEqual([(tab["key"], tab["panels"]) for tab in found["tabs"]], [("overview", [])])

	def test_what_the_user_makes_most_and_it_is_kept_an_hour(self):
		self.as_(["Accounts User"], FINANCE_READS, creatable={"Sales Invoice", "Payment Entry", "Journal Entry"})
		frappe.doctypes |= {"Journal Entry"}
		frappe.tables["Payment Entry"] += [{"name": f"PE-{i}", "owner": USER, "creation": "2026-10-1%d 09:00:00" % i, "docstatus": 1} for i in range(3, 6)]
		frappe.tables["Sales Invoice"][0].update(owner=USER, creation="2026-10-03 09:00:00")
		self.assertEqual(home.summary()["create"], ["Payment Entry", "Sales Invoice", "Journal Entry"])
		self.assertEqual(frappe.cache_seconds[(home.MADE_KEY, USER)], 3600)

	def test_a_document_the_user_may_make_but_not_read_is_offered_never_counted(self):
		self.as_(["Accounts User"], FINANCE_READS, creatable={"Journal Entry"})
		frappe.doctypes.add("Journal Entry")
		self.assertEqual(home.summary()["create"], ["Journal Entry"])
		self.assertFalse([query for query in frappe.queries if query.doctype == "Journal Entry"])

	def test_a_part_that_fails_is_logged_and_the_rest_comes(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.fail_get_all.add("ToDo")
		found = home.summary()
		self.assertEqual(found["waiting"]["tasks"], 0)
		self.assertTrue(any("CyveTech home" in error for error in frappe.errors))


class Accounts(Base):
	def setUp(self):
		super().setUp()
		self.as_(["Accounts User"], FINANCE_READS)
		self.found = self.read("accounts")

	def test_sales_this_month_against_the_same_days_last_month(self):
		sales = self.card(self.read("cards"), "sales")
		self.assertEqual(sales["value"], 1400)  # drafts, cancelled and other companies left out
		self.assertEqual(sales["change"], {"percent": 75, "direction": "up"})
		self.assertEqual(sales["filters"]["posting_date"], ["between", ["2026-10-01", "2026-10-22"]])

	def test_what_customers_owe_in_the_companys_currency(self):
		frappe.cached.clear()
		home._exchange_rate = lambda from_currency, to_currency, day: 3700.0 if from_currency == "USD" else None
		owed = self.card(self.read("accounts"), "receivable")
		self.assertEqual((owed["value"], owed["note"], owed["tone"]), (500 + 300 + 2 * 3700, {"money": 300 + 7400, "words": "overdue"}, "rose"))
		self.assertEqual((owed["route"], owed["options"]), (["query-report", "Accounts Receivable"], {"company": ACME}))

	def test_what_the_company_owes_and_what_falls_due_this_week(self):
		payable = self.card(self.found, "payable")
		self.assertEqual((payable["value"], payable["note"]), (1200, {"money": 900, "words": "due this week"}))

	def test_cash_and_bank_from_the_ledger(self):
		cash = self.card(self.found, "cash")
		self.assertEqual((cash["value"], cash["note"]), (250 + 4000, "In 2 accounts"))
		self.assertEqual([(bar["label"], bar["value"]) for bar in self.panel(self.found, "cash")["rows"]], [("Stanbic", 4000), ("Cash", 250)])

	def test_profit_and_loss_from_the_ledger_the_years_closing_left_out(self):
		profit = self.panel(self.found, "profit")
		self.assertEqual((profit["months"][-1]["values"], profit["months"][-1]["net"]), ([1000, 740], 260))
		self.assertEqual(profit["months"][-2]["values"], [800, 0])
		self.assertEqual(profit["net"], {"label": "Profit", "margin": 26})

	def test_this_months_expenses_by_account(self):
		expenses = self.panel(self.found, "expenses")
		self.assertEqual(expenses["kind"], "donut")
		self.assertEqual([(part["label"], part["value"]) for part in expenses["rows"]], [("Salaries", 400), ("Rent", 300), ("Fuel", 40)])
		self.assertEqual(expenses["rows"][0]["options"]["account"], ["Salaries - AL"])

	def test_six_months_of_billing_and_collecting(self):
		trend = self.panel(self.found, "trend")
		self.assertEqual(([series["key"] for series in trend["series"]], trend["months"][-1]["values"]), (["billed", "collected"], [1400, 600]))

	def test_the_aging_both_ways(self):
		frappe.cached.clear()
		home._exchange_rate = lambda *args: 3700.0
		found = self.read("accounts")
		buckets = {bucket["key"]: bucket["value"] for bucket in self.panel(found, "aging")["buckets"]}
		self.assertEqual(buckets, {"current": 500, "d30": 300, "d60": 0, "d90": 0, "older": 7400})
		payables = self.panel(found, "payables")
		self.assertEqual({bucket["key"]: bucket["value"] for bucket in payables["buckets"]}["d30"], 200)
		self.assertEqual([(row["title"], row["doctype"]) for row in payables["rows"]], [("Paint Co", "Supplier")])

	def test_what_needs_attention_on_the_tab(self):
		attention = self.panel(self.found, "attention")
		self.assertEqual([(row["key"], row["value"]) for row in attention["rows"]], [("invoices_overdue", 2), ("bills_due", 2)])

	def test_the_overview_says_how_much_needs_attention_on_each_tab(self):
		overview = self.read("overview")
		self.assertEqual(overview["badges"], {"accounts": {"value": 4, "band": "overdue"}})
		self.assertEqual([(row["doctype"], row["docname"]) for row in self.panel(overview, "drafts")["rows"]], [("Sales Invoice", "SI-7")])

	def test_every_query_was_one_the_user_may_make(self):
		for query in frappe.queries:
			if query.checked:
				self.assertIn(query.doctype, FINANCE_READS)

	def test_totals_go_as_frappe_v16_wants_them(self):
		fields = [field for query in frappe.queries for field in (query.fields or [])]
		self.assertIn({"SUM": "base_net_total", "as": "total"}, fields)
		self.assertFalse([field for field in fields if isinstance(field, str) and "(" in field])

	def test_each_part_is_kept_five_minutes_and_read_afresh_on_request(self):
		self.assertEqual(frappe.cache_seconds[(home.FIGURES_KEY + ":accounts", USER)], 300)
		frappe.tables["Purchase Invoice"][0]["outstanding_amount"] = 5000
		self.assertEqual(self.card(self.read("accounts"), "payable")["value"], 1200)
		found = home.figures(part="accounts", fresh=1)
		self.assertEqual(self.card(found["tabs"]["accounts"], "payable")["value"], 5500)

	def test_a_tab_the_user_does_not_have_is_never_read(self):
		found = home.figures(part="selling")
		self.assertEqual((found["cards"], found["tabs"]), ([], {}))


class OtherModules(Base):
	def test_a_sales_clerk_sees_orders_never_invoices(self):
		self.as_(["Sales User"], SALES_READS)
		found = self.read("selling")
		self.assertEqual([card["key"] for card in found["cards"]], ["orders", "to_deliver", "quotations"])
		self.assertEqual((self.card(found, "orders")["value"], self.card(found, "to_deliver")["note"]), (3000, "1 late"))
		trend = self.panel(found, "sales_trend")
		self.assertEqual(([series["key"] for series in trend["series"]], trend["months"][-1]["values"]), (["ordered"], [3000]))
		self.assertEqual([(bar["label"], bar["value"]) for bar in self.panel(found, "items")["rows"]], [("Gloss Paint", 2000), ("Brush", 1000)])
		self.assertEqual([(part["label"], part["value"]) for part in self.panel(found, "territories")["rows"]], [("Kampala", 2000), ("Mbarara", 1000)])
		self.assertFalse([query for query in frappe.queries if query.doctype in ("Sales Invoice", "Purchase Invoice")])

	def test_an_accountant_sees_the_items_and_territories_billed(self):
		self.as_(["Accounts User", "Sales User"], FINANCE_READS | SALES_READS)
		found = self.read("selling")
		self.assertEqual([(bar["label"], bar["value"]) for bar in self.panel(found, "items")["rows"]], [("Gloss Paint", 1200), ("Brush", 300)])
		self.assertEqual([(part["label"], part["value"]) for part in self.panel(found, "territories")["rows"]], [("Kampala", 900), ("Jinja", 500)])
		self.assertEqual(self.panel(found, "territories")["rows"][0]["filters"]["territory"], "Kampala")

	def test_quotations_by_stage_over_90_days(self):
		self.as_(["Sales User"], SALES_READS)
		quotes = self.panel(self.read("selling"), "quotations")
		self.assertEqual([(stage["key"], stage["value"]) for stage in quotes["stages"]], [("open", 1), ("won", 1), ("lost", 1), ("expired", 0)])
		self.assertEqual(quotes["won"], 50)

	def test_a_storekeeper_gets_the_stock(self):
		self.as_(["Stock User"], STOCK_READS | {"Sales Order", "Purchase Order"})
		summary = home.summary()
		self.assertEqual([tab["key"] for tab in summary["tabs"]], ["overview", "stock", "selling", "buying"])
		found = self.read("stock")
		self.assertEqual((self.card(found, "stock_value")["value"], self.card(found, "negative")["value"]), (1500, 1))
		self.assertEqual(self.panel(found, "stock_moves")["months"][-1]["values"], [1000, 400])
		self.assertEqual([(part["label"], part["value"]) for part in self.panel(found, "warehouses")["rows"]], [("Stores", 1500)])

	def test_projects_their_progress_and_hours(self):
		self.as_(["Projects User"], {"Project", "Task", "Timesheet"})
		found = self.read("projects")
		projects_open = self.card(found, "projects_open")
		self.assertEqual((projects_open["value"], projects_open["note"], projects_open["tone"]), (2, "1 past their end date", "rose"))
		self.assertEqual(self.card(found, "hours")["value"], 12.5)
		self.assertEqual([(row["docname"], row["progress"]) for row in self.panel(found, "projects")["rows"]], [("PRJ-1", 40), ("PRJ-2", 80)])
		self.assertEqual([(bar["label"], bar["value"]) for bar in self.panel(found, "hours_by_project")["rows"]], [("PRJ-1", 8), ("No project", 4.5)])

	def test_support_issues_by_status_and_priority(self):
		self.as_(["Support Team"], {"Issue"})
		found = self.read("support")
		self.assertEqual([(card["key"], card["value"]) for card in found["cards"]], [("issues", 2), ("issues_replied", 1), ("issues_on_hold", 1)])
		self.assertEqual([(part["label"], part["value"]) for part in self.panel(found, "issue_priorities")["rows"]], [("High", 2), ("Low", 1)])
		self.assertEqual([row["docname"] for row in self.panel(found, "issues")["rows"]], ["ISS-1", "ISS-2"])

	def test_purchasing_what_is_requested(self):
		self.as_(["Purchase User"], {"Purchase Order", "Material Request", "Purchase Invoice", "Supplier"})
		found = self.read("buying")
		requests = self.card(found, "requests")
		self.assertEqual((requests["value"], requests["note"]), (2, "1 past their date"))
		self.assertEqual([row["docname"] for row in self.panel(found, "requests_list")["rows"]], ["MR-1", "MR-2"])
		self.assertEqual([(bar["label"], bar["value"]) for bar in self.panel(found, "suppliers")["rows"]], [("Paint Co", 700), ("Tins Ltd", 300)])

	def test_crm_assets_quality_and_manufacturing(self):
		self.as_(["System Manager"], {"Lead", "Opportunity", "Asset", "Quality Inspection", "Non Conformance", "Work Order", "Job Card"})
		crm = self.read("crm")
		self.assertEqual((self.card(crm, "leads")["value"], self.card(crm, "pipeline")["value"]), (2, 8000))
		self.assertEqual([(part["label"], part["value"]) for part in self.panel(crm, "lead_sources")["rows"]], [("Facebook", 1), ("No source given", 1)])
		assets = self.read("assets")
		self.assertEqual((self.card(assets, "asset_value")["value"], self.card(assets, "assets")["value"]), (20000, 1))
		quality = self.read("quality")
		self.assertEqual([(card["key"], card["value"]) for card in quality["cards"]], [("inspections", 2), ("rejected", 1), ("non_conformances", 1)])
		making = self.read("manufacturing")
		self.assertEqual((self.card(making, "completed")["value"], self.card(making, "job_cards")["value"]), (1, 1))
		self.assertEqual(self.panel(making, "production_trend")["months"][-1]["values"], [1])

	def test_the_rest_of_a_ring_opens_the_whole_list_it_is_of(self):
		sources = ["Radio", "TV", "Email", "Walk-in", "Referral", "Billboard"]
		frappe.tables["Lead"] += [
			{"name": "L-%d" % day, "company": "Acme Ltd", "creation": "2026-10-%02d 09:00:00" % day, "utm_source": source}
			for day, source in enumerate(sources, start=11)
		]
		self.as_(["Sales Manager"], {"Lead", "Opportunity"})
		ring = self.panel(self.read("crm"), "lead_sources")
		self.assertEqual(len(ring["rows"]), 6)
		rest = ring["rows"][-1]
		self.assertEqual((rest["label"], rest["value"], rest["key"]), ("Everything else", 3, None))
		facebook = next(part for part in ring["rows"] if part["label"] == "Facebook")
		self.assertEqual(facebook["filters"]["utm_source"], "Facebook")
		self.assertEqual(rest["filters"], {key: value for key, value in facebook["filters"].items() if key != "utm_source"})
		unsourced = next(part for part in ring["rows"] if part["label"] == "No source given")
		self.assertEqual((unsourced["key"], unsourced["filters"]["utm_source"]), ("No source given", ["is", "not set"]))

	def test_figures_on_frappe_v15_go_as_sql_it_takes(self):
		frappe.__version__ = "15.40.0"
		self.as_(["Accounts User"], FINANCE_READS)
		self.assertEqual(self.card(self.read("cards"), "sales")["value"], 1400)
		fields = [field for query in frappe.queries for field in (query.fields or [])]
		self.assertIn("sum(`base_net_total`) as total", fields)
		self.assertFalse([field for field in fields if isinstance(field, dict)])

	def test_a_figure_that_fails_is_left_out_and_the_rest_come(self):
		self.as_(["Accounts User"], FINANCE_READS)
		frappe.fail_get_all.add("GL Entry")
		found = self.read("accounts")
		self.assertNotIn("cash", [card["key"] for card in found["cards"]])
		self.assertIn("receivable", [card["key"] for card in found["cards"]])
		self.assertIn("CyveTech home: figure: cash", frappe.errors)


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

	def test_what_waits_needs_attention_and_the_dashboard_of_the_module(self):
		self.as_(["Sales User"], SALES_READS, creatable={"Sales Order", "Quotation"})
		found = module_pages.summary("Selling")
		self.assertEqual((found["waiting"]["tasks"], found["waiting"]["items"][0]["docname"], found["doctypes"]), (1, "SO-1", ["Sales Order"]))
		self.assertEqual([(row["key"], row["value"]) for row in found["attention"]],
			[("orders_late", 1), ("orders_to_bill", 1), ("quotations_expiring", 1)])
		self.assertEqual((found["action"], found["dashboard"]), ("Sales Order", "selling"))

	def test_no_dashboard_where_the_module_is_not_the_users(self):
		self.as_(["Sales User"], SALES_READS)
		frappe.blocked[USER] = ["Selling"]
		self.assertIsNone(module_pages.summary("Selling")["dashboard"])

	def test_only_the_modules_documents_are_asked_for(self):
		self.as_(["Sales User"], SALES_READS)
		module_pages.summary("Selling")
		todo = next(query for query in frappe.queries if query.doctype == "ToDo")
		self.assertEqual(todo.filters["reference_type"], ["in", ["Quotation", "Sales Order", "Customer"]])

	def test_a_workspace_with_no_menu_still_answers(self):
		self.as_(["Sales User"], SALES_READS)
		found = module_pages.summary("Nowhere")
		self.assertEqual((found["waiting"]["tasks"], found["attention"], found["action"], found["dashboard"]), (0, [], None, None))


class SettingsAndBoot(Base):
	def test_an_update_writes_the_defaults_of_settings_never_saved(self):
		frappe.doctypes.add(settings.DOCTYPE)
		frappe.singles[settings.DOCTYPE] = {"sidebar_color": "#222222", "dash_crm": "0"}
		written = settings.ensure_defaults()
		self.assertIn("dash_accounts", written)
		self.assertEqual((frappe.singles[settings.DOCTYPE]["dash_accounts"], frappe.singles[settings.DOCTYPE]["accent_color"]), (1, "#2F64B0"))
		# what someone saved is left alone
		self.assertEqual((frappe.singles[settings.DOCTYPE]["sidebar_color"], frappe.singles[settings.DOCTYPE]["dash_crm"]), ("#222222", "0"))
		self.assertEqual(settings.ensure_defaults(), [])

	def test_a_site_that_never_saved_them_is_left_to_frappes_defaults(self):
		frappe.doctypes.add(settings.DOCTYPE)
		self.assertEqual(settings.ensure_defaults(), [])

	def test_the_boot_carries_the_home_and_the_module_pages(self):
		payload = boot.payload(settings.merge({}), [])
		self.assertEqual((payload["home"]["enabled"], payload["home"]["modules"][:3]), (1, ["CRM", "Selling", "Buying"]))
		self.assertEqual(payload["module_pages"]["actions"]["Selling"], "Sales Order")
		self.assertEqual(payload["theme"]["vars"]["--cvt-band-good"], "#1e7a46")

	def test_a_header_too_light_for_white_text_is_saved_with_a_warning(self):
		doc = settings_controller.CyveTechUISettings({"header_color": "#fde68a", "danger_color": "#c53030"})
		doc.validate()
		self.assertEqual(doc.header_color, "#FDE68A")
		self.assertEqual(len(frappe.messages), 1)

	def test_the_shipped_colors_raise_no_warning(self):
		settings_controller.CyveTechUISettings(dict(settings.DEFAULTS)).validate()
		self.assertEqual(frappe.messages, [])


if __name__ == "__main__":
	unittest.main()
