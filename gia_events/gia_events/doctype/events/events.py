# Copyright (c) 2021, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Events(Document):
	def after_insert(self):
		email_groups = ["All", "Media", "Sponsors", "Speakers", "Attendees", "Subscription"]
		
		for email_group in email_groups:
			if not frappe.db.exists("Email Group", str(self.event_name) + " " + email_group):
				recipient_type = "All"

				if email_group == "Media":
					recipient_type = "Media"

				elif email_group == "Sponsors":
					recipient_type = "Sponsor"

				elif email_group == "Speakers":
					recipient_type = "Speaker"

				elif email_group == "Subscription":
					recipient_type = "Newsletter"

				elif email_group == "Attendees":
					email_group = "Attendees"

				new_email_group = frappe.get_doc({
					"doctype": "Email Group",
					"title": str(self.event_name) + " " + str(email_group),
					"recipient_type": recipient_type,
					"event": self.event_name
				})

				new_email_group.save()
