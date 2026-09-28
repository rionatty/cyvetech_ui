# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""What the desk needs from CyveTech UI Settings, shipped with the boot.

extend_bootinfo hook. Frappe calls it on every page load after the cached
boot is assembled, so what it sets is always current, and the colors are on
the page before the first paint: no extra request, no flash of the default
theme.

It must never raise: a failure here would stop the desk from loading.
"""

import frappe

from cyvetech_ui import __version__
from cyvetech_ui.cyvetech_ui import branding, color_rules, desk_modules
from cyvetech_ui.cyvetech_ui.settings import (
	CHART_PALETTE,
	CHART_PALETTE_DARK,
	THEME_DEFAULTS,
	chart_colors,
	get_settings,
)


def boot_session(bootinfo):
	try:
		settings = get_settings()
		bootinfo.cyvetech_ui = payload(settings, desk_modules.hidden_labels())
		branding.rebrand_app_data(bootinfo.get("app_data"), settings)
		if settings.brand_logo:
			bootinfo.app_logo_url = settings.brand_logo
	except Exception:
		# the desk loads plain rather than not at all
		bootinfo.cyvetech_ui = {"version": __version__}


def payload(settings, hidden_modules):
	palette = color_rules.chart_palette(chart_colors(settings), CHART_PALETTE)
	return {
		"version": __version__,
		"theme": {
			"enabled": settings.apply_theme,
			"top_bar": settings.color_top_bar,
			"rounded": settings.rounded_tiles,
			"vars": color_rules.theme_variables(
				{
					"sidebar": settings.sidebar_color,
					"sidebar_text": settings.sidebar_text_color,
					"highlight": settings.highlight_color,
					"page": settings.page_color,
				},
				THEME_DEFAULTS,
				settings.tile_radius,
			),
		},
		"charts": {
			"enabled": settings.apply_chart_colors,
			"palette": palette,
			# the shipped palette has its own steps for dark mode; a custom
			# one is used as it is in both modes
			"dark_palette": CHART_PALETTE_DARK if palette == color_rules.chart_palette([], CHART_PALETTE) else palette,
			"vary": settings.vary_single_series,
			"override": settings.override_chart_colors,
		},
		"branding": {
			"logo": settings.brand_logo,
			"favicon": settings.favicon,
			"product_name": settings.product_name,
			"replace_all": settings.replace_all_app_logos,
		},
		"alerts": {
			"panel": settings.alerts_panel,
			"popup": settings.popup_notifications,
			"seconds": settings.popup_seconds,
			"sound": settings.popup_sound,
		},
		"hidden_modules": hidden_modules,
	}
