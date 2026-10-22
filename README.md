### CyveTech UI

Branding, theme, a desk home with a dashboard for each ERPNext module, module pages, desk modules, and user alerts for the Frappe / ERPNext desk, all managed from one settings page: **CyveTech UI Settings**.

Built for Frappe / ERPNext **v16**. It installs on v15 too, where everything works except the desk home and its dashboards, the module pages and the desk-module tiles, which are built on v16's desk.

---

### What it does

| | Feature | Where to set it |
|---|---|---|
| 1 | **Desk colors.** Pick the left sidebar color, the selected-item highlight and the page background (the central area). Sidebar text switches between white and dark automatically so it always stays readable. | Settings → Desk Theme |
| 2 | **Smooth tiles.** Rounded corners on the desktop's app tiles and on workspace cards (number cards, shortcuts, link lists, charts), with an adjustable radius. | Settings → Desk Theme |
| 3 | **Chart colors.** An eight-color palette for every chart on the desk, checked for color-blind readers. A single-series chart takes a color from its title, so charts side by side look different and each one keeps its color. Charts that choose their own colors on purpose (red for overdue) keep them. | Settings → Charts |
| 4 | **Branded sign-in page.** One card with your logo, a heading and Frappe's own sign-in form, over a backdrop in your brand colors, or over a full-screen photo of your choice. | Settings → Sign-in Page |
| 5 | **Navigation logo and browser icon.** Replace the ERPNext and Frappe logos (the "E") on the desktop's top bar, the loading screen, the app switcher and the sign-in page, put your mark at the top of the navigation pane, and set the browser-tab icon (favicon). Optionally rename "ERPNext" to your product name. | Settings → Branding |
| 6 | **My Alerts.** A panel in the bottom-right corner showing each user's own open assignments ("overdue by 8 days"), notifications and alerts, most urgent first, straight from ERPNext's own records. Admins can also send an alert to specific users or roles with **CyveTech User Alert**, by email too. | Settings → Alerts, and CyveTech User Alert |
| 7 | **Desk modules.** Choose which tiles show on everyone's desktop: every module, listed under its app or folder. | Settings → Desk Modules |
| 8 | **Pop-ups.** New notifications and alerts pop up the moment they arrive (within a minute if the site's realtime server is down). Alerts from ERPNext's own Notification rules and from CyveTech User Alert always pop up, and one that arrived while someone was away pops up the next time they open the desk. Sent alerts marked Important stay until closed; Urgent ones must be acknowledged. | Settings → Alerts |
| 9 | **Desk home for ERPNext.** The desk opens on a home: a greeting, what waits for each user, a button for the document they make most, and the pages they open most a click away. The modules run down the left in the order work flows through ERPNext, each opening to its own menu. | Settings → Home |
| 10 | **A dashboard for each module.** A row of tabs on the home: an **Overview** (the day's headline figures, what waits, everything that needs attention, and the user's unfinished drafts), then a dashboard for each module the user is assigned: Accounts, Sales, Purchasing, Stock, Manufacturing, Projects, CRM, Support, Assets and Quality. Each has the module's own figures, charts and lists (profit and loss by month, receivables and payables aging, expenses by account, sales by territory, quotations won and lost, stock by warehouse, work orders by status, projects' progress, hours by project, issues by priority...), what needs attention in it, and the reports decisions are made from, each opening for the user's company. Each tab counts what needs attention in it, so the pressing module shows from the overview. Every figure, bar, slice and row opens the documents behind it. | Settings → Home |
| 11 | **Module pages.** Each module (Selling, Buying, Stock, Invoicing...) opens under a header in the home's look: its picture, the groups of its menu, what needs attention in it, its step in the flow from lead to cash, what waits for the user there, a button for the document they make most there, and a **Dashboard** button that opens the module's tab on the desk. ERPNext's own figures, charts and cards follow, restyled to match. | Settings → Home |
| 12 | **Grouped menus and every color a setting.** The sidebar's groups (Selling's POS, Setup, Reports) read as headings with their entries under a guide line. The header, the accent and the status colors (overdue, due today, done) are settings, used by the home, the module pages and My Alerts alike. | Settings → Desk Theme |

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
6. **Home:** the desk home, its dashboards and the module pages are on from the start. Under **Dashboard Tabs**, untick any module whose dashboard shouldn't show for anyone. The header and status colors are under **Desk Theme**: keep the header dark, since white text goes on it (the page warns when a color is too light).

Save once, and every user sees the change on their next page load.

**ERPNext's own alerts:** any Notification rule (search "Notification") whose **Channel** is "System Notification", or that has **Send System Notification** ticked, shows in the bell and My Alerts and pops up with its message. For an email as well as the pop-up, set the **Channel** to Email and tick **Send System Notification**. A rule on the System Notification channel never sends an email: in Frappe v16 a rule's email comes only from its Email channel. With the default channel, Email, and the box unticked, it only sends an email.

