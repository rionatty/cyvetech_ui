# Copyright (c) 2026, CyveTech and contributors
# For license information, please see license.txt

"""An alert sent to specific users.

Submitting it delivers it: every recipient gets a Notification Log of type
"Alert", the same record Frappe's own notifications use. That one record
puts the alert in the bell menu, in the My Alerts panel, and — because
Frappe publishes "notification" to the recipient when the record is
created — pops it up on their desk the moment it arrives.

With "Email It Too" ticked (the default), each recipient is also sent it by
email. A Notification Log of type "Alert" never sends an email of its own
(Frappe lists "Alert" in notification_skip_email_types: whatever sends the
alert owns its email), so without this nobody would get one.

Roles are expanded to their enabled users when the alert is submitted, and
those users are written into the Users table, which is also what decides who
may read the alert (permissions.py). Cancelling withdraws it from everyone
who has not read it yet.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_fullname, get_url_to_form, now_datetime, validate_email_address

from cyvetech_ui.cyvetech_ui import alerts_rules, color_rules
from cyvetech_ui.cyvetech_ui.settings import get_settings

# From this many recipients on, delivery runs as a background job, so a
# broadcast to a large role does not hold up the Submit button.
BACKGROUND_FROM = 200


class CyveTechUserAlert(Document):
	def validate(self):
		self.drop_duplicate_recipients()
		if not self.get("recipients") and not self.get("roles"):
			frappe.throw(_("Choose at least one user or role to send this alert to."))
		if bool(self.reference_doctype) != bool(self.reference_name):
			frappe.throw(_("To link a document, choose both its type and the document itself."))

	def before_submit(self):
		users = self.resolve_users()
		if not users:
			frappe.throw(_("None of the chosen users or roles has an enabled user to send this alert to."))
		named = {row.user for row in self.recipients}
		for user in users:
			if user not in named:
				self.append("recipients", {"user": user})
		self.sent_on = now_datetime()
		self.delivered_to = len(users)

	def on_submit(self):
		if len(self.recipients) >= BACKGROUND_FROM:
			frappe.enqueue(deliver, queue="short", alert=self.name, enqueue_after_commit=True)
		else:
			deliver(self.name)

	def on_cancel(self):
		withdraw(self.name)

	def drop_duplicate_recipients(self):
		seen = set()
		rows = []
		for row in self.get("recipients") or []:
			if row.user and row.user not in seen:
				seen.add(row.user)
				rows.append(row)
		self.set("recipients", rows)

	def resolve_users(self):
		"""The enabled users named, plus the enabled users holding any chosen role."""
		candidates = {row.user for row in self.get("recipients") or [] if row.user}
		roles = [row.role for row in self.get("roles") or [] if row.role]
		if roles:
			candidates.update(
				frappe.get_all(
					"Has Role",
					filters={"parenttype": "User", "role": ["in", roles]},
					pluck="parent",
				)
			)
		candidates.discard("Guest")
		if not candidates:
			return []
		return sorted(
			frappe.get_all("User", filters={"name": ["in", list(candidates)], "enabled": 1}, pluck="name")
		)


def deliver(alert):
	"""A Notification Log for every recipient of the alert and, unless the
	sender unticked Email It Too, an email to each of them."""
	doc = frappe.get_doc("CyveTech User Alert", alert)
	sender = doc.modified_by or frappe.session.user
	for row in doc.recipients:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"type": "Alert",
				"for_user": row.user,
				"from_user": sender,
				"subject": doc.subject,
				"email_content": doc.message,
				"document_type": doc.doctype,
				"document_name": doc.name,
			}
		).insert(ignore_permissions=True)
	if doc.send_email:
		doc.db_set("emailed_to", email(doc, sender), update_modified=False)


def email(doc, sender):
	"""The alert by email: one message, sent to each recipient separately, so
	no one sees the others' addresses. Frappe's email queue sends it from the
	default outgoing Email Account. Returns how many it went to; a failure is
	logged and never stops the alert reaching the desk."""
	addresses = recipient_addresses([row.user for row in doc.recipients])
	if not addresses:
		return 0
	if doc.reference_doctype and doc.reference_name:
		link = get_url_to_form(doc.reference_doctype, doc.reference_name)
		link_label = _("Open {0} {1}").format(_(doc.reference_doctype), doc.reference_name)
	else:
		link = get_url_to_form(doc.doctype, doc.name)
		link_label = _("Open the alert")
	settings = get_settings()
	product = settings.product_name or frappe.db.get_single_value("Website Settings", "app_name") or "ERPNext"
	priority = doc.priority or "Normal"
	try:
		frappe.sendmail(
			recipients=addresses,
			subject=doc.subject,
			message=alerts_rules.email_body(
				doc.message,
				priority,
				_(priority),
				link,
				link_label,
				_("Sent by {0} from {1}").format(get_fullname(sender), product),
				button=color_rules.normalize_hex(settings.login_button_color) or "#16335e",
			),
			header=[doc.subject, alerts_rules.EMAIL_INDICATOR.get(priority, "blue")],
			reference_doctype=doc.doctype,
			reference_name=doc.name,
			x_priority=alerts_rules.email_x_priority(priority),
			add_unsubscribe_link=0,  # a message to the team, like Frappe's own notification emails
			is_notification=True,
		)
	except Exception:
		frappe.log_error(title=f"CyveTech UI: alert {doc.name} could not be emailed")
		return 0
	return len(addresses)


def recipient_addresses(users):
	"""The valid email addresses of these users, enabled ones only, each once."""
	if not users:
		return []
	rows = frappe.get_all(
		"User", filters={"name": ["in", list(users)], "enabled": 1}, fields=["name", "email"]
	)
	addresses = []
	for row in rows:
		address = validate_email_address((row.email or row.name or "").strip())
		if address and address not in addresses:
			addresses.append(address)
	return addresses


def withdraw(alert):
	"""Take the alert back from everyone who has not read it yet."""
	frappe.db.delete(
		"Notification Log",
		{"document_type": "CyveTech User Alert", "document_name": alert, "read": 0},
	)


@frappe.whitelist(methods=["POST"])
def send_test_alert():
	"""Send the signed-in System Manager an alert, to see alerts working end to end."""
	frappe.only_for("System Manager")
	alert = frappe.get_doc(
		{
			"doctype": "CyveTech User Alert",
			"subject": _("Test alert from CyveTech UI"),
			"priority": "Normal",
			"message": _(
				"<p>If you can read this, alerts reach this account. On the desk they pop up "
				"the moment they arrive and are listed in My Alerts, and a copy goes to your email.</p>"
			),
			"send_email": 1,
			"recipients": [{"user": frappe.session.user}],
		}
	)
	alert.insert()
	alert.submit()
	return alert.name
