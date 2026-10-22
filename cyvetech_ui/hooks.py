from cyvetech_ui.cyvetech_ui.asset_urls import versioned

app_name = "cyvetech_ui"
app_title = "CyveTech UI"
app_publisher = "CyveTech"
app_description = "Branding, theme, a desk home with a dashboard for each ERPNext module, module pages, desk modules, and user alerts for the Frappe / ERPNext desk"
app_email = "ferdinand@cyvetech.com"
app_license = "mit"

# Works on any Frappe site, with or without ERPNext.
# required_apps = []

# Desk
# ----
# Plain asset paths: nothing here needs `bench build`. Each carries a hash
# of its contents (asset_urls.py), so browsers fetch a file again once it
# changes instead of keeping the copy they cached.
#
#  cyvetech_ui.css         the theme, the sidebar's groups, rounded tiles, the
#                          My Alerts panel, pop-ups
#  cyvetech_ui_home.css    the desk home, the modules down the left of it, and
#                          the module pages, all in the theme's colors
#  cyvetech_ui_desk.js     applies the theme and branding from the boot, and
#                          hides the modules taken off the desk
#  cyvetech_ui_charts.js   gives charts the palette from the settings
#  cyvetech_ui_alerts.js   My Alerts and the pop-ups for what just arrived
#  cyvetech_ui_home.js     the desk home: a greeting, the day's ERPNext figures,
#                          what waits and what needs attention (home.py)
#  cyvetech_ui_module_pages.js
#                          each module's page under a header in the home's look
#                          (module_pages.py)
app_include_css = [
	versioned("/assets/cyvetech_ui/css/cyvetech_ui.css"),
	versioned("/assets/cyvetech_ui/css/cyvetech_ui_home.css"),
]
app_include_js = [
	versioned("/assets/cyvetech_ui/js/cyvetech_ui_desk.js"),
	versioned("/assets/cyvetech_ui/js/cyvetech_ui_charts.js"),
	versioned("/assets/cyvetech_ui/js/cyvetech_ui_alerts.js"),
	versioned("/assets/cyvetech_ui/js/cyvetech_ui_home.js"),
	versioned("/assets/cyvetech_ui/js/cyvetech_ui_module_pages.js"),
]

# The settings ride along with every desk boot, so colors and logos are in
# place before the first paint. See cyvetech_ui/cyvetech_ui/boot.py.
extend_bootinfo = "cyvetech_ui.cyvetech_ui.boot.boot_session"

# The sign-in page is www/login.html in this app, which Frappe serves in place
# of its own. It needs no hook.

# Installation and migration
# --------------------------
after_install = "cyvetech_ui.cyvetech_ui.setup.after_install"

# Each is idempotent and never fails a deploy. The first writes the defaults of
# settings an update has added, so the settings page shows them as they are in
# force; the others re-assert the branding and the hidden desk modules after an
# update has put Frappe's back.
after_migrate = [
	"cyvetech_ui.cyvetech_ui.settings.ensure_defaults",
	"cyvetech_ui.cyvetech_ui.branding.apply_on_migrate",
	"cyvetech_ui.cyvetech_ui.desk_modules.apply_on_migrate",
]

# Permissions
# -----------
# Everyone may read an alert sent to them, and only those. System Managers
# see them all.
permission_query_conditions = {
	"CyveTech User Alert": "cyvetech_ui.cyvetech_ui.permissions.alert_query",
}

has_permission = {
	"CyveTech User Alert": "cyvetech_ui.cyvetech_ui.permissions.alert_has_permission",
}
