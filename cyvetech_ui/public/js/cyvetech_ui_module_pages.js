// CyveTech UI — the module pages.
//
// The desk home (cyvetech_ui_home.js) opens on a greeting, the day's figures and
// what waits for the user; a module opened from it was Frappe's own workspace, in
// another look. This gives every module's page the home's look: a header of its own
// (the module's picture and name, the groups of its menu, what needs attention in
// it, where it falls in the flow from a lead to the money, what waits for the user
// there and a button to make the document most made there), over ERPNext's own
// charts, figures and cards, drawn as the home draws its panels.
//
// Its look is HRMS Addon's module pages (hrms_addon_module_pages.js).
//
// WHAT IT MUST NEVER DO
//
// Stop a module opening, or change what is on its page. Everything here is inside
// try/catch; ERPNext's blocks are restyled and never rewritten, and the header is
// added beside them. While a workspace is being edited its page is exactly Frappe's.
// CyveTech UI Settings > Home switches it off without a deploy. On a site where HRMS
// Addon's own module pages are on, this stands aside.
//
// The styles are public/css/cyvetech_ui_home.css, and every color in them comes
// from the settings.

(function () {
	if (typeof frappe === "undefined" || !frappe.boot) return;
	const conf = (frappe.boot.cyvetech_ui || {}).module_pages || {};
	if (!conf.enabled) return;
	if (frappe.boot.user && frappe.boot.user.name === "Guest") return;
	// HRMS Addon draws module pages of its own: two headers would stack on one page
	if (frappe.boot.hrms_addon_module_pages) return;
	// Frappe v16's workspaces, whose menus the boot carries; v15's have none to draw from
	if (!frappe.boot.workspace_sidebar_item) return;
	const nav = window.cyvetech_ui && cyvetech_ui.nav;
	if (!nav) return;
	frappe.provide("cyvetech_ui.module_pages");

	const METHOD = "cyvetech_ui.cyvetech_ui.module_pages.summary";
	const FRESH_MS = 60 * 1000; // how long an answer is shown before it is asked for again
	const ON = "cvt-mod-on"; // on <html>: every module page style holds only while it is there
	// the steps from a lead to the money (home_rules.FLOW)
	const FLOW = Array.isArray(conf.flow) ? conf.flow : [];
	// where each module's work usually starts (module_pages_rules.ACTIONS)
	const ACTIONS = conf.actions || {};
	// an app's light picture of a module (/assets/<app>/icons/desktop_icons/subtle/, as Frappe's
	// get_desktop_icon names them), whose glyph the header draws in the theme's colors
	const GLYPHS_AT = /\/icons\/desktop_icons\/subtle\/[^/]+\.svg$/;
	const answers = {}; // each workspace's answer: { data, at }
	const asking = {};
	let tab = "items";

	const ICONS = {
		waiting:
			'<path d="M4 13.5h4l1.5 2.5h5l1.5-2.5h4"/><path d="M6.2 5.5h11.6L20 13.5V18a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18v-4.5z"/>',
		plus: '<path d="M12 5.5v13M5.5 12h13"/>',
		chevron: '<path d="M9 6l6 6-6 6"/>',
		back: '<path d="M15 6l-6 6 6 6"/>',
		folder:
			'<path d="M4 7.5A1.5 1.5 0 0 1 5.5 6h4l2 2.2h7A1.5 1.5 0 0 1 20 9.7v8.8a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 18.5z"/>',
		attention: '<path d="M12 4l9 16H3z"/><path d="M12 10v4.2M12 17.2v.3"/>',
	};

	function icon(name) {
		return (
			'<svg class="cvt-mod-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" ' +
			`stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.folder}</svg>`
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

	// Frappe's workspace page as it is on the screen now
	function page_now() {
		const all = Array.from(document.querySelectorAll('.page-container[data-page-route="Workspaces"]'));
		return all.find((page) => page.offsetParent !== null) || null;
	}

	// the workspace that page shows: Frappe names it as it starts drawing it (workspace.js show_page)
	function shown() {
		const page = frappe.workspace && frappe.workspace._page;
		return page && page.name ? page : null;
	}

	// the headings of the module's menu with something under them: what the module holds
	function groups_of(name) {
		const items = ((nav.sidebar_of(name) || {}).items || []).filter((item) => item && !item.hidden);
		return items
			.filter((item, index) => item.type === "Section Break" && items[index + 1] && items[index + 1].type !== "Section Break")
			.map((item) => item.label)
			.filter(Boolean);
	}

	// a module the user may open: its tile leads somewhere they may go
	function may_open(name) {
		return !!nav.tile_path(name);
	}

	// The step of the flow a module is, or the folder it sits in on the desk is: Invoicing and Payments are
	// in Accounting.
	function step_of(name) {
		if (FLOW.includes(name)) return name;
		const tile = (frappe.boot.desktop_icons || []).find((one) => one && one.label === name);
		return tile && FLOW.includes(tile.parent_icon) ? tile.parent_icon : null;
	}

	// where the module falls in the flow, and the nearest step either side the user may open
	function stage_of(name) {
		const step = step_of(name);
		if (!step) return null;
		const index = FLOW.indexOf(step);
		const open = FLOW.map((module) => module !== step && may_open(module));
		let before = null;
		let after = null;
		for (let at = index - 1; at >= 0 && !before; at -= 1) if (open[at]) before = FLOW[at];
		for (let at = index + 1; at < FLOW.length && !after; at += 1) if (open[at]) after = FLOW[at];
		return { index: index, open: open, before: before, after: after };
	}

	// the document the header offers to make, for somebody who may make it: the one the user makes most in the
	// module, once the server has said, else where the module's work usually starts
	function action_of(name) {
		const answer = answers[name];
		const doctype = (answer && answer.data && answer.data.action) || ACTIONS[name];
		try {
			return doctype && frappe.model.can_create(doctype) ? doctype : null;
		} catch (error) {
			return null;
		}
	}

	// what the server said about the module: null until it has, or where it could not say
	function data_of(name) {
		const answer = answers[name];
		return answer && answer.data ? answer.data : null;
	}

	// The module's picture. Where the app ships one, its glyph (the light version of the tile's picture, used as
	// a mask) is drawn on a disc of the header's color ringed in the highlight, so it takes the colors picked in
	// the settings as the rest of the header does. Else the tile's own picture, else the workspace's icon.
	function picture(page) {
		let glyph = false;
		let address = false;
		try {
			glyph = frappe.utils.get_desktop_icon(page.name, "subtle");
			if (!GLYPHS_AT.test(String(glyph || ""))) glyph = false;
			address = glyph ? false : frappe.utils.get_desktop_icon(page.name, "solid");
		} catch (error) {
			glyph = address = false;
		}
		if (glyph) return `<span class="cvt-mod-picture cvt-mod-glyph"><i style="--cvt-m-glyph: url('${esc(glyph)}')"></i></span>`;
		if (address) return `<span class="cvt-mod-picture"><img src="${esc(address)}" alt=""></span>`;
		let drawn = icon("folder");
		try {
			if (page.icon) drawn = frappe.utils.icon(page.icon, "lg");
		} catch (error) {
			drawn = icon("folder");
		}
		return `<span class="cvt-mod-picture cvt-mod-drawn">${drawn}</span>`;
	}

	// the steps from the first to the last, this one marked, each the user may open one click away
	function track(stage) {
		const steps = FLOW.map((module, index) => {
			const now = index === stage.index;
			const state = now ? " cvt-now" : index < stage.index ? " cvt-done" : "";
			const label = esc(__(module));
			return stage.open[index]
				? `<button type="button" class="cvt-mod-step${state}" data-cvt-mod="go" data-module="${esc(module)}" ` +
						`title="${label}" aria-label="${label}"></button>`
				: `<span class="cvt-mod-step${state}" title="${label}"${now ? ' aria-current="step"' : ""}></span>`;
		}).join("");
		const near = (module, back) =>
			module
				? `<button type="button" class="cvt-mod-near" data-cvt-mod="go" data-module="${esc(module)}">` +
				  (back ? `${icon("back")}<span>${esc(__(module))}</span>` : `<span>${esc(__(module))}</span>${icon("chevron")}`) +
				  `</button>`
				: "";
		return (
			`<div class="cvt-mod-track"><span class="cvt-mod-steps">${steps}</span>` +
			`<span class="cvt-mod-stage">${esc(__("Step {0} of {1}, lead to cash", [stage.index + 1, FLOW.length]))}</span>` +
			`<span class="cvt-mod-nears">${near(stage.before, true)}${near(stage.after, false)}</span></div>`
		);
	}

	// what needs attention in the module, each opening its list
	function flags(data) {
		const all = (data && data.attention) || [];
		if (!all.length) return "";
		return (
			`<div class="cvt-mod-flags">` +
			all
				.map(
					(row, index) =>
						`<button type="button" class="cvt-mod-flag cvt-band-${esc(row.band || "none")}" data-cvt-mod="flag" ` +
						`data-index="${index}"><b>${count(row.value)}</b><span>${esc(__(row.label))}</span>${icon("chevron")}</button>`
				)
				.join("") +
			`</div>`
		);
	}

	function hero(page) {
		const name = page.name;
		const groups = groups_of(name);
		const stage = stage_of(name);
		const data = data_of(name);
		const waits = data && data.waiting;
		const doctype = action_of(name);
		const chip = waits
			? `<button type="button" class="cvt-mod-chip" data-cvt-mod="waiting">${icon("waiting")}` +
			  `<span><b>${count(waits.tasks)}</b><small>${esc(__("Waiting for you"))}</small></span></button>`
			: answers[name]
			? ""
			: `<span class="cvt-mod-chip cvt-mod-asking" aria-hidden="true"><span class="cvt-mod-bone"></span></span>`;
		const make = doctype
			? `<button type="button" class="cvt-mod-action" data-cvt-mod="new" data-doctype="${esc(doctype)}">${icon("plus")}` +
			  `<span>${esc(__("New {0}", [__(doctype)]))}</span></button>`
			: "";
		return (
			`<section class="cvt-mod-hero">${picture(page)}` +
			`<div class="cvt-mod-hero-text"><h2>${esc(__(page.title || name))}</h2>` +
			(groups.length ? `<p>${groups.map((group) => esc(__(group))).join(" · ")}</p>` : "") +
			flags(data) +
			(stage ? track(stage) : "") +
			`</div>` +
			(chip || make ? `<div class="cvt-mod-hero-side">${chip}${make}</div>` : "") +
			`</section>`
		);
	}

	function row(item, index, list) {
		const meta = [item.doctype ? __(item.doctype) : "", item.docname, item.when ? __(item.when) : ""]
			.filter(Boolean)
			.map(esc)
			.join(" · ");
		return (
			`<button type="button" class="cvt-mod-row" data-cvt-mod="row" data-list="${list}" data-index="${index}">` +
			`<span class="cvt-mod-dot cvt-band-${esc(item.band || "none")}"></span>` +
			`<span class="cvt-mod-row-text"><span class="cvt-mod-row-title">${esc(item.title)}</span>` +
			`<span class="cvt-mod-row-meta">${meta}</span></span>${item.doctype && item.docname ? icon("chevron") : ""}</button>`
		);
	}

	// what waits for the user among the module's documents, as the desk home lists it; nothing when nothing waits
	function panel(page) {
		const data = data_of(page.name);
		const waits = data && data.waiting;
		if (!waits || !(waits.tasks || waits.unread)) return "";
		const lists = { items: waits.items || [], notes: waits.notes || [] };
		const which = lists[tab] && lists[tab].length ? tab : lists.items.length ? "items" : "notes";
		const tabs = [
			["items", __("To Do"), waits.tasks],
			["notes", __("Notifications"), waits.unread],
		]
			.map(
				([key, label, total]) =>
					`<button type="button" class="cvt-mod-tab${which === key ? " cvt-on" : ""}" data-cvt-mod="tab" ` +
					`data-tab="${key}">${esc(label)}<i>${count(total)}</i></button>`
			)
			.join("");
		const total = which === "items" ? waits.tasks : waits.unread;
		const more =
			total > lists[which].length
				? `<div class="cvt-mod-more"><button type="button" class="cvt-mod-all" data-cvt-mod="all" data-list="${which}">` +
				  `<span>${esc(__("See all {0}", [count(total)]))}</span>${icon("chevron")}</button></div>`
				: "";
		return (
			`<section class="cvt-mod-panel"><header><span class="cvt-mod-panel-icon">${icon("waiting")}</span>` +
			`<h3>${esc(__("Waiting for You"))}</h3><span class="cvt-mod-tabs">${tabs}</span></header>` +
			`<div class="cvt-mod-list">${lists[which].map((item, index) => row(item, index, which)).join("")}</div>` +
			`${more}</section>`
		);
	}

	// the module's header, drawn afresh only when what it shows has changed
	function redraw(force) {
		const element = page_now();
		const page = shown();
		const holder = element && element.querySelector(".layout-main-section > .cvt-mod");
		if (!holder || !page) return;
		const answer = answers[page.name];
		const mark = [page.name, page.title || "", answer ? answer.at : 0, tab].join("|");
		if (!force && holder.getAttribute("data-mark") === mark) return;
		holder.setAttribute("data-mark", mark);
		holder.innerHTML = hero(page) + panel(page);
	}

	// the user's own list of what waits, kept to the module's documents
	function all(which, name) {
		const data = data_of(name);
		const doctypes = (data && data.doctypes) || [];
		const user = frappe.session.user;
		if (which === "notes") {
			frappe.route_options = Object.assign(
				{ for_user: user, read: 0 },
				doctypes.length ? { document_type: ["in", doctypes] } : {}
			);
			frappe.set_route("List", "Notification Log");
		} else {
			frappe.route_options = Object.assign(
				{ allocated_to: user, status: "Open" },
				doctypes.length ? { reference_type: ["in", doctypes] } : {}
			);
			frappe.set_route("List", "ToDo");
		}
	}

	// another step of the flow, opened as its tile opens it, with its own menu down the left
	function open_module(name) {
		const path = name && nav.tile_path(name);
		if (path) nav.follow(path, name);
	}

	function act(element) {
		const what = element.getAttribute("data-cvt-mod");
		const page = shown();
		if (!page) return;
		const index = Number(element.getAttribute("data-index"));
		if (what === "go") open_module(element.getAttribute("data-module"));
		else if (what === "new") {
			const doctype = action_of(page.name);
			if (doctype) frappe.new_doc(doctype);
		} else if (what === "flag") {
			const flag = ((data_of(page.name) || {}).attention || [])[index];
			if (flag && flag.route) {
				frappe.route_options = Object.assign({}, flag.filters || {});
				frappe.set_route(flag.route);
			}
		} else if (what === "waiting") {
			if (element.closest(".cvt-mod").querySelector(".cvt-mod-panel")) {
				tab = "items";
				redraw(true);
				const list = page_now() && page_now().querySelector(".cvt-mod-panel");
				if (list && list.scrollIntoView) list.scrollIntoView({ behavior: "smooth", block: "nearest" });
			} else all("items", page.name);
		} else if (what === "tab") {
			tab = element.getAttribute("data-tab") === "notes" ? "notes" : "items";
			redraw(true);
		} else if (what === "row") {
			const waits = (data_of(page.name) || {}).waiting || {};
			const list = element.getAttribute("data-list") === "notes" ? waits.notes : waits.items;
			const item = (list || [])[index];
			if (item && item.doctype && item.docname) frappe.set_route("Form", item.doctype, item.docname);
		} else if (what === "all") all(element.getAttribute("data-list"), page.name);
	}

	// where the header goes: first in Frappe's workspace body, which Frappe only ever adds its skeleton to and
	// takes it from again (workspace.js); the stylesheet keeps the header above the skeleton
	function mount(element) {
		const body = element.querySelector(".layout-main-section");
		if (!body) return null;
		let holder = body.querySelector(":scope > .cvt-mod");
		if (!holder) {
			holder = document.createElement("div");
			holder.className = "cvt-mod";
			body.insertBefore(holder, body.firstChild);
			holder.addEventListener("click", (event) => {
				const target = event.target.closest("[data-cvt-mod]");
				if (!target) return;
				try {
					act(target);
				} catch (error) {
					console.error(error);
				}
			});
		}
		return holder;
	}

	function load(name) {
		const answer = answers[name];
		if (asking[name] || (answer && Date.now() - answer.at < FRESH_MS)) return;
		asking[name] = true;
		// fetch, not frappe.call: a call that fails must leave the module alone, and frappe.call would open
		// Frappe's Server Error dialog over it
		fetch("/api/method/" + METHOD + "?workspace=" + encodeURIComponent(name), {
			credentials: "same-origin",
			cache: "no-store",
			headers: { Accept: "application/json" },
		})
			.then((response) => (response.ok ? response.json() : null))
			.then((r) => (r && r.message) || null)
			.catch(() => null)
			.then((data) => {
				// one that failed keeps what was shown before, and is asked again later, not at once
				answers[name] = { data: data || (answer && answer.data) || null, at: Date.now() };
				asking[name] = false;
				try {
					redraw(false);
				} catch (error) {
					console.error(error);
				}
			});
	}

	function show() {
		try {
			const element = page_now();
			const page = shown();
			if (!element || !page) return false;
			if (!mount(element)) return false;
			redraw(false);
			load(page.name);
			return true;
		} catch (error) {
			console.error(error);
			return true; // do not keep trying something that throws
		}
	}

	function on_workspace() {
		try {
			return (frappe.get_route() || [])[0] === "Workspaces";
		} catch (e) {
			return false;
		}
	}

	// Frappe says "page-change" first and names the workspace it shows straight after, as it starts drawing it
	// (container.js change_to, workspace.js show_page): the first look waits for that, and a few more follow,
	// each drawing the header for whichever workspace is shown, then it is left
	function arrive() {
		if (!on_workspace()) return;
		let tries = 0;
		const look = () => {
			tries += 1;
			const there = show();
			if (tries < 10 && (!there || tries < 4)) setTimeout(look, 120 * tries);
		};
		setTimeout(look, 0);
	}

	// on <html> at once, so a workspace is never seen in another look first
	document.documentElement.classList.add(ON);
	cyvetech_ui.module_pages.show = arrive;
	$(document).on("page-change", arrive);
	$(arrive);
})();
