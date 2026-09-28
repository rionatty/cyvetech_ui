"""The server side against the stand-in Frappe in fake_frappe.py: branding,
desk modules, My Alerts, alert permissions, alert delivery, the boot payload
and the settings form's checks."""

import unittest

import fake_frappe

frappe = fake_frappe.install()
branding = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.branding")
desk_modules = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.desk_modules")
alerts = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.alerts")
permissions = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.permissions")
boot = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.boot")
settings = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.settings")
user_alert = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.doctype.cyvetech_user_alert.cyvetech_user_alert")
settings_controller = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.doctype.cyvetech_ui_settings.cyvetech_ui_settings")

WS, NAV = "Website Settings", "Navbar Settings"


class Base(unittest.TestCase):
	def setUp(self):
		fake_frappe.reset(frappe)


class Branding(Base):
	def setUp(self):
		super().setUp()
		frappe.doctypes = {WS, NAV}

	def test_the_logo_goes_everywhere_frappe_reads_it(self):
		changed = branding.apply({"brand_logo": "/files/brand.png", "favicon": "/files/fav.png", "product_name": "Luuka ERP"})
		self.assertEqual(
			frappe.singles[WS],
			{"app_logo": "/files/brand.png", "splash_image": "/files/brand.png", "favicon": "/files/fav.png", "app_name": "Luuka ERP"},
		)
		self.assertEqual(frappe.singles[NAV], {"app_logo": "/files/brand.png"})
		self.assertEqual(
			sorted(changed),
			[
				"Navbar Settings.app_logo",
				"Website Settings.app_logo",
				"Website Settings.app_name",
				"Website Settings.favicon",
				"Website Settings.splash_image",  # the loading screen, in place of ERPNext's "E"
			],
		)

	def test_a_repeat_writes_nothing(self):
		branding.apply({"brand_logo": "/files/brand.png"})
		frappe.writes.clear()
		self.assertEqual(branding.apply({"brand_logo": "/files/brand.png"}), [])
		self.assertEqual(frappe.writes, [])

	def test_clearing_the_field_takes_back_only_what_this_app_put_there(self):
		branding.apply({"brand_logo": "/files/brand.png"})
		frappe.singles[NAV]["app_logo"] = "/files/set-by-hand.png"  # someone changed it since
		changed = branding.apply({"brand_logo": ""})
		self.assertIsNone(frappe.singles[WS]["app_logo"])
		self.assertIsNone(frappe.singles[WS]["splash_image"])
		self.assertEqual(frappe.singles[NAV]["app_logo"], "/files/set-by-hand.png")
		self.assertEqual(changed, ["Website Settings.app_logo", "Website Settings.splash_image"])

	def test_a_logo_never_set_here_is_never_cleared(self):
		frappe.singles[WS] = {"app_logo": "/files/theirs.png"}
		self.assertEqual(branding.apply({"brand_logo": ""}), [])
		self.assertEqual(frappe.singles[WS]["app_logo"], "/files/theirs.png")

	def test_once_taken_back_it_is_forgotten(self):
		branding.apply({"favicon": "/files/fav.png"})
		branding.apply({"favicon": ""})
		frappe.singles[WS]["favicon"] = "/files/fav.png"  # the same file, now set by hand
		self.assertEqual(branding.apply({"favicon": ""}), [])

	def test_a_settings_doctype_missing_on_this_site_is_skipped(self):
		frappe.doctypes = {WS}
		branding.apply({"brand_logo": "/files/brand.png"})
		self.assertNotIn(NAV, frappe.singles)

	def test_the_desk_caches_are_cleared_for_what_changed(self):
		branding.apply({"favicon": "/files/fav.png"})
		self.assertIn("doc:Website Settings", frappe.cleared)
		self.assertNotIn("doc:Navbar Settings", frappe.cleared)


