# Copyright (c) 2021, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import requests
import json
from frappe.utils import today
import re
from twilio.rest import Client
import os
from twilio.twiml.voice_response import Dial, VoiceResponse, Say
from frappe.utils.password import get_decrypted_password


def p(*args):
	if True:
		print(*args)

def ep(arg):
	if True:
		frappe.errprint(arg)

def update_lead(lead, method):
	#update_tags(lead)
	email_group(lead, method)


def email_group(lead, method):
	if lead.unsubscribed == 1 or not lead.event:
		return

	if lead.request_type:
		data = {"Speaking": "Speakers", "Attending": "Attendees", "Sponsoring": "Sponsors", "Exhibiting": "Media"}
		email_group = str(lead.event) + " " + data[lead.request_type]
		group_membership = frappe.get_list('Email Group Member', filters={'email_group': email_group, 'email': lead.email_id})

		ep(email_group)

		if len(group_membership) < 1:
			sub_to_group(email_group, lead.email_id, lead.event)
	
	all_group_membership = frappe.get_list('Email Group Member', filters={'email_group': lead.event + " All", 'email': lead.email_id})
	
	ep(all_group_membership)

	if len(all_group_membership) < 1:
		add_email_sub_all(lead.email_id, lead.event)

	subscription_update(lead, lead.email_id, lead.event)

	


"""
	adds email to particular email group and to "All" email group
"""
def subscription_update(lead, email, event):
	membership = frappe.get_list('Email Group Member', fields={'name', 'unsubscribed'}, filters={'email_group': lead.event + " Subscription", 'email': lead.email_id})
	if not lead.event:
		return
		
	if len(membership) < 1:
		
		all_email_group_member =  frappe.get_doc({
			"doctype": "Email Group Member",
			"email_group": str(event) + " Subscription",
			"event": event,
			"email": email
		})
		all_email_group_member.insert(ignore_permissions=True)

	else:
		if (membership[0].unsubscribed == 1 and lead.unsubscribed == 0) or (membership[0].unsubscribed == 0 and lead.unsubscribed == 1):
			m =  frappe.get_doc("Email Group Member", membership[0].name)
			m.unsubscribed = lead.unsubscribed
			m.save(ignore_permissions=True)
	
	frappe.db.commit()


def sub_to_group(email_group, email, event):

	email_group_member =  frappe.get_doc({
		"doctype": "Email Group Member",
		"email_group": email_group,
		"event": event,
		"email": email
	})
	email_group_member.insert(ignore_permissions=True)

def add_email_sub_all(email, event):

	all_email_group_member =  frappe.get_doc({
		"doctype": "Email Group Member",
		"email_group": str(event) + " All",
		"event": event,
		"email": email
	})
	all_email_group_member.insert(ignore_permissions=True)

	


@frappe.whitelist(allow_guest=True)
def test_api():
	return "API Called"

@frappe.whitelist(allow_guest=True)
def register_click(link):
	url = frappe.db.exists({
		"doctype": "Email Links",
		"original_url": link
	})
	if url:
		# frappe.errprint(url)  
		# frappe.errprint(url[0])
		#original_url = frappe.db.sql("""SELECT original_url FROM `tabEmail Links` WHERE """)
		#Get current click count
		click_count = frappe.db.sql("""SELECT click_rate FROM `tabEmail Links` WHERE name=%s """, url[0])
		
		if click_count != None:
			next_count = click_count[0][0] + 1
			#return next_count
		
			return frappe.db.sql("""UPDATE `tabEmail Links` SET clicked = 1, click_rate = %s WHERE original_url=%s""", (next_count, link))


@frappe.whitelist(allow_guest=True)
def read_receipt(em_id):
	doc = frappe.get_doc("Email Queue", em_id)
	doc.read_by_recipient = 1
	doc.save()
	frappe.db.commit()


@frappe.whitelist()
def call_logs():
	account_sid = frappe.db.get_single_value("Twilio Settings", "twilio_account_sid")
	auth_token = frappe.db.get_single_value("Twilio Settings", "twilio_auth_token")
	d_pass = get_decrypted_password(auth_token)
	client = Client(account_sid, d_pass)

	calls = client.calls.list()

	call_log = []

	for c in calls:
		log = {
			"from_": c.from_,
			"to": c.to,
			"duration": c.duration,
			"status": c.status
		}
		call_log.append(log)

	return call_log

@frappe.whitelist(allow_guest=True)
def make_call(to_number, logged_in_user):

	ts = frappe.get_doc('Twilio Settings')
	account_sid = ts.account_sid
	auth_token = ts.auth_token
	twilio_number = ts.twilio_number
	d_pass = get_decrypted_password("Twilio Settings", "Twilio Settings", 'auth_token')

	client = Client(account_sid, d_pass)

	try:
		erpnext_caller_number = frappe.db.get_value("User", {"email": logged_in_user}, "phone")

		call = client.calls.create(
			record=True,
			to=str(to_number),
			from_=str(twilio_number),
			url="http://twimlets.com/holdmusic?Bucket=com.twilio.music.ambient",
			twiml=f'<Response><Dial>{erpnext_caller_number}</Dial></Response>'
			#url="https://crm.giaglobalgroup.com/twilio_call/voice.xml"

		)

		new = frappe.get_doc({
			"doctype": 'GIA Call Log',
			"from": str(twilio_number),
			"to": str(to_number),
			"type_of_call": 'Outgoing',
			"status": call.status,
			"duration": call.duration,
			"date": call.date_created,
		})
		new.flags.ignore_permission = True
		frappe.msgprint(_("Calling 📞 {to_number}").format(to_number=to_number))
		new.insert()

	except Exception as e:
		frappe.throw(str(e))

@frappe.whitelist(allow_guest=True)
def answer_call(from_number):
	ignore_permissions = True

	# Create call log
	call_log = frappe.get_doc({
		"doctype": "Call Log Twilio",
		"caller_number": from_number
	})
	call_log.insert(ignore_permissions=True)
	# return last_call[0]

@frappe.whitelist(allow_guest=True)
def check_number(phone_number):
	ignore_permissions = True

	account_sid = frappe.db.get_single_value("Twilio Settings", "twilio_account_sid")
	auth_token = frappe.db.get_single_value("Twilio Settings", "twilio_auth_token")
	client = Client(account_sid, auth_token)

	calls = client.calls.list(limit=1)

	last_call = []

	for c in calls:
		last_call.append(c.from_)

	return last_call[0]

	number_exists = frappe.db.exists({
		'doctype': 'Contact Phone',
		'phone': phone_number
	})

	if not number_exists:
		# Contact doesn't, create new

		doc = frappe.get_doc({
			"doctype": "Contact",
			"first_name": "Unknown",
		})

		doc.insert(ignore_permissions=True)

		row = doc.append("phone_nos", {
			"phone": phone_number
		})

		row.insert(ignore_permissions=True)
		return "Strange number"

	else:
		return "Number exists"
			   
