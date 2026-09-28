# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""CyveTech UI Settings, read safely.

Everything in this app reads its settings through get_settings(), never
straight off the document, for two reasons:

  * It must never raise. It runs while the desk boots and while the sign-in
    page renders, and a half-migrated site or a bad value must not stop
    anyone from logging in.
  * A Single that has never been saved has no rows in tabSingles, so its
    checkboxes read as 0 rather than their defaults. Merging the stored
    values over DEFAULTS makes a fresh install behave exactly as the form
    shows it.
"""

import frappe

DOCTYPE = "CyveTech UI Settings"

# CyveTech's navy and gold, with a soft neutral page.
THEME_DEFAULTS = {
	"sidebar": "#16335E",
	"sidebar_text": "",  # blank: worked out from the sidebar color
	"highlight": "#EAA51A",
	"page": "#F4F6FA",
}

# The chart palette, validated for color-vision deficiency and separation on
# a white card (light) and on v16's dark card #171717 (dark). Slot order is
# part of the validation: neighbors are the pairs that must stay distinct.
CHART_PALETTE = ["#2F64B0", "#EB6834", "#1BAF7A", "#EAA51A", "#E87BA4", "#008300", "#4A3AA7", "#E34948"]
CHART_PALETTE_DARK = ["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#008300", "#9085E9", "#E66767"]

DEFAULTS = {
	# Branding
	"brand_logo": "",
	"favicon": "",
	"product_name": "",
	"replace_all_app_logos": 0,
	"sidebar_logo": 1,
	# Desk colors and tiles
	"apply_theme": 1,
	"sidebar_color": THEME_DEFAULTS["sidebar"],
	"sidebar_text_color": THEME_DEFAULTS["sidebar_text"],
	"highlight_color": THEME_DEFAULTS["highlight"],
	"page_color": THEME_DEFAULTS["page"],
	"color_top_bar": 1,
	"rounded_tiles": 1,
	"tile_radius": 16,
	# Charts
	"apply_chart_colors": 1,
	"vary_single_series": 1,
	"override_chart_colors": 0,
	**{f"chart_color_{i}": color for i, color in enumerate(CHART_PALETTE, start=1)},
	# Sign-in page
	"login_enabled": 1,
	"login_logo": "",
	"login_panel_color": "#16335E",
	"login_button_color": "#16335E",
	"login_background_color": "#F4F6FA",
	"login_heading": "Welcome back",
	"login_tagline": "Sign in to pick up where you left off.",
	"login_image": "",
	# Alerts
	"alerts_panel": 1,
	"popup_notifications": 1,
	"popup_seconds": 8,
	"popup_sound": 1,
}

CHECKS = {
	"replace_all_app_logos",
	"sidebar_logo",
	"apply_theme",
	"color_top_bar",
	"rounded_tiles",
	"apply_chart_colors",
	"vary_single_series",
	"override_chart_colors",
	"login_enabled",
	"alerts_panel",
	"popup_notifications",
	"popup_sound",
}
INTS = {"tile_radius", "popup_seconds"}


def get_settings():
	"""The settings as a frappe._dict, defaults filled in. Never raises."""
	stored = {}
	try:
		if frappe.db.exists("DocType", DOCTYPE):
			# raw strings on purpose: merge() does the typing, and `cast=` is
			# not accepted by every Frappe version this app runs on
			stored = frappe.db.get_singles_dict(DOCTYPE) or {}
	except Exception:
		stored = {}
	return merge(stored)


def merge(stored):
	"""DEFAULTS with every stored value that is actually set laid over them."""
	settings = frappe._dict(DEFAULTS)
	for key, value in (stored or {}).items():
		if key not in DEFAULTS or value is None:
			continue
		if key in CHECKS:
			settings[key] = 1 if _truthy(value) else 0
		elif key in INTS:
			try:
				settings[key] = int(value)
			except (TypeError, ValueError):
				pass
		elif isinstance(value, str) and value.strip():
			# a blank text field means "not set": its default stands, which for
			# the logos, images and the sidebar text color is blank anyway
			settings[key] = value.strip()
	return settings


def _truthy(value):
	if isinstance(value, str):
		return value.strip() not in ("", "0", "false", "False", "no")
	return bool(value)


def chart_colors(settings):
	return [settings.get(f"chart_color_{i}") for i in range(1, len(CHART_PALETTE) + 1)]


@frappe.whitelist()
def color_defaults():
	"""The shipped colors, for the settings page's Reset Colors button."""
	frappe.only_for("System Manager")
	return {
		key: value
		for key, value in DEFAULTS.items()
		if key.endswith("_color") or key.startswith("chart_color_")
	}
