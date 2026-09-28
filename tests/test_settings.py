"""Reading CyveTech UI Settings safely (cyvetech_ui/cyvetech_ui/settings.py).

settings.py imports frappe, so the stand-in in fake_frappe.py is installed first.
"""

import unittest

import fake_frappe

fake_frappe.install()
settings = fake_frappe.fresh_import("cyvetech_ui.cyvetech_ui.settings")


class Merge(unittest.TestCase):
	def test_a_site_that_never_saved_the_settings_gets_the_defaults(self):
		merged = settings.merge({})
		self.assertEqual(merged.apply_theme, 1)
		self.assertEqual(merged.sidebar_color, "#16335E")
		self.assertEqual(merged.tile_radius, 16)
		self.assertEqual(merged.popup_notifications, 1)

	def test_stored_checkboxes_and_numbers_are_typed(self):
		merged = settings.merge({"apply_theme": "0", "alerts_panel": "1", "tile_radius": "8", "popup_seconds": 12})
		self.assertEqual(merged.apply_theme, 0)
		self.assertEqual(merged.alerts_panel, 1)
		self.assertEqual(merged.tile_radius, 8)
		self.assertEqual(merged.popup_seconds, 12)

	def test_a_blank_or_missing_value_keeps_the_default(self):
		merged = settings.merge({"login_heading": "  ", "sidebar_color": None, "page_color": ""})
		self.assertEqual(merged.login_heading, "Welcome back")
		self.assertEqual(merged.sidebar_color, "#16335E")
		self.assertEqual(merged.page_color, "#F4F6FA")

	def test_set_values_win_and_unknown_keys_are_ignored(self):
		merged = settings.merge({"sidebar_color": "#000000", "brand_logo": "/files/a.png", "not_a_field": "x"})
		self.assertEqual(merged.sidebar_color, "#000000")
		self.assertEqual(merged.brand_logo, "/files/a.png")
		self.assertNotIn("not_a_field", merged)

	def test_a_bad_number_keeps_the_default(self):
		self.assertEqual(settings.merge({"tile_radius": "wide"}).tile_radius, 16)

	def test_the_chart_palette_has_eight_colors_in_both_modes(self):
		self.assertEqual(len(settings.CHART_PALETTE), 8)
		self.assertEqual(len(settings.CHART_PALETTE_DARK), 8)
		self.assertEqual(settings.chart_colors(settings.merge({})), settings.CHART_PALETTE)


if __name__ == "__main__":
	unittest.main()