def update_link_newsletter(newsletter, method):
	data = newsletter.message

	patterns = {"link": 'href rel'}
	site_url = frappe.utils.get_url()

	for pattern in patterns.values():
		result = re.findall(pattern, data)
		for link in result:
			if site_url not in link:
				#frappe.errprint("{link} has no {site_url}".format(link=link, site_url=site_url))
				tracking_link = site_url + "/email-tracking?link=" + link
				data = data.replace(link, tracking_link)

				newsletter.message = data
				row = newsletter.append("email_links", {
					"link_id": tracking_link,
					"original_url": link
					})
				row.insert()
				newsletter.save()
				newsletter.reload()
			
	#newsletter.message += '<img src="https://script.google.com/macros/s/AKfycbxJUkxR-xCwSHtGh04r3hvQyzcytLRCGwFwyovD3WZvVawx8WI/exec?email_id=%s" height="1" width="1" />' % newsletter.name
	#newsletter.save()
	frappe.db.commit()

def add_pixel_tracker(email_queue, method):
	email_queue.message += '<img src="https://script.google.com/macros/s/AKfycbxJUkxR-xCwSHtGh04r3hvQyzcytLRCGwFwyovD3WZvVawx8WI/exec?email_id=%s" height="1" width="1" />' % email_queue.name

	#Add email links
	if email_queue.reference_doctype == "Newsletter":
		newsletter_name = frappe.get_doc("Newsletter", email_queue.reference_name)

		#Empty table to avoid duplicates
		email_queue.email_links.clear()

		for link in newsletter_name.email_links:
			email_queue.append("email_links", {
				"link_id": link.link_id,
				"original_url": link.original_url,
				"clicked": link.clicked,
				"click_rate": link.click_rate
			})

	email_queue.save()
	frappe.db.commit()
   
@frappe.whitelist()
def delete_spam():
	frappe.db.delete("Request", {
	"workflow_state": "Spam"
	})
	frappe.db.commit()
	


def create_project(event, method):
	new_project = frappe.get_doc({
		"doctype": "Project",
		"project_name": event.event_name,
		"project_type": "Event"
		})
	new_project.insert(ignore_permissions=True)

	new_tag = frappe.get_doc({
		"doctype": "Tag",
		"__newname": event.event_name
		})
	new_tag.insert(ignore_permissions=True)
	frappe.db.commit()

def add_project(project, method):
	doc = frappe.get_doc("Events", project.project_name)
	doc.project_name = project.name
	doc.save()
	frappe.db.commit()

def link_lead(lead, method):
	requests = frappe.db.get_list('Request', filters={'email_address': lead.email_id}, fields=['name'])
	if len(requests) > 0:
		frappe.db.set_value("Request", requests[0]['name'], "lead", lead.name)
		frappe.db.commit()


def email_member(discount_request, method):
	event = frappe.get_doc("Events", discount_request.event_name)
	if discount_request.newsletter == True:
		if not frappe.db.exists({'doctype': 'Email Group Member', 'email_group': event.sub_group, 'email': discount_request.corporate_email}):
			email_member = frappe.get_doc({
				"doctype": "Email Group Member",
				"email": discount_request.corporate_email,
				"email_group": event.sub_group
				})
			email_member.insert(ignore_permissions=True)
	frappe.db.commit()

@frappe.whitelist()
def count_subscribers(email_group):
	total_subscribed = frappe.db.count('Email Group Member', {'unsubscribed': False, 'email_group': email_group})
	total_unsubscribed = frappe.db.count('Email Group Member', {'unsubscribed': True, 'email_group': email_group})
	return total_subscribed, total_unsubscribed

def attendee_exists(request, method):
	if frappe.db.exists({'doctype': 'Lead', 'email_id': request.email_address}):
		#Link Lead to Request
		data = frappe.db.sql("""SELECT name FROM `tabLead` WHERE email_id = %s""", (request.email_address)) #improve
		frappe.db.set_value('Request', request.name, {
				'lead': data[0][0],
				"already_exists": True
			}, update_modified=True)


	if request.request_type == "Paid Request":
		if frappe.db.exists({'doctype': 'Lead', 'email_id': request.email_address}):
			#Link Lead to Request
			data = frappe.db.sql("""SELECT name FROM `tabLead` WHERE email_id = %s""", (request.email_address))
			frappe.db.set_value('Request', request.name, {
				'lead': data[0][0],
				"already_exists": True,
				"workflow_state": "Paid Request"
				})
		else:
			frappe.db.set_value("Request", request.name, "workflow_state", "Paid Request")

	if request.newsletter == True:
		event = frappe.get_doc("Events", request.event_name)
		if not event.sub_group:
			frappe.throw(_("Please set <strong>email groups</strong> in {event}").format(event=event.name))

		if not frappe.db.exists({'doctype': 'Email Group Member', 'email_group': event.sub_group, 'email': request.email_address}):
			email_member = frappe.get_doc({
				"doctype": "Email Group Member",
				"email": request.email_address,
				"email_group": event.sub_group
				})
			email_member.insert(ignore_permissions=True)
	frappe.db.commit()

def update_email_group_subs(doc, method):
	email_group = frappe.get_doc("Email Group", doc.email_group)
	email_group.update_total_subscribers()
	

def reduce_email_group_subs(doc, method):
	email_group = frappe.get_doc("Email Group", doc.email_group)
	subs = int(email_group.get_total_subscribers()) - 1
	frappe.set_value("Email Group", email_group.name, 'total_subscribers', subs)
	frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def add_lead_to_request(request):
	# create lead and attach it to the request

	# if origin is javascript
	if type(request) is str: 
		request = frappe.get_doc("Request", request)
	
	# ep('add_lead_to_request')

	try:
		if request.already_exists == 0:
			if not request.lead:
				leads = frappe.get_list("Lead", filters={'email_id': request.email_address})
				if len(leads) > 0:
					frappe.set_value("Request", request.name, 'lead', leads[0].name)
				else:
					new_lead = frappe.get_doc({
						"doctype": "Lead",
						"event": request.event_name,
						"first_name": request.first_name,
						"last_name": request.last_name,
						"lead_name": request.full_name,
						"job_title": request.job_title,
						"company_name": request.company,
						"email_id": request.email_address,
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
						"unsubscribed": 1 if request.newsletter == 0 else 0,
						"terms_and_conditions": request.terms_conditions,
						"data_consent": 1
					})
					new_lead.insert(ignore_permissions=True)
					
					frappe.set_value("Request", request.name, 'lead', new_lead.name)
					new_lead.add_tag(request.event_name)
				frappe.db.commit()

	except Exception as e:
		frappe.throw(e)

