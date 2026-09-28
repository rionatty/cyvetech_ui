"""Which desktop tiles show (cyvetech_ui/cyvetech_ui/desk_modules_rules.py)."""

import unittest

from cyvetech_ui.cyvetech_ui import desk_modules_rules as rules


def icon(label, hidden=0, app="erpnext", icon_type="App"):
	return {"name": label, "label": label, "app": app, "icon_type": icon_type, "hidden": hidden}


def row(module, show):
	return {"module": module, "app": "erpnext", "icon_type": "App", "show_on_desk": show}


class MergeRows(unittest.TestCase):
	def test_new_icons_come_in_as_they_currently_are(self):
		rows = rules.merge_rows([], [icon("Selling"), icon("Quality", hidden=1)])
		self.assertEqual([(r["module"], r["show_on_desk"]) for r in rows], [("Selling", 1), ("Quality", 0)])

	def test_choices_already_made_are_kept(self):
		rows = rules.merge_rows([row("Selling", 0)], [icon("Selling"), icon("Buying")])
		self.assertEqual([(r["module"], r["show_on_desk"]) for r in rows], [("Selling", 0), ("Buying", 1)])

	def test_an_icon_that_is_gone_drops_out(self):
		rows = rules.merge_rows([row("Old Module", 0)], [icon("Selling")])
		self.assertEqual([r["module"] for r in rows], ["Selling"])


class Changes(unittest.TestCase):
	def test_only_icons_whose_flag_differs(self):
		icons = [icon("Selling"), icon("Buying", hidden=1), icon("Stock")]
		rows = [row("Selling", 0), row("Buying", 1), row("Stock", 1)]
		self.assertEqual(rules.changes(rows, icons), [("Selling", 1), ("Buying", 0)])

	def test_a_row_for_an_icon_that_no_longer_exists_is_ignored(self):
		self.assertEqual(rules.changes([row("Gone", 0)], [icon("Selling")]), [])

	def test_nothing_to_do_when_everything_matches(self):
		self.assertEqual(rules.changes([row("Selling", 1)], [icon("Selling")]), [])


class HiddenLabels(unittest.TestCase):
	def test_sorted_labels_of_the_unticked(self):
		rows = [row("Stock", 0), row("Selling", 1), row("Assets", 0)]
		self.assertEqual(rules.hidden_labels(rows), ["Assets", "Stock"])


if __name__ == "__main__":
	unittest.main()
