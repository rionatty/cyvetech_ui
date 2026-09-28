# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""Which modules show on the desk.

The desktop's tiles are Desktop Icon records (Frappe v16), each with a
`hidden` flag that Frappe itself honors. The Desk Modules table on the
settings page lists the top-level tiles; saving sets their flags.

One catch, handled in the browser: a user who has rearranged their own
desktop keeps a saved copy of every tile (Desktop Layout), and Frappe shows
that copy instead of the shared list, so a tile hidden here would still show
for them. The desk script (public/js/cyvetech_ui_desk.js) hides the tiles
listed in frappe.boot.cyvetech_ui.hidden_modules as well, which covers those
users without rewriting anyone's saved layout.

Frappe v15 has no Desktop Icon, so on v15 all of this does nothing.
"""

import frappe

from cyvetech_ui.cyvetech_ui import desk_modules_rules as rules
from cyvetech_ui.cyvetech_ui.settings import DOCTYPE

DESKTOP_ICON = "Desktop Icon"
CHILD = "CyveTech Desk Module"


def available():
	try:
		return bool(frappe.db.exists("DocType", DESKTOP_ICON))
	except Exception:
		return False


def top_level_icons():
	"""The tiles on the desktop itself: icons with no parent, shipped by an
	app or created by the Administrator (not users' own shortcuts)."""
	return frappe.get_all(
		DESKTOP_ICON,
		filters={"parent_icon": ["is", "not set"]},
		or_filters={"standard": 1, "owner": "Administrator"},
		fields=["name", "label", "app", "icon_type", "hidden"],
		order_by="idx asc, label asc",
	)


def saved_rows():
	return frappe.get_all(
		CHILD,
		filters={"parenttype": DOCTYPE, "parent": DOCTYPE},
		fields=["module", "app", "icon_type", "show_on_desk"],
		order_by="idx asc",
	)


def refresh_rows(settings_doc):
	"""Fill the settings table from the current tiles, keeping choices made."""
	if not available():
		frappe.throw(frappe._("This version of Frappe has no desktop tiles to choose from."))
	current = [row.as_dict() for row in settings_doc.get("desk_modules") or []]
	settings_doc.set("desk_modules", rules.merge_rows(current, top_level_icons()))


def apply():
	"""Set each tile's hidden flag from the saved table. True if any changed."""
	if not available():
		return False
	rows = saved_rows()
	if not rows:
		return False  # the table was never filled in: leave the desk as it is
	updates = rules.changes(rows, top_level_icons())
	for name, hidden in updates:
		frappe.db.set_value(DESKTOP_ICON, name, "hidden", hidden, update_modified=False)
	if updates:
		_clear_icon_caches()
	return bool(updates)


def hidden_labels():
	"""For the desk boot. Never raises."""
	try:
		if not available():
			return []
		return rules.hidden_labels(saved_rows())
	except Exception:
		return []


def apply_on_migrate():
	"""after_migrate: an app update can bring a hidden tile back; hide it again."""
	try:
		apply()
	except Exception:
		frappe.log_error(title="CyveTech UI: desk modules could not be applied")


def _clear_icon_caches():
	# Desktop Icon's own on_update clears these; set_value does not run it.
	cache = frappe.cache() if callable(frappe.cache) and not hasattr(frappe.cache, "delete_key") else frappe.cache
	for key in ("desktop_icons", "bootinfo"):
		cache.delete_key(key)
