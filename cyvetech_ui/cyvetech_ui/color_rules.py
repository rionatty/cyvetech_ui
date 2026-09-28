# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""Color math for the desk theme.

No Frappe import, so tests/test_color_rules.py runs without a bench.

The settings page asks for as few colors as possible — the sidebar, the
page, and the highlight on the selected menu item — and everything else is
worked out here: text that stays readable on whatever sidebar color is
picked, and hover and border shades that sit just off the background. A
navy sidebar gets white text and a pale sidebar gets dark text, without
anyone having to know which to choose.

Every color that leaves this module has been through normalize_hex, so a
stray value in the settings can never break out of the CSS it is put in.
"""

import re

_HEX = re.compile(r"#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})")

# The two text colors the theme picks between for any background.
LIGHT_INK = "#ffffff"
DARK_INK = "#111827"

# Corner radius for tiles and cards, in pixels.
RADIUS_MIN, RADIUS_MAX = 0, 32


def normalize_hex(value):
	"""'#1f3a5f' for a 3- or 6-digit hex color (with or without '#'), else None."""
	match = _HEX.fullmatch((value or "").strip())
	if not match:
		return None
	digits = match.group(1).lower()
	if len(digits) == 3:
		digits = "".join(ch * 2 for ch in digits)
	return "#" + digits


def to_rgb(color):
	color = normalize_hex(color)
	if not color:
		raise ValueError(f"not a hex color: {color!r}")
	return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))


def to_hex(rgb):
	return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def luminance(color):
	"""WCAG relative luminance, 0 (black) to 1 (white)."""

	def channel(c):
		c = c / 255
		return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

	r, g, b = (channel(c) for c in to_rgb(color))
	return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
	"""WCAG contrast ratio between two colors, 1 to 21."""
	la, lb = sorted((luminance(a), luminance(b)), reverse=True)
	return (la + 0.05) / (lb + 0.05)


def readable_text(background, light=LIGHT_INK, dark=DARK_INK):
	"""Whichever of the two inks reads better on the background."""
	return light if contrast(background, light) >= contrast(background, dark) else dark


def mix(a, b, weight):
	"""`a` moved `weight` (0 to 1) of the way toward `b`."""
	ra, rb = to_rgb(a), to_rgb(b)
	return to_hex(tuple(x + (y - x) * weight for x, y in zip(ra, rb, strict=True)))


def clamp_radius(value, default=14):
	try:
		radius = int(value)
	except (TypeError, ValueError):
		return default
	return max(RADIUS_MIN, min(RADIUS_MAX, radius))


def theme_variables(colors, defaults, radius=None):
	"""The CSS custom properties the desk stylesheet reads.

	colors / defaults: {"sidebar", "sidebar_text", "highlight", "page"}.
	A blank or malformed value falls back to the default; sidebar_text is the
	one exception, where blank means "work it out from the sidebar".
	"""

	def pick(key):
		return normalize_hex(colors.get(key)) or normalize_hex(defaults.get(key))

	sidebar = pick("sidebar")
	page = pick("page")
	highlight = pick("highlight")
	text = normalize_hex(colors.get("sidebar_text")) or readable_text(sidebar)

	return {
		"--cvt-sidebar-bg": sidebar,
		# a step darker, for the desktop's top bar and the alerts panel header
		"--cvt-sidebar-deep": mix(sidebar, "#000000", 0.12),
		"--cvt-sidebar-text": text,
		# captions and section titles sit back from the menu items
		"--cvt-sidebar-muted": mix(text, sidebar, 0.35),
		"--cvt-sidebar-hover": mix(sidebar, text, 0.1),
		"--cvt-sidebar-border": mix(sidebar, text, 0.14),
		"--cvt-highlight": highlight,
		"--cvt-highlight-deep": mix(highlight, "#000000", 0.25),
		"--cvt-highlight-text": readable_text(highlight),
		"--cvt-page-bg": page,
		"--cvt-page-text": readable_text(page),
		"--cvt-tile-radius": f"{clamp_radius(radius)}px",
	}


def chart_palette(values, defaults):
	"""The chart colors in order: each valid pick, else the default in its place."""
	palette = []
	for index, default in enumerate(defaults):
		value = values[index] if index < len(values) else None
		palette.append(normalize_hex(value) or normalize_hex(default))
	return [color for color in palette if color]
