// CyveTech UI — the desk home.
//
// Frappe v16's desk opens on a page of module tiles and nothing else. This puts a
// home beside them, on that same page: a greeting, the ERPNext figures that matter
// today, what waits for the logged-in user, what needs attention in the business,
// and the panels behind the figures (cyvetech_ui/cyvetech_ui/home.py reads them).
// Frappe's tiles stay Frappe's own, drawn as a list of modules down the left in the
// order work flows through ERPNext, each opening to its own menu, so search, the
// notifications, the avatar menu and editing the desktop all work as before.
//
// Its look is HRMS Addon's desk home (hrms_addon_home.js); what is on it is the
// business's: each user sees the figures of what their roles are about, and only
// what they may read (home_rules.py says whose figures are whose).
//
// WHAT IT MUST NEVER DO
//
// Stop the desk opening. Everything here is inside try/catch, the home is only
// ever added to the page, and a call that fails leaves the tiles exactly as Frappe
// drew them. CyveTech UI Settings > Home switches it off without a deploy. On a site
// where HRMS Addon's own desk home is on, this one stands aside.
//
// The styles are public/css/cyvetech_ui_home.css. Every color in them comes from
// the settings (color_rules.theme_variables): nothing here picks one.

(function () {
	if (typeof frappe === "undefined" || !frappe.boot) return;
	const conf = (frappe.boot.cyvetech_ui || {}).home || {};
	if (!conf.enabled) return;
	if (frappe.boot.user && frappe.boot.user.name === "Guest") return;
	// HRMS Addon draws a desk home of its own: two would fight over one page
	if (frappe.boot.hrms_addon_home) return;
	// where the modules and their entries open (cyvetech_ui_desk.js, which loads first)
	const nav = window.cyvetech_ui && cyvetech_ui.nav;
	if (!nav) return;
	frappe.provide("cyvetech_ui.home");

	const SUMMARY = "cyvetech_ui.cyvetech_ui.home.summary";
	const FIGURES = "cyvetech_ui.cyvetech_ui.home.figures";
	const FRESH_MS = 60 * 1000; // how long an answer is shown before it is asked for again
	const ORDER_ID = "cvt-home-order";
	// the modules in the order work flows through ERPNext (home_rules.MODULES)
	const MODULES = Array.isArray(conf.modules) ? conf.modules : [];
	// Frappe's tiles on the desk itself, and never while the desk is being edited
	const RAIL = '.desktop-wrapper.cvt-has-home:not([data-mode="Edit"]) > .desktop-container';
	const TILES = RAIL + " > .icons-container > .icons";
	// how far in a padded page may hold the desk and still be drawn out to the window's edges
	const MOST_INSET = 64;
	// what bleed() measures and the stylesheet reads
	const MEASURED = ["--cvt-bleed-l", "--cvt-bleed-r", "--cvt-bleed-t", "--cvt-bleed-b"];
	// how many shortcuts the strip under the figures offers, of each kind
	const SHOWN_CREATE = 3;
	const SHOWN_VISITED = 5;

	// where the tab each viewer last opened is kept, in their own browser
	const TAB_KEY = "cyvetech_ui:home_tab";
	const OVERVIEW = "overview";

	let answer = null; // the summary: the greeting, what waits, which figures and sections
	let asked_at = 0;
	let asking = false;
	// the figures, by part: "cards" (across the top of the overview), or a tab's key, each
	// {"cards", "panels", "badges", "at", "currency", "time"}
	const parts = {};
	const parts_asking = {};
	let current = OVERVIEW; // the tab of dashboards open now
	let requested = null; // a tab a module page's dashboard button asked for, until it is opened
	let tab = "items"; // the list open in Waiting for You
	let open_module = null; // the module whose own menu is open in the list
	const shown_groups = new Set(); // the headings of a module's menu that are open, as "module|heading"

	const ICONS = {
		waiting:
			'<path d="M4 13.5h4l1.5 2.5h5l1.5-2.5h4"/><path d="M6.2 5.5h11.6L20 13.5V18a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18v-4.5z"/>',
		unread: '<path d="M6.5 16.5V11a5.5 5.5 0 0 1 11 0v5.5l1.5 2h-14z"/><path d="M10 20.5a2.2 2.2 0 0 0 4 0"/>',
		sales: '<path d="M4 17l5-5 4 4 7-7"/><path d="M15 9h5v5"/>',
		receivable: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M12 8.8v6.4M9.4 12.6l2.6 2.6 2.6-2.6"/>',
		payable: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M12 15.2V8.8M9.4 11.4L12 8.8l2.6 2.6"/>',
		cash: '<path d="M3.5 9.5h17L12 4z"/><path d="M5.5 9.5v8M10 9.5v8M14 9.5v8M18.5 9.5v8M3.5 20h17"/>',
		orders: '<path d="M6 3.5h12v17l-3-2-3 2-3-2-3 2z"/><path d="M9 8.5h6M9 12h6M9 15.5h3.5"/>',
		to_deliver:
			'<path d="M3 6.5h11v9.5H3z"/><path d="M14 9.5h4l3 3.2V16h-7"/><circle cx="7" cy="17.6" r="1.8"/><circle cx="17.2" cy="17.6" r="1.8"/>',
		quotations:
			'<path d="M7 3.5h7l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-9.5A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5z"/><path d="M14 3.5v4h4M9 12.5h6M9 16h4"/>',
		purchases: '<path d="M5 8h14l-1.2 12H6.2z"/><path d="M9 8V6.5a3 3 0 0 1 6 0V8"/>',
		to_receive: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
		stock_value:
			'<rect x="4" y="12.5" width="7" height="7" rx="1.2"/><rect x="13" y="12.5" width="7" height="7" rx="1.2"/><rect x="8.5" y="4.5" width="7" height="7" rx="1.2"/>',
		reorder:
			'<path d="M19.5 11A7.5 7.5 0 0 0 6.2 6.6L4.5 8.3"/><path d="M4.5 4.5v3.8h3.8"/><path d="M4.5 13a7.5 7.5 0 0 0 13.3 4.4l1.7-1.7"/><path d="M19.5 19.5v-3.8h-3.8"/>',
		work_orders:
			'<circle cx="12" cy="12" r="3"/><path d="M12 3.5V6M12 18v2.5M3.5 12H6M18 12h2.5M6 6l1.8 1.8M16.2 16.2L18 18M6 18l1.8-1.8M16.2 7.8L18 6"/>',
		tasks: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>',
		issues: '<path d="M5 5h14v10H9.5L5 19z"/><path d="M9 9.5h6M9 12h3.5"/>',
		attention: '<path d="M12 4l9 16H3z"/><path d="M12 10v4.2M12 17.2v.3"/>',
		trend: '<path d="M5 19V10M10 19V5M15 19v-7M20 19v-11"/>',
		aging: '<circle cx="12" cy="13" r="7"/><path d="M12 9.5V13l2.5 1.6M9.5 3.5h5"/>',
		customers:
			'<path d="M16 19v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 17.5V19"/><circle cx="10" cy="8" r="3.2"/><path d="M20 19v-1.4a3.2 3.2 0 0 0-2.4-3.1M15.5 5a3.2 3.2 0 0 1 0 6.1"/>',
		drafts: '<path d="M4.5 19.5h4l10-10-4-4-10 10z"/><path d="M13 7l4 4"/>',
		overview:
			'<rect x="4" y="4" width="7" height="7" rx="1.6"/><rect x="13" y="4" width="7" height="7" rx="1.6"/>' +
			'<rect x="4" y="13" width="7" height="7" rx="1.6"/><rect x="13" y="13" width="7" height="7" rx="1.6"/>',
		assets: '<path d="M4 20V9l8-5 8 5v11"/><path d="M9 20v-6h6v6"/>',
		quality: '<path d="M12 3.5l7 3v5.2c0 4.3-3 7.7-7 8.8-4-1.1-7-4.5-7-8.8V6.5z"/><path d="M8.8 12.2l2.2 2.2 4.2-4.4"/>',
		reports:
			'<path d="M7 3.5h7l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-9.5A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5z"/>' +
			'<path d="M9 16v-3M12 16v-5M15 16v-2"/>',
		arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
		chevron: '<path d="M9 6l6 6-6 6"/>',
		plus: '<path d="M12 5.5v13M5.5 12h13"/>',
		refresh: '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3L19.5 9"/><path d="M19.5 4.5V9H15"/>',
		history: '<circle cx="12" cy="12" r="7.5"/><path d="M12 8.2V12l2.6 1.6"/>',
		up: '<path d="M7 14l5-5 5 5"/>',
		down: '<path d="M7 10l5 5 5-5"/>',
		page: '<path d="M5 19V9M10 19V5M15 19v-7M20 19v-11"/>',
	};
	// the panels that share a figure's picture
	const SAME_AS = {
		deliver: "to_deliver",
		receive: "to_receive",
		production: "work_orders",
		profit: "sales",
		payables: "payable",
		items: "stock_value",
		territories: "customers",
		suppliers: "purchases",
		warehouses: "stock_value",
		projects: "tasks",
		hours_by_project: "aging",
		sales_trend: "trend",
		purchase_trend: "trend",
		stock_moves: "trend",
		production_trend: "trend",
		work_order_status: "work_orders",
		job_cards_list: "work_orders",
		requests_list: "orders",
		requests: "orders",
		negative: "attention",
		job_cards: "work_orders",
		completed: "work_orders",
		projects_open: "tasks",
		hours: "aging",
		leads: "customers",
		opportunities: "sales",
		pipeline: "sales",
		opportunities_closing: "sales",
		opportunity_stages: "trend",
		lead_sources: "customers",
		issues_replied: "issues",
		issues_on_hold: "issues",
		issue_priorities: "issues",
		asset_value: "assets",
		asset_categories: "assets",
		maintenance_due: "assets",
		maintenance: "assets",
		inspections: "quality",
		rejected: "quality",
		inspection_results: "quality",
		non_conformances: "quality",
		non_conformance_list: "quality",
	};

	function icon(name) {
		return (
			'<svg class="cvt-home-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" ' +
			`stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${
				ICONS[name] || ICONS[SAME_AS[name]] || ICONS.page
			}</svg>`
		);
	}

	function esc(text) {
		return frappe.utils.escape_html(text == null ? "" : String(text));
	}

	function count(value) {
		const number = Number(value) || 0;
		try {
			return number.toLocaleString();
		} catch (e) {
			return String(number);
		}
	}

	function currency() {
		const read = Object.values(parts).find((part) => part.currency);
		return (read && read.currency) || (answer && answer.currency) || "";
	}

	// The tab a module page's dashboard button asks for. It comes as a route option, which Frappe's router may
	// also carry in the address, JSON-encoded (router.js set_route), and it is taken off both once read: the tab
	// the viewer moves to is not undone when the desk is drawn again, and the next list opened does not take it
	// for a filter. Only while the desk is on the screen: Frappe keeps the pages it has shown, hidden, and
	// another page's options are its own.
	function take_request() {
		const wrapper = desk();
		if (!wrapper || wrapper.offsetParent === null) return;
		try {
			let named = null;
			const options = frappe.route_options;
			if (options && options.dashboard != null) {
				named = options.dashboard;
				delete options.dashboard;
				if (!Object.keys(options).length) frappe.route_options = null;
			}
			const address = new URL(window.location.href);
			if (address.searchParams.has("dashboard")) {
				named = named || address.searchParams.get("dashboard");
				address.searchParams.delete("dashboard");
				window.history.replaceState(window.history.state, "", address.pathname + address.search + address.hash);
			}
			if (typeof named === "string" && named.startsWith('"')) named = JSON.parse(named);
			if (named) requested = String(named);
		} catch (error) {
			console.error(error);
		}
	}

	// The tab to open first: the one asked for, else the one the viewer last opened, else the overview; only one
	// the user has
	function first_tab(data) {
		const have = (key) => (data.tabs || []).some((one) => one.key === key);
		take_request();
		const named = requested;
		requested = null;
		if (named && have(named)) return named;
		let kept = null;
		try {
			kept = window.localStorage.getItem(TAB_KEY);
		} catch (error) {
			kept = null;
		}
		return kept && have(kept) ? kept : OVERVIEW;
	}

	function keep_tab() {
		try {
			window.localStorage.setItem(TAB_KEY, current);
		} catch (error) {
			// the tab still opens; it is only not remembered
		}
	}

	// A tab asked for once the summary is here opens over the one open; until then, the summary opens it. Frappe
	// says the page changed (container.js) before it draws the desk afresh, so the desk is drawn on this tab.
	function follow_request() {
		take_request();
		if (!requested || !answer) return;
		const named = requested;
		requested = null;
		if (!tab_of(named) || named === current) return;
		current = named;
		keep_tab();
		redraw(); // where the home is not on the desk yet, show() draws it on this tab
		load_parts(false);
	}

	// a sum of money as the home writes it: its currency, then the figure shortened (84.7M)
	function money(value) {
		const number = Number(value) || 0;
		let figure;
		try {
			figure = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 }).format(number);
		} catch (e) {
			figure = count(Math.round(number));
		}
		return (currency() ? currency() + " " : "") + figure;
	}

	// the same sum in full, for its tooltip
	function money_in_full(value) {
		try {
			if (typeof format_currency === "function") return format_currency(Number(value) || 0, currency() || undefined);
		} catch (e) {
			// the shortened figure is shown either way
		}
		return (currency() ? currency() + " " : "") + count(Math.round(Number(value) || 0));
	}

	function day_words(day) {
		try {
			const parts = String(day).split("-").map(Number);
			return new Date(parts[0], parts[1] - 1, parts[2]).toLocaleDateString(undefined, {
				weekday: "long",
				day: "numeric",
				month: "long",
			});
		} catch (e) {
			return day || "";
		}
	}

	// a month's label in the reader's own language, from the month's first day
	function month_words(month) {
		try {
			const parts = String(month.from).split("-").map(Number);
			return new Date(parts[0], parts[1] - 1, 1).toLocaleDateString(undefined, { month: "short" });
		} catch (e) {
			return month.label || "";
		}
	}

	function time_words(stamp) {
		try {
			const [day, time] = String(stamp).split(" ");
			const parts = day.split("-").map(Number);
			const clock = (time || "0:0").split(":").map(Number);
			return new Date(parts[0], parts[1] - 1, parts[2], clock[0], clock[1]).toLocaleTimeString(undefined, {
				hour: "numeric",
				minute: "2-digit",
			});
		} catch (e) {
			return "";
		}
	}

	// Frappe keeps its own order of the tiles, in the page and while the desk is
	// edited; the stylesheet shows them in ours. A tile that is not one of the
	// modules named keeps Frappe's place, after them.
	function order_rules() {
		const escape = window.CSS && window.CSS.escape;
		if (!escape) return "";
		return MODULES.map(
			(label, index) => `${TILES} > .desktop-icon[data-id=${escape(String(label))}] { order: ${index + 1}; }`
		).join("\n");
	}

	function style() {
		if (document.getElementById(ORDER_ID)) return;
		const sheet = document.createElement("style");
		sheet.id = ORDER_ID;
		sheet.textContent = order_rules();
		document.head.appendChild(sheet);
	}

	// Frappe's desk page as it is on the screen now. Frappe empties and draws it again every time the page is
	// shown (desktop.js: on_page_show -> make), so what was put on it before is gone and it is looked for afresh.
	function desk() {
		const all = Array.from(document.querySelectorAll(".desktop-wrapper"));
		return all.find((wrapper) => wrapper.offsetParent !== null) || all[0] || null;
	}

	// whether the home is on that desk already
	function present() {
		const wrapper = desk();
		const home = wrapper && wrapper.querySelector(".cvt-home");
		return !!(home && home.childElementCount && wrapper.classList.contains("cvt-has-home"));
	}

	// where the home goes: inside Frappe's desk page, before its tiles
	function mount() {
		const wrapper = desk();
		const tiles = wrapper && wrapper.querySelector(".desktop-container");
		if (!wrapper || !tiles) return null;
		let home = wrapper.querySelector(".cvt-home");
		if (!home) {
			home = document.createElement("div");
			home.className = "cvt-home";
			wrapper.insertBefore(home, tiles);
			wrapper.classList.add("cvt-has-home");
			home.addEventListener("click", clicked);
			home.addEventListener("keydown", keyed);
		}
		// the heading of the list of modules, which the stylesheet writes above Frappe's tiles
		wrapper.style.setProperty("--cvt-rail-title", JSON.stringify(__("Modules")));
		bleed(wrapper);
		menus(wrapper);
		return home;
	}

	// The page Frappe puts the desk in is padded, so the navbar stopped short of the window's edges and the
	// home sat in from them. How far in the desk sits is measured, and the stylesheet draws it out by that much;
	// at the foot too, so the padding under it does not lengthen the page. Past MOST_INSET something else holds
	// it (a sidebar), and on that side it is left where it is.
	function bleed(wrapper) {
		try {
			MEASURED.forEach((name) => wrapper.style.removeProperty(name));
			const box = wrapper.getBoundingClientRect();
			if (!box.width) return;
			// what the desk may be drawn out to: the pane that scrolls, or something inside it that would cut off
			// whatever is drawn past it
			const pane = wrapper.closest(".main-section");
			let frame = pane;
			let holder = wrapper; // the part of the frame that holds the desk
			for (let node = wrapper.parentElement; node && node !== pane && node !== document.body; node = node.parentElement) {
				const cut = getComputedStyle(node);
				if (cut.overflowX !== "visible" || cut.overflowY !== "visible") {
					frame = node;
					break;
				}
				holder = node;
			}
			const edge = frame ? frame.getBoundingClientRect() : null;
			const left = frame ? edge.left + frame.clientLeft : -window.scrollX;
			const top = frame ? edge.top + frame.clientTop - frame.scrollTop : -window.scrollY;
			const width = (frame || document.documentElement).clientWidth;
			// the top from the desk's own page: what Frappe shows above the page (its navbar, an announcement) is not
			// the page's padding
			const page = wrapper.closest(".page-container");
			const inset = {
				l: box.left - left,
				r: left + width - box.right,
				t: box.top - Math.max(top, page ? page.getBoundingClientRect().top : top),
				b: holder.getBoundingClientRect().bottom - box.bottom,
			};
			Object.keys(inset).forEach((side) => {
				const drawn_out = inset[side] > 0.5 && inset[side] <= MOST_INSET;
				wrapper.style.setProperty("--cvt-bleed-" + side, (drawn_out ? Math.round(inset[side]) : 0) + "px");
			});
		} catch (error) {
			console.error(error);
		}
	}

	// ── The modules down the left ───────────────────────────────────────────

	// a module's own menu, as its sidebar lists it: the headings and the entries under them. A folder has no
	// menu of its own: its modules are its entries.
	function entries(label) {
		const sidebar = nav.sidebar_of(label);
		const all = [];
		if (sidebar) {
			(sidebar.items || []).forEach((item) => {
				if (!item || item.hidden) return;
				if (item.type === "Section Break") all.push({ heading: item.label });
				else if (item.type === "Link") {
					const path = nav.path_of(item);
					// an address of the entry's own opens beside the desk, as it does from Frappe's sidebar
					if (path && item.label) all.push({ label: item.label, path: path, outside: item.link_type === "URL" });
				}
			});
		} else {
			nav.children_of(label).forEach((child) => {
				const path = nav.tile_path(child.label);
				if (path) all.push({ label: child.label, path: path, module: child.label });
			});
		}
		// a heading with nothing under it says nothing
		return all.filter((row, index) => !row.heading || (all[index + 1] && !all[index + 1].heading));
	}

	function open_state(wrapper) {
		wrapper.querySelectorAll(".desktop-icon.cvt-has-menu").forEach((tile) => {
			const open = tile.getAttribute("data-id") === open_module;
			tile.classList.toggle("cvt-open", open);
			const toggle = tile.querySelector(".cvt-rail-toggle");
			if (toggle) toggle.setAttribute("aria-expanded", open ? "true" : "false");
		});
	}

	// Each module in the list opens to its own menu, so an entry is one click from the desk. The row itself is
	// still Frappe's tile and opens the module as before; the arrow and the menu are added inside it, which
	// keeps them out of Frappe's count of the tiles when the desk is edited.
	function menus(wrapper) {
		try {
			wrapper
				.querySelectorAll(":scope > .desktop-container > .icons-container > .icons > .desktop-icon[data-id]")
				.forEach((tile) => {
					if (tile.querySelector(".cvt-rail-menu")) return;
					const module = tile.getAttribute("data-id");
					const list = entries(module);
					if (!list.length) return;
					tile.insertAdjacentHTML(
						"beforeend",
						`<span class="cvt-rail-toggle" role="button" tabindex="0" aria-expanded="false" ` +
							`title="${esc(__("Show menu"))}">${icon("chevron")}</span>` +
							`<span class="cvt-rail-menu">${menu_html(list, module)}</span>`
					);
					tile.classList.add("cvt-has-menu");
					// neither the arrow nor the menu is the tile: a click on them does not open the module
					const mine = (event) => {
						event.preventDefault();
						event.stopPropagation();
					};
					const flip = (event) => {
						mine(event);
						open_module = open_module === module ? null : module;
						open_state(wrapper);
					};
					const pick = (event) => {
						mine(event);
						const heading = event.target.closest(".cvt-rail-heading");
						if (heading) {
							const group = heading.parentElement;
							const key = module + "|" + list[Number(group.getAttribute("data-group"))].heading;
							const shown = !group.classList.contains("cvt-shown");
							group.classList.toggle("cvt-shown", shown);
							heading.setAttribute("aria-expanded", shown ? "true" : "false");
							if (shown) shown_groups.add(key);
							else shown_groups.delete(key);
							return;
						}
						const link = event.target.closest(".cvt-rail-link");
						const row = link && list[Number(link.getAttribute("data-index"))];
						try {
							if (row) nav.follow(row.path, row.module || module, row.outside);
						} catch (error) {
							console.error(error);
						}
					};
					const keyed = (act) => (event) => {
						if (event.key === "Enter" || event.key === " ") act(event);
					};
					const toggle = tile.querySelector(".cvt-rail-toggle");
					const menu = tile.querySelector(".cvt-rail-menu");
					toggle.addEventListener("click", flip);
					toggle.addEventListener("keydown", keyed(flip));
					menu.addEventListener("click", pick);
					menu.addEventListener("keydown", keyed(pick));
				});
			open_state(wrapper);
		} catch (error) {
			console.error(error);
		}
	}

	// A module's menu: its first entries as they are, and each heading with the entries under it, which the
	// heading opens and shuts. A heading stays as it was left while the desk is drawn again.
	function menu_html(list, module) {
		let html = "";
		let in_group = false;
		list.forEach((row, index) => {
			if (row.heading) {
				if (in_group) html += "</span></span>";
				const shown = shown_groups.has(module + "|" + row.heading);
				html +=
					`<span class="cvt-rail-group${shown ? " cvt-shown" : ""}" data-group="${index}">` +
					`<span class="cvt-rail-heading" role="button" tabindex="0" aria-expanded="${shown ? "true" : "false"}">` +
					`<span>${esc(__(row.heading))}</span>${icon("chevron")}</span><span class="cvt-rail-items">`;
				in_group = true;
			} else {
				html += `<span class="cvt-rail-link" role="link" tabindex="0" data-index="${index}">${esc(__(row.label))}</span>`;
			}
		});
		return html + (in_group ? "</span></span>" : "");
	}

	// the desk as Frappe drew it: nothing of the home's left on it
	function unmount(wrapper) {
		if (!wrapper) return;
		wrapper.querySelectorAll(".cvt-home, .cvt-rail-toggle, .cvt-rail-menu").forEach((node) => node.remove());
		wrapper.querySelectorAll(".cvt-has-menu").forEach((tile) => tile.classList.remove("cvt-has-menu", "cvt-open"));
		wrapper.classList.remove("cvt-has-home");
		MEASURED.forEach((name) => wrapper.style.removeProperty(name));
	}

	// ── The home ────────────────────────────────────────────────────────────

	function bone(width) {
		return `<span class="cvt-home-bone" style="width:${width}"></span>`;
	}

	function skeleton() {
		return (
			`<section class="cvt-home-hero"><div class="cvt-home-hero-text">${bone("260px")}${bone("180px")}</div></section>` +
			`<div class="cvt-home-cards">${[1, 2, 3, 4]
				.map(() => `<div class="cvt-home-card cvt-home-frame">${bone("90px")}${bone("60px")}${bone("120px")}</div>`)
				.join("")}</div>`
		);
	}

	// the document the user makes most, if they may still make it
	function creatable(doctype) {
		try {
			return !!doctype && frappe.model.can_create(doctype);
		} catch (error) {
			return false;
		}
	}

	function made(data) {
		return (data.create || []).filter(creatable);
	}

	function hero(data) {
		const name = data.first_name || "";
		const waits = data.waiting || {};
		const first = made(data)[0];
		const where = [day_words(data.today), data.company].filter(Boolean).map(esc).join(" · ");
		return (
			`<section class="cvt-home-hero">` +
			`<div class="cvt-home-avatar">${esc(name.trim().charAt(0).toUpperCase() || "•")}</div>` +
			`<div class="cvt-home-hero-text"><h2>${esc(__(data.greeting || "Welcome"))}, ${esc(name)}</h2>` +
			`<p>${where}</p></div>` +
			`<div class="cvt-home-hero-side">` +
			`<button type="button" class="cvt-home-chip" data-cvt-home="todo">${icon("waiting")}` +
			`<span><b>${count(waits.tasks)}</b><small>${esc(__("Waiting for you"))}</small></span></button>` +
			(first
				? `<button type="button" class="cvt-home-action" data-cvt-home="new" data-doctype="${esc(first)}">` +
				  `${icon("plus")}<span>${esc(__("New {0}", [__(first)]))}</span></button>`
				: "") +
			`</div></section>`
		);
	}

	// The figures across the top of a tab: the user's own work is there at once, a business figure as a frame
	// until it is read, and not at all where it could not be. frames: what the summary said; read: what the
	// server has read for them, once it has.
	function shown_cards(frames, read) {
		const found = (key) => ((read && read.cards) || []).find((one) => one.key === key) || null;
		return (frames || []).map((one) => (one.frame ? (read ? found(one.key) : one) : one)).filter(Boolean);
	}

	// the figures across the top of the tab open now
	function tab_cards(data) {
		const open = tab_of(current);
		if (!open || open.key === OVERVIEW) return shown_cards(data.cards, parts.cards);
		return shown_cards(open.cards, parts[open.key]);
	}

	// hours, to a tenth where they are not whole
	function hours(value) {
		return count(Math.round((Number(value) || 0) * 10) / 10) + " h";
	}

	function figure_of(card) {
		return card.kind === "money" ? money(card.value) : card.kind === "hours" ? hours(card.value) : count(card.value);
	}

	function note_of(card) {
		const note = card.note;
		if (note && typeof note === "object") return `${money(note.money)} ${__(note.words || "")}`;
		return __(note || "");
	}

	// a figure against the period before: which way it moved, and how far
	function moved(change) {
		if (!change || change.percent == null || change.direction === "same") return "";
		const way = change.direction === "up" ? "up" : "down";
		return `<span class="cvt-home-delta cvt-home-delta-${way}">${icon(way)}${esc(count(change.percent) + "%")}</span>`;
	}

	function cards(data) {
		const all = tab_cards(data);
		if (!all.length) return "";
		return (
			`<div class="cvt-home-cards">` +
			all
				.map((card) => {
					if (card.frame) {
						return (
							`<div class="cvt-home-card cvt-home-frame" data-key="${esc(card.key)}">` +
							`<span class="cvt-home-card-top"><span class="cvt-home-card-label">${esc(__(card.label))}</span>` +
							`<span class="cvt-home-card-icon">${icon(card.key)}</span></span>${bone("70%")}${bone("50%")}</div>`
						);
					}
					const full = card.kind === "money" ? ` title="${esc(money_in_full(card.value))}"` : "";
					return (
						`<button type="button" class="cvt-home-card cvt-tone-${esc(card.tone || "navy")}" ` +
						`data-cvt-home="card" data-key="${esc(card.key)}">` +
						`<span class="cvt-home-card-top"><span class="cvt-home-card-label">${esc(__(card.label))}</span>` +
						`<span class="cvt-home-card-icon">${icon(card.key)}</span></span>` +
						`<span class="cvt-home-card-value"${full}>${esc(figure_of(card))}</span>` +
						`<span class="cvt-home-card-note">${moved(card.change)}${esc(note_of(card))}</span></button>`
					);
				})
				.join("") +
			`</div>`
		);
	}

	// How a route Frappe recorded reads as a shortcut: "List/Sales Invoice/List" is Sales Invoice.
	function route_label(route) {
		const parts = String(route || "")
			.split("/")
			.filter(Boolean);
		if (!parts.length || parts[0] === "Form") return null;
		const kind = parts[0];
		if (["List", "query-report", "Workspaces", "dashboard-view", "Tree", "Report", "modules"].includes(kind)) {
			return parts[1] ? __(parts[parts[0] === "Workspaces" && parts[1] === "private" ? 2 : 1]) : null;
		}
		try {
			return __(frappe.utils.to_title_case(kind.replace(/-/g, " "), true));
		} catch (e) {
			return kind;
		}
	}

	// the pages the user opens most, as Frappe counts them (route_history.frequently_visited_links), else the
	// usual ones for their desk
	function visited(data) {
		const out = [];
		const seen = new Set();
		(frappe.boot.frequently_visited_links || []).forEach((link) => {
			const label = link && route_label(link.route);
			if (label && !seen.has(label) && out.length < SHOWN_VISITED) {
				seen.add(label);
				out.push({ label: label, route: link.route });
			}
		});
		(data.links || []).forEach((link) => {
			if (!seen.has(link.label) && out.length < SHOWN_VISITED) {
				seen.add(link.label);
				out.push(link);
			}
		});
		return out;
	}

	// Under the figures: the documents the user makes most after the one beside the greeting, and the pages they
	// open most, each one click away.
	function shortcuts(data) {
		const create = made(data).slice(1, 1 + SHOWN_CREATE);
		const pages = visited(data);
		if (!create.length && !pages.length) return "";
		const chips = (list, what) =>
			list
				.map(
					(item, index) =>
						`<button type="button" class="cvt-home-shortcut" data-cvt-home="${what}" data-index="${index}"` +
						(what === "new" ? ` data-doctype="${esc(item)}"` : "") +
						`>${what === "new" ? icon("plus") : ""}<span>${esc(what === "new" ? __(item) : item.label)}</span></button>`
				)
				.join("");
		return (
			`<nav class="cvt-home-shortcuts" aria-label="${esc(__("Shortcuts"))}">` +
			(create.length
				? `<span class="cvt-home-shortcuts-group"><span class="cvt-home-shortcuts-label">${esc(__("Create"))}</span>` +
				  `${chips(create, "new")}</span>`
				: "") +
			(pages.length
				? `<span class="cvt-home-shortcuts-group"><span class="cvt-home-shortcuts-label">${icon("history")}` +
				  `${esc(__("Jump back in"))}</span>${chips(pages, "visit")}</span>`
				: "") +
			`</nav>`
		);
	}

	// a list of rows, each opening what it names; what, panel and part say which list a click is on
	function rows(list, empty, what, part, panel) {
		if (!list.length) return `<div class="cvt-home-empty">${esc(empty)}</div>`;
		return list
			.map((row, index) => {
				const opens = row.doctype && row.docname;
				const meta = [
					row.docname && row.docname !== row.title ? row.docname : "",
					row.when ? __(row.when) : "",
					row.value != null ? money(row.value) : "",
					// how far along it is, once it is under way
					Number(row.progress) > 0 && row.progress_words ? `${count(row.progress)}% ${__(row.progress_words)}` : "",
				]
					.filter(Boolean)
					.map(esc)
					.join(" · ");
				return (
					`<button type="button" class="cvt-home-row" data-cvt-home="${what}" data-part="${esc(part || "rows")}" ` +
					(panel ? `data-panel="${esc(panel)}" ` : "") +
					`data-index="${index}"><span class="cvt-home-dot cvt-band-${esc(row.band || "none")}"></span>` +
					`<span class="cvt-home-row-text"><span class="cvt-home-row-title">${esc(row.title)}</span>` +
					`<span class="cvt-home-row-meta">${meta}</span></span>${opens ? icon("chevron") : ""}</button>`
				);
			})
			.join("");
	}

	function waiting_panel(data) {
		const waits = data.waiting || {};
		const shown = tab === "notes" ? waits.notes || [] : waits.items || [];
		const tabs = [
			["items", __("To Do"), waits.tasks],
			["notes", __("Notifications"), waits.unread],
		]
			.map(
				([key, label, total]) =>
					`<button type="button" class="cvt-home-tab${tab === key ? " cvt-on" : ""}" data-cvt-home="tab" ` +
					`data-tab="${key}">${esc(label)}<i>${count(total)}</i></button>`
			)
			.join("");
		return (
			`<section class="cvt-home-panel cvt-home-waiting cvt-home-wide"><header><span class="cvt-home-panel-icon">${icon("waiting")}</span>` +
			`<h3>${esc(__("Waiting for You"))}</h3><span class="cvt-home-tabs">${tabs}</span></header>` +
			`<div class="cvt-home-list">${rows(
				shown,
				tab === "notes" ? __("Nothing unread.") : __("Nothing is waiting for you."),
				"waiting"
			)}</div></section>`
		);
	}

	// ── The dashboards (home.py figures) ────────────────────────────────────
	// The summary says which tabs the user has, each with its figures and its dashboards as {key, title,
	// size}, and a tab's figures come in a call of their own once it is opened: the greeting and what waits
	// are never held up by them, and a tab never opened is never read. A dashboard is drawn as a frame while
	// its figures are on their way, and not at all where they could not be read.

	function tab_of(key) {
		return ((answer && answer.tabs) || []).find((one) => one.key === key) || null;
	}

	// a dashboard of the tab open now, as the server read it
	function panel_of(key) {
		const read = parts[current];
		return ((read && read.panels) || []).find((one) => one.key === key) || null;
	}

	function one_panel(item) {
		if (!parts[current]) return frame_panel(item);
		const one = panel_of(item.key);
		return one ? draw_panel(one, item.size === "wide") : "";
	}

	function frame_panel(item) {
		return (
			`<section class="cvt-home-panel${item.size === "wide" ? " cvt-home-wide" : ""}" data-panel="${esc(item.key)}"><header>` +
			`<span class="cvt-home-panel-icon">${icon(item.key)}</span><h3>${esc(__(item.title))}</h3></header>` +
			`<div class="cvt-home-list cvt-home-pad">${bone("72%")}${bone("88%")}${bone("54%")}</div></section>`
		);
	}

	function draw_panel(one, wide) {
		const body = KINDS[one.kind];
		if (!body) return "";
		return (
			`<section class="cvt-home-panel cvt-home-${esc(one.key)}${wide ? " cvt-home-wide" : ""}" data-panel="${esc(one.key)}">` +
			`<header><span class="cvt-home-panel-icon">${icon(one.key)}</span><h3>${esc(__(one.title))}</h3>` +
			(one.note ? `<span class="cvt-home-panel-note">${esc(__(one.note))}</span>` : "") +
			`</header><div class="cvt-home-list">${body(one)}</div>${see_all(one)}</section>`
		);
	}

	// the way to the whole list, where the panel shows only some of it
	function see_all(one) {
		const listed = (one.rows || []).length;
		if (!one.route || !one.total || one.total <= listed) return "";
		return (
			`<div class="cvt-home-more"><button type="button" class="cvt-home-all" data-cvt-home="all" data-panel="${esc(one.key)}">` +
			`<span>${esc(__("See all {0}", [count(one.total)]))}</span>${icon("chevron")}</button></div>`
		);
	}

	function nothing(words) {
		return `<div class="cvt-home-empty">${esc(words)}</div>`;
	}

	// Needs Attention: what is late, owed or short, the most pressing first, each opening its list
	function attention_body(one) {
		const all = one.rows || [];
		if (!all.length) return nothing(__("Nothing is late or short. All clear."));
		return all
			.map(
				(row, index) =>
					`<button type="button" class="cvt-home-row cvt-home-check" data-cvt-home="more" data-panel="${esc(one.key)}" ` +
					`data-part="rows" data-index="${index}"><b class="cvt-home-count cvt-band-${esc(row.band || "none")}">` +
					`${count(row.value)}</b><span class="cvt-home-row-text"><span class="cvt-home-row-title">${esc(__(row.label))}</span>` +
					`</span>${icon("chevron")}</button>`
			)
			.join("");
	}

	// Sales and Collections, Profit and Loss: a column for each series in each month, the month opening its
	// documents. Where the months carry what is left of them (net), it is said under each, in green or red.
	function columns_body(one) {
		const months = one.months || [];
		const series = one.series || [];
		if (!months.length || !series.length) return nothing(__("Nothing to show yet."));
		const most = Math.max(1, ...months.map((month) => Math.max(...(month.values || []).map((v) => Number(v) || 0))));
		const tall = (value) => Math.round((100 * Math.max(0, Number(value) || 0)) / most);
		const net = (value) =>
			`<span class="cvt-home-column-net cvt-band-${Number(value) < 0 ? "overdue" : "good"}">${esc(money(value))}</span>`;
		const chart =
			`<div class="cvt-home-columns${one.net ? " cvt-home-with-net" : ""}">` +
			months
				.map((month, index) => {
					const values = month.values || [];
					const says = series.map((s, at) => `${__(s.label)} ${money_in_full(values[at])}`).join(", ");
					return (
						`<button type="button" class="cvt-home-column" data-cvt-home="month" data-panel="${esc(one.key)}" ` +
						`data-index="${index}" title="${esc(month_words(month) + ": " + says)}">` +
						`<span class="cvt-home-column-bars">${series
							.map((s, at) => `<i class="cvt-band-${esc(s.band || "soon")}" style="height:${tall(values[at])}%"></i>`)
							.join("")}</span>` +
						`<span class="cvt-home-column-label">${esc(month_words(month))}</span>` +
						(one.net ? net(month.net) : `<span class="cvt-home-column-figures">${esc(money(values[0]))}</span>`) +
						`</button>`
					);
				})
				.join("") +
			`</div>`;
		const last = months[months.length - 1];
		const values = last.values || [];
		const summary = one.net
			? `${__(one.net.label || "Profit")} <b>${esc(money(last.net))}</b>` +
			  (one.net.margin != null ? ` · ${esc(__("{0}% of income", [one.net.margin]))}` : "")
			: esc(__("This month so far"));
		const legend =
			`<div class="cvt-home-legend">` +
			series
				.map(
					(s, at) =>
						`<span><i class="cvt-band-${esc(s.band || "soon")}"></i>${esc(__(s.label))} ` +
						`<b>${esc(money(values[at]))}</b></span>`
				)
				.join("") +
			`<span class="cvt-home-legend-figure">${summary}</span></div>`;
		return chart + legend;
	}

	// Receivables and Payables Aging: the whole owed as one bar split by how overdue, each part listed, then who
	// owes, or is owed, the most past due
	function aging_body(one) {
		const buckets = one.buckets || [];
		const whole = buckets.reduce((sum, bucket) => sum + (Number(bucket.value) || 0), 0);
		if (!whole) return nothing(__("Nothing is owed. Every invoice is paid."));
		const split =
			`<div class="cvt-home-split" role="img" aria-label="${esc(__("Owed by days overdue"))}">` +
			buckets
				.filter((bucket) => Number(bucket.value) > 0)
				.map(
					(bucket) =>
						`<i class="cvt-band-${esc(bucket.band)}" style="width:${((100 * Number(bucket.value)) / whole).toFixed(2)}%" ` +
						`title="${esc(__(bucket.label) + ": " + money_in_full(bucket.value))}"></i>`
				)
				.join("") +
			`</div>`;
		const pieces = buckets
			.map(
				(bucket, index) =>
					`<button type="button" class="cvt-home-bucket" data-cvt-home="more" data-panel="${esc(one.key)}" ` +
					`data-part="buckets" data-index="${index}"><span class="cvt-home-dot cvt-band-${esc(bucket.band)}"></span>` +
					`<span class="cvt-home-bar-label">${esc(__(bucket.label))}</span><b>${esc(money(bucket.value))}</b>` +
					`<small>${whole ? Math.round((100 * (Number(bucket.value) || 0)) / whole) : 0}%</small></button>`
			)
			.join("");
		const owing = (one.rows || []).length
			? `<div class="cvt-home-sub">${esc(__(one.owing || "Owing the most past due"))}</div>` +
			  rows(one.rows, "", "more", "rows", one.key)
			: "";
		return `<div class="cvt-home-pad-x">${split}</div><div class="cvt-home-buckets">${pieces}</div>${owing}`;
	}

	// the filled part of a bar: none where there is nothing, not even the sliver the stylesheet keeps for a share
	// too small to see
	function filled(percent, band) {
		return percent > 0 ? `<i class="cvt-band-${esc(band)}" style="width:${percent}%"></i>` : "";
	}

	// Cash and Bank, Top Customers, Top Items, Top Suppliers: bars, each as long as its share of the largest
	function bars_body(one) {
		const all = one.rows || [];
		if (!all.length) return nothing(__(one.empty || "Nothing to show yet."));
		const most = Math.max(1, ...all.map((row) => Math.abs(Number(row.value) || 0)));
		return (
			`<div class="cvt-home-bars">` +
			all
				.map((row, index) => {
					const width = Math.round((100 * Math.abs(Number(row.value) || 0)) / most);
					const figure = one.money ? money(row.value) : one.hours ? hours(row.value) : count(row.value);
					return (
						`<button type="button" class="cvt-home-bar" data-cvt-home="more" data-panel="${esc(one.key)}" ` +
						`data-part="rows" data-index="${index}"${one.money ? ` title="${esc(money_in_full(row.value))}"` : ""}>` +
						`<span class="cvt-home-bar-label">${esc(row.label)}</span>` +
						`<span class="cvt-home-bar-track">${filled(width, row.band || "soon")}</span>` +
						`<b>${esc(figure)}</b></button>`
					);
				})
				.join("") +
			`</div>`
		);
	}

	// the chart colors picked in the settings, the dark set in dark mode; only colors go into a style
	function palette() {
		const charts = (frappe.boot.cyvetech_ui || {}).charts || {};
		const dark = document.documentElement.getAttribute("data-theme") === "dark";
		const chosen = (dark && charts.dark_palette) || charts.palette || [];
		const colors = chosen.filter((color) => /^#[0-9a-fA-F]{6}$/.test(String(color)));
		return colors.length ? colors : ["#2f64b0", "#eb6834", "#1baf7a", "#eaa51a", "#e87ba4", "#008300"];
	}

	// Expenses This Month, Sales by Territory, Stock by Warehouse: a ring of the whole's parts, each listed with
	// its share and opening what it is made of. The rest, put together, is drawn in the quiet gray.
	function donut_body(one) {
		const all = one.rows || [];
		const whole = all.reduce((sum, row) => sum + Math.max(0, Number(row.value) || 0), 0);
		if (!all.length || !whole) return nothing(__(one.empty || "Nothing to show yet."));
		const colors = palette();
		const color_of = (row, index) => (row.key == null ? "var(--cvt-band-none)" : colors[index % colors.length]);
		let at = 0;
		const stops = all
			.map((row, index) => {
				const from = at;
				at += (100 * Math.max(0, Number(row.value) || 0)) / whole;
				return `${color_of(row, index)} ${from.toFixed(2)}% ${at.toFixed(2)}%`;
			})
			.join(", ");
		const ring =
			`<div class="cvt-home-donut"><span class="cvt-home-donut-ring" role="img" ` +
			`aria-label="${esc(all.map((row) => `${row.label}: ${money_in_full(row.value)}`).join(", "))}" ` +
			`style="background: conic-gradient(${stops})"></span>` +
			`<span class="cvt-home-donut-middle"><b>${esc(one.money ? money(whole) : count(whole))}</b>` +
			`<small>${esc(__("in all"))}</small></span></div>`;
		const legend = all
			.map(
				(row, index) =>
					`<button type="button" class="cvt-home-slice" data-cvt-home="more" data-panel="${esc(one.key)}" data-part="rows" ` +
					`data-index="${index}"><i style="background:${color_of(row, index)}"></i>` +
					`<span class="cvt-home-bar-label">${esc(__(row.label))}</span>` +
					`<b>${esc(one.money ? money(row.value) : count(row.value))}</b>` +
					`<small>${Math.round((100 * Math.max(0, Number(row.value) || 0)) / whole)}%</small></button>`
			)
			.join("");
		return `<div class="cvt-home-ring-row">${ring}<div class="cvt-home-slices">${legend}</div></div>`;
	}

	// Quotations: each stage a bar as long as its share of the largest, how many and their worth, and how many of
	// those decided were won
	function stages_body(one) {
		const all = one.stages || [];
		const most = Math.max(1, ...all.map((stage) => Number(stage.value) || 0));
		if (!all.some((stage) => Number(stage.value) > 0)) return nothing(__("No quotations in the last 90 days."));
		const bars = all
			.map(
				(stage, index) =>
					`<button type="button" class="cvt-home-bar cvt-home-stage" data-cvt-home="more" data-panel="${esc(one.key)}" ` +
					`data-part="stages" data-index="${index}" title="${esc(money_in_full(stage.amount))}">` +
					`<span class="cvt-home-bar-label">${esc(__(stage.label))}</span>` +
					`<span class="cvt-home-bar-track">${filled(Math.round((100 * (Number(stage.value) || 0)) / most), stage.band || "soon")}</span>` +
					`<b>${count(stage.value)}</b><small>${esc(money(stage.amount))}</small></button>`
			)
			.join("");
		const won =
			one.won != null
				? `<div class="cvt-home-legend"><span class="cvt-home-legend-figure">` +
				  `${esc(__("Won {0}% of those decided", [one.won]))}</span></div>`
				: "";
		return `<div class="cvt-home-bars">${bars}</div>${won}`;
	}

	// Projects in Progress: each project, when it is due, and how far along it is
	function progress_body(one) {
		const all = one.rows || [];
		if (!all.length) return nothing(__(one.empty || "Nothing here."));
		return all
			.map((row, index) => {
				const done = Math.max(0, Math.min(100, Math.round(Number(row.progress) || 0)));
				return (
					`<button type="button" class="cvt-home-row cvt-home-progress" data-cvt-home="more" data-panel="${esc(one.key)}" ` +
					`data-part="rows" data-index="${index}"><span class="cvt-home-dot cvt-band-${esc(row.band || "none")}"></span>` +
					`<span class="cvt-home-row-text"><span class="cvt-home-row-title">${esc(row.title)}</span>` +
					`<span class="cvt-home-row-meta">${esc(__(row.when || ""))}</span>` +
					`<span class="cvt-home-bar-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${done}">` +
					`${filled(done, "good")}</span></span>` +
					`<b class="cvt-home-percent">${done}%</b>${icon("chevron")}</button>`
				);
			})
			.join("");
	}

	// Orders to Deliver, Purchases to Receive, Work Orders Due, Tasks Due, Open Support Issues, Your Drafts
	function list_body(one) {
		const words = one.progress;
		return rows(
			(one.rows || []).map((row) => Object.assign({ progress_words: words }, row)),
			__(one.empty || "Nothing here."),
			"more",
			"rows",
			one.key
		);
	}

	// Stock to Reorder: each item, where it is kept, and what is expected against its reorder level
	function reorder_body(one) {
		const all = one.rows || [];
		if (!all.length) return nothing(__(one.empty || "Everything is above its reorder level"));
		return all
			.map((row, index) => {
				const level =
					row.level != null
						? __("{0} expected, reorder at {1}", [count(row.projected), count(row.level)])
						: __("{0} expected", [count(row.projected)]);
				return (
					`<button type="button" class="cvt-home-row" data-cvt-home="more" data-panel="${esc(one.key)}" data-part="rows" ` +
					`data-index="${index}"><span class="cvt-home-dot cvt-band-${esc(row.band || "today")}"></span>` +
					`<span class="cvt-home-row-text"><span class="cvt-home-row-title">${esc(row.title)}</span>` +
					`<span class="cvt-home-row-meta">${esc([row.warehouse, level].filter(Boolean).join(" · "))}</span></span>` +
					`${icon("chevron")}</button>`
				);
			})
			.join("");
	}

	const KINDS = {
		attention: attention_body,
		columns: columns_body,
		aging: aging_body,
		bars: bars_body,
		donut: donut_body,
		stages: stages_body,
		progress: progress_body,
		list: list_body,
		reorder: reorder_body,
	};

	// ── The tabs ────────────────────────────────────────────────────────────

	// how much needs attention on a tab, as the overview read it
	function badge_of(key) {
		const badges = (parts[OVERVIEW] && parts[OVERVIEW].badges) || {};
		return badges[key] || null;
	}

	// a tab for each module the user has, the overview first: each says how much needs attention in it
	function tab_bar(data) {
		const all = data.tabs || [];
		if (all.length < 2) return "";
		return (
			`<nav class="cvt-home-tabbar" role="tablist" aria-label="${esc(__("Dashboards"))}">` +
			all
				.map((one) => {
					const on = one.key === current;
					const badge = badge_of(one.key);
					const says = badge && badge.value ? __("{0} need attention", [count(badge.value)]) : "";
					return (
						`<button type="button" role="tab" id="cvt-home-tab-${esc(one.key)}" class="cvt-home-tabbtn${on ? " cvt-on" : ""}" ` +
						`data-cvt-home="open" data-tab="${esc(one.key)}" aria-selected="${on ? "true" : "false"}" ` +
						`aria-controls="cvt-home-tabpanel" tabindex="${on ? "0" : "-1"}"${says ? ` title="${esc(says)}"` : ""}>` +
						`${icon(one.icon)}<span>${esc(__(one.title))}</span>` +
						(badge && badge.value
							? `<i class="cvt-home-badge cvt-band-${esc(badge.band || "none")}" aria-label="${esc(says)}">${count(badge.value)}</i>`
							: "") +
						`</button>`
					);
				})
				.join("") +
			`</nav>`
		);
	}

	// The heading of the tab open now: what it is, when its figures were read with a way to read them again,
	// and for a module, the way into the module itself
	function tab_head(data, open) {
		const workspace = (open.workspaces || []).find((name) => nav.tile_path(name));
		const into = workspace
			? `<button type="button" class="cvt-home-into" data-cvt-home="module" data-workspace="${esc(workspace)}">` +
			  `<span>${esc(__("Open {0}", [__(workspace)]))}</span>${icon("arrow")}</button>`
			: "";
		const title = open.key === OVERVIEW ? __("Overview") : __("{0} Dashboard", [__(open.title)]);
		const under = open.key === OVERVIEW ? __("The day at a glance, across your modules") : data.company || "";
		return (
			`<div class="cvt-home-tabhead"><div class="cvt-home-tabhead-text"><h3>${esc(title)}</h3>` +
			(under ? `<p>${esc(under)}</p>` : "") +
			`</div><div class="cvt-home-tabhead-side">${stamp(open.key)}${into}</div></div>`
		);
	}

	// the reports a decision is made from, each opening for the user's company
	function reports_panel(open) {
		const all = open.reports || [];
		if (!all.length) return "";
		return (
			`<section class="cvt-home-panel cvt-home-reports" data-panel="reports"><header>` +
			`<span class="cvt-home-panel-icon">${icon("reports")}</span><h3>${esc(__("Reports"))}</h3>` +
			`<span class="cvt-home-panel-note">${esc(__("For a closer look"))}</span></header>` +
			`<div class="cvt-home-list cvt-home-report-list">${all
				.map(
					(report, index) =>
						`<button type="button" class="cvt-home-row cvt-home-report" data-cvt-home="report" data-index="${index}">` +
						`<span class="cvt-home-row-text"><span class="cvt-home-row-title">${esc(__(report.label))}</span></span>` +
						`${icon("chevron")}</button>`
				)
				.join("")}</div></section>`
		);
	}

	// the tab open now: its heading, its figures, its dashboards and its reports
	function tab_panel(data) {
		const open = tab_of(current) || (data.tabs || [])[0];
		if (!open) return "";
		const blocks = (open.key === OVERVIEW ? [waiting_panel(data)] : [])
			.concat((open.panels || []).map((item) => one_panel(item)))
			.concat([reports_panel(open)])
			.filter(Boolean);
		return (
			`<div class="cvt-home-tabpanel" id="cvt-home-tabpanel" role="tabpanel" aria-labelledby="cvt-home-tab-${esc(open.key)}">` +
			tab_head(data, open) +
			cards(data) +
			(blocks.length ? `<div class="cvt-home-grid">${blocks.join("")}</div>` : "") +
			`</div>`
		);
	}

	// when the figures of a tab were read, and a way to read them again
	function stamp(key) {
		const times = [parts[key], key === OVERVIEW ? parts.cards : null]
			.filter(Boolean)
			.map((part) => part.at)
			.filter(Boolean)
			.sort();
		if (!times.length) return "";
		const busy = !!(parts_asking[key] || (key === OVERVIEW && parts_asking.cards));
		return (
			`<span class="cvt-home-stamp"><span>${esc(__("As of {0}", [time_words(times[0])]))}</span>` +
			`<button type="button" class="cvt-home-refresh${busy ? " cvt-busy" : ""}" data-cvt-home="refresh">${icon("refresh")}` +
			`<span>${esc(__("Refresh"))}</span></button></span>`
		);
	}

	// scrolled: how far along the tab bar was scrolled before it was drawn again
	function draw(home, scrolled) {
		const data = answer;
		if (!data) {
			home.innerHTML = skeleton();
			return;
		}
		home.innerHTML = hero(data) + shortcuts(data) + tab_bar(data) + tab_panel(data);
		const bar = home.querySelector(".cvt-home-tabbar");
		if (bar) reveal(bar, scrolled || 0);
	}

	// A tab bar wider than the screen scrolls sideways. It stays where the viewer left it, unless the open tab is
	// out of sight there: then it moves just far enough to show it.
	function reveal(bar, scrolled) {
		bar.scrollLeft = scrolled;
		const on = bar.querySelector(".cvt-home-tabbtn.cvt-on");
		if (!on || bar.scrollWidth <= bar.clientWidth) return;
		const edge = parseFloat(getComputedStyle(bar).paddingLeft) || 0;
		const start = on.offsetLeft - edge;
		const end = on.offsetLeft + on.offsetWidth + edge;
		if (start < bar.scrollLeft) bar.scrollLeft = start;
		else if (end > bar.scrollLeft + bar.clientWidth) bar.scrollLeft = end - bar.clientWidth;
	}

	// a route the server names, opened as Frappe opens it: a list on its filters, a report or page on its options
	function go(target) {
		if (!target || !target.route) return;
		const route = target.route.slice();
		const filters = Object.assign({}, target.filters || {});
		if (target.mine && route[1] === "ToDo") Object.assign(filters, { allocated_to: frappe.session.user, status: "Open" });
		if (target.mine && route[1] === "Notification Log") Object.assign(filters, { for_user: frappe.session.user, read: 0 });
		if (route[0] === "List" && Object.keys(filters).length) frappe.route_options = filters;
		else if (target.options) frappe.route_options = Object.assign({}, target.options);
		frappe.set_route(route);
	}

	function clicked(event) {
		const element = event.target.closest("[data-cvt-home]");
		if (!element || !answer) return;
		try {
			act(element);
		} catch (error) {
			console.error(error);
		}
	}

	// The tab bar as a row of tabs is worked by the keyboard (the WAI-ARIA tabs pattern): the arrows move to the
	// next tab and open it, Home and End to the first and the last.
	function keyed(event) {
		const button = event.target.closest(".cvt-home-tabbtn");
		if (!button || !answer) return;
		const all = (answer.tabs || []).map((one) => one.key);
		const at = all.indexOf(button.getAttribute("data-tab"));
		const to = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: all.length - 1 }[event.key];
		if (to == null || at < 0) return;
		event.preventDefault();
		open_tab(all[(to + all.length) % all.length], true);
	}

	function act(element) {
		const data = answer;
		const what = element.getAttribute("data-cvt-home");
		const index = Number(element.getAttribute("data-index"));
		if (what === "tab") {
			tab = element.getAttribute("data-tab") === "notes" ? "notes" : "items";
			redraw();
		} else if (what === "open") {
			open_tab(element.getAttribute("data-tab"), false);
		} else if (what === "todo") go({ route: ["List", "ToDo"], mine: 1 });
		else if (what === "new") {
			const doctype = element.getAttribute("data-doctype");
			if (creatable(doctype)) frappe.new_doc(doctype);
		} else if (what === "visit") {
			const link = visited(data)[index];
			if (link) frappe.set_route(link.route);
		} else if (what === "card") {
			const key = element.getAttribute("data-key");
			go(tab_cards(data).find((one) => one.key === key && !one.frame));
		} else if (what === "waiting") {
			const row = ((tab === "notes" ? data.waiting.notes : data.waiting.items) || [])[index];
			if (row && row.doctype && row.docname) frappe.set_route("Form", row.doctype, row.docname);
			else go({ route: ["List", "ToDo"], mine: 1 });
		} else if (what === "more") {
			// a row of one of the dashboards: the record it names, else the list or report it opens on
			const one = panel_of(element.getAttribute("data-panel"));
			const row = one && (one[element.getAttribute("data-part") || "rows"] || [])[index];
			if (!row) return;
			if (row.doctype && row.docname) frappe.set_route("Form", row.doctype, row.docname);
			else if (row.route) go(row);
			else if (row.filters && one.route) go({ route: one.route, filters: Object.assign({}, one.filters, row.filters) });
		} else if (what === "month") {
			const one = panel_of(element.getAttribute("data-panel"));
			const month = one && (one.months || [])[index];
			if (month && one.route && one.day) {
				go({ route: one.route, filters: Object.assign({}, one.filters, { [one.day]: ["between", [month.from, month.to]] }) });
			} else if (month && one.route) {
				go({ route: one.route, options: Object.assign({}, one.options, { from_date: month.from, to_date: month.to }) });
			}
		} else if (what === "all") {
			const one = panel_of(element.getAttribute("data-panel"));
			if (one) go(one);
		} else if (what === "report") {
			const open = tab_of(current);
			const report = open && (open.reports || [])[index];
			if (report) go({ route: report.route, options: data.company ? { company: data.company } : null });
		} else if (what === "module") {
			const workspace = element.getAttribute("data-workspace");
			const path = workspace && nav.tile_path(workspace);
			if (path) nav.follow(path, workspace);
		} else if (what === "refresh") {
			load_parts(true);
		}
	}

	// another tab opened: drawn at once, its figures asked for if they are not here yet
	function open_tab(key, focus) {
		if (!tab_of(key)) return;
		current = key;
		keep_tab();
		redraw();
		load_parts(false);
		if (focus) {
			const button = document.getElementById("cvt-home-tab-" + key);
			if (button) button.focus();
		}
	}

	function redraw() {
		try {
			const wrapper = desk();
			const home = present() ? wrapper.querySelector(".cvt-home") : null;
			if (home && answer) {
				// the tab bar scrolled to where the viewer left it, not back to its start
				const bar = home.querySelector(".cvt-home-tabbar");
				draw(home, bar ? bar.scrollLeft : 0);
			}
		} catch (error) {
			console.error(error);
		}
	}

	// fetch, not frappe.call: a call that fails must leave the desk alone, and frappe.call would open Frappe's
	// Server Error dialog on the page everybody lands on
	function ask(method, query) {
		return fetch("/api/method/" + method + (query || ""), {
			credentials: "same-origin",
			cache: "no-store",
			headers: { Accept: "application/json" },
		})
			.then((response) => (response.ok ? response.json() : null))
			.then((r) => (r && r.message) || null)
			.catch(() => null);
	}

	function load() {
		if (asking || Date.now() - asked_at < FRESH_MS) return;
		asking = true;
		ask(SUMMARY).then((data) => {
			const first = !answer;
			answer = data || answer;
			asked_at = Date.now(); // a call that failed is tried again later, not at once
			asking = false;
			if (answer && first) {
				current = first_tab(answer);
				keep_tab();
			}
			try {
				const there = mount();
				if (there && answer) draw(there);
				else if (there && !answer) unmount(desk()); // nothing to show: the desk as Frappe drew it
			} catch (error) {
				console.error(error);
			}
			load_parts(false);
		});
	}

	// What the tab open now needs, and the overview's figures, which say how much needs attention on each tab.
	// Refresh asks the server to read again each part already read.
	function load_parts(fresh) {
		if (!answer) return;
		const wanted = [OVERVIEW, current];
		if (current === OVERVIEW && (answer.cards || []).some((one) => one.frame)) wanted.push("cards");
		const again = fresh ? Object.keys(parts) : [];
		Array.from(new Set(wanted.concat(again))).forEach((part) => load_part(part, fresh));
	}

	// One part's figures, by fetch for the same reason as the summary. A call that fails leaves no dashboard
	// where its frames were, and is tried again later.
	function load_part(part, fresh) {
		if (!answer || parts_asking[part]) return;
		const had = parts[part];
		if (!fresh && had && Date.now() - had.time < FRESH_MS) return;
		if (part !== "cards" && !tab_of(part)) return;
		parts_asking[part] = true;
		if (fresh) redraw(); // the refresh turns while it reads
		ask(FIGURES, "?part=" + encodeURIComponent(part) + (fresh ? "&fresh=1" : "")).then((data) => {
			let read;
			if (!data) read = had || { cards: [], panels: [] };
			else if (part === "cards") read = { cards: data.cards || [] };
			else read = Object.assign({ cards: [], panels: [] }, (data.tabs || {})[part] || {});
			parts[part] = Object.assign(read, { at: (data && data.at) || (had && had.at), currency: data && data.currency, time: Date.now() });
			parts_asking[part] = false;
			redraw();
		});
	}

	function show() {
		try {
			// the last call failed: the desk stays as Frappe drew it until it is worth asking again
			if (!answer && asked_at && Date.now() - asked_at < FRESH_MS) return true;
			style();
			const home = mount();
			if (!home) return false;
			draw(home);
			load();
			load_parts(false);
			return true;
		} catch (error) {
			console.error(error);
			return true; // do not keep trying something that throws
		}
	}

	function on_desk() {
		try {
			return (frappe.get_route() || [])[0] === "desktop" || !!document.querySelector(".desktop-wrapper");
		} catch (e) {
			return false;
		}
	}

	// Frappe draws its desk page as the route settles, so the tiles may not be there yet when the page changes:
	// look a few times, then leave it. It draws the desk afresh after "page-change" each time the page is come
	// back to, which takes the home off again: so it looks a few times more than it takes to find the desk, and
	// puts the home back where it is missing.
	function arrive() {
		if (!on_desk()) return;
		follow_request();
		let tries = 0;
		const look = () => {
			tries += 1;
			const there = present() || show();
			// measured again each time: the page may not have been laid out yet when the home went on
			if (there) measure();
			if (tries < 12 && (!there || tries < 5)) setTimeout(look, 150 * tries);
		};
		look();
	}

	// Frappe says when it has drawn the desk (desktop.js setup: "desktop_screen"): the home goes on at once, and is
	// measured again once Frappe has done what it does after. Frappe means a page it shows to open at its top, but
	// scrolls the window, and the desk scrolls in a pane of its own: come back to, it was shown as far down as the
	// module left it.
	function drawn_again() {
		try {
			if (!on_desk()) return;
			if (!present()) show();
			const wrapper = desk();
			const pane = wrapper && wrapper.closest(".main-section");
			if (pane) pane.scrollTop = 0;
			setTimeout(measure, 0);
		} catch (error) {
			console.error(error);
		}
	}

	// how far in the desk sits, wherever the home is on it
	function measure() {
		const wrapper = desk();
		if (wrapper && wrapper.classList.contains("cvt-has-home")) bleed(wrapper);
	}

	let measuring = null;
	function resized() {
		clearTimeout(measuring);
		measuring = setTimeout(measure, 150);
	}

	cyvetech_ui.home.show = arrive;
	cyvetech_ui.home.refresh = () => load_parts(true);
	$(document).on("page-change", arrive);
	$(document).on("desktop_screen", drawn_again);
	$(window).on("resize", resized);
	$(arrive);
})();
