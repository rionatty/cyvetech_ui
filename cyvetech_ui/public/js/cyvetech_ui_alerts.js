// CyveTech UI — My Alerts, and the pop-ups for what just arrived.
//
// MY ALERTS is a small panel fixed to the bottom-right corner of the desk with
// the signed-in user's own work, most urgent first: their open assignments
// ("overdue by 8 days"), their notifications, and the alerts an administrator
// has sent them (CyveTech User Alert). It can be shrunk to its header and
// stays as it was left. The rows come from
// cyvetech_ui.cyvetech_ui.alerts.my_alerts, which only ever reads the
// session user's own records.
//
// POP-UPS. Whatever is new since the last answer pops up:
//
//   * an alert an administrator sent, always. Normal ones close by
//     themselves; Important ones stay until closed; Urgent ones open a
//     message the user has to acknowledge. An alert sent while the user was
//     away pops up the next time they open the desk.
//   * any other new notification or assignment, if the settings say so.
//
// KEEPING UP. Frappe publishes "notification" to a user the moment a
// Notification Log is created for them — every assignment, mention, share
// and sent alert creates one — so that event is the cue to reload at once.
// It travels over the site's socket.io server, which is not always running
// or reachable, so the list is also reloaded:
//
//   * every minute while the page is in view and the realtime socket is not
//     connected, every five minutes while it is (for a task whose due date
//     passes while the page is open: nothing is published for that);
//   * on coming back to the page or moving to another page of the desk, if
//     the last load is more than 15 seconds old.
//
// A page out of view never polls.

