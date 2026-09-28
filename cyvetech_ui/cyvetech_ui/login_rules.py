# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""The sign-in page's look, made safe to put in a stylesheet.

No Frappe import (tests/test_login_rules.py). www/login.py reads the
settings and hands them here; www/login.html draws the page.

Everything the page prints inside CSS goes through this module first: each
color must be a plain hex color, and each picture must be one of the site's
public files, a shipped asset or an https address, with anything that could
end the url('') it sits in percent-encoded. Text (heading, tagline) is left
to Jinja's escaping in the template.
"""

import re
from urllib.parse import quote

from cyvetech_ui.cyvetech_ui import color_rules

DEFAULT_HEADING = "Welcome back"
DEFAULT_TAGLINE = "Sign in to pick up where you left off."
FALLBACK = {"brand": "#16335E", "accent": "#EAA51A", "button": "#16335E", "background": "#F4F6FA"}

# How strongly the backdrop behind the card takes the brand's colors, as the
# alpha of an 8-digit hex color: soft pools of color, and a faint dot grid.
GLOW_ALPHA = "2E"  # 18%
ACCENT_GLOW_ALPHA = "24"  # 14%
DOTS_ALPHA = "1A"  # 10%

# a guest on the sign-in page can load these; /private/files/ it cannot
IMAGE_SOURCES = ("/files/", "/assets/", "https://")
_URL_KEEP = "/:?=&%+,@!$*#~"
_LONE_PERCENT = re.compile(r"%(?![0-9a-fA-F]{2})")


def safe_color(value, fallback):
	return (color_rules.normalize_hex(value) or color_rules.normalize_hex(fallback)).upper()


def safe_url(url):
	"""A public picture's address, safe inside url('') and src="", else ""."""
	url = (url or "").strip()
	if not any(url.startswith(source) and len(url) > len(source) for source in IMAGE_SOURCES):
		return ""
	return quote(_LONE_PERCENT.sub("%25", url), safe=_URL_KEEP)


def look(settings):
	"""What login.html needs, from the merged settings (settings.get_settings)."""
	brand = safe_color(settings.get("login_panel_color"), FALLBACK["brand"])
	accent = safe_color(settings.get("highlight_color"), FALLBACK["accent"])
	button = safe_color(settings.get("login_button_color"), FALLBACK["button"])
	background = safe_color(settings.get("login_background_color"), FALLBACK["background"])
	on_background = color_rules.readable_text(background)
	colors = {
		"--cvt-login-brand": brand,
		"--cvt-login-accent": accent,
		"--cvt-login-glow": brand + GLOW_ALPHA,
		"--cvt-login-glow-accent": accent + ACCENT_GLOW_ALPHA,
		"--cvt-login-button": button,
		"--cvt-login-button-hover": color_rules.mix(button, "#000000", 0.18),
		"--cvt-login-button-text": color_rules.readable_text(button),
		# links sit on the white card: the button color only where it reads there
		"--cvt-login-link": button if color_rules.contrast(button, "#FFFFFF") >= 4.5 else "#1F2937",
		"--cvt-login-background": background,
		# the footer and the dot grid sit on the page background itself
		"--cvt-login-on-background": on_background,
		"--cvt-login-dots": on_background + DOTS_ALPHA,
	}
	logos = {safe_url(settings.get("login_logo")), safe_url(settings.get("brand_logo"))} - {""}
	image = safe_url(settings.get("login_image"))
	if image in logos:
		image = ""  # a logo stretched to fill the screen only ever looks blurry
	return {
		"enabled": 1 if settings.get("login_enabled") else 0,
		# the sign-in logo, else the navigation logo, else none
		"logo": safe_url(settings.get("login_logo")) or safe_url(settings.get("brand_logo")),
		"image": image,
		"heading": (settings.get("login_heading") or "").strip() or DEFAULT_HEADING,
		"tagline": (settings.get("login_tagline") or "").strip() or DEFAULT_TAGLINE,
		"colors": {name: value.upper() for name, value in colors.items()},
	}
