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
| 4 | **Branded sign-in page.** One card with your logo, a heading and Frappe's own sign-in form, over a backdrop in your brand colors, or over a full-screen photo of your choice. | Settings → Sign-in Page |
| 5 | **Navigation logo and browser icon.** Replace the ERPNext and Frappe logos (the "E") on the desktop's top bar, the loading screen, the app switcher and the sign-in page, put your mark at the top of the navigation pane, and set the browser-tab icon (favicon). Optionally rename "ERPNext" to your product name. | Settings → Branding |
| 6 | **My Alerts.** A panel in the bottom-right corner showing each user's own open assignments ("overdue by 8 days"), notifications and alerts, most urgent first, straight from ERPNext's own records. Admins can also send an alert to specific users or roles with **CyveTech User Alert**. | Settings → Alerts, and CyveTech User Alert |
| 7 | **Desk modules.** Choose which tiles show on everyone's desktop: every module, listed under its app or folder. | Settings → Desk Modules |
| 8 | **Pop-ups.** New notifications and alerts pop up the moment they arrive (within a minute if the site's realtime server is down). Alerts from ERPNext's own Notification rules and from CyveTech User Alert always pop up, and one that arrived while someone was away pops up the next time they open the desk. Sent alerts marked Important stay until closed; Urgent ones must be acknowledged. | Settings → Alerts |

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

Nothing needs `bench build`: the app's CSS and JavaScript are plain assets. Each is linked with a hash of its contents, so after an update every browser picks up the new files on its next page load, with no hard refresh.

**To update later:**

```bash
cd ~/frappe-bench/apps/cyvetech_ui && git pull && cd ~/frappe-bench && bench --site YOUR-SITE migrate && bench --site YOUR-SITE clear-cache && bench restart
```

---

### Setting it up

Open **CyveTech UI Settings** from the search bar (System Managers only).

1. **Branding:** upload the navigation logo (a wide logo, about 240 × 64 px) and a square browser icon. The browser icon also goes at the top of the navigation pane, where there's only room for a square. Upload both as **public** files: the sign-in page and the browser tab are seen before anyone logs in.
2. **Desk Theme:** the defaults are CyveTech navy and gold. The preview updates as you type.
3. **Sign-in Page:** leave the sign-in logo blank to reuse the navigation logo. The background photo is optional: use a photo at least 1600 px wide. A smaller picture, or the logo itself, isn't used, because stretched across the screen it would look blurry.
4. **Desk Modules:** click **Load Desk Modules**, untick what should not show, and save. Every tile is listed, each module under its group: an app (such as ERPNext) or a folder (such as Accounting). A hidden group doesn't hide its modules: Frappe shows them on the desk one by one instead, which is how ERPNext ships, with its own tile hidden. So when you untick a group, you're asked whether to take its modules off the desk too.
5. **Alerts:** click **Send Me a Test Alert** to see a pop-up and the My Alerts panel working end to end.

Save once, and every user sees the change on their next page load.

**ERPNext's own alerts:** any Notification rule (search "Notification") whose **Channel** is "System Notification", or that has **Send System Notification** ticked, shows in the bell and My Alerts and pops up with its message. With the default channel, Email, and the box unticked, it only sends an email.

**Sending an alert:** create a **CyveTech User Alert**, pick the users and/or roles, choose a priority (Normal, Important, Urgent) and optionally link a document, then **Send**. Each recipient gets it in the bell menu and in My Alerts, as a pop-up. Recipients can only read alerts sent to them. Cancelling an alert withdraws it from everyone who hasn't read it yet.

---

### Good to know

- **Colors apply in light mode.** Dark mode keeps Frappe's own dark colors.
- **Pop-ups arrive instantly through Frappe's realtime (socket.io) server.** If it isn't running, nothing is lost: My Alerts checks every minute while the page is open, and straight away when someone comes back to the tab or moves to another page.
- **Frappe's Getting Started checklist** opens in the same corner as My Alerts. While it's open, My Alerts moves over to sit beside it. On a phone, the checklist moves up above My Alerts instead.
- **To check My Alerts in a browser**, open the console (F12) and run `cyvetech_ui.alerts_status()`. It shows the signed-in user, whether the panel is on the page, whether the realtime socket is connected, and when the list last loaded.
- **Hiding a module changes what shows, not who may open it.** Use roles and Module Profiles for access. Users who have rearranged their own desktop keep their layout, and hidden modules are hidden for them too.
- **Blank logo fields leave your current logos alone.** Clearing a logo here removes only what this app put in Website Settings and Navbar Settings. A logo set there by hand is never touched.
- **With Stock Addon or HRMS Addon installed:** both ship their own navy theme. CyveTech UI's colors take over theirs, as long as **Use Custom Colours** in *Stock Addon Theme Settings* / *HRMS Addon Theme Settings* is switched off. Its theme also keeps Frappe's white panels (the bell's notifications list and the Getting Started checklist) readable beside theirs. HRMS Addon also has its own My Alerts panel and sign-in page. Use one or the other: switch off **Show the My Alerts Panel** here, or remove HRMS Addon's. The sign-in page shown is the one from whichever app was installed last.

---

### Development

The Python tests run without a bench. They cover the rules behind the colors, alerts, sign-in page and desk modules, and the server code, which runs against a small in-memory stand-in for Frappe (`tests/fake_frappe.py`):

```bash
python -m unittest discover -s tests -v
```

The desk scripts and stylesheets are tested in a real browser, against a mock of the v16 desk. The mock includes Stock Addon's and HRMS Addon's theme rules, so the tests also prove this app's colors and corners win over them. A layout test checks where My Alerts sits beside Frappe's Getting Started checklist at desktop and phone widths, and the sign-in tests run against Frappe's own sign-in markup and styles. Serve the repository with the browser's cache switched off, so every run loads the files as they are on disk:

```bash
python tests/browser/serve.py
```

Then open <http://localhost:8766/tests/browser/>. `tests/browser/login_preview.html` shows the sign-in page with the shipped colors: add `?photo=big` for a background photo, or `#forgot` for the forgot-password step.

This app uses `pre-commit` for formatting and linting:

```bash
cd apps/cyvetech_ui
pre-commit install
```

### License

MIT
