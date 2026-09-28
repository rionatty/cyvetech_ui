# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""The sign-in page (login.html beside this file).

Frappe serves an app's www/login.html in place of its own, and then runs the
login.py that sits beside it, so this one first builds exactly the context
Frappe's own does and then adds the branded look. Frappe's get_context
raises a redirect for someone already signed in; that is left to happen.
"""

import frappe
from frappe.www.login import get_context as frappe_login_context

from cyvetech_ui.cyvetech_ui import login_rules
from cyvetech_ui.cyvetech_ui.asset_urls import versioned
from cyvetech_ui.cyvetech_ui.settings import get_settings

no_cache = True
STYLESHEET = "/assets/cyvetech_ui/css/cyvetech_ui_login.css"
SCRIPT = "/assets/cyvetech_ui/js/cyvetech_ui_login.js"


def get_context(context):
	frappe_login_context(context)
	cvt = look()
	cvt["stylesheet"] = versioned(STYLESHEET)
	cvt["script"] = versioned(SCRIPT)
	cvt["year"] = frappe.utils.now_datetime().year  # for the footer
	context.cvt = cvt
	if cvt["enabled"] and cvt["logo"]:
		context.logo = cvt["logo"]  # the logo on Frappe's card too
	return context


def look():
	"""Never in anyone's way of signing in: on any trouble, Frappe's own page."""
	try:
		return login_rules.look(get_settings())
	except Exception:
		frappe.log_error(title="CyveTech UI: sign-in page look")
		return {"enabled": 0}
