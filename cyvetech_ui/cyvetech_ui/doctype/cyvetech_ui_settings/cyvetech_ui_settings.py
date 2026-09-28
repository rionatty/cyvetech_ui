# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from cyvetech_ui.cyvetech_ui import branding, color_rules, desk_modules
from cyvetech_ui.cyvetech_ui.settings import CHART_PALETTE, merge

COLOR_FIELDS = (
	"sidebar_color",
	"sidebar_text_color",
	"highlight_color",
	"page_color",
	"login_panel_color",
	"login_button_color",
	"login_background_color",
	*(f"chart_color_{i}" for i in range(1, len(CHART_PALETTE) + 1)),
)

# Shown to guests (the sign-in page, the browser tab), so they must be public.
PUBLIC_IMAGE_FIELDS = ("brand_logo", "favicon", "login_logo", "login_image")


class CyveTechUISettings(Document):
	def validate(self):
		for fieldname in COLOR_FIELDS:
			value = (self.get(fieldname) or "").strip()
			if not value:
				continue
			color = color_rules.normalize_hex(value)
			if not color:
				frappe.throw(
					_("{0} must be a hex color, such as #16335E.").format(frappe.bold(_(self.meta.get_label(fieldname))))
				)
			self.set(fieldname, color.upper())

		self.tile_radius = color_rules.clamp_radius(self.tile_radius)
		self.popup_seconds = min(60, max(3, cint(self.popup_seconds) or 8))

		for fieldname in PUBLIC_IMAGE_FIELDS:
			if (self.get(fieldname) or "").startswith("/private/"):
				frappe.throw(
					_(
						"{0} is a private file, which the sign-in page and the browser tab cannot show. "
						"Upload it again with Private switched off."
					).format(frappe.bold(_(self.meta.get_label(fieldname))))
				)

	def on_update(self):
		settings = merge(self.as_dict())
		changed = branding.apply(settings)
		if desk_modules.apply():
			changed.append("Desktop Icon.hidden")
		# the theme, logos and chart palette ride the cached desk boot
		frappe.clear_cache()
		if changed:
			frappe.msgprint(
				_("Also updated: {0}").format(", ".join(changed)), alert=True, indicator="green"
			)

	@frappe.whitelist()
	def refresh_desk_modules(self):
		"""Bring the Desk Modules table in line with the desktop's current tiles."""
		frappe.only_for("System Manager")
		desk_modules.refresh_rows(self)
