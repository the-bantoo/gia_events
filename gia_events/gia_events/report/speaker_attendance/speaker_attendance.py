# Copyright (c) 2013, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
    data = frappe.db.sql("""SELECT parent, COUNT(speaker_id), country FROM `tabSpeaker Table` GROUP BY country;""")
    return data

def get_columns():
    return [
        "Event: Data",
		"Number Of Speakers: Data",
		"Country: Data"
	]
