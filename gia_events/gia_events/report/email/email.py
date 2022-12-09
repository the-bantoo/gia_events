# Copyright (c) 2013, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
	data = frappe.db.sql("""SELECT email.reference_name, COUNT(CASE WHEN email.read_by_recipient = 0 THEN 1 END), COUNT(CASE WHEN email.read_by_recipient = 1 THEN 1 END), COUNT(CASE WHEN links.clicked = 1 THEN 1 END) FROM `tabEmail Links` AS links INNER JOIN `tabEmail Queue` AS email ON links.parent = email.name WHERE email.reference_doctype = "Newsletter" GROUP BY email.reference_name;""")
	#data = frappe.db.sql("""SELECT email.reference_name, COUNT(CASE WHEN email.read_by_recipient = 0 THEN 1 END), COUNT(CASE WHEN email.read_by_recipient = 1 THEN 1 END) FROM `tabEmail Queue` AS email WHERE email.reference_doctype = "Newsletter" GROUP BY email.reference_name;""")
	return data

def get_columns():
    return [
        "Newsletter: Data",
		"Number of Unread Emails: Data",
		"Number of Read Emails: Data",
		"Number of Clicked Links: Data",
		#"Number of Clicks: Data"
	]

"""
SELECT email.reference_name, COUNT(CASE email.read_by_recipient WHEN email.read_by_recipient = 0 THEN 1 END), 
COUNT(CASE email.read_by_recipient WHEN email.read_by_recipient = 1 THEN 1 END), 
COUNT(CASE links.clicked WHEN links.clicked = 1 THEN 1 END), 
SUM(links.click_rate) 
FROM `tabEmail Links` AS links 
INNER JOIN `tabEmail Queue` AS email ON links.parent = email.name 
WHERE email.reference_doctype = "Newsletter" 
GROUP BY email.reference_name;
"""
