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
				
def email_group(lead, method):
	if str(lead.workflow_state) == "Confirmed":
		data = {"Speaking": "Speakers", "Attending": "Attendees", "Sponsoring": "Sponsors", "Exhibiting": "Media"}
		pre_email_group = str(lead.event) + " " + data[lead.interest_type]
		add_email_sub(pre_email_group, lead.email_address, lead.event)

"""
	adds email to particular email group and to "All" email group
"""
def add_email_sub(email_group, email, event):
	email_group_member =  frappe.get_doc({
		"doctype": "Email Group Member",
		"email_group": email_group,
		"event": event,
		"email": email
	})
	email_group_member.save()

	all_email_group_member =  frappe.get_doc({
		"doctype": "Email Group Member",
		"email_group": str(event) + " All",
		"event": event,
		"email": email
	})
	all_email_group_member.save()

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
   
@frappe.whitelist()
def delete_spam():
	frappe.db.delete("Request", {
	"workflow_state": "Spam"
	})
	


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

def add_project(project, method):
	doc = frappe.get_doc("Events", project.project_name)
	doc.project_name = project.name
	doc.save()

def link_lead(lead, method):
	requests = frappe.db.get_list('Request', filters={'email_address': lead.email_id}, fields=['name'])
	list_size = len(requests)
	i = 0
	while i < list_size:
		frappe.db.set_value("Request", requests[i]['name'], "lead", lead.name)
		i =+ 1

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

		if not frappe.db.exists({'doctype': 'Email Group Member', 'email_group': event.sub_group, 'email': request.email_address}):
			email_member = frappe.get_doc({
				"doctype": "Email Group Member",
				"email": request.email_address,
				"email_group": event.sub_group
				})
			email_member.insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def add_lead_to_request(request):
	# create lead and attach it to the request

	# if origin is javascript
	if type(request) is str: 
		request = frappe.get_doc("Request", request)
	
	# ep('add_lead_to_request')

	try:
		if request.already_exists == False:
			if not request.lead:
				new_lead = frappe.get_doc({
					"doctype": "Lead",
					"event": request.event_name,
					"first_name": request.first_name,
					"last_name": request.last_name,
					"lead_name": request.full_name,
					"designation": request.job_title,
					"company_name": request.company,
					"email_id": request.email_address,
					"country": request.country,
					"phone": request.phone_number,
					"industry": validate_industry(request.industry),
					"type": request.type,
					"request_type": request.interest_type,
					"mobile_no": request.phone_number,
					"lead_number": request.phone_number,
					"source": request.source
					})
				new_lead.insert(ignore_permissions=True)
				
				frappe.set_value("Request", request.name, 'lead', new_lead.name)
				#new_lead.add_tag(request.event_name)

	except Exception as e:
		frappe.throw(e)

def verify(request, method):
	print(1)
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
		doc = frappe.get_doc('Lead', request.lead)
		doc.email_id = request.email_address
		doc.mobile_number = request.phone_number
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
					
					group_member = frappe.get_doc({
						"doctype": "Email Group Member",
						"email_group": event.attendee_group,
						"email": request.email_address,
						"event": request.event_name
						})
					group_member.insert(ignore_permissions=True)
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
				group_member = frappe.get_doc({
					"doctype": "Email Group Member",
					"email_group": request_event.attendee_group,
					"email": request.email_address,
					"event": request.event_name
					})
				group_member.insert(ignore_permissions=True)
				
		elif request.type == "Speaker":
			if frappe.db.exists({'doctype': 'Speaker', 'email_address': request.email_address}):
				event = frappe.get_doc('Events', request.event_name)
				row = event.append("speakers", {
					"payment_status": request.payment_status,
					"speaker_id": request.email_address,
					"attendance_type": request.attendance_type
					})
				row.insert()
				speaker = frappe.get_doc("Speaker", request.email_address)
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
				group_member = frappe.get_doc({
					"doctype": "Email Group Member",
					"email_group": request_event.speaker_group,
					"email": request.email_address,
					"event": request.event_name
				})
				group_member.insert(ignore_permissions=True)

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
	
	print(0)

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


def verify_job_title(job_title):
	if not frappe.db.exists({"doctype": "Designation", "name": job_title}):
		new_designation = frappe.get_doc({
			"doctype": "Designation",
			"designation_name": job_title
			})
		new_designation.insert(ignore_permissions=True)
	return


@frappe.whitelist()
def add_event_to_milestone(doc):
	ms = frappe.get_doc("Milestone", doc)
	event_name = frappe.get_doc("Request", ms.reference_name).event_name
	frappe.db.set_value('Milestone', doc, 'event', event_name, update_modified=True)


def verify_country_existence(country):
	#Create Country
	if not frappe.db.exists({"doctype": "Country", "name": country}):
		new_country = frappe.get_doc({
			"doctype": "Country",
			"country_name": country
			})
		new_country.insert(ignore_permissions=True)
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

	return


@frappe.whitelist(allow_guest=True)
def process_speaker_form(data):
	p(data)
	
	if not data['fields[email][value]']:
		return "improper data"
	
	speaker_form = frappe.get_doc({
		"doctype": "Speaker Form",
		"event_name": data['fields[event_name][value]'],
		"data_consent": True,
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
		privacy_concent = True
	else:
		privacy_concent = False

	if data['fields[acceptance2][value]'] == "on":
		data_concent = True
	else:
		data_concent = False

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
		"terms_conditions": privacy_concent,
		"data_concent": data_concent,
		"payment_status": "Free"
		})
	free_request.insert(ignore_permissions=True)

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


def validate_industry(industry=None):
	industry = industry if (industry and industry != '') else 'Not Captured'

	if not frappe.db.exists("Industry Type", {'industry': industry}):
		doc = frappe.get_doc({
			'doctype': 'Industry Type',
			'industry': industry
		})
		doc.insert(ignore_permissions=True)

	return industry



@frappe.whitelist(allow_guest=True)
def process_free_request(data):
	p(data)

	if not data['fields[email][value]']:
		return "improper data"

	if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
		request_status = True
	else:
		request_status = False

	if data['fields[acceptance][value]'] == "on":
		privacy_concent = True
	else:
		privacy_concent = False

	if data['fields[acceptance2][value]'] == "on":
		data_concent = True
	else:
		data_concent = False

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
		"terms_conditions": privacy_concent,
		"data_consent": data_concent,
		"payment_status": "Free"
		})
	free_request.insert(ignore_permissions=True)

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
