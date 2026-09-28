### CyveTech UI

Branding, theme, desk modules, and user alerts for the Frappe / ERPNext desk, all managed from one settings page: **CyveTech UI Settings**.

Built for Frappe / ERPNext **v16**. It installs on v15 too, where everything except the desk-module tiles works (v15 has no desktop tiles).

---

### What it does

| | Feature | Where to set it |
|---|---|---|
| 1 | **Desk colors.** Pick the left sidebar color, the selected-item highlight and the page background (the central area). Sidebar text switches between white and dark automatically so it always stays readable. | Settings → Desk Theme |
| 2 | **Smooth tiles.** Rounded corners on the desktop's app tiles and on workspace cards (number cards, shortcuts, link lists, charts), with an adjustable radius. | Settings → Desk Theme |
| 3 | **Chart colors.** An eight-color palette for every chart on the desk, checked for color-blind readers. A single-series chart takes a color from its title, so charts side by side look different and each one keeps its color. Charts that choose their own colors on purpose (red for overdue) keep them. | Settings → Charts |
| 4 | **Branded sign-in page.** A brand panel beside Frappe's own sign-in card, with a logo, heading, tagline, optional background picture, and your panel, button and page colors. | Settings → Sign-in Page |
| 5 | **Navigation logo and browser icon.** Replace the ERPNext and Frappe logos (the "E") in the app switcher, the desktop's top bar and the sign-in page, and set the browser-tab icon (favicon). Optionally rename "ERPNext" to your product name. | Settings → Branding |
| 6 | **My Alerts.** A panel in the bottom-right corner showing each user's own open assignments ("overdue by 8 days"), notifications and alerts, most urgent first. Admins can send an alert to specific users or roles with **CyveTech User Alert**. | Settings → Alerts, and CyveTech User Alert |
| 7 | **Desk modules.** Choose which module tiles show on everyone's desktop. | Settings → Desk Modules |
| 8 | **Pop-ups.** New notifications and alerts pop up the moment they arrive. Important alerts stay until closed. Urgent ones must be acknowledged. An alert sent while someone was away pops up the next time they open the desk. | Settings → Alerts |

---

### Installation

```bash
cd ~/frappe-bench
bench get-app https://github.com/rionatty/cyvetech_ui.git
bench --site YOUR-SITE install-app cyvetech_ui
bench --site YOUR-SITE migrate
bench --site YOUR-SITE clear-cache
bench restart
```

Nothing needs `bench build`: the app's CSS and JavaScript are plain assets. After installing, hard-refresh the browser (Ctrl+Shift+R).

**To update later:**

```bash
cd ~/frappe-bench/apps/cyvetech_ui && git pull && cd ~/frappe-bench && bench --site YOUR-SITE migrate && bench --site YOUR-SITE clear-cache && bench restart
```

---

### Setting it up

Open **CyveTech UI Settings** from the search bar (System Managers only).

1. **Branding:** upload the navigation logo (a wide logo, about 240 × 64 px) and a square browser icon. Upload both as **public** files: the sign-in page and the browser tab are seen before anyone logs in.
2. **Desk Theme:** the defaults are CyveTech navy and gold. The preview updates as you type.
3. **Sign-in Page:** leave the sign-in logo blank to reuse the navigation logo.
4. **Desk Modules:** click **Load Desk Modules**, untick what should not show, and save.
5. **Alerts:** click **Send Me a Test Alert** to see a pop-up and the My Alerts panel working end to end.

Save once, and every user sees the change on their next page load.

**Sending an alert:** create a **CyveTech User Alert**, pick the users and/or roles, choose a priority (Normal, Important, Urgent) and optionally link a document, then **Send**. Each recipient gets it in the bell menu and in My Alerts, as a pop-up. Recipients can only read alerts sent to them. Cancelling an alert withdraws it from everyone who hasn't read it yet.

---

### Good to know

- **Colors apply in light mode.** Dark mode keeps Frappe's own dark colors.
- **Hiding a module changes what shows, not who may open it.** Use roles and Module Profiles for access. Users who have rearranged their own desktop keep their layout, and hidden modules are hidden for them too.
- **Blank logo fields leave your current logos alone.** Clearing a logo here removes only what this app put in Website Settings and Navbar Settings. A logo set there by hand is never touched.
- **With Stock Addon or HRMS Addon installed:** both ship their own navy theme. CyveTech UI's colors take over theirs, as long as the colour override in *Stock Addon Theme Settings* / *HRMS Addon Theme Settings* is switched off. HRMS Addon also has its own My Alerts panel and sign-in page. Use one or the other: switch off **Show the My Alerts Panel** here, or remove HRMS Addon's. The sign-in page shown is the one from whichever app was installed last.

---

### Development

The Python tests run without a bench. They cover the rules behind the colors, alerts, sign-in page and desk modules, and the server code, which runs against a small in-memory stand-in for Frappe (`tests/fake_frappe.py`):

```bash
python -m unittest discover -s tests -v
```

The desk scripts and stylesheet are tested in a real browser, against a mock of the v16 desk. The mock includes Stock Addon's theme rules, so the tests also prove this app's colors and corners win over them. Serve the repository and open the test page:

```bash
python -m http.server 8765 --directory .
```

Then open <http://localhost:8765/tests/browser/>. `tests/browser/login_preview.html` shows the sign-in page with the shipped colors (add `?image=1` for the brand panel with a picture).

This app uses `pre-commit` for formatting and linting:

```bash
cd apps/cyvetech_ui
pre-commit install
```

### License

MIT