class RebrandAppData(Base):
	APPS = [
		{"app_name": "frappe", "app_title": "Framework", "app_logo_url": "/f.svg"},
		{"app_name": "erpnext", "app_title": "ERPNext", "app_logo_url": "/e.svg"},
		{"app_name": "hrms", "app_title": "Frappe HR", "app_logo_url": "/hr.svg"},
		"not a dict",
	]

	def apps(self):
		return [dict(app) if isinstance(app, dict) else app for app in self.APPS]

	def test_the_platform_logos_and_name_change_and_other_apps_keep_theirs(self):
		apps = branding.rebrand_app_data(self.apps(), {"brand_logo": "/files/b.png", "product_name": "Luuka ERP"})
		self.assertEqual([a["app_logo_url"] for a in apps[:3]], ["/files/b.png", "/files/b.png", "/hr.svg"])
		self.assertEqual([a["app_title"] for a in apps[:3]], ["Luuka ERP", "Luuka ERP", "Frappe HR"])

	def test_every_app_on_request(self):
		apps = branding.rebrand_app_data(self.apps(), {"brand_logo": "/files/b.png", "replace_all_app_logos": 1})
		self.assertEqual(apps[2]["app_logo_url"], "/files/b.png")
		self.assertEqual(apps[2]["app_title"], "Frappe HR")

	def test_nothing_set_nothing_changed(self):
		self.assertEqual(branding.rebrand_app_data(self.apps(), {}), self.apps())
		self.assertIsNone(branding.rebrand_app_data(None, {"brand_logo": "/x"}))


class DeskModules(Base):
	def setUp(self):
		super().setUp()
		frappe.doctypes = {"Desktop Icon"}
		frappe.tables["Desktop Icon"] = [
			{"name": "Selling", "label": "Selling", "app": "erpnext", "icon_type": "App", "hidden": 0, "standard": 1, "owner": "Administrator"},
			{"name": "Quality", "label": "Quality", "app": "erpnext", "icon_type": "App", "hidden": 0, "standard": 1, "owner": "Administrator"},
			{"name": "Leaves", "label": "Leaves", "app": "hrms", "icon_type": "Link", "hidden": 0, "standard": 1, "parent_icon": "Frappe HR", "owner": "Administrator"},
			{"name": "My Shortcut", "label": "My Shortcut", "app": "", "icon_type": "Link", "hidden": 0, "standard": 0, "owner": "jane@example.com"},
		]

	def rows(self, *pairs):
		frappe.tables["CyveTech Desk Module"] = [
			{"module": module, "show_on_desk": show, "parenttype": "CyveTech UI Settings", "parent": "CyveTech UI Settings"}
			for module, show in pairs
		]

	def test_the_table_lists_every_shared_tile_each_under_its_group(self):
		frappe.tables["Desktop Icon"].append(
			{"name": "Frappe HR", "label": "Frappe HR", "app": "hrms", "icon_type": "App", "hidden": 0, "standard": 1, "owner": "Administrator"}
		)
		doc = settings_controller.CyveTechUISettings({"desk_modules": []})
		desk_modules.refresh_rows(doc)
		rows = [(row["module"], row["group"]) for row in doc.get("desk_modules")]
		# a user's own shortcut is theirs, not the desk's
		self.assertEqual(rows, [("Selling", ""), ("Quality", ""), ("Frappe HR", ""), ("Leaves", "Frappe HR")])

	def test_a_module_inside_a_group_can_be_hidden(self):
		self.rows(("Selling", 1), ("Quality", 1), ("Leaves", 0))
		self.assertTrue(desk_modules.apply())
		self.assertEqual(frappe.writes, [("value", "Desktop Icon", "Leaves", "hidden", 1)])

	def test_unticking_hides_the_tile(self):
		self.rows(("Selling", 1), ("Quality", 0))
		self.assertTrue(desk_modules.apply())
		self.assertEqual(frappe.writes, [("value", "Desktop Icon", "Quality", "hidden", 1)])
		self.assertIn("desktop_icons", frappe.cleared)
		self.assertIn("bootinfo", frappe.cleared)

	def test_nothing_changes_when_the_flags_already_match(self):
		self.rows(("Selling", 1), ("Quality", 1))
		self.assertFalse(desk_modules.apply())
		self.assertEqual(frappe.writes, [])
		self.assertEqual(frappe.cleared, [])

	def test_a_table_never_filled_in_leaves_the_desk_alone(self):
		self.assertFalse(desk_modules.apply())
		self.assertEqual(frappe.writes, [])

	def test_on_frappe_v15_there_is_nothing_to_do(self):
		frappe.doctypes = set()
		self.assertFalse(desk_modules.apply())
		self.assertEqual(desk_modules.hidden_labels(), [])

	def test_the_boot_gets_the_hidden_labels_and_never_an_error(self):
		self.rows(("Selling", 1), ("Quality", 0))
		self.assertEqual(desk_modules.hidden_labels(), ["Quality"])
		frappe.fail_get_all = {"CyveTech Desk Module"}
		self.assertEqual(desk_modules.hidden_labels(), [])


