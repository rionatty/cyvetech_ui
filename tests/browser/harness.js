// Shared by the browser test pages: collect checks, then show them.
//
// Each page sets up a stand-in `frappe`, loads the app's real scripts and
// stylesheet, and checks what they did — computed styles included, which is
// why these run in a browser rather than in Node.

window.results = [];

window.check = function (label, ok, got) {
	window.results.push({ label, ok: !!ok, got: ok ? "" : JSON.stringify(got) });
};

window.css = function (selector, property, pseudo) {
	const el = document.querySelector(selector);
	return el ? getComputedStyle(el, pseudo || null).getPropertyValue(property).trim() : "(no element)";
};

window.report = function () {
	const failed = window.results.filter((r) => !r.ok).length;
	const total = window.results.length;
	const box = document.getElementById("results") || document.body.appendChild(document.createElement("div"));
	box.id = "results";
	box.innerHTML =
		`<h2 style="font:600 15px system-ui;margin:16px 0 8px">${total - failed}/${total} passed</h2>` +
		window.results
			.map(
				(r) =>
					`<div style="font:13px system-ui;color:${r.ok ? "#166534" : "#b91c1c"}">${r.ok ? "PASS" : "FAIL"} ${r.label}` +
					(r.ok ? "" : ` <code style="color:#555">${r.got.replace(/</g, "&lt;")}</code>`) +
					"</div>"
			)
			.join("");
	document.title = `${failed ? "FAIL" : "PASS"} ${total - failed}/${total}`;
	window.test_summary = { total, failed, failures: window.results.filter((r) => !r.ok) };
};

// Colors as computed styles give them, and how well one reads on another
// (the WCAG contrast ratio).
window.rgba = function (color) {
	const parts = (String(color).match(/[\d.]+/g) || []).map(Number);
	return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
};

window.contrast = function (foreground, background) {
	const luminance = (color) => {
		const c = rgba(color);
		const channel = (v) => ((v /= 255) <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
		return 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
	};
	const [light, dark] = [luminance(foreground), luminance(background)].sort((x, y) => y - x);
	return (light + 0.05) / (dark + 0.05);
};

// Frappe v16's start-up, as the app's scripts see it (frappe/public/js/frappe/desk.js):
// the scripts in the page's <head> run first, while frappe.session is still
// empty; then frappe.Application signs the user in (set_globals) and fires
// "app_ready" on the document. start_desk() is that second half.
window.app_ready_handlers = [];

window.$ = function () {
	return {
		on(event, fn) {
			if (event === "app_ready") window.app_ready_handlers.push(fn);
		},
	};
};

window.start_desk = function () {
	frappe.session.user = frappe.boot.user.name;
	window.app_ready_handlers.forEach((fn) => fn({ type: "app_ready" }));
};

// The small part of Frappe the app's scripts touch outside what each page stubs.
window.make_frappe = function (boot) {
	const frappe = {
		boot: Object.assign({ user: { name: "jane@example.com" } }, boot),
		session: {}, // the user arrives with start_desk(), as in Frappe
		provide(path) {
			let node = window;
			for (const part of path.split(".")) node = node[part] = node[part] || {};
			return node;
		},
		utils: {
			escape_html(text) {
				return String(text)
					.replace(/&/g, "&amp;")
					.replace(/</g, "&lt;")
					.replace(/>/g, "&gt;")
					.replace(/"/g, "&quot;")
					.replace(/'/g, "&#39;");
			},
			get_form_link(doctype, name) {
				return `/app/${doctype.toLowerCase().replace(/ /g, "-")}/${encodeURIComponent(name)}`;
			},
		},
	};
	window.__ = (text, args) => (args ? text.replace(/\{(\d+)\}/g, (_, i) => args[i]) : text);
	return frappe;
};

// Load one of the app's files. A test run can swap a file for another copy by
// naming it in the address: ?use:cyvetech_ui_desk.js=<url>. Only used while
// parsing the page's <head>, so the file runs in its place in the order.
window.load_app_file = function (path) {
	const name = path.split("/").pop().split("?")[0];
	const swapped = new URLSearchParams(location.search).get("use:" + name);
	const src = swapped || path;
	if (name.endsWith(".css")) document.write(`<link rel="stylesheet" href="${src}">`);
	else document.write(`<script src="${src}"><\/script>`);
};
