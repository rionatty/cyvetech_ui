"""The sign-in page's look (cyvetech_ui/cyvetech_ui/login_rules.py)."""

import re
import unittest

from cyvetech_ui.cyvetech_ui import login_rules as rules

HEX = re.compile(r"#[0-9A-F]{6}")


class SafeUrl(unittest.TestCase):
	def test_public_files_assets_and_https_are_allowed(self):
		self.assertEqual(rules.safe_url("/files/logo.png"), "/files/logo.png")
		self.assertEqual(rules.safe_url("/assets/cyvetech_ui/images/x.svg"), "/assets/cyvetech_ui/images/x.svg")
		self.assertEqual(rules.safe_url("https://cdn.example.com/a.png"), "https://cdn.example.com/a.png")

	def test_anything_a_guest_cannot_load_or_that_could_run_is_refused(self):
		for url in (
			"/private/files/logo.png",
			"javascript:alert(1)",
			"data:image/svg+xml,<svg onload=alert(1)>",
			"http://insecure.example.com/a.png",
			"/files/",
			"",
			None,
		):
			self.assertEqual(rules.safe_url(url), "", url)

	def test_nothing_in_the_address_can_end_the_url_it_sits_in(self):
		url = rules.safe_url("/files/my logo') ; background:red;(.png")
		self.assertNotIn("'", url)
		self.assertNotIn(")", url)
		self.assertNotIn("(", url)
		self.assertNotIn(" ", url)
		self.assertNotIn(";", url)
		self.assertTrue(url.startswith("/files/my%20logo"))

	def test_a_stray_percent_is_encoded_but_an_escape_is_kept(self):
		self.assertEqual(rules.safe_url("/files/50%off%20now.png"), "/files/50%25off%20now.png")


class Look(unittest.TestCase):
	def test_blank_settings_give_the_defaults(self):
		look = rules.look({})
		self.assertEqual(look["heading"], rules.DEFAULT_HEADING)
		self.assertEqual(look["tagline"], rules.DEFAULT_TAGLINE)
		self.assertEqual(look["logo"], "")
		self.assertEqual(look["enabled"], 0)

	def test_every_color_is_a_plain_hex_color(self):
		look = rules.look({"login_panel_color": "red;}", "login_button_color": "#abc", "login_enabled": 1})
		for name, value in look["colors"].items():
			self.assertTrue(name.startswith("--cvt-login-"), name)
			self.assertRegex(value, HEX)
		self.assertEqual(look["colors"]["--cvt-login-panel"], "#16335E")  # the bad one fell back
		self.assertEqual(look["colors"]["--cvt-login-button"], "#AABBCC")

	def test_the_sign_in_logo_falls_back_to_the_navigation_logo(self):
		self.assertEqual(rules.look({"brand_logo": "/files/brand.png"})["logo"], "/files/brand.png")
		self.assertEqual(
			rules.look({"brand_logo": "/files/brand.png", "login_logo": "/files/login.png"})["logo"],
			"/files/login.png",
		)

	def test_links_only_take_the_button_color_where_it_reads_on_white(self):
		dark = rules.look({"login_button_color": "#16335E"})["colors"]
		light = rules.look({"login_button_color": "#EAA51A"})["colors"]
		self.assertEqual(dark["--cvt-login-link"], "#16335E")
		self.assertEqual(light["--cvt-login-link"], "#1F2937")

	def test_button_text_reads_on_the_button(self):
		from cyvetech_ui.cyvetech_ui import color_rules

		for button in ("#16335E", "#EAA51A", "#FFFFFF", "#008300"):
			colors = rules.look({"login_button_color": button})["colors"]
			text = colors["--cvt-login-button-text"]
			self.assertGreaterEqual(color_rules.contrast(button, text), 4.5, button)


if __name__ == "__main__":
	unittest.main()