def verify(request, method):
	if request.workflow_state == "Verify Interest":
		#Create Designation
		if not frappe.db.exists({"doctype": "Designation", "name": request.job_title}):
			new_designation = frappe.get_doc({
				"doctype": "Designation",
				"designation_name": request.job_title
				})
			new_designation.insert(ignore_permissions=True)
			
		#Create Country
		if not frappe.db.exists({"doctype": "Country", "name": request.country}):
			new_country = frappe.get_doc({
				"doctype": "Country",
				"country_name": request.country
				})
			new_country.insert(ignore_permissions=True)

		#Create Industry Type
		validate_industry(request.industry)

		# create lead and attach it to the request
		add_lead_to_request(request)


		#Brochure Task
		if request.request_type == "Brochure Request":
			event = frappe.get_doc("Events", request.event_name)
			new_task = frappe.get_doc({
				"doctype": "Task",
				"project": event.project_name,
				"type": "Brochure Request",
				"expected_start_date": today(),
				"subject": "Send Brochure",
				"description": str(request.full_name) + " would like a brochure for the " + str(request.event_name) + " event." + "\nRequest ID: " + str(request.name) + "\nEmail ID: " + str(request.email_address) + "\nPhone Number: " + str(request.phone_number)
				})
			new_task.insert(ignore_permissions=True)
		
		#Speaker Task
		if request.request_type == "Speaker Request":
			event = frappe.get_doc("Events", request.event_name)
			new_task = frappe.get_doc({
				"doctype": "Task",
				"project": event.project_name,
				"type": "Send Sponsorship Package",
				"expected_start_date": today(),
				"subject": "Sponsorship Package",
				"description": "Send the sponsorship package to " + str(request.full_name) + " for the " + str(request.event_name) + " event." + "\nRequest ID: " + str(request.name) + "\nEmail ID: " + str(request.email_address) + "\nPhone Number: " + str(request.phone_number)
				})
			new_task.insert(ignore_permissions=True)

		#Media Task
		if request.request_type == "Media Request":
			event = frappe.get_doc("Events", request.event_name)
			new_task = frappe.get_doc({
				"doctype": "Task",
				"project": event.project_name,
				"type": "Send Media Package",
				"expected_start_date": today(),
				"subject": "Media Package",
				"description": "Send the media package to " + str(request.full_name) + " for the " + str(request.event_name) + " event." + "\nRequest ID: " + str(request.name) + "\nEmail ID: " + str(request.email_address) + "\nPhone Number: " + str(request.phone_number)
				})
			new_task.insert(ignore_permissions=True)
		
	if request.workflow_state == 'Merged':
		#Update the lead:
		ep("Update the lead")
		
		doc = frappe.get_doc('Lead', request.lead)

		doc.email_id = request.email_address
		if request.corporate_email:
			doc.second_email = request.corporate_email
		doc.address = request.address
		doc.city = request.city
		doc.job_title = request.job_title
		doc.industry = request.industry
		doc.company_name = request.company
		if request.corporate_number:
			doc.phone = request.corporate_number
		#doc.mobile_number = request.phone_number
		doc.phone = request.phone_number
		doc.company_name = request.company

		doc.save()

		#Update the contact entry:
		contacts = frappe.get_all('Contact', filters={'email_id': request.email_address}, fields=['name'])
		if len(contacts) != 0:
			i = 0
			while i < len(contacts):
				value = contacts[i]['name']
				doc = frappe.get_doc('Contact', value)
				row = doc.append("phone_nos", {
					"phone": request.phone_number
					})
				if request.corporate_number:

					row2 = doc.append("phone_nos", {
						"phone": request.corporate_number
						})
					row2.insert(ignore_permissions=True)

				row.insert(ignore_permissions=True)
				i += 1

	if request.workflow_state == "Verified":

		if request.type == "Attendee":

			"""if not request.payment_status:
				frappe.throw("Payment Status is required to create the attendee")

			if not request.attendance_type:
				frappe.throw("Type of Attendance is required to create the attendee")
			"""

			if frappe.db.exists({'doctype': 'Attendee', 'email_address': request.email_address}):

				attendee = frappe.get_doc("Attendee", request.email_address)
				tags = attendee.get_tags()

				if(request.event_name not in tags):				

					event = frappe.get_doc('Events', request.event_name)
					row = event.append("attendees", {
						"attendee_id": request.email_address,
						"payment_status": request.payment_status,
						"attendance_type": request.attendance_type,
						"paid_amount": request.paid_amount
						})
					row.insert(ignore_permissions=True)
					
					attendee.add_tag(request.event_name)
					
					try:
						group_member = frappe.get_doc({
							"doctype": "Email Group Member",
							"email_group": event.attendee_group,
							"email": request.email_address,
							"event": request.event_name
							})
						group_member.insert(ignore_permissions=True)

					except frappe.exceptions.UniqueValidationError as e:
						pass
			else:
				#Create New Attendee
				new_attendee = frappe.get_doc({
					"doctype": "Attendee",
					"first_name": request.first_name,
					"last_name": request.last_name,
					"full_name": request.full_name,
					"email_address": request.email_address,
					"country": request.country,
					"phone_number": request.phone_number,
					"company": request.company,
					"job_title": request.job_title
					})
				new_attendee.insert(ignore_permissions=True)
				new_attendee.add_tag(request.event_name)

				#Add Attendee to Event
				event = frappe.get_doc('Events', request.event_name)
				row = event.append("attendees", {
					"attendee_id": request.email_address,
					"payment_status": request.payment_status,
					"attendance_type": request.attendance_type,
					"paid_amount": request.paid_amount
					})
				row.insert(ignore_permissions=True)

				#Add Attendee the Attendee Email Group
				request_event = frappe.get_doc('Events', request.event_name)
				try:
					group_member = frappe.get_doc({
						"doctype": "Email Group Member",
						"email_group": request_event.attendee_group,
						"email": request.email_address,
						"event": request.event_name
						})
					group_member.insert(ignore_permissions=True)

				except frappe.exceptions.UniqueValidationError as e:
					pass
				
		elif request.type == "Speaker":
			if frappe.db.exists({'doctype': 'Speaker', 'email_address': request.email_address}):
				
				event = frappe.get_doc('Events', request.event_name)
				row = event.append("speakers", {
					"payment_status": request.payment_status,
					"speaker_id": request.email_address,
					"attendance_type": request.attendance_type
					})
				row.insert()

				speaker_name = frappe.get_list("Speaker", filters={'email_address': request.email_address}, pluck='name', limit=1)[0]
				
				speaker = frappe.get_doc("Speaker", speaker_name)
				speaker.add_tag(request.event_name)
			else:
				new_speaker = frappe.get_doc({
					"doctype": "Speaker",
					"first_name": request.first_name,
					"last_name": request.last_name,
					"full_name": request.full_name,
					"email_address": request.email_address,
					"corporate_number": request.corporate_number,
					"speaker_bio": request.speaker_bio,
					"country": request.country,
					"phone_number": request.phone_number,
					"company": request.company,
					"job_title": request.job_title,
					"payment_status": request.payment_status,
					"attendance_type": request.attendance_type,
					"event_name": request.event_name
					})
				new_speaker.insert(ignore_permissions=True)
				new_speaker.add_tag(request.event_name)

				event = frappe.get_doc('Events', request.event_name)
				row = event.append("speakers", {
					"payment_status": request.payment_status,
					"speaker_id": request.email_address,
					"attendance_type": request.attendance_type
				})
				row.insert()

				request_event = frappe.get_doc('Events', request.event_name)
				try:
					group_member = frappe.get_doc({
						"doctype": "Email Group Member",
						"email_group": request_event.speaker_group,
						"email": request.email_address,
						"event": request.event_name
					})
					group_member.insert(ignore_permissions=True)
				except frappe.exceptions.UniqueValidationError as e:
					pass

		elif request.type == "Sponsor":
			if frappe.db.exists({'doctype': 'Sponsor', 'email_address': request.email_address}):
				event = frappe.get_doc('Events', request.event_name)
				row = event.append("sponsors", { "sponsor_name": request.full_name, "sponsor_id": request.email_address, "sponsorship_type": request.type_of_sponsorship })
				row.insert()

				group_member = frappe.get_doc({
					"doctype": "Email Group Member", "email_group": event.sponsor_group, "email": event.email_address, "event": event.event_name
				})
				group_member.insert(ignore_permissions=True)
			else:
				new_sponsor = frappe.get_doc({
					"doctype": "Event Sponsor", "first_name": request.first_name, "last_name": request.last_name, "full_name": request.full_name,
					"email_address": request.email_address, "country": request.country, "phone_number": request.phone_number,
					"company": request.company, "job_title": request.job_title
				})
				new_sponsor.insert(ignore_permissions=True)

				new_sponsor.add_tag(request.event_name)

				event = frappe.get_doc('Events', request.event_name)

				row = event.append("sponsors", {
					"sponsor_name": request.full_name, "sponsor_id": request.email_address, "sponsorship_type": request.type_of_sponsorship
					})
				row.insert()


		elif request.type == "Exhibitor":

			if not frappe.db.exists({'doctype': 'Exhibitor', 'email_address': request.email_address}):

				new_exhibitor = frappe.get_doc({
					"doctype": "Exhibitor",
					"first_name": request.first_name,
					"last_name": request.last_name,
					"full_name": request.full_name,
					"email_address": request.email_address,
					"country": request.country,
					"phone_number": request.phone_number,
					"company": request.company,
					"job_title": request.job_title
				})
				new_exhibitor.insert(ignore_permissions=True)

		elif request.type == "Media Partner":

			if not frappe.db.exists({'doctype': 'Media Partner', 'email_address': request.email_address}):
				media_partner = frappe.get_doc({
					"doctype": "Media Partner",
					"first_name": request.first_name,
					"last_name": request.last_name,
					"full_name": request.full_name,
					"email_address": request.email_address,
					"country": request.country,
					"phone_number": request.mobile_number,
					"company": request.company,
					"job_title": request.job_title
					})
				media_partner.insert(ignore_permissions=True)
				media_partner.add_tag(request.event_name)
	frappe.db.commit()

