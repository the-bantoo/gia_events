# Copyright (c) 2021, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from gia_events.api import validate_industry
from frappe.model.document import Document
from gia_events.api import find_request_by_email
from gia_events.api import update_lead_import_tags_field

class DiscountRequest(Document):
	@frappe.whitelist()
	def set_lead_n_request(self):
		save = False

		if self.lead and self.request:
			return False
			
		leads = self.get_lead()
		requests = find_request_by_email(self.corporate_email)

		if leads:
			self.lead = leads[0].name
			save = True

		if requests:
			self.request = requests[0].name
			save = True
		
		if save:
			self.save()
			
		if leads or requests:
			return True
		else:
			return False

	
	@frappe.whitelist()
	def _add_tags_to_lead(self):
		""" creates relevant tags and adds them to the given lead if they arent already added """
		if self.lead:
			lead = frappe.get_doc("Lead", self.lead)		
		else:
			lead_name = get_lead(self.corporate_email)
			if lead_name:
				lead = frappe.get_doc("Lead", lead_name)
			else:
				return
			
		r_tags = self.get_tags()
		if not r_tags or r_tags[0]=='': return

		lead_tags = lead.get_tags()

		for tag in r_tags:
			if tag not in lead_tags:
				lead.add_tag(tag)
		
		# update import_tags field in lead
		update_lead_import_tags_field(lead)

	def insert_lead(self):
		fullname = self.full_name.split()
		l_name = ''
		
		if len(fullname) > 1:
			l_name = fullname[1]


		doc_dict = {
			'doctype': 'Lead',
			'email_id': self.corporate_email,
			'event': self.event_name,
			'company_name': self.company_name,
			'first_name': fullname[0],
			'last_name': l_name,
			"type": "Attendee",
			"request_type": "Attending",
			"unsubscribed": 1 if self.newsletter == 0 else 0,
			"terms_and_conditions": 1,
			"data_consent": 1,
			"first_request": self.creation,
		}
				
		req = self.get_request()
		if req:
			request = frappe.get_doc('Request', req[0].name)
			
			second_email = ''
			# Determine second_email based on the conditions
			if request.corporate_email and self.corporate_email != request.corporate_email:
				second_email = self.corporate_email
			elif request.corporate_email:
				second_email = request.corporate_email
				
			doc_dict.update({
				"event": request.event_name,
				"first_name": request.first_name,
				"last_name": request.last_name,
				"lead_name": request.full_name,
				"job_title": request.job_title,
				"company_name": request.company,
				"email_id": request.email_address,
				"second_email": second_email,
				"country": request.country,
				"phone": request.phone_number,
				"industry": validate_industry(request.industry),
				"type": request.type,
				"request_type": request.interest_type,
				"mobile_no": request.phone_number,
				"lead_number": request.phone_number,
				"address": request.address,
				"city": request.city,
				"source": request.source,
				"terms_and_conditions": request.terms_conditions,
				"data_consent": 1,
				"first_request": request.creation,
			})
			frappe.msgprint('A new Lead has been created along with data from a related Attendance Request')

		new_lead = frappe.get_doc(doc_dict)
		new_lead.insert(ignore_permissions=True)
		frappe.db.commit()
		if not req:
			frappe.msgprint('A new Lead has been created for the discount request, no related Attendance Request was found, so some info will need updating')
		return frappe.get_doc("Lead", new_lead.name)

	def get_lead(self):
		sql = """select `name`
		from `tabLead`
		where `email_id` = '{}' or `second_email` = '{}'
		
		order by `creation` DESC
		limit 1 offset 0
		""".format(self.corporate_email, self.corporate_email)

		return frappe.db.sql(sql, as_dict=1)

	def get_request(self):
		sql = """select `name`
		from `tabRequest`
		where `email_address` = '{}' or `corporate_email` = '{}'
		
		order by `creation` DESC
		limit 1 offset 0
		""".format(self.corporate_email, self.corporate_email)
		return frappe.db.sql(sql, as_dict=1)

	
	def on_update(self):
		"""
		- Create lead if non exists
		- Add tags to lead if Lead exists and add email subscription """

		lead_exists = []
		if self.workflow_state == "Confirmed":

			if self.lead:
				lead = frappe.get_doc('Lead', self.lead)
			else:
				lead_exists = self.get_lead()

				if lead_exists:
					lead = frappe.get_doc('Lead', lead_exists[0].name)
				else:
					# create, if lead doesnt exist
					lead = self.insert_lead()			

			event = frappe.get_cached_doc('Events', self.event_name)
			event_email_group = event.sub_group
			
			if not event.sub_group:
				frappe.throw("Please setup a Newsletter Email Group in event <strong>{}</strong>".format(self.event_name))

			# add egm if not exist
			self.add_new_emailgroupmember(event_email_group)

			# create and add event tags 
			import_tags = self.add_tags_to_lead(lead)
			frappe.db.set_value("Lead", lead.name, "import_tags", import_tags, update_modified=False)
			
			if not self.lead_has_email_group(lead, event_email_group):
				""" add the email group to the lead's email groups """			
				
				# first uncheck unsub if it is checked
				if lead.unsubscribed == 1:
					lead.unsubscribed = 0
				
				eg_sub = lead.append("email_group_subscriptions", {
					"subscription": event_email_group
				})
				eg_sub.insert(ignore_permissions=True)

			


	def lead_has_email_group(self, lead, email_group):
		for eg in lead.email_group_subscriptions:
			if eg.subscription == email_group:
				return True
		return

	def add_new_emailgroupmember(self, event_email_group):
		""" adds new email group member if it doesnt exist """
		egm = frappe.get_all('Email Group Member', filters={'email_group': event_email_group, 'email': self.corporate_email}, limit=0)
		if egm: return

		new_egm = frappe.get_doc({
			'doctype': 'Email Group Member', 
			'email_group': event_email_group, 
			'email': self.corporate_email
			})
		new_egm.insert(ignore_mandatory=True)

	def add_tags_to_lead(self, lead):
		""" creates relevant tags and adds them to the given lead if they arent already added """
		tags = self.create_tags()
		existing_tags = lead.get_tags()

		for tag in tags:
			if tag not in existing_tags:
				lead.add_tag(tag)
		
		# update import_tags field in lead
		return self.update_lead_import_tags_field(lead)

	def create_tags(self):
		tags = ['Discount Request', self.event_name]
		initials = self.get_initials(self.event_name)
		#year = self.get_year()
		#tags.append('{} Delegate {}'.format(initials, year))
		tags.append(initials)

		return tags

	def get_initials(self, input_string):
		words = input_string.split()
		initials = [word[0].upper() for word in words]
		return ''.join(initials)

	def get_year(self):
		date = getdate()
		return str(date.year)


	def update_lead_import_tags_field(self, lead):
		tags = self.get_tag_string(lead)

		if tags == "" or tags == lead.import_tags:
			return
		else:
			tag_len = len(tags or "")
			import_tag_len = len(lead.import_tags or "")

			if tag_len >= 0:
				return tags


	
	def get_tag_string(self, lead):
		tags = lead.get_tags()
		if tags:
			if len(tags) == 0 or tags[0] == '':
				tag_string = ""
			else:
				tag_string = ", ".join(tags)
		elif lead.event:
			tag_string = lead.event
		else:
			tag_string = ""
		return tag_string