class MyAlerts(Base):
	def setUp(self):
		super().setUp()
		frappe.tables["ToDo"] = [
			{"name": "TODO-1", "allocated_to": "jane@example.com", "status": "Open", "reference_type": "Interview Shortlist",
			 "reference_name": "HR-SHL-2026-0001", "description": "<p>Interview shortlist: <b>pending HOD screening</b></p>",
			 "date": "2026-09-20", "priority": "Medium", "creation": "2026-09-01 10:00:00"},
			{"name": "TODO-2", "allocated_to": "jane@example.com", "status": "Open", "reference_type": None,
			 "reference_name": None, "description": "Call the bank", "date": None, "priority": "High", "creation": "2026-09-02"},
			{"name": "TODO-3", "allocated_to": "someone@example.com", "status": "Open", "reference_type": "Task",
			 "reference_name": "T-9", "description": "Not Jane's", "date": "2026-09-01", "priority": "Medium", "creation": "2026-09-01"},
			{"name": "TODO-4", "allocated_to": "jane@example.com", "status": "Closed", "reference_type": "Task",
			 "reference_name": "T-8", "description": "Done", "date": "2026-09-01", "priority": "Medium", "creation": "2026-09-01"},
		]
		frappe.tables["Notification Log"] = [
			{"name": "NL-1", "for_user": "jane@example.com", "subject": "You were assigned HR-SHL-2026-0001", "type": "Assignment",
			 "document_type": "Interview Shortlist", "document_name": "HR-SHL-2026-0001", "from_user": "hr@example.com", "creation": "2026-09-27", "read": 0},
			{"name": "NL-2", "for_user": "jane@example.com", "subject": "<b>Mentioned</b> you", "type": "Mention",
			 "document_type": "Task", "document_name": "T-1", "from_user": "bob@example.com", "creation": "2026-09-26", "read": 1},
			{"name": "NL-3", "for_user": "jane@example.com", "subject": "Server maintenance", "type": "Alert",
			 "document_type": "CyveTech User Alert", "document_name": "ALERT-1", "from_user": "admin@example.com", "creation": "2026-09-28", "read": 0},
			{"name": "NL-4", "for_user": "someone@example.com", "subject": "Not Jane's", "type": "Alert",
			 "document_type": "Task", "document_name": "T-2", "from_user": "x", "creation": "2026-09-28", "read": 0},
			# from one of ERPNext's own Notification rules (Channel: System Notification)
			{"name": "NL-5", "for_user": "jane@example.com", "subject": "Cement is below its reorder level", "type": "Alert",
			 "document_type": "Item", "document_name": "CEMENT-50KG", "from_user": "Administrator", "creation": "2026-09-28", "read": 0,
			 "description": "<p>Only <b>12 bags</b> left in Stores - MI.</p>", "email_content": "Add your message here"},
		]
		frappe.tables["CyveTech User Alert"] = [
			{"name": "ALERT-1", "priority": "Urgent", "message": "<p>Save your work.</p>", "reference_doctype": "Sales Order", "reference_name": "SO-1"},
		]

	def test_a_guest_gets_nothing(self):
		frappe.session.user = "Guest"
		with self.assertRaises(fake_frappe.PermissionError):
			alerts.my_alerts()

	def test_every_query_is_for_the_session_user_only(self):
		result = alerts.my_alerts()
		todo_query = next(q for q in frappe.queries if q.doctype == "ToDo")
		log_query = next(q for q in frappe.queries if q.doctype == "Notification Log")
		self.assertEqual(todo_query.filters, {"allocated_to": "jane@example.com", "status": "Open"})
		self.assertEqual(log_query.filters, {"for_user": "jane@example.com"})
		keys = {a["key"] for a in result["alerts"]}
		self.assertNotIn("TODO-3", keys)
		self.assertNotIn("NL-4", keys)
		self.assertNotIn("TODO-4", keys)

	def test_an_assignment_reads_like_the_screenshot(self):
		row = next(a for a in alerts.my_alerts()["alerts"] if a["key"] == "TODO-1")
		self.assertEqual(row["title"], "Interview shortlist: pending HOD screening")
		self.assertEqual((row["doctype"], row["docname"]), ("Interview Shortlist", "HR-SHL-2026-0001"))
		self.assertEqual(row["when"], "overdue by 8 days")
		self.assertEqual(row["urgency"], "overdue")

	def test_a_personal_todo_opens_the_todo_itself(self):
		row = next(a for a in alerts.my_alerts()["alerts"] if a["key"] == "TODO-2")
		self.assertEqual((row["doctype"], row["docname"]), ("ToDo", "TODO-2"))
		self.assertEqual(row["urgency"], "today")  # High priority, no due date

	def test_the_assignment_is_not_listed_twice(self):
		keys = [a["key"] for a in alerts.my_alerts()["alerts"]]
		self.assertNotIn("NL-1", keys)

	def test_a_standard_erpnext_alert_carries_its_message(self):
		row = next(a for a in alerts.my_alerts()["alerts"] if a["key"] == "NL-5")
		self.assertEqual((row["type"], row["unread"], row["alert"]), ("Alert", 1, None))
		self.assertEqual(row["message"], "Only 12 bags left in Stores - MI.")
		self.assertEqual((row["doctype"], row["docname"]), ("Item", "CEMENT-50KG"))

	def test_on_frappe_v15_the_message_comes_from_email_content(self):
		frappe.meta_fields = {"Notification Log": {"subject", "email_content"}}
		row = next(a for a in alerts.my_alerts()["alerts"] if a["key"] == "NL-5")
		self.assertEqual(row["message"], "Add your message here")
		log_query = next(q for q in frappe.queries if q.doctype == "Notification Log")
		self.assertNotIn("description", log_query.fields)  # v15 has no such column

	def test_a_sent_alert_carries_its_priority_and_opens_its_document(self):
		row = next(a for a in alerts.my_alerts()["alerts"] if a["key"] == "NL-3")
		self.assertEqual(row["urgency"], "overdue")  # Urgent
		self.assertEqual((row["doctype"], row["docname"]), ("Sales Order", "SO-1"))
		self.assertEqual(row["alert"], {"name": "ALERT-1", "priority": "Urgent", "message": "<p>Save your work.</p>"})
		self.assertEqual(row["unread"], 1)

	def test_markup_is_taken_out_of_titles(self):
		row = next(a for a in alerts.my_alerts()["alerts"] if a["key"] == "NL-2")
		self.assertEqual(row["title"], "Mentioned you")
		self.assertIsNone(row["alert"])

	def test_the_count_is_what_is_outstanding_and_the_most_urgent_first(self):
		result = alerts.my_alerts()
		self.assertEqual(result["total"], 4)  # two open to-dos and the two unread alerts; the read mention is not counted
		self.assertEqual(result["band"], "overdue")
		self.assertEqual(result["alerts"][0]["urgency"], "overdue")

	def test_the_limit_is_clamped(self):
		self.assertEqual(len(alerts.my_alerts(limit=1)["alerts"]), 1)
		self.assertEqual(len(alerts.my_alerts(limit=0)["alerts"]), 5)
		self.assertEqual(len(alerts.my_alerts(limit="lots")["alerts"]), 5)


