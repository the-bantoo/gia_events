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
from frappe.utils import getdate, now


def p(*args):
	if True:
		print(*args)

def ep(arg):
	if True:
		frappe.errprint(arg)

def daily_run():
	print('Daily run start ###############################################################################################')
	run_update_lead_for_all_members()
	create_missing_email_group_members()

def chunked_data(data, size):
	"""Yield successive size chunks from data."""
	for i in range(0, len(data), size):
		yield data[i:i + size]
		
@frappe.whitelist()
def run_update_lead_for_all_members():
	
	members = frappe.get_all(
		"Email Group Member",
		fields=["email", "email_group", "unsubscribed"],
		# filters={"unsubscribed": 0}, 
		limit=0
	)
	for data_chunk in chunked_data(members, 50):
		for member in data_chunk:
			update_lead_eg_sub(member, "run_update_lead_for_all_members")

	frappe.msgprint("Updated {} Lead Subscriptions".format(str(len(members))))

@frappe.whitelist()
def create_missing_email_group_members(): # schedule
	""" creates missing email group members by checking if the each Leads email_id and second_email have a related contact for the Lead's event """
	email_groups = frappe.get_all("Email Group", fields=["name", "event"], limit=0)
	created = 0
	for group in email_groups:
		members = frappe.get_all("Email Group Member", fields=["email", "email_group"], filters={'email_group': group.name}, limit=0)
		leads = frappe.get_all("Lead", fields=["name", "email_id", "second_email", "event", "unsubscribed"], filters={'event': group.event}, limit=0)

		for data_chunk in chunked_data(leads, 200):
			for lead in data_chunk:
				added = False
				if {"email": lead.email_id, "email_group": group.name} not in members:
					sub_to_group(group.name, lead.email_id, lead.event)
					added = True

				if lead.second_email and {"email": lead.second_email, "email_group": group.name} not in members:
					sub_to_group(group.name, lead.second_email, lead.event)
					added = True

				if added:
					created += 1
					lead_doc = frappe.get_doc("Lead", lead.name)

					add_mail_group_to_lead(lead_doc, group.name)
					if lead_doc.unsubscribed == 1:
						set_lead_unsubscribed(lead_doc, 0)

					# add email to members
		# 		break
		# 	break
		# if created > 1:
		# 	break
	if created > 0:
		frappe.msgprint("Created {} Email Group Members".format(str(len(members))))
		frappe.msgprint("Created new Email Group Members") # .format(str(len(members)))
	else:
		frappe.msgprint("No new Email Group Members were created")


def update_lead_eg_sub(member, method):
	""" updates the email groups a lead is subscribed to every time the egm changes """

	# get lead by email_id or second_email fields
	lead_name = get_lead(member.email)

	if lead_name:
		lead = frappe.get_doc("Lead", lead_name[0].name)
		eg_count = len(lead.email_group_subscriptions)

		added = None
		removed = None

		if member.unsubscribed == 0:
			
			added = add_mail_group_to_lead(lead, member.email_group)
			# if lead.unsubscribed == 0: pass		
			
			if added:
				if lead.unsubscribed == 1:
					# set lead.unsubscribed to 0
					set_lead_unsubscribed(lead, 0)
		else:
			removed = remove_mail_group_from_lead(lead, member.email_group)
			
			if removed:
				if eg_count <= 1:
					# set lead.unsubscribed to 1
					if lead.unsubscribed == 0:
						set_lead_unsubscribed(lead, 1)
				else:
					# set lead.unsubscribed to 0
					if lead.unsubscribed == 1:
						set_lead_unsubscribed(lead, 0)
			
		if (not added and not removed):
			if eg_count == 0:
				# set lead.unsubscribed to 1
				if lead.unsubscribed == 0:
					set_lead_unsubscribed(lead, 1)
			else:
				# set lead.unsubscribed to 0
				if lead.unsubscribed == 1:
					set_lead_unsubscribed(lead, 0)


