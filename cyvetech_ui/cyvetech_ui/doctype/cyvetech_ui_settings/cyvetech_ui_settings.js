// Copyright (c) 2026, CyveTech and contributors
// For license information, please see license.txt

// CyveTech UI Settings: a live preview of the colors and tiles, a way to put
// the colors back to CyveTech's defaults, a test alert, and the list of
// modules on the desk.

const CVT_THEME_FIELDS = ["sidebar_color", "sidebar_text_color", "highlight_color", "page_color", "tile_radius", "rounded_tiles"];
const CVT_HEX = /^#(?:[0-9a-fA-F]{3}){1,2}$/;

frappe.ui.form.on("CyveTech UI Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Send Me a Test Alert"), () => {
			frappe
				.xcall("cyvetech_ui.cyvetech_ui.doctype.cyvetech_user_alert.cyvetech_user_alert.send_test_alert")
				.then(() => frappe.show_alert({ message: __("Sent. It pops up in a moment."), indicator: "green" }));
		});
		frm.add_custom_button(__("Send an Alert to Users"), () => frappe.new_doc("CyveTech User Alert"));
		frm.add_custom_button(__("Reset Colors to Defaults"), () => reset_colors(frm), __("Colors"));

		render_preview(frm);
		render_modules_help(frm);
	},

	...Object.fromEntries(CVT_THEME_FIELDS.map((fieldname) => [fieldname, (frm) => render_preview(frm)])),
});

function reset_colors(frm) {
	frappe.confirm(__("Put the desk, chart and sign-in colors back to CyveTech's defaults?"), () => {
		frappe.xcall("cyvetech_ui.cyvetech_ui.settings.color_defaults").then((defaults) => {
			Object.entries(defaults || {}).forEach(([fieldname, value]) => frm.set_value(fieldname, value));
			frappe.show_alert({ message: __("Colors reset. Save to apply them."), indicator: "blue" });
		});
	});
}

function refresh_modules(frm) {
	frm.call("refresh_desk_modules").then(() => {
		frm.dirty();
		frm.refresh_field("desk_modules");
		frappe.show_alert({ message: __("Module list updated. Untick what should not show, then save."), indicator: "blue" });
	});
}

function render_modules_help(frm) {
	const field = frm.get_field("desk_modules_help");
	if (!field) return;
	const has_icons = frappe.boot.desktop_icons !== undefined;
	const message = has_icons
		? __("The tiles on everyone's desktop. Load the current list, untick the modules that should not show, and save.")
		: __("This version of Frappe has no desktop tiles to choose from, so this section does nothing here.");
	field.$wrapper.html(`
		<div class="text-muted small" style="margin-bottom: 10px">${frappe.utils.escape_html(message)}</div>
		${has_icons ? `<button type="button" class="btn btn-default btn-sm cvt-load-modules">${frappe.utils.escape_html(__("Load Desk Modules"))}</button>` : ""}
	`);
	field.$wrapper.find(".cvt-load-modules").on("click", () => refresh_modules(frm));
}

// A small picture of the desk in the chosen colors: sidebar with a selected
// item, the page, and two cards with the chosen corner radius.
function render_preview(frm) {
	const field = frm.get_field("theme_preview");
	if (!field) return;
	const d = frm.doc;
	const pick = (value, fallback) => (CVT_HEX.test(value || "") ? value : fallback);
	const sidebar = pick(d.sidebar_color, "#16335E");
	const highlight = pick(d.highlight_color, "#EAA51A");
	const page = pick(d.page_color, "#F4F6FA");
	const text = pick(d.sidebar_text_color, ink_for(sidebar));
	const radius = d.rounded_tiles ? Math.max(0, Math.min(32, cint(d.tile_radius))) : 4;
	field.$wrapper.html(`
		<div style="display:flex; height:150px; border:1px solid var(--border-color); border-radius:12px; overflow:hidden; font-size:11px;">
			<div style="width:34%; background:${sidebar}; color:${text}; padding:10px 8px; display:flex; flex-direction:column; gap:6px;">
				<div style="font-weight:600; opacity:.95;">${__("Selling")}</div>
				<div style="padding:4px 6px; border-radius:6px; background:${highlight}; color:${ink_for(highlight)}; font-weight:600;">${__("Sales Order")}</div>
				<div style="padding:4px 6px; opacity:.9;">${__("Sales Invoice")}</div>
				<div style="padding:4px 6px; opacity:.9;">${__("Customer")}</div>
			</div>
			<div style="flex:1; background:${page}; padding:12px; display:flex; gap:10px; align-items:flex-start;">
				<div style="flex:1; height:56px; background:#fff; border:1px solid #e2e8f0; border-radius:${radius}px;"></div>
				<div style="flex:1; height:56px; background:#fff; border:1px solid #e2e8f0; border-radius:${radius}px;"></div>
			</div>
		</div>
		<div class="text-muted small" style="margin-top:6px;">${__("Preview. Save to apply it to everyone's desk.")}</div>
	`);
}

// White or near-black text, whichever reads better on the color (WCAG).
function ink_for(hex) {
	const value = hex.length === 4 ? "#" + [...hex.slice(1)].map((c) => c + c).join("") : hex;
	const channel = (i) => {
		const c = parseInt(value.slice(i, i + 2), 16) / 255;
		return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
	};
	const luminance = 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
	const on_white = 1.05 / (luminance + 0.05);
	const on_dark = (luminance + 0.05) / 0.0592; // #111827
	return on_white >= on_dark ? "#FFFFFF" : "#111827";
}
