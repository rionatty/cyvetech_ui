"""My Alerts ordering (cyvetech_ui/cyvetech_ui/alerts_rules.py)."""

import datetime
import unittest

from cyvetech_ui.cyvetech_ui import alerts_rules as rules

TODAY = "2026-09-28"


def assignment(key, due=None, created="2026-09-01 10:00:00", priority=None):
	return {
		"kind": rules.ASSIGNMENT,
		"key": key,
		"due": due,
		"created": created,
		"urgency": rules.urgency(due, TODAY, priority),
	}


def notification(key, created, unread=1, urgency=rules.NONE, **extra):
	return {"kind": rules.NOTIFICATION, "key": key, "due": None, "created": created, "unread": unread, "urgency": urgency, **extra}


class Urgency(unittest.TestCase):
	def test_bands_by_due_date(self):
		self.assertEqual(rules.urgency("2026-09-20", TODAY), rules.OVERDUE)
		self.assertEqual(rules.urgency("2026-09-28", TODAY), rules.TODAY)
		self.assertEqual(rules.urgency("2026-09-29", TODAY), rules.TODAY)
		self.assertEqual(rules.urgency("2026-10-05", TODAY), rules.SOON)
		self.assertEqual(rules.urgency("2026-10-06", TODAY), rules.LATER)
		self.assertEqual(rules.urgency(None, TODAY), rules.NONE)

	def test_high_priority_is_never_quieter_than_today(self):
		self.assertEqual(rules.urgency("2026-12-01", TODAY, "High"), rules.TODAY)
		self.assertEqual(rules.urgency(None, TODAY, "High"), rules.TODAY)
		self.assertEqual(rules.urgency("2026-09-01", TODAY, "High"), rules.OVERDUE)

	def test_accepts_dates_and_datetimes(self):
		self.assertEqual(rules.urgency(datetime.date(2026, 9, 1), TODAY), rules.OVERDUE)
		self.assertEqual(rules.urgency(datetime.datetime(2026, 9, 28, 9, 0), TODAY), rules.TODAY)

	def test_alert_priorities(self):
		self.assertEqual(rules.alert_band("Urgent"), rules.OVERDUE)
		self.assertEqual(rules.alert_band("Important"), rules.TODAY)
		self.assertEqual(rules.alert_band("Normal"), rules.NONE)
		self.assertEqual(rules.alert_band(None), rules.NONE)


class When(unittest.TestCase):
	def test_reads_like_the_panel_says_it(self):
		self.assertEqual(rules.when("2026-09-20", TODAY), "overdue by 8 days")
		self.assertEqual(rules.when("2026-09-27", TODAY), "overdue by 1 day")
		self.assertEqual(rules.when("2026-09-28", TODAY), "due today")
		self.assertEqual(rules.when("2026-09-29", TODAY), "due tomorrow")
		self.assertEqual(rules.when("2026-10-01", TODAY), "due in 3 days")
		self.assertEqual(rules.when(None, TODAY), "")


class Order(unittest.TestCase):
	def test_most_urgent_first_then_soonest_then_newest(self):
		alerts = [
			notification("n-old", "2026-09-10 08:00:00"),
			assignment("later", "2026-11-01"),
			notification("n-new", "2026-09-27 08:00:00"),
			assignment("overdue-3", "2026-09-25"),
			assignment("overdue-8", "2026-09-20"),
			assignment("soon", "2026-10-02"),
		]
		keys = [a["key"] for a in rules.order(alerts, TODAY)]
		self.assertEqual(keys, ["overdue-8", "overdue-3", "soon", "later", "n-new", "n-old"])

	def test_an_urgent_alert_sits_with_the_overdue(self):
		alerts = [assignment("soon", "2026-10-02"), notification("urgent", "2026-09-28 08:00:00", urgency=rules.OVERDUE)]
		self.assertEqual([a["key"] for a in rules.order(alerts, TODAY)], ["urgent", "soon"])


class DuplicateAssignments(unittest.TestCase):
	def test_an_assignment_notification_behind_an_open_todo_is_dropped(self):
		todos = [{"doctype": "Task", "docname": "TASK-1"}]
		notes = [
			{"type": "Assignment", "doctype": "Task", "docname": "TASK-1"},  # the same assignment
			{"type": "Assignment", "doctype": "Task", "docname": "TASK-2"},  # e.g. "assignment removed"
			{"type": "Mention", "doctype": "Task", "docname": "TASK-1"},  # not an assignment
		]
		kept = rules.without_duplicate_assignments(notes, todos)
		self.assertEqual(
			[(n["type"], n["docname"]) for n in kept],
			[("Assignment", "TASK-2"), ("Mention", "TASK-1")],
		)


class Counting(unittest.TestCase):
	def test_outstanding_is_every_assignment_and_the_unread_rest(self):
		alerts = [assignment("a"), notification("read", "2026-09-01", unread=0), notification("new", "2026-09-02", unread=1)]
		self.assertEqual([a["key"] for a in rules.outstanding(alerts)], ["a", "new"])

	def test_the_badge_takes_the_most_urgent_band(self):
		self.assertEqual(rules.badge_band([assignment("x", "2026-10-02"), assignment("y", "2026-09-01")]), rules.OVERDUE)
		self.assertEqual(rules.badge_band([]), rules.NONE)


class Title(unittest.TestCase):
	def test_collapses_blank_space(self):
		self.assertEqual(rules.title("  Review\n\n the   contract "), "Review the contract")

	def test_long_titles_are_cut_on_a_word(self):
		text = "word " * 40
		cut = rules.title(text, limit=30)
		self.assertTrue(cut.endswith("…"))
		self.assertLessEqual(len(cut), 31)
		self.assertNotIn("wor…", cut)


class EmailBody(unittest.TestCase):
	def body(self, **changes):
		args = {
			"message_html": "<p>Count the <b>main store</b>.</p>",
			"priority": "Normal",
			"priority_label": "Normal",
			"link": "https://erp.example.com/app/sales-order/SO-1",
			"link_label": "Open Sales Order SO-1",
			"footer": "Sent by Admin User from Luuka ERP",
		}
		args.update(changes)
		return rules.email_body(**args)

	def test_the_message_keeps_its_formatting(self):
		self.assertIn("<p>Count the <b>main store</b>.</p>", self.body())

	def test_every_other_piece_is_text(self):
		body = self.body(
			link_label="<script>x</script>", footer='Sent by "<b>Eve</b>"', link='https://x.example/a"onmouseover="y'
		)
		self.assertNotIn("<script>", body)
		self.assertNotIn("<b>Eve</b>", body)
		self.assertNotIn('"onmouseover', body)

	def test_only_important_and_urgent_alerts_carry_a_pill(self):
		self.assertNotIn("text-transform: uppercase", self.body())
		self.assertIn(">Urgent</span>", self.body(priority="Urgent", priority_label="Urgent"))
		self.assertIn(">Wichtig</span>", self.body(priority="Important", priority_label="Wichtig"))  # translated label

	def test_the_button_takes_the_brand_color(self):
		self.assertIn("background: #2f64b0", self.body(button="#2f64b0"))

	def test_no_link_no_button(self):
		self.assertNotIn("<a ", self.body(link=""))

	def test_important_and_urgent_are_flagged_for_mail_clients(self):
		self.assertEqual([rules.email_x_priority(p) for p in ("Normal", "Important", "Urgent", None)], [3, 1, 1, 3])


if __name__ == "__main__":
	unittest.main()