**Sending an alert:** create a **CyveTech User Alert**, pick the users and/or roles, choose a priority (Normal, Important, Urgent) and optionally link a document, then **Send**. Each recipient gets it in the bell menu and in My Alerts, as a pop-up, and with **Email It Too** ticked (the default) by email as well: one email each, so nobody sees who else got it. Recipients can only read alerts sent to them. Cancelling an alert withdraws it from everyone who hasn't read it yet.

---

### Good to know

- **Colors apply in light mode.** Dark mode keeps Frappe's own dark colors.
- **Which dashboards each user gets.** A module's tab shows when the module is assigned to the user (not blocked under **Allowed Modules** on their User record, or by their Module Profile; a module blocked for Administrator is blocked for everyone) and they may read its documents: the Sales tab needs Sales Orders or Quotations, the Stock tab the stock ledger, and so on. Within a tab, a figure or chart they may not read is left out, and only the reports they may open are offered. So a storekeeper gets the Stock tab first, and the Sales and Purchasing tabs too where they may read sales and purchase orders, unless Selling and Buying are unticked under their Allowed Modules. The tabs come in the order of what the user's roles are about, the money first, then the rest. A user with no module's documents to read gets the overview alone: what waits for them and their drafts.
- **Every figure is read with the user's own permissions**, so User Permissions narrow it the way they narrow the lists: a sales clerk limited to one territory sees that territory's orders.
- **Money on the home is the user's default company's**, in its currency. Invoices owed in another currency are converted at today's rate from Currency Exchange.
- **A tab's figures are read when it's first opened,** and kept for five minutes per user, so a desk that's opened often doesn't query the database every time. **Refresh**, beside the tab's heading, reads everything shown so far again on the spot. The home opens on the tab the user had open last.
- **The desk can always be edited as before.** While someone edits the desktop, the home steps aside and the tiles are Frappe's own again. Any part of the home that can't be read is left out and written to the Error Log; the desk itself always opens.
- **Emails need the site's outgoing email set up:** an Email Account with **Default Outgoing** ticked, and the scheduler running, which sends the Email Queue every minute. If an alert's email doesn't arrive, look in the **Email Queue** list for the reason.
- **Pop-ups arrive instantly through Frappe's realtime (socket.io) server.** If it isn't running, nothing is lost: My Alerts checks every minute while the page is open, and straight away when someone comes back to the tab or moves to another page.
- **Frappe's Getting Started checklist** opens in the same corner as My Alerts. While it's open, My Alerts moves over to sit beside it. On a phone, the checklist moves up above My Alerts instead.
- **To check My Alerts in a browser**, open the console (F12) and run `cyvetech_ui.alerts_status()`. It shows the signed-in user, whether the panel is on the page, whether the realtime socket is connected, and when the list last loaded.
- **Hiding a module changes what shows, not who may open it.** Use roles and Module Profiles for access. Users who have rearranged their own desktop keep their layout, and hidden modules are hidden for them too.
- **Blank logo fields leave your current logos alone.** Clearing a logo here removes only what this app put in Website Settings and Navbar Settings. A logo set there by hand is never touched.
- **With Stock Addon or HRMS Addon installed:** both ship their own navy theme. CyveTech UI's colors take over theirs, as long as **Use Custom Colours** in *Stock Addon Theme Settings* / *HRMS Addon Theme Settings* is switched off. Its theme also keeps Frappe's white panels (the bell's notifications list and the Getting Started checklist) readable beside theirs. HRMS Addon also has its own My Alerts panel and sign-in page. Use one or the other: switch off **Show the My Alerts Panel** here, or remove HRMS Addon's. The sign-in page shown is the one from whichever app was installed last. HRMS Addon also has its own HR desk home and module pages: where those are on, CyveTech UI's step aside, so a site has one home, not two.

---

### Development

The Python tests run without a bench. They cover the rules behind the colors, alerts, sign-in page, desk modules and the desk home, and the server code, which runs against a small in-memory stand-in for Frappe (`tests/fake_frappe.py`). The home's tests put a small ERPNext company in it, and check what each kind of user is shown and that nothing they may not read is ever asked for:

```bash
python -m unittest discover -s tests -v
```

The desk scripts and stylesheets are tested in a real browser, against a mock of the v16 desk. The mock includes Stock Addon's and HRMS Addon's theme rules, so the tests also prove this app's colors and corners win over them. A layout test checks where My Alerts sits beside Frappe's Getting Started checklist at desktop and phone widths, and the sign-in tests run against Frappe's own sign-in markup and styles. The home and module page tests run on mocks of v16's desk page and of a workspace, with Frappe's own desktop styles: the tabs and every figure, chart and click on them, the keyboard, a module page's Dashboard button, the modules down the left, editing the desk, a call that fails, and a phone's and a wide screen's width. Serve the repository with the browser's cache switched off, so every run loads the files as they are on disk:

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
