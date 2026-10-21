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

	// ── Where the desk's modules and their entries open ──────────────────
	// Shared by the desk home (cyvetech_ui_home.js) and the module pages
	// (cyvetech_ui_module_pages.js), each of which may be switched off alone.
	const nav = cyvetech_ui.nav || {};

	// where an entry of a module's menu goes, as Frappe's own sidebar works it
	// out (frappe/public/js/frappe/ui/sidebar/sidebar_item.js, get_path)
	nav.path_of = function (item) {
		try {
			if (item.link_type === "URL") return item.url || null;
			if (item.link_type === "Workspace") {
				if (item.route) return item.route;
				const slug = frappe.router.slug(item.link_to);
				const workspace = (frappe.workspaces || {})[slug];
				return (workspace && !workspace.public ? "/desk/private/" : "/desk/") + slug;
			}
			const args = { type: item.link_type, name: item.link_to };
			if (item.link_type === "Report") {
				if (!item.report) return null;
				args.is_query_report =
					item.report.report_type === "Query Report" || item.report.report_type === "Script Report";
				args.report_ref_doctype = item.report.ref_doctype;
			} else if (item.link_type === "Page" && item.route_options) {
				args.route_options = JSON.parse(item.route_options);
			} else {
				args.tab = item.tab;
				// a list opened on the entry's own filters
				const filtered =
					item.link_type === "DocType" && (item.filters ? list_filters(item.filters) : item.route_options);
				if (filtered) {
					args.doc_view = "List";
					args.route_options = typeof filtered === "string" ? JSON.parse(filtered) : filtered;
				}
			}
			return frappe.utils.generate_route(args) || null;
		} catch (error) {
			return null;
		}
	};

	// an entry's filters as the list takes them: each field's value, without its operator
	function list_filters(filters) {
		const found = JSON.parse(frappe.utils.get_filter_as_json(JSON.parse(filters)) || "null");
		if (!found) return null;
		Object.keys(found).forEach((field) => {
			if (Array.isArray(found[field])) found[field] = found[field][1];
		});
		return found;
	}

	// a module's menu, as the boot carries it cut down to what the user may open
	nav.sidebar_of = function (label) {
		return (frappe.boot.workspace_sidebar_item || {})[String(label).toLowerCase()] || null;
	};

	// The modules a folder or an app holds on the desk (Accounting holds
	// Invoicing, Payments and the rest), as Frappe nests them: a hidden one is
	// not among them.
	nav.children_of = function (label) {
		return (frappe.boot.desktop_icons || []).filter(
			(tile) => tile && tile.parent_icon === label && !tile.hidden && tile.label !== label
		);
	};

	// where a module's tile opens: its menu's first entry, or for a folder, its
	// first module's
	nav.tile_path = function (label, depth) {
		const sidebar = nav.sidebar_of(label);
		const first = sidebar && (sidebar.items || []).find((item) => item && item.type === "Link" && !item.hidden);
		if (first) return nav.path_of(first);
		if ((depth || 0) > 1) return null;
		for (const child of nav.children_of(label)) {
			const path = nav.tile_path(child.label, (depth || 0) + 1);
			if (path) return path;
		}
		return null;
	};

	// An address opened as Frappe's router opens a link of its own (router.js,
	// a click on an <a>): what follows the ? as route options, what follows the
	// # as the tab. The module's sidebar is asked for by name, as Frappe's tile
	// asks for it, but only where nothing else rides on the route options:
	// Frappe's sidebar clears them all once it has read its own, and a list's
	// filters would go with it. Another site's address opens beside the desk.
	nav.follow = function (path, module, outside) {
		const url = new URL(path, window.location.origin);
		if (outside || url.origin !== window.location.origin || !frappe.router.is_app_route(url.pathname)) {
			window.open(url.href, "_blank", "noopener");
			return;
		}
		const options = {};
		url.searchParams.forEach((value, key) => {
			options[key] = value;
		});
		frappe.route_options = Object.keys(options).length ? options : module ? { sidebar: module } : null;
		if (url.hash) frappe.route_hash = url.hash;
		frappe.set_route(url.pathname);
	};

	cyvetech_ui.nav = nav;

	cyvetech_ui.apply_theme(conf.theme);
	rebrand();
	cyvetech_ui.hide_modules(conf.hidden_modules);
})();
