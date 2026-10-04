// Copyright (c) 2026, CyveTech and contributors
// For license information, please see license.txt

frappe.ui.form.on("CyveTech User Alert", {
	setup(frm) {
		// a Table MultiSelect is a Link control underneath: the query goes on the field itself
		frm.set_query("recipients", () => ({ filters: { enabled: 1, user_type: "System User" } }));
		frm.set_query("reference_doctype", () => ({ filters: { istable: 0, issingle: 0 } }));
	},

	refresh(frm) {
		const manager = frappe.user.has_role("System Manager");
		// who else received an alert is the sender's business, not each recipient's
		frm.toggle_display(["section_recipients"], manager);

		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.page.set_primary_action(__("Send"), () => frm.save("Submit"));
		}
		if (frm.doc.reference_doctype && frm.doc.reference_name) {
			frm.add_custom_button(__("Open {0}", [__(frm.doc.reference_doctype)]), () =>
				frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name)
			);
		}
		if (frm.doc.docstatus === 1 && manager) {
			const sent = [__("Sent to {0} user(s).", [frm.doc.delivered_to || 0])];
			if (frm.doc.send_email) sent.push(__("Emailed to {0} of them.", [frm.doc.emailed_to || 0]));
			sent.push(
				frm.doc.send_email
					? __("Cancelling takes it off the desk for anyone who has not read it yet; emails already sent stay sent.")
					: __("Cancelling withdraws it from anyone who has not read it yet.")
			);
			frm.set_intro(sent.join(" "), "blue");
		}
	},
});
