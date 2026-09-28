"""The sign-in page's look (cyvetech_ui/cyvetech_ui/login_rules.py)."""

import re
import unittest

from cyvetech_ui.cyvetech_ui import login_rules as rules

HEX = re.compile(r"#[0-9A-F]{6}([0-9A-F]{2})?")  # an 8-digit one carries an alpha


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
			self.assertTrue(HEX.fullmatch(value), f"{name}: {value}")
		self.assertEqual(look["colors"]["--cvt-login-brand"], "#16335E")  # the bad one fell back
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

	def test_the_backdrop_takes_the_brand_colors_faintly(self):
		colors = rules.look({"login_panel_color": "#2F64B0", "highlight_color": "#EB6834"})["colors"]
		self.assertEqual(colors["--cvt-login-brand"], "#2F64B0")
		self.assertEqual(colors["--cvt-login-accent"], "#EB6834")  # the desk's highlight color
		self.assertEqual(colors["--cvt-login-glow"], "#2F64B02E")  # 18%
		self.assertEqual(colors["--cvt-login-glow-accent"], "#EB683424")  # 14%

	def test_the_footer_reads_on_any_page_background(self):
		from cyvetech_ui.cyvetech_ui import color_rules

		for background in ("#F4F6FA", "#FFFFFF", "#0E213D", "#EAA51A"):
			colors = rules.look({"login_background_color": background})["colors"]
			self.assertGreaterEqual(color_rules.contrast(colors["--cvt-login-on-background"], background), 4.5, background)
			self.assertTrue(colors["--cvt-login-dots"].startswith(colors["--cvt-login-on-background"]))

	def test_a_logo_set_as_the_background_photo_is_left_out(self):
		# stretched over the whole page it can only look blurry
		self.assertEqual(rules.look({"brand_logo": "/files/logo.png", "login_image": "/files/logo.png"})["image"], "")
		self.assertEqual(rules.look({"login_logo": "/files/sign-in.png", "login_image": "/files/sign-in.png"})["image"], "")

	def test_a_photo_of_its_own_is_kept(self):
		look = rules.look({"brand_logo": "/files/logo.png", "login_image": "/files/office.jpg"})
		self.assertEqual(look["image"], "/files/office.jpg")
		self.assertEqual(rules.look({"login_image": "/private/files/office.jpg"})["image"], "")  # a guest cannot load it

	def test_button_text_reads_on_the_button(self):
		from cyvetech_ui.cyvetech_ui import color_rules

		for button in ("#16335E", "#EAA51A", "#FFFFFF", "#008300"):
			colors = rules.look({"login_button_color": button})["colors"]
			text = colors["--cvt-login-button-text"]
			self.assertGreaterEqual(color_rules.contrast(button, text), 4.5, button)


if __name__ == "__main__":
	unittest.main()
