# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""Logo, browser icon and product name, written where Frappe reads them.

Frappe already has a field for each of these, but every screen reads a
different one (checked against Frappe v16.34):

  brand_logo   -> Website Settings.app_logo and Navbar Settings.app_logo
                  * sign-in and password pages: get_app_logo(), which tries
                    Website Settings first, then Navbar Settings
                  * the desktop's top bar: desktop.py reads Navbar Settings
                    only, never Website Settings
                  Hence both. (The `app_logo_url` hook is no use here: once
                  three or more apps define it, get_app_logo() falls back to
                  Frappe's own logo.)

  favicon      -> Website Settings.favicon
                  www/desk.html and the website pages both print it, and it
                  beats ERPNext's own favicon, which only comes from a hook.

  product_name -> Website Settings.app_name
                  the desk's browser tab title, and the sign-in page title

The app switcher's logos and names come from each app's hooks through the
desk boot, not from a stored field; boot.py replaces those.

A value cleared here is taken back only where it is still the value this app
put there: a logo someone set by hand in Website Settings is never wiped.
"""

import frappe

TARGETS = {
	"brand_logo": (("Website Settings", "app_logo"), ("Navbar Settings", "app_logo")),
	"favicon": (("Website Settings", "favicon"),),
	"product_name": (("Website Settings", "app_name"),),
}


def _applied_key(doctype, fieldname):
	return f"cyvetech_ui_applied:{doctype}:{fieldname}"


def apply(settings):
	"""Write the branding into Frappe's fields. Returns what changed, as
	["Doctype.field", ...]. Idempotent: a repeat call writes nothing."""
	changed = []
	for source, targets in TARGETS.items():
		value = (settings.get(source) or "").strip()
		for doctype, fieldname in targets:
			if not frappe.db.exists("DocType", doctype):
				continue
			current = frappe.db.get_single_value(doctype, fieldname) or ""
			key = _applied_key(doctype, fieldname)
			if value:
				if current != value:
					frappe.db.set_single_value(doctype, fieldname, value)
					changed.append(f"{doctype}.{fieldname}")
				frappe.db.set_default(key, value)
				continue
			applied = frappe.db.get_default(key)
			if applied and current == applied:
				frappe.db.set_single_value(doctype, fieldname, None)
				changed.append(f"{doctype}.{fieldname}")
			if applied:
				frappe.db.set_default(key, None)

	for doctype in {change.split(".")[0] for change in changed}:
		frappe.clear_document_cache(doctype, doctype)
	return changed


def apply_on_migrate():
	"""after_migrate: re-assert the branding after an update. Never fails a deploy."""
	try:
		from cyvetech_ui.cyvetech_ui.settings import get_settings

		if apply(get_settings()):
			frappe.clear_cache()
	except Exception:
		frappe.log_error(title="CyveTech UI: branding could not be applied")


# The apps whose logo and name are the platform's own branding, as opposed to
# an app describing what it does (Frappe HR, a client's own app).
PLATFORM_APPS = ("frappe", "erpnext")


def rebrand_app_data(app_data, settings):
	"""Put the navigation logo (and product name) on the desk's per-app data:
	the app switcher and the sidebar header's fallback logo read these."""
	logo = (settings.get("brand_logo") or "").strip()
	product = (settings.get("product_name") or "").strip()
	every_app = bool(settings.get("replace_all_app_logos"))
	for app in app_data or []:
		if not isinstance(app, dict):
			continue
		platform = app.get("app_name") in PLATFORM_APPS
		if logo and (platform or every_app):
			app["app_logo_url"] = logo
		if product and platform:
			app["app_title"] = product
	return app_data