class AlertPermissions(Base):
	def setUp(self):
		super().setUp()
		frappe.roles = {"boss@example.com": ["System Manager"], "jane@example.com": ["Sales User"]}

	def alert(self, docstatus=1, users=("jane@example.com",)):
		return fake_frappe.Row(docstatus=docstatus, recipients=[fake_frappe.Row(user=u) for u in users])

	def test_managers_see_every_alert(self):
		self.assertEqual(permissions.alert_query("boss@example.com"), "")
		self.assertEqual(permissions.alert_query("Administrator"), "")
		self.assertTrue(permissions.alert_has_permission(self.alert(users=()), "write", "boss@example.com"))

	def test_everyone_else_sees_only_submitted_alerts_sent_to_them(self):
		condition = permissions.alert_query("jane@example.com")
		self.assertIn("docstatus = 1", condition)
		self.assertIn("user = 'jane@example.com'", condition)
		self.assertIn("parenttype = 'CyveTech User Alert'", condition)

	def test_the_user_is_escaped_in_the_condition(self):
		condition = permissions.alert_query("x' or '1'='1")
		self.assertIn("user = 'x\\' or \\'1\\'=\\'1'", condition)

	def test_a_recipient_may_read_and_print_but_nothing_more(self):
		self.assertTrue(permissions.alert_has_permission(self.alert(), "read", "jane@example.com"))
		self.assertTrue(permissions.alert_has_permission(self.alert(), "print", "jane@example.com"))
		self.assertFalse(permissions.alert_has_permission(self.alert(), "write", "jane@example.com"))

	def test_not_a_recipient_or_not_yet_sent_means_no(self):
		self.assertFalse(permissions.alert_has_permission(self.alert(users=("bob@example.com",)), "read", "jane@example.com"))
		self.assertFalse(permissions.alert_has_permission(self.alert(docstatus=0), "read", "jane@example.com"))


