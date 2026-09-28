// CyveTech UI — the desk: theme colors, rounded tiles, logos, the browser icon,
// and the modules taken off the desktop.
//
// Everything arrives with the desk boot (frappe.boot.cyvetech_ui, built by
// cyvetech_ui/cyvetech_ui/boot.py), so it is applied before the first paint.
// This file loads as a plain app_include_js asset, before the desk starts up,
// which matters for the app switcher: its logos and names are read from
// frappe.boot.apps_data when the sidebar is built, so they must be replaced
// before that.

(function () {
	if (typeof frappe === "undefined" || !frappe.boot) return;
	frappe.provide("cyvetech_ui");

	const conf = frappe.boot.cyvetech_ui || {};
	const root = document.documentElement;

	// Only a CSS variable name and a hex color or a pixel length ever go into
	// the stylesheet. The server has checked them already; this is the second lock.
	const VAR_NAME = /^--cvt-[a-z-]+$/;
	const SAFE_VALUE = /^(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|\d{1,2}px)$/;

	function upsert_style(id, css) {
		let el = document.getElementById(id);
		if (!css) {
			if (el) el.remove();
			return;
		}
		if (!el) {
			el = document.createElement("style");
			el.id = id;
			document.head.appendChild(el);
		}
		if (el.textContent !== css) el.textContent = css;
	}

	// ── Theme ────────────────────────────────────────────────────────────
	cyvetech_ui.apply_theme = function (theme) {
		theme = theme || {};
		root.classList.toggle("cvt-theme", !!theme.enabled);
		root.classList.toggle("cvt-top-bar", !!(theme.enabled && theme.top_bar));
		root.classList.toggle("cvt-rounded", !!theme.rounded);
		const declarations = Object.entries(theme.vars || {})
			.filter(([name, value]) => VAR_NAME.test(name) && SAFE_VALUE.test(String(value)))
			.map(([name, value]) => `${name}: ${value};`)
			.join(" ");
		upsert_style("cvt-theme-vars", declarations ? `:root { ${declarations} }` : "");
	};

	// ── Logos, product name and browser icon ─────────────────────────────
	// The server puts the logo on frappe.boot.app_data (boot.py). apps_data,
	// which the app switcher reads, is added to the boot after that, so its
	// copy is replaced here.
	const PLATFORM_APPS = ["frappe", "erpnext"];

	function rebrand() {
		const branding = conf.branding || {};
		const logo = (branding.logo || "").trim();
		const product = (branding.product_name || "").trim();
		const apps = (frappe.boot.apps_data && frappe.boot.apps_data.apps) || [];
		apps.forEach((app) => {
			const platform = PLATFORM_APPS.includes(app.name || app.app_name);
			if (logo && (platform || branding.replace_all)) app.app_logo_url = logo;
			if (product && platform) app.app_title = product;
		});
		// the stylesheet sizes the desktop's top-bar logo for a wide one
		root.classList.toggle("cvt-brand", !!logo);
		if (branding.favicon) set_favicon(branding.favicon);
		cyvetech_ui.brand_sidebar_header(branding);
	}

	// The navigation pane's header shows each workspace's own icon, or a
	// letter where there is none. With the logo switched on there, it shows
	// the brand's mark instead: the browser icon, which is square, else the
	// logo. The header is built from this class on every page, after this
	// file has run, so changing the class once covers them all.
	cyvetech_ui.brand_sidebar_header = function (branding, Header) {
		branding = branding || {};
		Header = Header || (frappe.ui && frappe.ui.SidebarHeader);
		const mark = (branding.favicon || branding.logo || "").trim();
		if (!Header || !branding.sidebar_logo || !mark || Header.prototype.cvt_branded) return false;
		const own = Header.prototype.set_header_icon;
		Header.prototype.set_header_icon = function () {
			if (own) own.apply(this, arguments);
			this.header_icon = `<img class="cvt-brand-mark" src="${frappe.utils.escape_html(mark)}" alt="">`;
		};
		Header.prototype.cvt_branded = true;
		return true;
	};

	function set_favicon(href) {
		const links = document.querySelectorAll('link[rel~="icon"]');
		if (!links.length) {
			const link = document.createElement("link");
			link.rel = "icon";
			link.href = href;
			document.head.appendChild(link);
			return;
		}
		links.forEach((link) => {
			if (link.getAttribute("href") !== href) link.setAttribute("href", href);
		});
	}

	// ── Modules taken off the desk ───────────────────────────────────────
	// The server sets the tiles' hidden flag (desk_modules.py). A user who has
	// rearranged their own desktop sees their saved copy instead, so the
	// tiles are hidden here by name as well, which covers them without
	// touching anyone's saved layout.
	function css_string(value) {
		return String(value).replace(/[\\"]/g, "\\$&").replace(/[\n\r\f]/g, " ");
	}

	cyvetech_ui.hide_modules = function (labels) {
		const selectors = (labels || []).map(
			(label) => `.desktop-icon[data-id="${css_string(label)}"]`
		);
		upsert_style(
			"cvt-hidden-modules",
			selectors.length ? `${selectors.join(",\n")} { display: none !important; }` : ""
		);
	};

	cyvetech_ui.apply_theme(conf.theme);
	rebrand();
	cyvetech_ui.hide_modules(conf.hidden_modules);
})();