""" Add exhibitor: Media Partner, Sponsor, to email groups """

@frappe.whitelist()
def merge_req(old, new_doc):
	from frappe.utils import cint
	
	phone_number = old.phone_number
	email_address = old.email_address
	company = old.company

	# Validate properties before merging
	if not frappe.db.exists("Request", new_doc):
		frappe.throw(_("Request {0} does not exist").format(new_doc))

	val = list(frappe.db.get_value("Request", new_doc, ["phone_number", "email_address", "company"]))

	if val != [cint(phone_number), email_address, company]:
		frappe.throw(_("""Merging is only possible if following properties are same in both records. Phone Number, Email Address, Company"""))

	#  if is_group and frappe.db.get_value("Request", new, "parent_account") == old:
	#   frappe.db.set_value("Request", new, "parent_account",
	#    frappe.db.get_value("Request", old, "parent_account"))

	frappe.rename_doc("Request", old, new_doc, merge=1, force=1)
	frappe.db.commit()

	return new_doc

# called by Speaker Form submission in hooks, passes request doc as d
@frappe.whitelist()
def make_speaker(d, method):
	
	frappe.errprint(d.name)

	if speaker_entry_exists(d.email_address, d.event_name):
		frappe.throw("<strong>" + d.full_name + "</strong> is already registered to speak at <strong>" + d.event_name + "</strong>")

	if not d.job_title:
		frappe.throw("Make sure a job title is set for " + d.full_name)
		
	verify_job_title(d.job_title)
	verify_country_existence(d.country)

	speaker = frappe.get_doc({
		"doctype": "Speaker",
		"full_name": d.full_name,
		"job_title": d.job_title,
		"company": d.company,
		"event_name": d.event_name,
		"email_address": d.email_address,
		"phone_number": d.phone_number,
		"country": d.country,
		"speaker_bio": d.speaker_bio,
		"speaker_form": d.name,
		"profile_image": d.profile_image
	})
	speaker.insert(ignore_mandatory=True)
	frappe.db.commit()
	frappe.msgprint("Speaker successfully created!")

	# add speaker to email groups
	add_email_sub(d.event_name + " Speakers", d.email_address, d.event_name)

	"""
		interested_session
		corporate_number
		topic
		bullet_points
		profile_image
	"""

def speaker_entry_exists(email, event):
	if frappe.db.exists("Speaker", {"email_address": email, "event_name": event}):
		return True
	else:
		return False


def verify_job_title(job_title):
	if not frappe.db.exists({"doctype": "Designation", "name": job_title}):
		new_designation = frappe.get_doc({
			"doctype": "Designation",
			"designation_name": job_title
			})
		new_designation.insert(ignore_permissions=True)
		frappe.db.commit()
	return


