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

	let answer = null; // the summary: the greeting, what waits, which figures and panels
	let asked_at = 0;
	let asking = false;
	let more = null; // the figures: {"cards": [...], "panels": [...], "at", "currency"}
	let more_at = 0;
	let more_asking = false;
	let tab = "items";
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
		return (more && more.currency) || (answer && answer.currency) || "";
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

	// a business figure as the server read it, once it has
	function card_of(key) {
		return ((more && more.cards) || []).find((one) => one.key === key) || null;
	}

	// The figures across the top: the user's own work is there at once, a business figure as a frame until it
	// is read, and not at all where it could not be.
	function shown_cards(data) {
		return (data.cards || [])
			.map((one) => (one.frame ? (more ? card_of(one.key) : one) : one))
			.filter(Boolean);
	}

	function figure_of(card) {
		return card.kind === "money" ? money(card.value) : count(card.value);
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
		const all = shown_cards(data);
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
			`<section class="cvt-home-panel cvt-home-waiting"><header><span class="cvt-home-panel-icon">${icon("waiting")}</span>` +
			`<h3>${esc(__("Waiting for You"))}</h3><span class="cvt-home-tabs">${tabs}</span></header>` +
			`<div class="cvt-home-list">${rows(
				shown,
				tab === "notes" ? __("Nothing unread.") : __("Nothing is waiting for you."),
				"waiting"
			)}</div></section>`
		);
	}

	// ── The panels (home.py figures) ────────────────────────────────────────
	// Each comes with the summary as {key, title, place}, and its figures in the second call: the greeting and
	// what waits are never held up by them. A panel is drawn as a frame while its figures are on their way, and
	// not at all where they could not be read.

	function panel_of(key) {
		return ((more && more.panels) || []).find((one) => one.key === key) || null;
	}

	function placed(data, place) {
		return (data.panels || []).filter((item) => item.place === place);
	}

	function one_panel(item, wide) {
		if (!more) return frame_panel(item, wide);
		const one = panel_of(item.key);
		return one ? draw_panel(one, wide) : "";
	}

	function frame_panel(item, wide) {
		return (
			`<section class="cvt-home-panel${wide ? " cvt-home-wide" : ""}" data-panel="${esc(item.key)}"><header>` +
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

	// Sales and Collections: a column for each series in each month, the month opening its documents
	function columns_body(one) {
		const months = one.months || [];
		const series = one.series || [];
		if (!months.length || !series.length) return nothing(__("Nothing to show yet."));
		const most = Math.max(1, ...months.map((month) => Math.max(...(month.values || []).map((v) => Number(v) || 0))));
		const tall = (value) => Math.round((100 * Math.max(0, Number(value) || 0)) / most);
		const chart =
			`<div class="cvt-home-columns">` +
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
						`<span class="cvt-home-column-figures">${esc(money(values[0]))}</span></button>`
					);
				})
				.join("") +
			`</div>`;
		const last = months[months.length - 1].values || [];
		const legend =
			`<div class="cvt-home-legend">` +
			series
				.map(
					(s, at) =>
						`<span><i class="cvt-band-${esc(s.band || "soon")}"></i>${esc(__(s.label))} ` +
						`<b>${esc(money(last[at]))}</b></span>`
				)
				.join("") +
			`<span class="cvt-home-legend-figure">${esc(__("This month so far"))}</span></div>`;
		return chart + legend;
	}

	// Receivables Aging: the whole owed as one bar split by how overdue, each part listed, then who owes the most
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
		const parts = buckets
			.map(
				(bucket, index) =>
					`<button type="button" class="cvt-home-bucket" data-cvt-home="more" data-panel="${esc(one.key)}" ` +
					`data-part="buckets" data-index="${index}"><span class="cvt-home-dot cvt-band-${esc(bucket.band)}"></span>` +
					`<span class="cvt-home-bar-label">${esc(__(bucket.label))}</span><b>${esc(money(bucket.value))}</b>` +
					`<small>${whole ? Math.round((100 * (Number(bucket.value) || 0)) / whole) : 0}%</small></button>`
			)
			.join("");
		const owing = (one.rows || []).length
			? `<div class="cvt-home-sub">${esc(__("Owing the most past due"))}</div>` + rows(one.rows, "", "more", "rows", one.key)
			: "";
		return `<div class="cvt-home-pad-x">${split}</div><div class="cvt-home-buckets">${parts}</div>${owing}`;
	}

	// Cash and Bank, Top Customers: bars, each as long as its share of the largest
	function bars_body(one) {
		const all = one.rows || [];
		if (!all.length) return nothing(__(one.empty || "Nothing to show yet."));
		const most = Math.max(1, ...all.map((row) => Math.abs(Number(row.value) || 0)));
		return (
			`<div class="cvt-home-bars">` +
			all
				.map((row, index) => {
					const width = Math.round((100 * Math.abs(Number(row.value) || 0)) / most);
					const figure = one.money ? money(row.value) : count(row.value);
					return (
						`<button type="button" class="cvt-home-bar" data-cvt-home="more" data-panel="${esc(one.key)}" ` +
						`data-part="rows" data-index="${index}"${one.money ? ` title="${esc(money_in_full(row.value))}"` : ""}>` +
						`<span class="cvt-home-bar-label">${esc(row.label)}</span>` +
						`<span class="cvt-home-bar-track"><i class="cvt-band-${esc(row.band || "soon")}" style="width:${width}%"></i></span>` +
						`<b>${esc(figure)}</b></button>`
					);
				})
				.join("") +
			`</div>`
		);
	}

	// Orders to Deliver, Purchases to Receive, Work Orders Due, Tasks Due, Your Drafts
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
		list: list_body,
		reorder: reorder_body,
	};

	// what waits for the user, and what needs attention beside it
	function first_row(data) {
		const beside = placed(data, "beside")
			.map((item) => one_panel(item, false))
			.filter(Boolean);
		return `<div class="cvt-home-panels${beside.length ? "" : " cvt-home-one"}">${waiting_panel(data)}${beside.join("")}</div>`;
	}

	function wide_row(data) {
		return placed(data, "wide")
			.map((item) => one_panel(item, true))
			.join("");
	}

	function grid_row(data) {
		const blocks = placed(data, "grid")
			.map((item) => one_panel(item, false))
			.filter(Boolean);
		if (!blocks.length) return "";
		const across = blocks.length > 2 ? "three" : blocks.length > 1 ? "two" : "one";
		return `<div class="cvt-home-panels cvt-home-grid cvt-home-${across}">${blocks.join("")}</div>`;
	}

	// when the figures were read, and a way to read them again
	function stamp() {
		if (!more || !more.at) return "";
		return (
			`<div class="cvt-home-stamp"><span>${esc(__("Figures as of {0}", [time_words(more.at)]))}</span>` +
			`<button type="button" class="cvt-home-refresh" data-cvt-home="refresh">${icon("refresh")}` +
			`<span>${esc(__("Refresh"))}</span></button></div>`
		);
	}

	function draw(home) {
		const data = answer;
		if (!data) {
			home.innerHTML = skeleton();
			return;
		}
		home.innerHTML =
			hero(data) + cards(data) + shortcuts(data) + first_row(data) + wide_row(data) + grid_row(data) + stamp();
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

	function act(element) {
		const data = answer;
		const what = element.getAttribute("data-cvt-home");
		const index = Number(element.getAttribute("data-index"));
		if (what === "tab") {
			tab = element.getAttribute("data-tab") === "notes" ? "notes" : "items";
			redraw();
		} else if (what === "todo") go({ route: ["List", "ToDo"], mine: 1 });
		else if (what === "new") {
			const doctype = element.getAttribute("data-doctype");
			if (creatable(doctype)) frappe.new_doc(doctype);
		} else if (what === "visit") {
			const link = visited(data)[index];
			if (link) frappe.set_route(link.route);
		} else if (what === "card") {
			const key = element.getAttribute("data-key");
			go(shown_cards(data).find((one) => one.key === key && !one.frame));
		} else if (what === "waiting") {
			const row = ((tab === "notes" ? data.waiting.notes : data.waiting.items) || [])[index];
			if (row && row.doctype && row.docname) frappe.set_route("Form", row.doctype, row.docname);
			else go({ route: ["List", "ToDo"], mine: 1 });
		} else if (what === "more") {
			// a row of one of the panels: the record it names, else the list or report it opens on
			const one = panel_of(element.getAttribute("data-panel"));
			const row = one && (one[element.getAttribute("data-part") || "rows"] || [])[index];
			if (!row) return;
			if (row.doctype && row.docname) frappe.set_route("Form", row.doctype, row.docname);
			else if (row.route) go(row);
			else if (row.filters && one.route) go({ route: one.route, filters: Object.assign({}, one.filters, row.filters) });
		} else if (what === "month") {
			const one = panel_of(element.getAttribute("data-panel"));
			const month = one && (one.months || [])[index];
			if (month && one.route) {
				go({ route: one.route, filters: Object.assign({}, one.filters, { [one.day]: ["between", [month.from, month.to]] }) });
			}
		} else if (what === "all") {
			const one = panel_of(element.getAttribute("data-panel"));
			if (one) go(one);
		} else if (what === "refresh") {
			load_figures(true);
		}
	}

	function redraw() {
		try {
			const wrapper = desk();
			const home = present() ? wrapper.querySelector(".cvt-home") : null;
			if (home && answer) draw(home);
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
			answer = data || answer;
			asked_at = Date.now(); // a call that failed is tried again later, not at once
			asking = false;
			try {
				const there = mount();
				if (there && answer) draw(there);
				else if (there && !answer) unmount(desk()); // nothing to show: the desk as Frappe drew it
			} catch (error) {
				console.error(error);
			}
			load_figures(false);
		});
	}

	// The figures, once the home is drawn, by fetch for the same reason as the summary. A call that fails leaves
	// no panel where the frames were, and is tried again later. Refresh asks the server to read them afresh.
	function load_figures(fresh) {
		if (more_asking || !answer) return;
		if (!fresh && Date.now() - more_at < FRESH_MS) return;
		const wanted = (answer.panels || []).length || (answer.cards || []).some((one) => one.frame);
		if (!wanted) return;
		more_asking = true;
		const refresh = document.querySelector(".cvt-home-refresh");
		if (refresh) refresh.classList.add("cvt-busy");
		ask(FIGURES, fresh ? "?fresh=1" : "").then((data) => {
			more = data || more || { cards: [], panels: [] };
			more_at = Date.now();
			more_asking = false;
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
			load_figures(false);
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
	cyvetech_ui.home.refresh = () => load_figures(true);
	$(document).on("page-change", arrive);
	$(document).on("desktop_screen", drawn_again);
	$(window).on("resize", resized);
	$(arrive);
})();