def remove_mail_group_from_lead(lead, email_group):
	""" Removes the email group from the lead if it exists. """
	# Iterate through the subscriptions to find and remove the specified email group
	for row in lead.email_group_subscriptions:
		if row.subscription == email_group:
			lead.email_group_subscriptions.remove(row)
			# Optionally, you can delete the row from the database
			row.delete(ignore_permissions=True)
			return True
	# If the email group does not exist in the lead's subscriptions, return False
	return False
			
def add_mail_group_to_lead(lead, email_group):
	""" adds the email group to the lead if not already there"""
	for row in lead.email_group_subscriptions:
		if row.subscription == email_group:
			return False

	row = lead.append('email_group_subscriptions', {
		'subscription': email_group
	})
	row.insert(ignore_permissions=True)
	return True

	
def set_lead_unsubscribed(lead, val):
	lead.unsubscribed = val
	lead.save(ignore_permissions=True)

@frappe.whitelist(allow_guest=True)
def get_lead(email):
	sql = """select `name`
	from `tabLead`
	where `email_id` = '{}' or `second_email` = '{}'
	
	order by `creation` DESC
	limit 1 offset 0
	""".format(email, email)

	return frappe.db.sql(sql, as_dict=1)

def update_lead(lead, method):
	ep('update_lead')
	add_default_mail_groups(lead, method)

def hello(a, b):
	ep('hello')

def add_default_mail_groups(lead, method):

	# list all email group members this lead has and add subscriptions to table
	if lead.unsubscribed == 1 or not lead.event:
		return

	if lead.request_type:
		attendance_type = {"Speaking": "Speakers", "Attending": "Attendees", "Sponsoring": "Sponsors", "Exhibiting": "Media"}
		email_group = str(lead.event) + " " + attendance_type[lead.request_type]
		group_membership = frappe.get_list('Email Group Member', filters={'email_group': email_group, 'email': lead.email_id})

		# ep(email_group)

		if len(group_membership) < 1:
			sub_to_group(email_group, lead.email_id, lead.event)
	
	all_group_membership = frappe.get_list('Email Group Member', filters={'email_group': lead.event + " All", 'email': lead.email_id})
	
	
	# ep(all_group_membership)

	if len(all_group_membership) < 1:
		add_email_sub_all(lead.email_id, lead.event)

	add_to_subs_group(lead, lead.email_id, lead.event)
	if lead.second_email:
		add_to_subs_group(lead, lead.second_email, lead.event)

		if len(group_membership) < 1:
			sub_to_group(email_group, lead.second_email, lead.event)

		all_group_membership2 = frappe.get_list('Email Group Member', filters={'email_group': lead.event + " All", 'email': lead.second_email})

		if len(all_group_membership2) < 1:
			add_email_sub_all(lead.second_email, lead.event)

"""
	adds email to particular email group and to "All" email group
"""
def add_to_subs_group(lead, email, event):
	membership = frappe.get_list('Email Group Member', fields={'name', 'unsubscribed'}, filters={
		'email_group': str(lead.event) + " All", 'email': lead.email_id
	})
	if not lead.event:
		return
		
	if not membership:		
		sub_to_group(str(lead.event) + " Subscription", lead.email_id, str(lead.event))
		frappe.db.commit()

	# else:
	# 	# hold result of conditional check in variable

	# 	lead_subbed_eg_unsubbed = (membership[0].unsubscribed == 1 and lead.unsubscribed == 0)
	# 	if lead_subbed_eg_unsubbed or (membership[0].unsubscribed == 0 and lead.unsubscribed == 1):
	# 		m =  frappe.get_doc("Email Group Member", membership[0].name)
	# 		m.unsubscribed = lead.unsubscribed
	# 		m.save(ignore_permissions=True)
	
	


