# Copyright (c) 2021, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from gia_events.api import update_lead_import_tags_field, get_lead

class Request(Document):
	def on_update(self):
		self.add_tags_to_lead()


	@frappe.whitelist()
	def add_tags_to_lead(self):
		""" creates relevant tags and adds them to the given lead if they arent already added """
		if self.lead:
			lead = frappe.get_doc("Lead", self.lead)
		else:
			lead_name = get_lead(self.email_address)
			if lead_name:
				lead = frappe.get_doc("Lead", lead_name)
			else:
				return
			
		r_tags = get_tags(self.doctype, self.name)
		
		if not r_tags or r_tags[0]=='': return

		lead_tags = lead.get_tags()

		for tag in r_tags:
			if tag not in lead_tags:
				lead.add_tag(tag)
		
		# update import_tags field in lead
		update_lead_import_tags_field(lead)


	def on_submit(self):
		pass
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

def get_tags(doc, name):
		return frappe.get_all("Tag Link", fields=["tag"], filters={'document_type': doc, 'document_name': name}, limit=0, pluck='tag')