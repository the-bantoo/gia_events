# Copyright (c) 2013, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    	return get_columns(), get_data(filters)

def get_data(filters):
    data = frappe.db.sql("""SELECT c.user, c.sender, c.recipients, c.subject, c.read_by_recipient, e.creation, e.original_url, e.clicked, e.click_rate FROM `tabEmail Links` e INNER JOIN `tabCommunication` c ON e.parent = c.name;""")
    return data

def get_columns():
    return [
        "User Name: Data",
        "Sender Email: Data",
        "Recipient: Data",
        "Subject: Data",
		"Seen: Check",
		"Date: Date",
  		"Link: Data",
		"Clicked: Check",
		"Click Rate: Int",
	]