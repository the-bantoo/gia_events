# Copyright (c) 2013, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
    data = frappe.db.sql("""SELECT parent, COUNT(sponsor_name), sponsorship_type, SUM(amount) FROM `tabSponsor Table` GROUP BY sponsorship_type;""")
    return data

def get_columns():
    return [
        "Event: Data",
		"Number Of Sponsors: Data",
		"Type Of Sponsorship: Data",
  		"Amount: Currency"
	]