@frappe.whitelist()
def add_event_to_milestone(doc):
	ms = frappe.get_doc("Milestone", doc)
	event_name = frappe.get_doc("Request", ms.reference_name).event_name
	frappe.db.set_value('Milestone', doc, 'event', event_name, update_modified=True)
	frappe.db.commit()


def verify_country_existence(country):
	#Create Country
	if not frappe.db.exists({"doctype": "Country", "name": country}):
		new_country = frappe.get_doc({
			"doctype": "Country",
			"country_name": country
			})
		new_country.insert(ignore_permissions=True)
		frappe.db.commit()
	return

@frappe.whitelist()
def add_speaker_to_event(d, method):
	#Add Speaker to Event
	event = frappe.get_doc('Events', d.event_name)
	row = event.append("speakers", {
		"full_name": d.full_name,
		"speaker_id": d.email_address,
		"attendance_type": d.attendance_type,
		"payment_status": d.payment_status,
		"country": d.country,
		})
	row.insert(ignore_permissions=True)
	frappe.db.commit()

# @frappe.whitelist()
# def lead_terms_conditions_fields(doc):
# 	if frappe.get_doc('Request', {"doc.terms_coditions": True, "doc.privacy_consent": True}):
# 		terms = frappe.db.set_value('Lead', doc,{ 
# 		"pravacy_consent": doc.privacy_consent, 
# 		"terms_and_conditions":doc.terms_coditions,  
# 		})
# 	terms.insert(ignore_permissions=True)
# 	return


@frappe.whitelist(allow_guest=True)
def process_brochure_request(data):

	p(data)

	if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
		request_status = True
	else:
		request_status = False
	
	#check the type of interest.
	if data['fields[more_about][value]'] == "Speaking":
		interest = "Speaker"
	elif data['fields[more_about][value]'] == "Attending":
		interest = "Attendee"
	elif data['fields[more_about][value]'] == "Sponsoring":
		interest = "Sponsor"
	elif data['fields[more_about][value]'] == "Exhibiting":
		interest = "Exhibitor"

	if data['fields[acceptance][value]'] == "on":
		acceptance = True
	else:
		acceptance = False

	country = get_country(data['fields[country][value]'])

	
	brochure_request = frappe.get_doc({
		"doctype": "Request",
		"request_type": "Brochure Request",
		"event_name": data['fields[event_name][value]'],
		"already_exists": request_status,
		"newsletter": acceptance,
		"source": "Online Registration",
		"first_name": data['fields[f_name][value]'],
		"last_name": data['fields[l_name][value]'],
		"full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
		"job_title": data['fields[job_title][value]'],
		"company": data['fields[company][value]'],
		"email_address": data['fields[email][value]'],
		"phone_number": data['fields[phone][value]'],
		"country": country,
		"interest_type": data['fields[more_about][value]'],
		"type": interest
		})
	brochure_request.insert(ignore_permissions=True)
	frappe.db.commit()

	return


@frappe.whitelist(allow_guest=True)
def process_speaker_form(data):
	p(data)
	
	if not data['fields[email][value]']:
		return "improper data"
	
	speaker_form = frappe.get_doc({
		"doctype": "Speaker Form",
		"event_name": data['fields[event_name][value]'],
		"data_consent": 1,
		"full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
		"job_title": data['fields[job_title][value]'],
		"company": data['fields[company][value]'],
		"email_address": data['fields[email][value]'],
		"phone_number": data['fields[mobile_phone][value]'],
		"corporate_number": data['fields[phone][value]'],
		"country": data['fields[country][value]'],
		"speaker_bio": str(data['fields[biography][value]']),
		"topic": str(data['fields[presentation_title][value]']),
		"bullet_points": str(data['fields[bullet_points][value]']),
		"interested_session": data['fields[interested][value]'],
		"profile_image": data['fields[file][value]']
		})
	speaker_form.insert(ignore_permissions=True)
	frappe.db.commit()
	return

@frappe.whitelist(allow_guest=True)
def process_speaker_request(data):

	if not data['fields[email][value]']:
		return "improper data"

	p(data)
	
	if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
		request_status = True
	else:
		request_status = False

	if data['fields[acceptance][value]'] == "on":
		acceptance = True
	else:
		acceptance = False

	country = get_country(data['fields[country][value]'])
	 
	speaker_request = frappe.get_doc({
		"doctype": "Request",
		"request_type": "Speaker Request",
		"event_name": data['fields[event_name][value]'],
		"already_exists": request_status,
		"first_name": data['fields[f_name][value]'],
		"newsletter": acceptance,
		"source": "Online Registration",
		"last_name": data['fields[l_name][value]'],
		"full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
		"job_title": data['fields[job_title][value]'],
		"company": data['fields[company][value]'],
		"email_address": data['fields[email][value]'],
		"phone_number": data['fields[phone][value]'],
		"country": country,
		"interest_type": data['fields[more_about][value]'],
		"type": "Speaker",
		"speaker_bio": str(data['fields[speaker_bio][value]']),
		"topic": str(data['fields[topic][value]'])
		})
	speaker_request.insert(ignore_permissions=True)
	frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def get_country(country):

	existing_country = frappe.get_list("Country", limit=1, or_filters=[
			['name', 'like', '%{country}%'.format(country=country)],
			['code', 'like', '%{country}%'.format(country=country)],
		])

	if len(existing_country) > 0: 
		country = existing_country[0].name
	else: 
		doc = frappe.get_doc({
			"doctype": "Country",
			"country_name": country
		})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

	return country

