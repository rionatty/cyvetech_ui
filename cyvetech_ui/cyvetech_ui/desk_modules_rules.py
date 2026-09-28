# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""Which desktop tiles show: the table on the settings page against the
Desktop Icon records. No Frappe import (tests/test_desk_modules_rules.py).

icons: [{"name", "label", "app", "icon_type", "hidden"}] — Desktop Icon rows.
rows:  [{"module", "app", "icon_type", "show_on_desk"}] — the settings table,
       keyed by the icon's label, which is also its name in Frappe.
"""


def merge_rows(rows, icons):
	"""The table for the icons there are now.

	Each icon keeps the choice already made for it; an icon that is new to
	the table comes in as it currently is (shown unless already hidden); an
	icon that no longer exists drops out.
	"""
	choice = {row["module"]: 1 if row.get("show_on_desk") else 0 for row in rows}
	return [
		{
			"module": icon["label"],
			"app": icon.get("app") or "",
			"icon_type": icon.get("icon_type") or "",
			"show_on_desk": choice.get(icon["label"], 0 if icon.get("hidden") else 1),
		}
		for icon in icons
	]


def changes(rows, icons):
	"""[(icon name, hidden)] for each icon whose hidden flag must change."""
	by_label = {icon["label"]: icon for icon in icons}
	out = []
	for row in rows:
		icon = by_label.get(row["module"])
		if not icon:
			continue
		hidden = 0 if row.get("show_on_desk") else 1
		if (1 if icon.get("hidden") else 0) != hidden:
			out.append((icon["name"], hidden))
	return out


def hidden_labels(rows):
	"""The labels of the tiles taken off the desk."""
	return sorted(row["module"] for row in rows if not row.get("show_on_desk"))
