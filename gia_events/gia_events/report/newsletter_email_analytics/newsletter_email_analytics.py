# Copyright (c) 2013, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
	data = frappe.db.sql("""SELECT recipients.recipient, links.owner, email_queue.read_by_recipient, links.original_url, recipients.status, links.click_rate , links.clicked, email_queue.reference_name FROM ((`tabEmail Links` AS links INNER JOIN `tabEmail Queue Recipient` AS recipients ON links.parent = recipients.parent) INNER JOIN `tabEmail Queue` AS email_queue ON links.parent = email_queue.name) WHERE email_queue.reference_doctype = "Newsletter";""")
	return data

def get_columns():
    return [
		"Email Recipient: Data",
		"Sent By: Data",
        "Read by Recipient: Data",
		"Email Link: Data",
		"Email Status: Data",
		"Click Rate: Data",
		"Clicked: Data",
		"Newsletter: Data"
	]