class SendingAnAlert(Base):
	def setUp(self):
		super().setUp()
		user_alert.CyveTechUserAlert._tables = ("recipients", "roles")
		frappe.tables["User"] = [
			{"name": "jane@example.com", "enabled": 1},
			{"name": "bob@example.com", "enabled": 1},
			{"name": "old@example.com", "enabled": 0},
			{"name": "Guest", "enabled": 1},
		]
		frappe.tables["Has Role"] = [
			{"parenttype": "User", "parent": "bob@example.com", "role": "Stock User"},
			{"parenttype": "User", "parent": "old@example.com", "role": "Stock User"},
			{"parenttype": "User", "parent": "Guest", "role": "Stock User"},
			{"parenttype": "DocType", "parent": "Item", "role": "Stock User"},
		]

	def alert(self, **data):
		base = {"doctype": "CyveTech User Alert", "name": "ALERT-1", "subject": "Count stock", "priority": "Normal",
				"message": "<p>Before noon</p>", "recipients": [], "roles": [], "modified_by": "admin@example.com"}
		base.update(data)
		return user_alert.CyveTechUserAlert(base)

	def test_it_needs_someone_to_send_to(self):
		with self.assertRaises(fake_frappe.ValidationError):
			self.alert().validate()

	def test_a_document_link_needs_both_halves(self):
		with self.assertRaises(fake_frappe.ValidationError):
			self.alert(recipients=[{"user": "jane@example.com"}], reference_doctype="Sales Order").validate()

	def test_a_user_named_twice_is_kept_once(self):
		doc = self.alert(recipients=[{"user": "jane@example.com"}, {"user": "jane@example.com"}])
		doc.validate()
		self.assertEqual([r.user for r in doc.recipients], ["jane@example.com"])

	def test_roles_become_their_enabled_users_on_submit(self):
		doc = self.alert(recipients=[{"user": "jane@example.com"}], roles=[{"role": "Stock User"}])
		doc.before_submit()
		self.assertEqual([r.user for r in doc.recipients], ["jane@example.com", "bob@example.com"])
		self.assertEqual(doc.delivered_to, 2)
		self.assertIsNotNone(doc.sent_on)

	def test_nobody_enabled_to_send_to_stops_the_submit(self):
		frappe.tables["User"][0]["enabled"] = 0
		with self.assertRaises(fake_frappe.ValidationError):
			self.alert(recipients=[{"user": "jane@example.com"}]).before_submit()

	def test_submitting_delivers_a_notification_to_each_recipient(self):
		doc = self.alert(recipients=[{"user": "jane@example.com"}, {"user": "bob@example.com"}])
		frappe.docs[("CyveTech User Alert", "ALERT-1")] = doc
		doc.on_submit()
		logs = [row for row in frappe.inserted if row["doctype"] == "Notification Log"]
		self.assertEqual([log["for_user"] for log in logs], ["jane@example.com", "bob@example.com"])
		for log in logs:
			self.assertEqual(log["type"], "Alert")
			self.assertEqual((log["document_type"], log["document_name"]), ("CyveTech User Alert", "ALERT-1"))
			self.assertEqual(log["subject"], "Count stock")
			self.assertEqual(log["from_user"], "admin@example.com")

	def test_a_large_audience_is_delivered_in_the_background(self):
		doc = self.alert(recipients=[{"user": f"u{i}@example.com"} for i in range(user_alert.BACKGROUND_FROM)])
		doc.on_submit()
		self.assertEqual(frappe.inserted, [])
		self.assertEqual(frappe.enqueued[0][1]["alert"], "ALERT-1")
		self.assertTrue(frappe.enqueued[0][1]["enqueue_after_commit"])

	def test_cancelling_withdraws_it_from_whoever_has_not_read_it(self):
		frappe.tables["Notification Log"] = [
			{"name": "a", "document_type": "CyveTech User Alert", "document_name": "ALERT-1", "read": 0},
			{"name": "b", "document_type": "CyveTech User Alert", "document_name": "ALERT-1", "read": 1},
			{"name": "c", "document_type": "CyveTech User Alert", "document_name": "ALERT-2", "read": 0},
		]
		self.alert().on_cancel()
		self.assertEqual([row["name"] for row in frappe.tables["Notification Log"]], ["b", "c"])

	def test_only_a_system_manager_can_send_a_test_alert(self):
		with self.assertRaises(fake_frappe.PermissionError):
			user_alert.send_test_alert()


