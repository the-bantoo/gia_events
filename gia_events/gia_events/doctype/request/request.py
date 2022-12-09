# Copyright (c) 2021, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Request(Document):
	def on_submit(self):
		"""if self.interest_type == "Speaking":
			if self.workflow_state == "Already Exists" or self.workflow_state == "Approved":
				pre_email_group = str(self.event_name) + " Speakers"

				email_groups(pre_email_group, self.email_address, self.event_name)

		elif self.interest_type == "Attending":
			if self.workflow_state == "Already Exists" or self.workflow_state == "Approved":
				pre_email_group = str(self.event_name) + " Attendee"

				email_groups(pre_email_group, self.email_address, self.event_name)

		elif self.interest_type == "Sponsoring":
			if self.workflow_state == "Already Exists" or self.workflow_state == "Approved":
				pre_email_group = str(self.event_name) + " Sponsors"

				email_groups(pre_email_group, self.email_address, self.event_name)

		elif self.interest_type == "Exhibiting":
			if self.workflow_state == "Already Exists" or self.workflow_state == "Approved":
				pre_email_group = str(self.event_name) + " Media"

				email_groups(pre_email_group, self.email_address, self.event_name)"""

# def email_groups(email_group, email, event_name):
# 	email_group_member =  frappe.get_doc({
# 		"doctype": "Email Group Member",
# 		"email_group": email_group,
# 		"event": event_name,
# 		"email": email
# 	})

# 	email_group_member.save()

# 	all_email_group_member =  frappe.get_doc({
# 		"doctype": "Email Group Member",
# 		"email_group": str(self.event_name) + " All",
# 		"event": event_name,
# 		"email": email
# 	})

# 	all_email_group_member.save()