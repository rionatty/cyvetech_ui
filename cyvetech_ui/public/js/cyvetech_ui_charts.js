// CyveTech UI — chart colors.
//
// Every chart on the desk — workspace charts, report charts, the charts on a
// form's dashboard — is built with `new frappe.Chart(...)`, read at the moment
// the chart is made (frappe/public/js/frappe/ui/chart.js). Wrapping it here
// gives charts the palette from CyveTech UI Settings without touching any of
// the code that draws them.
//
// Which colors a chart gets:
//
//   * A chart that chose its own colors keeps them (a report that draws
//     overdue in red means something by it) — unless the settings say to
//     recolor those too. Any series it left without a color, and any beyond
//     its list, take palette colors rather than Frappe's defaults.
//   * A chart that chose nothing takes the palette in order. Frappe's own
//     widgets pass a placeholder rather than nothing — an empty list, a list
//     with an empty entry, or ["light-blue"] from frappe.utils.make_chart —
//     and those count as nothing.
//   * A chart with a single series (one line, one set of bars) starts at a
//     palette color picked from its title, so the charts side by side on a
//     workspace differ, and each chart keeps its color wherever it appears.
//     Pie, donut and percentage charts color each slice, so they always take
//     the palette in order.
//   * Heatmaps are a single-color ramp, not categories, and are left alone.

(function () {
	if (typeof frappe === "undefined" || !frappe.boot) return;
	const conf = (frappe.boot.cyvetech_ui || {}).charts || {};
	if (!conf.enabled || typeof frappe.Chart !== "function" || frappe.Chart.cyvetech_ui) return;

	const OriginalChart = frappe.Chart;
	// the names frappe-charts accepts besides hex and rgb()/hsl()
	const PRESETS = new Set([
		"pink", "blue", "green", "grey", "red", "yellow", "purple", "teal", "cyan", "orange",
		"light-pink", "light-blue", "light-green", "light-grey", "light-red", "light-yellow",
		"light-purple", "light-teal", "light-cyan", "light-orange",
	]);
	const HEX = /^\s*#(?:[0-9a-f]{3}){1,2}\s*$/i;
	const COLOR_FUNCTION = /^\s*(?:rgb|rgba|hsl|hsla)\(/i;
	const PER_SLICE = new Set(["pie", "donut", "percentage"]);

	function is_color(value) {
		return (
			typeof value === "string" &&
			(HEX.test(value) || COLOR_FUNCTION.test(value) || PRESETS.has(value.trim()))
		);
	}

	function palette() {
		const dark = document.documentElement.getAttribute("data-theme") === "dark";
		const colors = (dark ? conf.dark_palette : conf.palette) || [];
		return colors.filter(is_color);
	}

	function chart_title(parent, options) {
		const element = typeof parent === "string" ? document.querySelector(parent) : parent;
		const card = element && element.closest ? element.closest(".widget, .chart-wrapper") : null;
		const title = card && card.querySelector(".widget-title, .chart-title");
		const datasets = (options.data && options.data.datasets) || [];
		return (
			(title && title.textContent.trim()) ||
			options.title ||
			(datasets[0] && datasets[0].name) ||
			""
		);
	}

	function hash(text) {
		let value = 0;
		for (const character of String(text)) {
			value = (value * 31 + character.codePointAt(0)) >>> 0;
		}
		return value;
	}

	function rotate(colors, start) {
		return colors.slice(start).concat(colors.slice(0, start));
	}

	// The colors to give a chart, or null to leave its options as they are.
	function colors_for(parent, options) {
		const colors = palette();
		const type = String(options.type || "").toLowerCase();
		if (!colors.length || type === "heatmap") return null;

		const given = Array.isArray(options.colors) ? options.colors : [];
		const chosen = given.filter(is_color);
		const placeholder = given.length === 1 && chosen.length === 1 && chosen[0].trim() === "light-blue";
		if (chosen.length && !placeholder && !conf.override) {
			return given.map((color, i) => (is_color(color) ? color : colors[i % colors.length])).concat(colors);
		}

		const datasets = (options.data && options.data.datasets) || [];
		if (conf.vary && !PER_SLICE.has(type) && datasets.length <= 1) {
			return rotate(colors, hash(chart_title(parent, options)) % colors.length);
		}
		return colors.slice();
	}

	function CyveTechChart(parent, options) {
		let painted = options;
		try {
			const colors = options && colors_for(parent, options);
			if (colors) painted = Object.assign({}, options, { colors });
		} catch (error) {
			console.warn("cyvetech_ui: chart colors skipped", error);
		}
		return new OriginalChart(parent, painted);
	}

	// Chart's constructor hands back a chart of the right type rather than
	// itself, so `new` on this wrapper returns that same object; the rest is
	// kept as it was for anything that inspects frappe.Chart.
	CyveTechChart.prototype = OriginalChart.prototype;
	Object.setPrototypeOf(CyveTechChart, OriginalChart);
	CyveTechChart.cyvetech_ui = true;
	frappe.Chart = CyveTechChart;
})();