class Boot(Base):
	def setUp(self):
		super().setUp()
		frappe.doctypes = {"CyveTech UI Settings"}

	def boot(self):
		info = frappe._dict(app_data=[{"app_name": "erpnext", "app_title": "ERPNext", "app_logo_url": "/e.svg"}])
		boot.boot_session(bootinfo=info)
		return info

	def test_a_fresh_site_boots_with_the_defaults(self):
		payload = self.boot().cyvetech_ui
		self.assertEqual(payload["theme"]["enabled"], 1)
		self.assertEqual(payload["theme"]["vars"]["--cvt-sidebar-bg"], "#16335e")
		self.assertEqual(payload["charts"]["palette"], [c.lower() for c in settings.CHART_PALETTE])
		self.assertEqual(payload["charts"]["dark_palette"], settings.CHART_PALETTE_DARK)
		self.assertEqual(payload["alerts"], {"panel": 1, "popup": 1, "seconds": 8, "sound": 1})
		self.assertEqual(payload["branding"]["sidebar_logo"], 1)  # the logo in the navigation pane, on out of the box
		self.assertEqual(payload["hidden_modules"], [])

	def test_a_custom_palette_is_used_in_both_modes(self):
		frappe.singles["CyveTech UI Settings"] = {"chart_color_1": "#000000"}
		charts = self.boot().cyvetech_ui["charts"]
		self.assertEqual(charts["palette"][0], "#000000")
		self.assertEqual(charts["dark_palette"], charts["palette"])

	def test_the_logo_reaches_the_app_data(self):
		frappe.singles["CyveTech UI Settings"] = {"brand_logo": "/files/b.png"}
		info = self.boot()
		self.assertEqual(info.app_data[0]["app_logo_url"], "/files/b.png")
		self.assertEqual(info.app_logo_url, "/files/b.png")

	def test_a_failure_never_stops_the_desk(self):
		frappe.fail_singles = True
		frappe.doctypes = {"CyveTech UI Settings"}
		payload = self.boot().cyvetech_ui
		self.assertIn("theme", payload)  # get_settings fell back to the defaults
		original, original_logger = boot.payload, frappe.logger
		boot.payload = lambda *a, **k: 1 / 0
		try:
			self.assertEqual(set(self.boot().cyvetech_ui), {"version"})
			self.assertEqual([module for module, _ in frappe.logged], ["cyvetech_ui"])  # and says why, in its log
			frappe.logger = lambda *a, **k: 1 / 0
			self.assertEqual(set(self.boot().cyvetech_ui), {"version"})  # even when the log cannot be written
		finally:
			boot.payload, frappe.logger = original, original_logger


class SettingsForm(Base):
	def doc(self, **data):
		return settings_controller.CyveTechUISettings(data)

	def test_colors_are_stored_as_uppercase_hex(self):
		doc = self.doc(sidebar_color="#abc", chart_color_3="1baf7a")
		doc.validate()
		self.assertEqual((doc.sidebar_color, doc.chart_color_3), ("#AABBCC", "#1BAF7A"))

	def test_a_color_that_is_not_one_is_refused(self):
		with self.assertRaises(fake_frappe.ValidationError):
			self.doc(page_color="light blue").validate()

	def test_a_private_logo_is_refused(self):
		with self.assertRaises(fake_frappe.ValidationError):
			self.doc(favicon="/private/files/fav.png").validate()

	def test_numbers_are_brought_into_range(self):
		doc = self.doc(tile_radius=90, popup_seconds=1)
		doc.validate()
		self.assertEqual((doc.tile_radius, doc.popup_seconds), (32, 3))


if __name__ == "__main__":
	unittest.main()
