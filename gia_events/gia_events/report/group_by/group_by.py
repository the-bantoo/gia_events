# Copyright (c) 2013, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
    data = frappe.db.sql("""SELECT parent, COUNT(attendee_id), COUNT(CASE payment_status WHEN 'Paid' THEN 1 ELSE NULL END), 
	COUNT(CASE payment_status WHEN 'Free' THEN 1 ELSE NULL END), location FROM `tabAttendee Table` GROUP BY location;""")
    return data

def get_columns():
    return [
        "Event: Data",
		"Number Of Attendees: Data",
		"Paid Attendance: Data",
		"Free Attendance: Data",
		"Country: Data"
	]

"""
SELECT recipients.recipient, links.owner, email_queue.read_by_recipient, links.original_url, 
recipients.status, links.click_rate, links.clicked, email_queue.reference_name 
FROM ((`tabEmail Links` AS links 
INNER JOIN `tabEmail Queue Recipient` 
AS recipients ON links.parent = recipients.parent) 
INNER JOIN `tabEmail Queue` 
AS email_queue 
ON links.parent = email_queue.name) 
WHERE email_queue.reference_doctype = "Newsletter";
"""

"""
SELECT p.name, p.posting_date, p.supplier,p.tax_withholding_category,p.base_net_total
FROM ((tab`tabPurchase Invoice` AS p
INNER JOIN `tabPurchase Taxes and Charges` as t 
ON p.name = t.parent)
INNER JOIN `tabTax Withholding Category` AS c
ON c. = t.)
GROUPBY = ;
"""
