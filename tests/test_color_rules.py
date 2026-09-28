"""Color math for the desk theme (cyvetech_ui/cyvetech_ui/color_rules.py)."""

import re
import unittest

from cyvetech_ui.cyvetech_ui import color_rules as rules

HEX = re.compile(r"#[0-9a-f]{6}")


class NormalizeHex(unittest.TestCase):
	def test_accepts_three_and_six_digits_with_or_without_hash(self):
		self.assertEqual(rules.normalize_hex("#ABC"), "#aabbcc")
		self.assertEqual(rules.normalize_hex("16335E"), "#16335e")
		self.assertEqual(rules.normalize_hex("  #16335e "), "#16335e")

	def test_refuses_anything_else(self):
		for value in (None, "", "red", "#12345", "#1234567", "#ggg", "rgb(0,0,0)"):
			self.assertIsNone(rules.normalize_hex(value), value)

	def test_nothing_can_break_out_of_the_stylesheet(self):
		self.assertIsNone(rules.normalize_hex("#fff; } body { display: none"))
		self.assertIsNone(rules.normalize_hex("#fff</style><script>"))


class Contrast(unittest.TestCase):
	def test_black_on_white_is_21_to_1(self):
		self.assertAlmostEqual(rules.contrast("#000000", "#ffffff"), 21, places=2)

	def test_readable_text_picks_the_better_ink(self):
		self.assertEqual(rules.readable_text("#16335e"), rules.LIGHT_INK)  # navy sidebar
		self.assertEqual(rules.readable_text("#eaa51a"), rules.DARK_INK)  # gold highlight
		self.assertEqual(rules.readable_text("#ffffff"), rules.DARK_INK)
		self.assertEqual(rules.readable_text("#000000"), rules.LIGHT_INK)

	def test_the_chosen_ink_is_never_the_worse_one(self):
		for color in ("#777777", "#3a5f86", "#f0ab00", "#2f64b0", "#e87ba4", "#008300", "#cccccc"):
			chosen = rules.readable_text(color)
			other = rules.DARK_INK if chosen == rules.LIGHT_INK else rules.LIGHT_INK
			self.assertGreaterEqual(rules.contrast(color, chosen), rules.contrast(color, other), color)

	def test_default_theme_reads_at_aa(self):
		variables = rules.theme_variables({}, {"sidebar": "#16335E", "highlight": "#EAA51A", "page": "#F4F6FA"})
		self.assertGreaterEqual(rules.contrast(variables["--cvt-sidebar-bg"], variables["--cvt-sidebar-text"]), 4.5)
		self.assertGreaterEqual(rules.contrast(variables["--cvt-highlight"], variables["--cvt-highlight-text"]), 4.5)


class Mix(unittest.TestCase):
	def test_halfway_between_black_and_white_is_mid_gray(self):
		self.assertEqual(rules.mix("#000000", "#ffffff", 0.5), "#808080")

	def test_the_ends_are_the_colors_themselves(self):
		self.assertEqual(rules.mix("#16335e", "#ffffff", 0), "#16335e")
		self.assertEqual(rules.mix("#16335e", "#ffffff", 1), "#ffffff")


class Radius(unittest.TestCase):
	def test_clamped_to_zero_to_thirty_two(self):
		self.assertEqual(rules.clamp_radius(50), 32)
		self.assertEqual(rules.clamp_radius(-3), 0)
		self.assertEqual(rules.clamp_radius("12"), 12)

	def test_rubbish_falls_back_to_the_default(self):
		self.assertEqual(rules.clamp_radius(None), 14)
		self.assertEqual(rules.clamp_radius("abc"), 14)


class ThemeVariables(unittest.TestCase):
	DEFAULTS = {"sidebar": "#16335E", "sidebar_text": "", "highlight": "#EAA51A", "page": "#F4F6FA"}

	def test_every_value_is_a_hex_color_or_a_pixel_length(self):
		variables = rules.theme_variables({"sidebar": "#ffffff"}, self.DEFAULTS, 20)
		for name, value in variables.items():
			self.assertTrue(name.startswith("--cvt-"), name)
			self.assertTrue(HEX.fullmatch(value) or value == "20px", (name, value))

	def test_a_bad_color_falls_back_to_the_default(self):
		variables = rules.theme_variables({"sidebar": "not a color", "page": "#12"}, self.DEFAULTS)
		self.assertEqual(variables["--cvt-sidebar-bg"], "#16335e")
		self.assertEqual(variables["--cvt-page-bg"], "#f4f6fa")

	def test_a_light_sidebar_gets_dark_text(self):
		variables = rules.theme_variables({"sidebar": "#f8fafc"}, self.DEFAULTS)
		self.assertEqual(variables["--cvt-sidebar-text"], rules.DARK_INK)

	def test_a_chosen_sidebar_text_color_is_kept(self):
		variables = rules.theme_variables({"sidebar_text": "#ffd700"}, self.DEFAULTS)
		self.assertEqual(variables["--cvt-sidebar-text"], "#ffd700")

	def test_hover_and_border_sit_between_the_sidebar_and_its_text(self):
		variables = rules.theme_variables({}, self.DEFAULTS)
		background, text = variables["--cvt-sidebar-bg"], variables["--cvt-sidebar-text"]
		for shade in (variables["--cvt-sidebar-hover"], variables["--cvt-sidebar-border"]):
			self.assertLess(rules.contrast(background, shade), rules.contrast(background, text))
			self.assertNotEqual(shade, background)

	def test_radius_is_written_in_pixels(self):
		self.assertEqual(rules.theme_variables({}, self.DEFAULTS, 99)["--cvt-tile-radius"], "32px")


class ChartPalette(unittest.TestCase):
	DEFAULTS = ["#2F64B0", "#EB6834", "#1BAF7A"]

	def test_a_bad_pick_is_replaced_by_the_default_in_its_place(self):
		self.assertEqual(
			rules.chart_palette(["#ff0000", "nonsense", None], self.DEFAULTS),
			["#ff0000", "#eb6834", "#1baf7a"],
		)

	def test_missing_picks_take_the_defaults(self):
		self.assertEqual(rules.chart_palette([], self.DEFAULTS), ["#2f64b0", "#eb6834", "#1baf7a"])


if __name__ == "__main__":
	unittest.main()
