"""Which desktop tiles show (cyvetech_ui/cyvetech_ui/desk_modules_rules.py)."""

import unittest

from cyvetech_ui.cyvetech_ui import desk_modules_rules as rules


def icon(label, hidden=0, app="erpnext", icon_type="App", parent=None):
	return {
		"name": label,
		"label": label,
		"app": app,
		"icon_type": icon_type,
		"hidden": hidden,
		"parent_icon": parent,
	}


# As ERPNext v16 ships them (erpnext/*/desktop_icon/*.json), in idx order.
DESKTOP = [
	icon("Accounting", icon_type="Folder"),
	icon("Selling", icon_type="Link", parent="ERPNext"),
	icon("Taxes", icon_type="Link", parent="Accounting"),
	icon("ERPNext", hidden=1),
	icon("Subcontracting", icon_type="Link"),
	icon("Stock", icon_type="Link", parent="ERPNext"),
	icon("Support", hidden=1, icon_type="Link", parent="ERPNext"),
	icon("Banking", icon_type="Link", parent="Accounting"),
]


def row(module, show):
	return {"module": module, "app": "erpnext", "icon_type": "App", "show_on_desk": show}


class Ordered(unittest.TestCase):
	def test_each_group_is_followed_by_the_modules_inside_it(self):
		self.assertEqual(
			[i["label"] for i in rules.ordered(DESKTOP)],
			["Accounting", "Taxes", "Banking", "ERPNext", "Selling", "Stock", "Support", "Subcontracting"],
		)

	def test_a_module_whose_group_is_gone_stands_on_its_own(self):
		icons = [icon("Selling", icon_type="Link", parent="Gone"), icon("Stock", icon_type="Link")]
		self.assertEqual([i["label"] for i in rules.ordered(icons)], ["Selling", "Stock"])

	def test_groups_inside_groups_nest(self):
		icons = [
			icon("Leaves", icon_type="Link", parent="People"),
			icon("People", icon_type="Folder", parent="Frappe HR"),
			icon("Frappe HR"),
		]
		self.assertEqual([i["label"] for i in rules.ordered(icons)], ["Frappe HR", "People", "Leaves"])

	def test_two_groups_naming_each_other_are_still_listed_once_each(self):
		icons = [
			icon("A", icon_type="Folder", parent="B"),
			icon("B", icon_type="Folder", parent="A"),
			icon("C", icon_type="Link"),
		]
		self.assertEqual(sorted(i["label"] for i in rules.ordered(icons)), ["A", "B", "C"])
		self.assertEqual(len(rules.ordered(icons)), 3)


class MergeRows(unittest.TestCase):
	def test_every_tile_is_listed_with_the_group_it_sits_in(self):
		rows = rules.merge_rows([], DESKTOP)
		self.assertEqual(len(rows), len(DESKTOP))
		by_module = {r["module"]: r for r in rows}
		self.assertEqual(by_module["Selling"]["group"], "ERPNext")
		self.assertEqual(by_module["Taxes"]["group"], "Accounting")
		self.assertEqual(by_module["Subcontracting"]["group"], "")
		self.assertEqual(by_module["Accounting"]["icon_type"], "Folder")

	def test_a_hidden_group_does_not_untick_the_modules_in_it(self):
		# ERPNext's own tile ships hidden; its modules still show, each on its own
		by_module = {r["module"]: r["show_on_desk"] for r in rules.merge_rows([], DESKTOP)}
		self.assertEqual((by_module["ERPNext"], by_module["Selling"], by_module["Support"]), (0, 1, 0))

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