@frappe.whitelist(allow_guest=True)
def process_free_virtual_request(data):
	p(data)

	if not data['fields[email][value]']:
		return "improper data"

	if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
		request_status = True
	else:
		request_status = False

	if data['fields[acceptance][value]'] == "on":
		privacy_consent = True
	else:
		privacy_consent = False

	if data['fields[acceptance2][value]'] == "on":
		data_consent = True
	else:
		data_consent = False

	free_request = frappe.get_doc({
		"doctype": "Request",
		"request_type": "Free Virtual Guest Request",
		"event_name": data['fields[event_name][value]'],
		"already_exists": request_status,
		"source": "Online Registration",
		"first_name": data['fields[f_name][value]'],
		"newsletter": data['fields[acceptance][value]'],
		"last_name": data['fields[l_name][value]'],
		"full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
		"job_title": data['fields[job_title][value]'],
		"company": data['fields[company][value]'],
		"email_address": data['fields[email][value]'],
		"phone_number": data['fields[phone][value]'],
		"country": get_country(data['fields[country][value]']),
		"attendance_type": "Online",
		"interest_type": "Attending",
		"type": "Attendee",
		"industry": validate_industry(data['fields[industry][value]']),
		"terms_conditions": 1,
		"data_consent": 1,
		"payment_status": "Free"
		})
	free_request.insert(ignore_permissions=True)
	frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def process_free_virtual_request(data):
	ep(data)

	if not data['fields[email][value]']:
		return "improper data"

	if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
		request_status = True
	else:
		request_status = False

	if data['fields[acceptance][value]'] == "on":
		acceptance = True
	else:
		acceptance = False
		
	sponsor_request = frappe.get_doc({
		"doctype": "Request",
		"request_type": "Sponsor Request",
		"event_name": data['fields[event_name][value]'],
		"already_exists": request_status,
		"first_name": data['fields[f_name][value]'],
		"newsletter": acceptance,
		"source": "Online Registration",
		"last_name": data['fields[l_name][value]'],
		"full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
		"job_title": data['fields[job_title][value]'],
		"company": data['fields[company][value]'],
		"email_address": data['fields[email][value]'],
		"phone_number": data['fields[phone][value]'],
		"country": get_country(data['fields[country][value]']),
		"interest_type": data['fields[more_about][value]'],
		"type": "Sponsor"
		})
	sponsor_request.insert(ignore_permissions=True)
	frappe.db.commit()


def validate_industry(industry=None):
	industry = industry if (industry and industry != '') else 'Not Captured'

	if not frappe.db.exists("Industry Type", {'industry': industry}):
		doc = frappe.get_doc({
			'doctype': 'Industry Type',
			'industry': industry
		})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()

	return industry


@frappe.whitelist(allow_guest=True)
def process_free_request(data):
	ep(data)

	if not data['fields[email][value]']:
		return "improper data"

	if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
		request_status = True
	else:
		request_status = False

	if data['fields[acceptance][value]'] == "on":
		privacy_consent = True
	else:
		privacy_consent = False

	if data['fields[acceptance2][value]'] == "on":
		data_consent = True
	else:
		data_consent = False

	free_request = frappe.get_doc({
		"doctype": "Request",
		"request_type": "Free Guest Request",
		"event_name": data['fields[event_name][value]'],
		"already_exists": request_status,
		"source": "Online Registration",
		"first_name": data['fields[f_name][value]'],
		"last_name": data['fields[l_name][value]'],
		"full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
		"job_title": data['fields[job_title][value]'],
		"company": data['fields[company][value]'],
		"email_address": data['fields[email][value]'],
		"phone_number": data['fields[phone][value]'],
		"country": get_country(data['fields[country][value]']),
		"interest_type": "Attending",
		"attendance_type": "In-Person",
		"type": "Attendee",
		"industry": validate_industry(data['fields[industry][value]']),
		"terms_conditions": 1,
		"data_consent": 1,
		"payment_status": "Free"
		})
	free_request.insert(ignore_permissions=True)
	frappe.db.commit()

@frappe.whitelist(allow_guest=True)
def process_discount_request(data):

	if not data['fields[corporate_email][value]']:
		return "improper data"

	p(data)
	new_discount = frappe.get_doc({
		"doctype": "Discount Request",
		"full_name": data['fields[full_name][value]'],
		"company_name": data['fields[company_name][value]'],
		"corporate_email": data['fields[corporate_email][value]'],
		"event_name": data['fields[event_name][value]'],
		"newsletter": True
		})
	new_discount.insert(ignore_permissions=True)
	frappe.db.commit()
	return 


@frappe.whitelist(allow_guest=True)
def log_email_to_lead(doc, method=None):
	"""
		recieves a Mailjet Webhook doctype

		verify event type is sent
		then verify that the lead exists
		if so, 
			verify email belongs to a campaign
				add the email campaign subject activity to the lead
			else: return
	"""
	
	if type(doc) is str: 
		doc = frappe.get_doc("Mailjet Webhook Log", doc)

	if doc.event_type != "sent":
		return

	if not doc.campaign:
		return
	
	if frappe.db.exists({'doctype': 'Lead', 'email_id': doc.email}):
		
		campaign = frappe.get_doc("Mailjet Email Campaign", doc.campaign)
		lead_name = frappe.get_list('Lead', filters={'email_id': doc.email}, pluck='name', limit=1)[0]

		# do insert the email in the activity section
		from frappe.utils import now

		comm = frappe.get_doc({
			'doctype': 'Communication',
			'subject': campaign.title, 
			'communication_medium': 'Email', 
			'sender': campaign.sender, 
			'recipients': doc.email, 
			'content': 'Campaign Subject: ' + campaign.title, 
			'text_content': None, 
			'communication_type': 'Communication', 
			'status': 'Linked', 
			'sent_or_received': 'Sent', 
			'communication_date': now(),  
			'sender_full_name': 'Mailjet',
			'reference_doctype': 'Lead', 
			'reference_name': lead_name, 
			'reference_owner': 'Administrator', 
			'user': 'Administrator', 
			'message_id': '', 
			'email_status': 'Open',
			'has_attachment': 1,
			'docstatus': 1, 
		})
		comm.insert(ignore_permissions=True)
		frappe.db.commit()


def format(tag):
	tag = tag.strip()
	return tag[:1].upper() + tag[1:]


@frappe.whitelist(allow_guest=True)
def tag_imported_leads(doc, method=None):
	"""
		NEW LEAD INSERTED
		if import_tags
			tags = capitalise words then separate tags on comma
			for tag in tags
				if not tag exists
					create
				add tag to lead
	"""

	if type(doc) is str: 
		doc = frappe.get_doc("Lead", doc)

	if doc.import_tags:
		tags = doc.import_tags.split(",")

		for tag in tags:
			tag = format(tag)

			if not frappe.db.exists({'doctype': 'Tag', 'name': tag}):
				miles_teg = frappe.get_doc({
					'doctype': 'Tag',
					'name': tag
				})

				tag = miles_teg.insert(ignore_permissions=True)
				tag = tag.name

			doc.add_tag(tag)
		frappe.db.commit()

	return

