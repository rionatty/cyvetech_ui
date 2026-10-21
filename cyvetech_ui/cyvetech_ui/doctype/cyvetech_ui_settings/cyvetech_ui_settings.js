// Copyright (c) 2026, CyveTech and contributors
// For license information, please see license.txt

// CyveTech UI Settings: a live preview of the colors and tiles, a way to put
// the colors back to CyveTech's defaults, a test alert, and the list of
// modules on the desk.

const CVT_THEME_FIELDS = [
	"sidebar_color",
	"sidebar_text_color",
	"highlight_color",
	"page_color",
	"tile_radius",
	"rounded_tiles",
	"header_color",
	"accent_color",
	"danger_color",
	"warning_color",
	"success_color",
];
const CVT_HEX = /^#(?:[0-9a-fA-F]{3}){1,2}$/;

frappe.ui.form.on("CyveTech UI Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Send Me a Test Alert"), () => {
			frappe
				.xcall("cyvetech_ui.cyvetech_ui.doctype.cyvetech_user_alert.cyvetech_user_alert.send_test_alert")
				.then(() => {
					frappe.show_alert({ message: __("Sent. It pops up in a moment, and a copy goes to your email."), indicator: "green" });
					// straight away, rather than waiting on the realtime event or the next poll
					if (window.cyvetech_ui && cyvetech_ui.reload_alerts) cyvetech_ui.reload_alerts();
				});
		});
		frm.add_custom_button(__("Send an Alert to Users"), () => frappe.new_doc("CyveTech User Alert"));
		frm.add_custom_button(__("Reset Colors to Defaults"), () => reset_colors(frm), __("Colors"));

		render_preview(frm);
		render_modules_help(frm);
	},

	...Object.fromEntries(CVT_THEME_FIELDS.map((fieldname) => [fieldname, (frm) => render_preview(frm)])),
});

// Frappe's desktop shows the modules of a hidden group (an app or a folder)
// on their own instead of hiding them, which is rarely what unticking the
// group means: offer to take them off the desk too, and to bring them back.
frappe.ui.form.on("CyveTech Desk Module", {
	show_on_desk(frm, cdt, cdn) {
		const group = locals[cdt][cdn];
		if (!["App", "Folder"].includes(group.icon_type)) return;
		const members = (frm.doc.desk_modules || []).filter((row) => row.group === group.module);
		const shown = members.filter((row) => row.show_on_desk);
		if (!group.show_on_desk && shown.length) {
			frappe.confirm(
				__("Take the {0} modules in {1} off the desk too? If you don't, they show on the desk on their own.", [
					shown.length,
					frappe.utils.escape_html(group.module),
				]),
				() => set_shown(frm, shown, 0)
			);
		} else if (group.show_on_desk && members.length && !shown.length) {
			frappe.confirm(
				__("Show the {0} modules in {1} again?", [members.length, frappe.utils.escape_html(group.module)]),
				() => set_shown(frm, members, 1)
			);
		}
	},
});

function set_shown(frm, rows, value) {
	rows.forEach((row) => frappe.model.set_value(row.doctype, row.name, "show_on_desk", value));
	frm.refresh_field("desk_modules");
}

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
		? __(
				"Every tile on everyone's desktop, each module listed under its group (an app or a folder). Load the current list, untick the modules that should not show, and save."
		  )
		: __("This version of Frappe has no desktop tiles to choose from, so this section does nothing here.");
	field.$wrapper.html(`
		<div class="text-muted small" style="margin-bottom: 10px">${frappe.utils.escape_html(message)}</div>
		${has_icons ? `<button type="button" class="btn btn-default btn-sm cvt-load-modules">${frappe.utils.escape_html(__("Load Desk Modules"))}</button>` : ""}
	`);
	field.$wrapper.find(".cvt-load-modules").on("click", () => refresh_modules(frm));
}

// A small picture of the desk in the chosen colors: sidebar with a selected
// item, and on the page the home's header with its button, and two cards with
// the chosen corner radius, each with a status color.
function render_preview(frm) {
	const field = frm.get_field("theme_preview");
	if (!field) return;
	const d = frm.doc;
	const pick = (value, fallback) => (CVT_HEX.test(value || "") ? value : fallback);
	const sidebar = pick(d.sidebar_color, "#16335E");
	const highlight = pick(d.highlight_color, "#EAA51A");
	const page = pick(d.page_color, "#F4F6FA");
	const text = pick(d.sidebar_text_color, ink_for(sidebar));
	const header = pick(d.header_color, sidebar);
	const accent = pick(d.accent_color, "#2F64B0");
	const danger = pick(d.danger_color, "#C53030");
	const success = pick(d.success_color, "#1E7A46");
	const radius = d.rounded_tiles ? Math.max(0, Math.min(32, cint(d.tile_radius))) : 4;
	const card = (band, label) => `
		<div style="flex:1; padding:8px 10px; background:#fff; border:1px solid #e2e8f0; border-top:3px solid ${band}; border-radius:${radius}px;">
			<div style="color:#64748b;">${label}</div>
			<div style="font-weight:700; font-size:15px; color:#111827;">UGX 12.4M</div>
		</div>`;
	field.$wrapper.html(`
		<div style="display:flex; height:170px; border:1px solid var(--border-color); border-radius:12px; overflow:hidden; font-size:11px;">
			<div style="width:30%; background:${sidebar}; color:${text}; padding:10px 8px; display:flex; flex-direction:column; gap:6px;">
				<div style="font-weight:600; opacity:.95;">${__("Selling")}</div>
				<div style="padding:4px 6px; border-radius:6px; background:${highlight}; color:${ink_for(highlight)}; font-weight:600;">${__("Sales Order")}</div>
				<div style="padding:4px 6px; opacity:.9;">${__("Sales Invoice")}</div>
				<div style="padding:4px 6px; opacity:.9;">${__("Customer")}</div>
			</div>
			<div style="flex:1; background:${page}; padding:10px; display:flex; flex-direction:column; gap:8px;">
				<div style="display:flex; align-items:center; justify-content:space-between; gap:8px; padding:10px 12px; border-radius:12px; color:${ink_for(header)}; background:linear-gradient(118deg, ${header}, ${accent});">
					<b style="font-size:13px;">${__("Good morning")}</b>
					<span style="padding:4px 9px; border-radius:8px; background:${highlight}; color:${ink_for(highlight)}; font-weight:700;">+ ${__("New Sales Invoice")}</span>
				</div>
				<div style="display:flex; gap:8px;">${card(success, __("Sales This Month"))}${card(danger, __("To Collect"))}</div>
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