(function () {
	if (typeof frappe === "undefined" || !frappe.boot) return;
	frappe.provide("cyvetech_ui");

	const conf = (frappe.boot.cyvetech_ui || {}).alerts || {};
	const METHOD = "cyvetech_ui.cyvetech_ui.alerts.my_alerts";
	const MARK_READ = "frappe.desk.doctype.notification_log.notification_log.mark_as_read";
	const MARK_ALL_READ = "frappe.desk.doctype.notification_log.notification_log.mark_all_as_read";
	const TICK_MS = 15 * 1000; // how often to see whether a load is due (no request)
	const POLL_MS = 60 * 1000; // without the realtime socket
	const LIVE_POLL_MS = 5 * 60 * 1000; // with it: news arrives by itself
	const CATCH_UP_MS = 15 * 1000;
	const COLLAPSED_KEY = "cyvetech_ui:alerts_collapsed";
	const POPPED_LIMIT = 300;
	const MAX_POPUPS = 3;
	const SECONDS = Math.min(60, Math.max(3, parseInt(conf.seconds, 10) || 8));

	let user = null; // the signed-in user, known once the desk has started
	let started = false;
	let panel = null;
	let answer = null; // the last answer from the server
	let known = null; // its keys; null until the first answer lands
	let busy = false;
	let again = false; // asked to reload while a load was in flight
	let last_load = 0; // when the last load was asked for (ms)
	const urgent_queue = [];
	let urgent_open = false;

	// ── storage (private windows can refuse it; everything still works) ──
	function stored(key) {
		try {
			return window.localStorage.getItem(key);
		} catch (e) {
			return null;
		}
	}

	function store(key, value) {
		try {
			window.localStorage.setItem(key, value);
		} catch (e) {
			/* nothing to remember it in: it just works for this visit */
		}
	}

	function collapsed() {
		const value = stored(COLLAPSED_KEY);
		if (value === null) return window.innerWidth < 768; // out of the way on a phone
		return value === "1";
	}

	// per user: two people taking turns on one browser each get their own
	function popped_store_key() {
		return "cyvetech_ui:popped:" + user;
	}

	function popped_keys() {
		try {
			return new Set(JSON.parse(stored(popped_store_key()) || "[]"));
		} catch (e) {
			return new Set();
		}
	}

	function remember_popped(key) {
		const keys = [...popped_keys()].filter((k) => k !== key);
		keys.push(key);
		store(popped_store_key(), JSON.stringify(keys.slice(-POPPED_LIMIT)));
	}

	// ── text ────────────────────────────────────────────────────────────
	function e(value) {
		return frappe.utils.escape_html(String(value == null ? "" : value));
	}

	// Parsed in an inert document: nothing in it runs or loads.
	function inert(html) {
		return new DOMParser().parseFromString(String(html || ""), "text/html").body;
	}

	function plain_text(html) {
		return (inert(html).textContent || "").replace(/\s+/g, " ").trim();
	}

	// The alert's message for the Urgent dialog. Frappe cleans Text Editor
	// content when it is saved; this strips anything active a second time.
	function safe_html(html) {
		const body = inert(html);
		body.querySelectorAll("script, style, iframe, object, embed, link, meta, form").forEach((el) => el.remove());
		body.querySelectorAll("*").forEach((el) => {
			[...el.attributes].forEach((attr) => {
				const name = attr.name.toLowerCase();
				const value = attr.value.trim().toLowerCase();
				if (name.startsWith("on") || ((name === "href" || name === "src") && value.startsWith("javascript:"))) {
					el.removeAttribute(attr.name);
				}
			});
		});
		return body.innerHTML;
	}

	function when(alert) {
		if (alert.when) return __(alert.when);
		if (alert.created && frappe.datetime && frappe.datetime.prettyDate) {
			return frappe.datetime.prettyDate(alert.created);
		}
		return "";
	}

	function full_name(user) {
		return (frappe.user && frappe.user.full_name && frappe.user.full_name(user)) || user || "";
	}

	function meta_line(alert) {
		if (alert.alert) {
			return [__("Alert"), alert.from_user ? __("from {0}", [full_name(alert.from_user)]) : "", when(alert)]
				.filter(Boolean)
				.join(" · ");
		}
		const personal = alert.doctype === "ToDo" && alert.docname === alert.key;
		return [__(alert.doctype || ""), personal ? "" : alert.docname, when(alert)].filter(Boolean).join(" · ");
	}

	function link(alert) {
		if (!alert.doctype || !alert.docname) return "#";
		if (frappe.utils.get_form_link) return frappe.utils.get_form_link(alert.doctype, alert.docname);
		return "#";
	}

	// ── the panel ───────────────────────────────────────────────────────
	function build() {
		if (!conf.panel || document.querySelector(".cvt-alerts")) return;
		const shrunk = collapsed();
		panel = document.createElement("section");
		panel.className = "cvt-alerts" + (shrunk ? " cvt-alerts-collapsed" : "");
		panel.setAttribute("aria-label", __("My Alerts"));
		panel.innerHTML = `
			<button class="cvt-alerts-head" type="button" aria-expanded="${shrunk ? "false" : "true"}">
				<span class="cvt-alerts-title">${e(__("My Alerts"))}</span>
				<span class="cvt-alerts-count cvt-band-none">0</span>
				<span class="cvt-alerts-chevron" aria-hidden="true"></span>
			</button>
			<div class="cvt-alerts-body" role="list">
				<div class="cvt-alerts-empty">${e(__("Loading…"))}</div>
			</div>
			<div class="cvt-alerts-foot" hidden>
				<button class="cvt-alerts-read-all" type="button">${e(__("Mark notifications read"))}</button>
			</div>`;
		document.body.appendChild(panel);
		panel.querySelector(".cvt-alerts-head").addEventListener("click", toggle);
		panel.querySelector(".cvt-alerts-body").addEventListener("click", clicked);
		panel.querySelector(".cvt-alerts-read-all").addEventListener("click", read_all);
		if (answer) render(answer);
	}

	function toggle() {
		const shrink = !panel.classList.contains("cvt-alerts-collapsed");
		panel.classList.toggle("cvt-alerts-collapsed", shrink);
		panel.querySelector(".cvt-alerts-head").setAttribute("aria-expanded", shrink ? "false" : "true");
		store(COLLAPSED_KEY, shrink ? "1" : "0");
	}

	function expand() {
		if (panel && panel.classList.contains("cvt-alerts-collapsed")) toggle();
	}

	function render(data) {
		if (!panel) return;
		const alerts = data.alerts || [];
		const count = data.total || 0;
		const badge = panel.querySelector(".cvt-alerts-count");
		badge.textContent = count > 99 ? "99+" : String(count);
		badge.className = "cvt-alerts-count cvt-band-" + (data.band || "none");
		badge.setAttribute("aria-label", __("{0} outstanding", [count]));
		panel.querySelector(".cvt-alerts-body").innerHTML = alerts.length
			? alerts.map(row_html).join("")
			: `<div class="cvt-alerts-empty">${e(__("Nothing needs your attention."))}</div>`;
		panel.querySelector(".cvt-alerts-foot").hidden = !alerts.some((alert) => alert.unread);
	}

	function row_html(alert) {
		const unread = alert.kind === "assignment" || alert.unread ? " cvt-alert-unread" : "";
		return `
			<a class="cvt-alert cvt-band-${e(alert.urgency || "none")}${unread}" role="listitem"
				href="${e(link(alert))}" data-key="${e(alert.key)}">
				<span class="cvt-alert-dot" aria-hidden="true"></span>
				<span class="cvt-alert-text">
					<span class="cvt-alert-title">${e(alert.title)}</span>
					<span class="cvt-alert-meta">${e(meta_line(alert))}</span>
				</span>
			</a>`;
	}

	function find(key) {
		return ((answer && answer.alerts) || []).find((alert) => alert.key === key);
	}

	function clicked(event) {
		const row = event.target.closest(".cvt-alert");
		if (!row) return;
		const alert = find(row.dataset.key);
		if (!alert) return;
		// a new tab or window: let the browser open the link, and still mark it read
		if (event.ctrlKey || event.metaKey || event.shiftKey || event.button === 1) {
			if (alert.unread) mark_read(alert.key);
			return;
		}
		event.preventDefault();
		open(alert);
	}

	function open(alert) {
		if (alert.kind === "notification" && alert.unread) mark_read(alert.key);
		if (alert.doctype && alert.docname) frappe.set_route("Form", alert.doctype, alert.docname);
	}

	function mark_read(key) {
		frappe.xcall(MARK_READ, { docname: key }).then(() => {
			bell_count((n) => n - 1);
			load();
		});
	}

	function read_all() {
		frappe.xcall(MARK_ALL_READ).then(() => {
			bell_count(() => 0);
			load();
		});
	}

	// Keep the count on Frappe's own bell in step with what was read here.
	function bell_count(next) {
		try {
			const bell = frappe.app.sidebar.notifications.tabs.notifications;
			if (bell && typeof bell.update_count_badge === "function") {
				bell.update_count_badge(Math.max(0, next(bell.unread_count || 0)));
			}
		} catch (error) {
			/* this version of Frappe keeps its bell elsewhere: it catches up on reload */
		}
	}

	// ── loading ─────────────────────────────────────────────────────────
	function load() {
		if (busy) {
			again = true; // something arrived mid-request: ask once more after
			return;
		}
		busy = true;
		last_load = Date.now();
		frappe
			.xcall(METHOD)
			.then((fresh) => {
				answer = fresh || {};
				render(answer);
				announce(answer.alerts || []);
			})
			.catch((error) => {
				// say so rather than leave an empty panel that looks like nothing is due
				const body = panel && panel.querySelector(".cvt-alerts-body");
				if (body) {
					body.innerHTML = `<div class="cvt-alerts-empty">${e(__("Alerts could not be loaded."))}</div>`;
				}
				console.error("cyvetech_ui: my_alerts failed", error);
			})
			.finally(() => {
				busy = false;
				if (again) {
					again = false;
					load();
				}
			});
	}

	// ── pop-ups ─────────────────────────────────────────────────────────
	function is_sent_alert(alert) {
		return !!alert.alert;
	}

	// What in this answer is news.
	function news(alerts) {
		const popped = popped_keys();
		if (known === null) {
			// The first answer is the state of things, not news — except alerts
			// sent to this user that never popped up (they arrived while away).
			return alerts.filter((a) => is_sent_alert(a) && a.unread && !popped.has(a.key));
		}
		const seen = new Set(known);
		return alerts.filter((a) => {
			if (seen.has(a.key)) return false;
			if (is_sent_alert(a)) return a.unread && !popped.has(a.key);
			return conf.popup && (a.kind === "assignment" || a.unread);
		});
	}

	function announce(alerts) {
		const fresh = news(alerts);
		known = alerts.map((alert) => alert.key);
		if (!fresh.length) return;

		const urgent = fresh.filter((a) => a.alert && a.alert.priority === "Urgent");
		const rest = fresh.filter((a) => !urgent.includes(a));
		rest.slice(0, MAX_POPUPS).forEach(popup);
		if (rest.length > MAX_POPUPS) more(rest.length - MAX_POPUPS);
		urgent.forEach((alert) => {
			if (!urgent_queue.some((queued) => queued.key === alert.key)) urgent_queue.push(alert);
		});
		show_next_urgent();

		if (conf.sound && frappe.utils && frappe.utils.play_sound) frappe.utils.play_sound("alert");
	}

	function stack() {
		let container = document.querySelector(".cvt-popups");
		if (!container) {
			container = document.createElement("div");
			container.className = "cvt-popups";
			container.setAttribute("aria-live", "polite");
			document.body.appendChild(container);
		}
		return container;
	}

	function kicker(alert) {
		if (alert.alert) return alert.alert.priority === "Important" ? __("Important alert") : __("Alert");
		return alert.kind === "assignment" ? __("New assignment") : __("New notification");
	}

	function popup(alert) {
		const sent = alert.alert;
		const sticky = !!(sent && sent.priority === "Important");
		const body = sent ? plain_text(sent.message) : meta_line(alert);
		const opens = !!(alert.doctype && alert.docname);
		const card = document.createElement("div");
		card.className = "cvt-popup cvt-band-" + (alert.urgency || "none");
		card.setAttribute("role", sticky ? "alert" : "status");
		card.innerHTML = `
			<div class="cvt-popup-text">
				<span class="cvt-popup-kicker">${e(kicker(alert))}</span>
				<span class="cvt-popup-title">${e(alert.title)}</span>
				${body ? `<span class="cvt-popup-body">${e(body)}</span>` : ""}
				<div class="cvt-popup-actions">
					${opens ? `<button type="button" class="cvt-popup-open">${e(__("Open"))}</button>` : ""}
					<button type="button" class="cvt-popup-dismiss">${e(__("Dismiss"))}</button>
				</div>
			</div>
			<button type="button" class="cvt-popup-close" aria-label="${e(__("Close"))}">&times;</button>
			${sticky ? "" : `<span class="cvt-popup-timer" style="animation-duration: ${SECONDS}s"></span>`}`;

		let closed = false;
		const close = () => {
			if (closed) return;
			closed = true;
			card.remove();
		};
		card.querySelector(".cvt-popup-close").addEventListener("click", close);
		card.querySelector(".cvt-popup-dismiss").addEventListener("click", close);
		if (opens) {
			card.querySelector(".cvt-popup-open").addEventListener("click", () => {
				open(alert);
				close();
			});
		}
		if (!sticky) {
			// the timer line runs down (pausing while hovered) and closes the card
			card.querySelector(".cvt-popup-timer").addEventListener("animationend", close);
			setTimeout(close, SECONDS * 3000); // in case animations are switched off
		}
		stack().appendChild(card);
		if (sent) remember_popped(alert.key);
	}

	function more(count) {
		const card = document.createElement("div");
		card.className = "cvt-popup cvt-band-none";
		card.setAttribute("role", "status");
		card.innerHTML = `
			<div class="cvt-popup-text">
				<span class="cvt-popup-title">${e(__("{0} more waiting in My Alerts", [count]))}</span>
				<div class="cvt-popup-actions">
					<button type="button" class="cvt-popup-open">${e(__("Show"))}</button>
					<button type="button" class="cvt-popup-dismiss">${e(__("Dismiss"))}</button>
				</div>
			</div>
			<span class="cvt-popup-timer" style="animation-duration: ${SECONDS}s"></span>`;
		const close = () => card.remove();
		card.querySelector(".cvt-popup-open").addEventListener("click", () => {
			expand();
			close();
		});
		card.querySelector(".cvt-popup-dismiss").addEventListener("click", close);
		card.querySelector(".cvt-popup-timer").addEventListener("animationend", close);
		setTimeout(close, SECONDS * 3000);
		stack().appendChild(card);
	}

	// Urgent alerts: one message at a time, acknowledged with "Got it". One
	// closed any other way stays unread and comes back on the next visit.
	function show_next_urgent() {
		if (urgent_open || !urgent_queue.length) return;
		const alert = urgent_queue.shift();
		urgent_open = true;
		const opens = !!(alert.doctype && alert.docname);
		const dialog = new frappe.ui.Dialog({
			title: alert.title,
			indicator: "red",
			fields: [{ fieldtype: "HTML", fieldname: "message" }],
			primary_action_label: __("Got it"),
			primary_action() {
				remember_popped(alert.key);
				if (alert.unread) mark_read(alert.key);
				dialog.hide();
			},
			secondary_action_label: opens ? __("Open") : null,
			secondary_action: opens
				? () => {
						remember_popped(alert.key);
						dialog.hide();
						open(alert);
				  }
				: null,
		});
		const message = safe_html(alert.alert && alert.alert.message) || e(alert.title);
		const from = alert.from_user ? __("From {0}", [full_name(alert.from_user)]) : "";
		dialog.fields_dict.message.$wrapper.html(
			`<div class="cvt-urgent-message">${message}</div>` +
				(from ? `<p class="text-muted small" style="margin-top: 12px">${e(from)}</p>` : "")
		);
		dialog.onhide = () => {
			urgent_open = false;
			show_next_urgent();
		};
		dialog.show();
	}

	// ── keeping up ──────────────────────────────────────────────────────
	function in_view() {
		return document.visibilityState !== "hidden";
	}

	// Whether Frappe's realtime socket is connected, so news arrives by itself.
	function live() {
		const socket = frappe.realtime && frappe.realtime.socket;
		return !!(socket && socket.connected);
	}

	function tick() {
		if (in_view() && Date.now() - last_load >= (live() ? LIVE_POLL_MS : POLL_MS)) load();
	}

	function catch_up() {
		if (in_view() && Date.now() - last_load >= CATCH_UP_MS) load();
	}

	// ── start ───────────────────────────────────────────────────────────
	// Whatever takes the panel out of the page (a route that rebuilds the
	// body, another app's script), it is put straight back from the answer
	// in hand.
	function watch() {
		if (!conf.panel || !window.MutationObserver) return;
		new MutationObserver(() => {
			if (!document.querySelector(".cvt-alerts")) build();
		}).observe(document.body, { childList: true });
	}

	function start() {
		if (started) return;
		// Frappe sets frappe.session.user as the desk starts
		// (frappe.Application.set_globals), after this file has run, so it
		// is read here and never when the file loads.
		user = (frappe.session && frappe.session.user) || (frappe.boot.user && frappe.boot.user.name) || null;
		if (!user || user === "Guest") return;
		started = true;

		build();
		watch();
		load();
		if (frappe.router && frappe.router.on) {
			frappe.router.on("change", () => {
				build();
				catch_up();
			});
		}
		// the realtime socket only exists once the desk has started, which is
		// why all of this waits for app_ready
		if (frappe.realtime && frappe.realtime.on) frappe.realtime.on("notification", load);
		setInterval(tick, TICK_MS);
		document.addEventListener("visibilitychange", catch_up);
		window.addEventListener("focus", catch_up);
	}

	cyvetech_ui.reload_alerts = () => started && load();

	// For a look from the browser console: cyvetech_ui.alerts_status()
	cyvetech_ui.alerts_status = () => ({
		user,
		started,
		panel: !!document.querySelector(".cvt-alerts"),
		realtime: live(),
		last_load: last_load ? new Date(last_load).toLocaleTimeString() : null,
		listed: answer ? (answer.alerts || []).length : null,
		settings: conf,
	});

	function begin() {
		if (!document.body) {
			document.addEventListener("DOMContentLoaded", begin, { once: true });
			return;
		}
		start();
	}

	if (frappe.app) begin();
	else $(document).on("app_ready", begin);
})();