@frappe.whitelist()
def update_tags(lead):
	if type(lead) is str:
		lead = frappe.get_doc("Lead", lead)

	tags = lead.get_tags()
	if tags:
		if len(tags) == 0 or tags[0] == '':
			frappe.errprint(23)
			tag_string = ""
		else:
			frappe.errprint(25)
			frappe.errprint(tags)
			tag_string = ", ".join(tags)
	elif lead.event:
		frappe.errprint(2)
		tag_string = lead.event
	else:
		frappe.errprint(3)
		tag_string = ""

	#lead.import_tags = tag_string
	frappe.db.set_value("Lead", lead.name, "import_tags", tag_string, update_modified=True)

	"""# update from server if its not a client call
	import inspect
	caller_function = inspect.stack()[1][3]

	if caller_function == "update_lead" and lead.import_tags == tag_string:
		return
	
	elif caller_function == "update_lead":
		frappe.db.set_value("Lead", lead.name, "import_tags", tag_string, update_modified=True)
		frappe.db.commit()
		lead.reload()
	else:
	"""
	


# create a function to create an attendee doctype from a lead and add the attendee to the event
@frappe.whitelist(allow_guest=True)
def create_event_participant_from_lead(lead, method=None):

	if type(lead) is str:
		lead = frappe.get_doc("Lead", lead)

	if not lead.event:
		frappe.throw("Please set an event for this lead")

	event = frappe.get_doc('Events', lead.event)
	event_name = event.name
	event_url = frappe.utils.get_url_to_form("Event", event_name)

	payment_status = ""
	attendance_type = ""
	paid_amount = 0
	type_of_sponsorship = ""
	speaker_info = ""

	# get request if it exists with lead email and event name
	if frappe.db.exists({'doctype': 'Attendee', 'email_address': lead.email_id, 'event_name': lead.email_id}):
		request = frappe.get_list('Attendee', filters={'email_address': lead.email_id, 'event': lead.event_name}, fields={'*'}, pluck='name', limit=1)[0]
		
		payment_status = request.payment_status
		attendance_type = request.attendance_type
		paid_amount = request.paid_amount
		type_of_sponsorship = request.type_of_sponsorship or ""
		speaker_info = request.speaker_bio or ""

	state = "Updated"

	if lead.type == "Attendee":
		attendee_name = ""
		
		if not frappe.db.exists({'doctype': 'Attendee', 'email_address': lead.email_id}):
			#Create New Attendee
			attendee = frappe.get_doc({
				"doctype": "Attendee",
				"first_name": lead.first_name,
				"last_name": lead.last_name,
				"full_name": lead.lead_name,
				"email_address": lead.email_id,
				"country": lead.country,
				"phone_number": lead.lead_number,
				"company": lead.company_name,
				"job_title": lead.job_title,
				"industry": lead.industry,
				"city": lead.city,
				"address": lead.address
			})
			attendee.insert(ignore_permissions=True, ignore_mandatory=True)

			state = "Created"
		else:
			#Update Existing Attendee
			attendee_name = frappe.get_list("Attendee", filters={'email_address': lead.email_id}, limit=1)[0].name
			attendee = frappe.get_doc("Attendee", attendee_name)
			attendee.first_name = lead.first_name
			attendee.last_name = lead.last_name
			attendee.full_name = lead.lead_name
			attendee.email_address = lead.email_id
			attendee.country = lead.country
			attendee.phone_number = lead.lead_number
			attendee.company = lead.company_name
			attendee.job_title = lead.job_title
			attendee.industry = lead.industry
			attendee.city = lead.city
			attendee.address = lead.address
			attendee.flags.ignore_mandatory=True
			attendee.save(ignore_permissions=True)

		if attendee_name == "":
			attendee_name = frappe.get_list("Attendee", filters={'email_address': lead.email_id}, limit=1)[0].name

		attendee = frappe.get_doc("Attendee", attendee_name)

		# add event to attendee tickets if not already there
		tickets = []
		for t in attendee.tickets:
			tickets.append(t.event_name)

		if lead.event not in tickets:
			row = attendee.append("tickets", {
				"event_name": lead.event,
			})
			row.insert(ignore_permissions=True)

		# check if attendee has tag for event, add if not
		tags = attendee.get_tags()
		if(lead.event not in tags):
			attendee.add_tag(lead.event)

		# get event doctype and check if attendee is already in event.attendees
		# Then add attendee to event.attendees if not already there
		
		attendees = []
		for a in event.attendees:
			attendees.append(a.attendee_id)

		if lead.email_id not in attendees:
			row = event.append("attendees", {
				"attendee_id": lead.email_id,
				"payment_status": payment_status,
				"attendance_type": attendance_type,
				"paid_amount": paid_amount
				})
			row.insert(ignore_permissions=True)

		frappe.msgprint( _("{5} <strong><a href='{0}'>{2} document for {1}</a></strong> and added them to <strong><a href='{4}'>{3}</a></strong>".format(
			frappe.utils.get_url_to_form("Attendee", attendee.name), 
			attendee.full_name, 
			attendee.doctype, 
			lead.event, 
			event_url,
			state
		)) )

	# 2. If Lead is a Speaker, insert into Speaker doctype and add speaker to event.speakers table
	elif lead.type == "Speaker":

		speaker_name = ""
			
		if not frappe.db.exists({'doctype': 'Speaker', 'email_address': lead.email_id}):
			#Create New Speaker
			speaker = frappe.get_doc({
				"doctype": "Speaker",
				"first_name": lead.first_name,
				"last_name": lead.last_name,
				"full_name": lead.lead_name,
				"email_address": lead.email_id,
				"country": lead.country,
				"phone_number": lead.lead_number,
				"company": lead.company_name,
				"job_title": lead.job_title,
				"industry": lead.industry,
				"city": lead.city,
				"address": lead.address,
				"speaker_bio": lead.speaker_info,
				"payment_status": payment_status,
				"attendance_type": attendance_type,
				"event_name": lead.event
			})
			speaker.insert(ignore_permissions=True, ignore_mandatory=True)
			state = "Created"
			
		else:
			#Update Existing speaker
			speaker_name = frappe.get_list("Speaker", filters={'email_address': lead.email_id}, limit=1)[0].name
			speaker = frappe.get_doc("Speaker", speaker_name)
			speaker.first_name = lead.first_name
			speaker.last_name = lead.last_name
			speaker.full_name = lead.lead_name
			speaker.email_address = lead.email_id
			speaker.country = lead.country
			speaker.phone_number = lead.lead_number
			speaker.company = lead.company_name
			speaker.job_title = lead.job_title
			speaker.industry = lead.industry
			speaker.city = lead.city
			speaker.address = lead.address
			speaker.speaker_bio = lead.speaker_info
			speaker.payment_status = payment_status
			speaker.attendance_type = attendance_type
			speaker.flags.ignore_mandatory=True
			speaker.save(ignore_permissions=True)

		if speaker_name == "":
			speaker_name = frappe.get_list("Speaker", filters={'email_address': lead.email_id}, limit=1)[0].name

		speaker = frappe.get_doc("Speaker", speaker_name)

		# check if speaker has tag for event, add if not
		tags = speaker.get_tags()
		if(lead.event not in tags):
			speaker.add_tag(lead.event)

		# get event doctype and check if speaker is already in event.speakers
		# Then add speaker to event.speakers if not already there		

		speakers = []
		for a in event.speakers:
			speakers.append(a.speaker_id)

		if lead.email_id not in speakers:
			row = event.append("speakers", {
				"full_name": lead.lead_name,
				"speaker_id": lead.email_id,
				"payment_status": payment_status,
				"attendance_type": attendance_type,
				"country": lead.country
			})
			row.flags.ignore_mandatory=True
			row.insert(ignore_permissions=True)

		frappe.msgprint( _("{5} <strong><a href='{0}'>{2} document for {1}</a></strong> and added them to <strong><a href='{4}'>{3}</a></strong>".format(
			frappe.utils.get_url_to_form("Speaker", speaker.name), 
			speaker.full_name, 
			speaker.doctype, 
			lead.event, 
			event_url,
			state
		)) )

	# 3. If Lead is a Media Partner, insert into Media Partner doctype and add media partner to event.media_partners table
	elif lead.type == "Media Partner":

		if not frappe.db.exists({'doctype': 'Media Partner', 'email_address': lead.email_id}):
			media_partner = frappe.get_doc({
				"doctype": "Media Partner",
				"first_name": lead.first_name,
				"last_name": lead.last_name,
				"full_name": lead.lead_name,
				"email_address": lead.email_id,
				"country": lead.country,
				"phone_number": lead.lead_number,
				"company": lead.company_name,
				"job_title": lead.job_title
			})
			media_partner.insert(ignore_permissions=True)
			media_partner.add_tag(lead.event)


	# 4. If Lead is a Sponsor, insert into Sponsor doctype and add sponsor to event.sponsors table
	elif lead.type == "Sponsor":
		sponsor = {}
		if not frappe.db.exists({'doctype': 'Event Sponsor', 'sponsor_name': lead.company_name}):
			sponsor = frappe.get_doc({
				"doctype": "Event Sponsor", 
				"sponsor_name": lead.company_name, 
				"contact_person": lead.lead_name,
				"email_address": lead.email_id, 
				"country": lead.country, 
				"phone_number": lead.lead_number,
				"job_title": lead.job_title,
				"city": lead.city,
				"address": lead.address
			})
			sponsor.insert(ignore_permissions=True)
			state = "Created"

		else:
			sponsor = frappe.get_doc("Event Sponsor", lead.company_name)
			sponsor.contact_person = lead.lead_name
			sponsor.email_address = lead.email_id
			sponsor.country = lead.country
			sponsor.phone_number = lead.lead_number
			sponsor.company = lead.company_name
			sponsor.job_title = lead.job_title
			sponsor.city = lead.city
			sponsor.address = lead.address
			sponsor.flags.ignore_mandatory=True
			sponsor.save(ignore_permissions=True)

		if not sponsor:
			sponsor = frappe.get_doc("Event Sponsor", lead.company_name)

		# check if speaker has tag for event, add if not
		tags = sponsor.get_tags()
		if(lead.event not in tags):
			sponsor.add_tag(lead.event)

		# get event doctype and check if speaker is already in event.speakers
		# Then add speaker to event.speakers if not already there		

		sponsors = []
		for s in event.sponsors:
			sponsors.append(s.sponsor_id)

		if lead.email_id not in sponsors:
			row = event.append("sponsors", {
				"sponsor_name": lead.company_name, 
				"sponsor_id": lead.email_id, 
				"sponsorship_type": type_of_sponsorship
			})
			row.flags.ignore_mandatory=True
			row.insert(ignore_permissions=True)


		frappe.msgprint( _("{5} <strong><a href='{0}'>{2} document for {1}</a></strong> and added them to <strong><a href='{4}'>{3}</a></strong>".format(
			frappe.utils.get_url_to_form("Sponsor", sponsor.name), 
			sponsor.sponsor_name, 
			sponsor.doctype, 
			lead.event, 
			event_url,
			state
		)) )


	elif lead.type == "Exhibitor":
		exhibitor = {}
		if not frappe.db.exists({'doctype': 'Exhibitor', 'email_address': lead.email_id}):
			exhibitor = frappe.get_doc({
				"doctype": "Exhibitor",
				"salutation": lead.salutation,
				"contact_person": lead.lead_name,
				"company_name": lead.company_name,
				"email_address": lead.email_id,
				"country": lead.country,
				"address": lead.address,
				"city": lead.city,
				"phone_number": lead.lead_number
			})
			exhibitor.insert(ignore_permissions=True)
			state = "Created"

		else:
			exhibitor = frappe.get_doc("Exhibitor", lead.company_name)
			exhibitor.contact_person = lead.lead_name
			exhibitor.email_address = lead.email_id
			exhibitor.country = lead.country
			exhibitor.phone_number = lead.lead_number
			exhibitor.company = lead.company_name
			exhibitor.city = lead.city
			exhibitor.address = lead.address
			exhibitor.salutation = lead.salutation
			
			exhibitor.flags.ignore_mandatory=True
			exhibitor.save(ignore_permissions=True)

		if not exhibitor:
			exhibitor = frappe.get_doc("Exhibitor", lead.company_name)

		# check if exhibitor has tag for event, add if not
		tags = exhibitor.get_tags()
		if(lead.event not in tags):
			exhibitor.add_tag(lead.event)

		# get event doctype and check if exhibitor is already in event.exhibitors
		# Then add speaker to event.exhibitors if not already there		

		exhibitors = []
		for s in event.exhibitors:
			exhibitors.append(s.exhibitor_id)

		if lead.email_id not in exhibitors:
			row = event.append("exhibitors", {
				"exhibitor_name": lead.company_name,
				"exhibitor_id": lead.email_id
			})
			row.flags.ignore_mandatory=True
			row.insert(ignore_permissions=True)

		frappe.msgprint( _("{5} <strong><a href='{0}'>{2} document for {1}</a></strong> and added them to <strong><a href='{4}'>{3}</a></strong>".format(
			frappe.utils.get_url_to_form("Exhibitor", exhibitor.name), 
			exhibitor.name, 
			exhibitor.doctype, 
			lead.event, 
			event_url,
			state
		)) )


	frappe.db.commit()


# get all leads for the passed event and call create_participant for each
@frappe.whitelist(allow_guest=True)
def create_participants_for_event_from_leads(event):
	leads = frappe.get_all("Lead", filters={"event": event})
	
	for lead in leads:
		create_event_participant_from_lead(lead.name)