def sub_to_group(email_group, email, event):
	exists = frappe.get_all("Email Group Member", filters={'email_group': email_group, 'email': email}, limit=1)
	if not exists:
		email_group_member =  frappe.get_doc({
			"doctype": "Email Group Member",
			"email_group": email_group,
			"event": event,
			"email": email
		})
		email_group_member.insert(ignore_permissions=True)

def add_email_sub_all(email, event):
	sub_to_group(event + " All", email, event)	


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

	frappe.db.delete("Discount Request", {
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


def discount_request_hook(d, method):
	email_member(d, method)
	# add_discount_to_lead(d)



def find_request_by_email(email):
	sql = """
		SELECT `name`, `creation`, `type`
		FROM `tabRequest`
		where `email_address` = '{}' or `corporate_email` = '{}'
		ORDER BY `creation` DESC
	""".format(email, email)
	
	return frappe.db.sql(sql, as_dict=1)

	
def email_member(discount_request, method):
	event = frappe.get_doc("Events", discount_request.event_name)
	
	if not event.sub_group:
		url = event.get_url()
		frappe.msgprint(f"<a href='{url}'>{event.name}</a> has no subscriber group set. Click <a href='{url}'>here</a> to set one.")
		return

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

def get_lead(email):
	sql = """select `name`
	from `tabLead`
	where `email_id` = '{}' or `second_email` = '{}'
	
	order by `creation` DESC
	limit 1 offset 0
	""".format(email, email)

	return frappe.db.sql(sql, as_dict=1)

def attendee_exists(request, method):
	lead_exists = get_lead(request.email_address)
	if lead_exists:
		#Link Lead to Request
		frappe.db.set_value('Request', request.name, {
				'lead': lead_exists[0].name,
				"already_exists": True
			}, update_modified=True)


	if request.request_type == "Paid Request":
		if lead_exists:
			#Link Lead to Request
			frappe.db.set_value('Request', request.name, {
				'lead': lead_exists[0].name,
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
	

def delete_member(doc, method):
	# recount email group members
	update_email_group_subs(doc, method)

	# remove eg from lead
	remove_emailgroup_from_lead(doc)

def remove_emailgroup_from_lead(doc):
	# get lead, find and rm group's name
	l = get_lead_by_email(doc.email)
	if l:
		lead = frappe.get_doc('Lead', l[0].name)

		name = get_lead_email_group_name(lead, doc.email_group)
		if name:
			frappe.delete_doc('Contact Subscriptions', name)
			frappe.db.commit()


def get_lead_email_group_name(lead, email_group):
	for eg in lead.email_group_subscriptions:
		if str(eg.subscription) == str(email_group):
			return eg.name
	return False


def get_lead_by_email(email):
	sql = """select `name`
	from `tabLead`
	where `email_id` = '{}' or `second_email` = '{}'
	
	order by `creation` DESC
	limit 1 offset 0
	""".format(email, email)

	return frappe.db.sql(sql, as_dict=1)

# @frappe.whitelist(allow_guest=True)
def add_lead_to_request(request):
	"""create lead and attach it to the request"""
	# validate
	if request.type == "Attendee":
		if not request.payment_status:
			frappe.throw('Payment Status is required to create a Lead')
		if not request.attendance_type:
			frappe.throw('Type of Attendance is required to create a Lead')

	if request.payment_status != "":
		if request.payment_status == "Paid" and request.paid_amount <= 0:
			frappe.throw('Paid amount should be more than 0')
		if request.payment_status == "Sponsored" and request.paid_amount <= 0:
			frappe.throw('Paid amount should be more than 0')

	# if origin is javascript
	if type(request) is str: 
		request = frappe.get_doc("Request", request)	

	try:
		if request.already_exists == 0:
			if not request.lead:
				leads = frappe.get_list("Lead", filters={'email_id': request.email_address})
				if len(leads) > 0:
					frappe.set_value("Request", request.name, 'lead', leads[0].name)
					lead = frappe.get_doc("Lead", leads[0].name)
					lead.add_tag(request.event_name)
				else:
					project_name = get_or_create_project(None, request.event_name)
					new_lead = frappe.get_doc({
						"doctype": "Lead",
						"event": request.event_name,
						"project": project_name,
						"first_name": request.first_name,
						"last_name": request.last_name,
						"lead_name": request.full_name,
						"job_title": request.job_title,
						"company_name": request.company,
						"email_id": request.email_address,
						"second_email": request.corporate_email or '',
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
						"blog_subscriber": 1 if request.newsletter == 1 else 0,
						"terms_and_conditions": request.terms_conditions,
						"data_consent": 1,
						"first_request": request.creation,
						"first_request_entry": request.name,
						"latest_request_date": request.creation,
						"latest_request_entry": request.name
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
		# ep("Update the lead")
		
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
		doc.project = update_lead_project(doc.name, request.event_name)

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

						if not event.attendee_group:
							frappe.throw(_('Please set a default Email Group for <strong>{}</strong> in the Event <strong>{}</strong>'.format(request.type, request.event_name)))
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
					
					if not request_event.attendee_group:
						frappe.throw(_('Please set a default Email Group for <strong>{}</strong> in the Event <strong>{}</strong>'.format(request.type, request.event_name)))
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
				if not request_event.speaker_group:
					frappe.throw(_('Please set a default Email Group for <strong>{}</strong> in the Event <strong>{}</strong>'.format(request.type, request.event_name)))
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

				if not event.sponsor_group:
					frappe.throw(_('Please set a default Email Group for <strong>{}</strong> in the Event <strong>{}</strong>'.format(request.type, request.event_name)))

				group_member = frappe.get_doc({
					"doctype": "Email Group Member", "email_group": event.sponsor_group, "email": event.email_address, "event": event.event_name
				})
				group_member.insert(ignore_permissions=True)
			else:
				name = request.full_name
				if request.type_of_sponsor != "Individual":
					if request.sponsor_name:
						name = request.sponsor_name
					elif request.sponsor_name:
						name = request.company

				new_sponsor = frappe.get_doc({
					"doctype": "Event Sponsor", "sponsor_name": name, "contact_person": request.full_name, 
					"postalzip_code": request.zip_code, "city": request.city, "sponsor_type": request.type_of_sponsor,
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
	# ep(data)

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
	# ep(data)

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


def get_current_tags(lead_name):
	# returns current tags on lead
	lead = frappe.get_doc("Lead", lead_name)
	return lead.get_tags()

def get_tags_as_str(lead):
	""" return current lead tags as string """
	if type(lead) is str:
		lead = frappe.get_doc("Lead", lead)

	tags = get_current_tags(lead.name)
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
	

# which has more tags field vs tags?
## count each, update lesser
## update zero
## update oldest

# X if lead.import_tags has value but lead has no tags add tags from import_tags
def make_default_tags(lead):
	"""
	Generates a list of default tags for a lead based on specific rules:
	1. The lead's event.
	2. A capitalized acronym derived from the company name.
	3. The year of creation for all associated Requests.
	"""
	default_tags = set()
	requests = get_request(lead.email_id, lead.second_email)
	
	if (requests and (not lead.event or not lead.type or not lead.request_type or not lead.first_request or not lead.phone or not lead.first_name or not lead.last_name or not lead.company_name)):
		r = requests[0]
		lead.event = r.event_name

		frappe.db.set_value("Lead", lead.name, {
				"event": r.event_name,
				"type": r.type,
				"request_type": r.interest_type,
				"first_request": r.creation,
				"phone": r.phone_number,
				"first_name": r.first_name,
				"last_name": r.last_name,
				"company_name": r.company,
				"job_title": r.job_title,
				"lead_name": r.full_name,
				"country": r.country,
				"industry": validate_industry(r.industry),
				"lead_number": r.phone_number,
				"address": r.address,
				"city": r.city,
				"source": r.source,
				"blog_subscriber": r.newsletter if r.newsletter else 0,
				"terms_and_conditions": r.terms_conditions,
				"data_consent": 1,
			}, update_modified=False)

	event = lead.event 
	
	if not event and requests:
		event = requests[0].event_name
	
	# 1. Add lead.event as a tag
	if event:
		default_tags.add(event)
		
		# 2. Add capitalized acronym from company name excluding the year
		# Example: "We Do This" becomes "WDT"

		acronym = "".join([
			word[0] 
			for word in event.split() 
			if not (len(word) == 4 and word.isdigit() and word.startswith('20'))
		]).upper()

		if acronym:
			default_tags.add(acronym)

			
	# 3. Add creation year for all associated Requests
	# Assuming there is a link field in 'Request' called 'lead'

	# for req in requests:
	#     creation_year = frappe.utils.getdate(req.creation).year
	#     if creation_year:
	#         default_tags.add(f"{req.type} {str(creation_year)}")
			
	return list(default_tags)


def get_request(email, second_email=None):
    # Start with the primary email
    emails_to_search = [email]
    
    # Add the second email if it's provided and is not the same as the first one
    if second_email and second_email != email and second_email != '':
        emails_to_search.append(second_email)

    # Use a parameterized query for safety. 
    # frappe.db.sql will handle converting the Python list/tuple into the appropriate 
    # SQL IN clause format (e.g., ('email1@example.com', 'email2@example.com')).
    sql = """
        SELECT `name`, `creation`, `event_name`, `type`, `event_name`, `type`, `interest_type`, `phone_number`, `first_name`, `last_name`, `company`, `job_title`,
				`country`, `industry`, `address`, `city`, `source`, `terms_conditions`, `full_name`, `newsletter`
        FROM `tabRequest`
        WHERE `email_address` IN %s
        ORDER BY `creation` DESC
        LIMIT 1
    """
    
    # Execute the query, passing the list of emails as the parameter
    # frappe.db.sql expects a tuple of parameters when using %s
    results = frappe.db.sql(sql, (emails_to_search,), as_dict=1)
    
    # The function already returns the results from the query
    return results
	

@frappe.whitelist()
def sync_request_tags():
    """
    Triggers the sync_request_tags function to run asynchronously via the worker.
    """
    frappe.enqueue('gia_events.api.bg_sync_request_tags', queue='default')
    frappe.msgprint("Sync is running in the background", indicator="blue", alert=True)


def bg_sync_request_tags():
	leads = frappe.get_all("Lead", fields=["name", "lead_name", "latest_request_entry"],
		order_by="modified asc",  limit=0)

	for lead in leads:
		if not lead.latest_request_entry:
			update_request_details(lead.name)
		else:
			add_request_tags_to_lead(lead.name, lead.latest_request_entry)



def update_tags_hook():
	if import_tags and not (current_tags or current_tags[0]==''):
		tag_lead(lead)
		frappe.db.commit()
	# else:
	# 	update_tags_from_frm(lead)


def tag_is_only_event_name(lead):
	if lead.event and lead.import_tags:
		return lead.event == lead.import_tags
	return False
	

@frappe.whitelist()
def update_tags_and_request_details(lead, project=None, event=None, method=None):
	update_tags_from_frm(lead)
	check_refresh = update_request_details(lead)
	if not project:
		update_lead_project(lead, event)
		check_refresh = "refresh"
		
	if check_refresh == "refresh":
		frappe.db.commit()

	return check_refresh

def update_lead_project(lead, event=None):

	if type(lead) is not str:
		lead = lead.name

	prj = get_or_create_project(lead, event)
	frappe.db.set_value("Lead", lead, "project", prj)

def get_or_create_project(lead=None, event=None):
	if not lead and not event: return

	project = None
	if not event:
		lead_doc = frappe.get_doc("Lead", lead)
		requests = get_request(lead_doc.email_id, lead_doc.second_email)
		event = requests[0].event_name

	projects = frappe.get_all("Project", filters={"project_name": event}, fields=['name'], limit=1)
	if len(projects) < 1:
		new_project = frappe.get_doc({
			"doctype": "Project",
			"project_name": event.event_name,
			"project_type": "Event"
			})
		new_project.insert(ignore_permissions=True)
		project = new_project.name
	else:
		project = projects[0].name
	return project
	
def get_first_and_last_requests(email, second_email=None):
	emails_to_search = [email]

	if second_email and second_email != email and second_email != '':
		emails_to_search.append(second_email)

	# Use a concise alias for the long select list
	select_cols = "`name`, `creation`, `event_name`, `type`, `interest_type`, `phone_number`, `first_name`, `last_name`, `company`, `job_title`, `country`, `industry`, `address`, `city`, `source`, `terms_conditions`, `full_name`"

	sql = f"""
		(
			-- Get the Newest (Most Recent) Entry
			SELECT {select_cols}
			FROM `tabRequest` T1
			WHERE T1.`email_address` IN %s OR T1.`corporate_email` IN %s
			ORDER BY T1.`creation` DESC
			LIMIT 1
		)
		UNION ALL
		(
			-- Get the Oldest Entry
			SELECT {select_cols}
			FROM `tabRequest` T1
			WHERE (T1.`email_address` IN %s OR T1.`corporate_email` IN %s)
			-- Find the absolute MIN creation time for the given emails
			AND T1.`creation` = (
				SELECT MIN(T2.`creation`)
				FROM `tabRequest` T2
				WHERE (T2.`email_address` IN %s OR T2.`corporate_email` IN %s)
			)
			-- Add a condition to prevent selecting the same record twice
			-- if only one request exists (i.e., min(creation) == max(creation))
			AND T1.`name` != (
				SELECT T3.`name`
				FROM `tabRequest` T3
				WHERE (T3.`email_address` IN %s OR T3.`corporate_email` IN %s)
				ORDER BY T3.`creation` DESC
				LIMIT 1
			)
			LIMIT 1
		)
		ORDER BY `creation` DESC
	"""

	# We repeat the tuple to fill all the %s placeholders (2 * 4 = 8 total)
	params = (
		emails_to_search, emails_to_search, # Newest SELECT
		emails_to_search, emails_to_search, # Oldest SELECT outer
		emails_to_search, emails_to_search, # Oldest SELECT MIN subquery
		emails_to_search, emails_to_search  # Oldest SELECT NOT EQUAL subquery
	)

	results = frappe.db.sql(sql, params, as_dict=1)
	return results


def update_request_details(lead):
	"""
	Updates the Lead document with details from the newest and oldest related Request documents.
	Consolidates updates for missing core fields and tracks first/latest requests.
	Updates missing core fields one by one on condition (only if the field is empty).
	"""
	# Get the Lead object if only the name is passed
	if isinstance(lead, str):
		lead = frappe.get_doc("Lead", lead)

	# Retrieves the newest request at index [0] and the oldest at index [-1]
	requests = get_first_and_last_requests(lead.email_id, lead.second_email)

	# Dictionary to hold all fields that need updating
	update_data = {}

	if requests:
		latest_req = requests[0]
		first_req = requests[-1] # This is the oldest request, even if there's only one.
		
		if not lead.event and latest_req.event_name:
			update_data["event"] = latest_req.event_name
			
		# type (Lead.type)
		if not lead.type and latest_req.type:
			update_data["type"] = latest_req.type
			
		# interest_type (Lead.request_type)
		if not lead.request_type and latest_req.interest_type:
			update_data["request_type"] = latest_req.interest_type
			
		# phone_number (Lead.phone and Lead.lead_number)
		if not lead.phone and latest_req.phone_number:
			update_data["phone"] = latest_req.phone_number
			update_data["lead_number"] = latest_req.phone_number
			
		# first_name (Lead.first_name)
		if not lead.first_name and latest_req.first_name:
			update_data["first_name"] = latest_req.first_name
			
		# last_name (Lead.last_name)
		if not lead.last_name and latest_req.last_name:
			update_data["last_name"] = latest_req.last_name
			
		# company (Lead.company_name)
		if not lead.company_name and latest_req.company:
			update_data["company_name"] = latest_req.company
			
		# job_title (Lead.job_title)
		if not lead.job_title and latest_req.job_title:
			update_data["job_title"] = latest_req.job_title
			
		# full_name (Lead.lead_name)
		if not lead.lead_name and latest_req.full_name:
			update_data["lead_name"] = latest_req.full_name
			
		# country (Lead.country)
		if not lead.country and latest_req.country:
			update_data["country"] = latest_req.country
			
		# industry (Lead.industry) - requires validation
		if not lead.industry and latest_req.industry:
			# Assuming validate_industry is defined and available
			validated_industry = validate_industry(latest_req.industry)
			if validated_industry:
				update_data["industry"] = validated_industry
			
		# address (Lead.address)
		if not lead.address and latest_req.address:
			update_data["address"] = latest_req.address
			
		# city (Lead.city)
		if not lead.city and latest_req.city:
			update_data["city"] = latest_req.city
			
		# source (Lead.source)
		if not lead.source and latest_req.source:
			update_data["source"] = latest_req.source
			
		# terms_conditions (Lead.terms_and_conditions)
		if not lead.terms_and_conditions and latest_req.terms_conditions:
			update_data["terms_and_conditions"] = latest_req.terms_conditions
			
		# data_consent (Lead.data_consent)
		# Assuming data consent should be marked if the lead is created from a request, and it's not already set
		if not lead.data_consent:
			update_data["data_consent"] = 1


		# --- 2. Request History Logic: Conditionally update first/latest request details ---

		# Latest Request Details
		# Compare dates as strings for robust comparison (handles datetime/date/string fields)
		# Latest Request Details (Expanded condition)
		latest_req_date = getdate(latest_req.creation)
		
		# Update if the field is empty OR if the lead's date (normalized) does not match the latest request date
		if not lead.latest_request_date or getdate(lead.latest_request_date) != latest_req_date:
			update_data["latest_request_date"] = latest_req_date
		
		if lead.latest_request_entry != latest_req.name:
			update_data["latest_request_entry"] = latest_req.name

		# First Request Details (Expanded condition)
		first_req_date = getdate(first_req.creation)
		
		# Update if the field is empty OR if the lead's date (normalized) does not match the first request date
		if not lead.first_request or getdate(lead.first_request) != first_req_date:
			update_data["first_request"] = first_req_date

		if lead.first_request_entry != first_req.name:
			update_data["first_request_entry"] = first_req.name
		
		# add request tags
		add_request_tags_to_lead(lead=lead.name, request=latest_req.name)
			
	# Final database write: Only execute set_value if update_data contains any changes
	if update_data:
		# Use a single database call for all compiled updates
		frappe.db.set_value("Lead", lead.name, update_data, update_modified=False)
		return "refresh"
	return

def add_request_tags_to_lead(lead, request):
	lead_doc = frappe.get_doc("Lead", lead)
	req_doc = frappe.get_doc("Request", request)

	lead_tags = lead_doc.get_tags()

	for tag in req_doc.get_tags():
		if tag not in lead_tags:
			lead_doc.add_tag(tag)



@frappe.whitelist()
def update_tags_from_frm(lead, method=None):
	""" if lead has tags but lead.import_tags has no tags. update import_tags
		if lead is tagless, add default tags """

	if type(lead) is str:
		lead = frappe.get_doc("Lead", lead)

	current_tags = get_current_tags(lead.name)
	import_tags = lead.import_tags
	is_tagged = len(current_tags)>1 and (current_tags[0]!='')
	""" current_tags[0]=='') checks for empty tags bc tags always have a default tag with an empty str value '' """

	tags_are_updated = tags_field_is_updated(import_tags, current_tags)
	tag_is_just_event_name = tag_is_only_event_name(lead)

	# if tags are fine, discontinue
	if (is_tagged and tags_are_updated) and not tag_is_just_event_name:
		# ep(1)
		return

	# Condition 2: If the lead has tags but import_tags is different, update import_tags to match tags.
	elif (is_tagged and not tags_are_updated) and not tag_is_just_event_name:
		# ep(2)
		update_lead_import_tags_field(lead)
		frappe.db.commit()
	
	# Condition 3: If the lead is tagless (has no tags), add default tags.
	elif (not is_tagged and not import_tags) or tag_is_just_event_name: 
		# ep(3)
		default_tags = make_default_tags(lead)
		for tag in default_tags:
			lead.add_tag(tag)
		update_lead_import_tags_field(lead)

		frappe.db.commit()
		frappe.msgprint("Reset to default tags", indicator="blue", alert=True)
	
	# set tags from import_tags
	elif import_tags and not is_tagged:
		# ep(4)
		update_lead_tags_from_field(lead)
		frappe.db.commit()
	else:
		ep('else')



def tags_field_is_updated(import_tags, current_tags):
	if import_tags and current_tags:
		tag_string = ", ".join(current_tags)	
		return import_tags == tag_string
	else:
		return False

@frappe.whitelist(allow_guest=True)
def update_lead_tags_from_field(doc, method=None):
	""" add tags to match lead.import_tags 
		- called by hooks.py"""

	if type(doc) is str: 
		doc = frappe.get_doc("Lead", doc)

	if doc.import_tags:
		tags = doc.import_tags.split(",")

		for tag in tags:
			tag = format(tag)
			doc.add_tag(tag)

def update_lead_import_tags_field(lead):
	""" update lead.import_tags field to match tags on the doctype """

	tag_string = get_tags_as_str(lead)
	frappe.db.set_value("Lead", lead.name, "import_tags", tag_string) #, update_modified=False)

def get_incomplete_leads():
	# The SQL query to select name, project, and event where import_tags is NULL.
	sql_query = """
		SELECT
			name,
			project,
			event
		FROM
			tabLead
		WHERE
			import_tags IS NULL OR
			first_request IS NULL OR
			project IS NULL
		ORDER BY
			modified DESC
	"""

	# Execute the query. The 'as_list=True' (default) returns a list of tuples/lists.
	# We use 'as_dict=1' here for a more convenient list of dictionaries, 
	# which is similar to what frappe.get_all returns by default.
	leads = frappe.db.sql(sql_query, as_dict=1)

	return leads


# gets all leads then updates lead.import_tags field if its not equal to the tags on the doctype
@frappe.whitelist(allow_guest=True)
def set_empty_lead_tags():

	skipped = 0
	updated = 0

	leads = get_incomplete_leads()
	total = len(leads)
	
	count = 0
	for lead in leads:
		update_tags_and_request_details(lead.name, lead.project, lead.event)
		count += 1
		if count >= 500: break

	bal = total - count
	return [total, count, bal]



# gets all leads then updates lead.import_tags field if its not equal to the tags on the doctype
@frappe.whitelist(allow_guest=True)
def update_lead_tags():

	skipped = 0
	updated = 0

	leads = frappe.get_all("Lead", fields=["name", "import_tags"], order_by="modified asc", limit=0)

	for lead in leads:
		lead_name = lead.name
		tags = get_tags_as_str(lead_name)

		if tags == "" or tags == lead.import_tags:
			skipped += 1
			continue
		else:
			tag_len = len(tags or "")
			import_tag_len = len(lead.import_tags or "")
			
			if tag_len >= 0:
				updated += 1
				frappe.db.set_value("Lead", lead_name, "import_tags", tags, update_modified=False)
				frappe.db.commit()
			else:
				skipped += 1


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