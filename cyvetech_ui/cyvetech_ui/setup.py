# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""Installation."""

import frappe

from cyvetech_ui.cyvetech_ui import desk_modules
from cyvetech_ui.cyvetech_ui.settings import DEFAULTS, DOCTYPE


def after_install():
	"""Store the defaults, so the settings page opens showing what is in force,
	and list the desktop's modules (all shown) ready to be switched off."""
	doc = frappe.get_single(DOCTYPE)
	for key, value in DEFAULTS.items():
		if doc.get(key) in (None, ""):
			doc.set(key, value)
	if desk_modules.available():
		desk_modules.refresh_rows(doc)
	doc.flags.ignore_permissions = True
	doc.save()
