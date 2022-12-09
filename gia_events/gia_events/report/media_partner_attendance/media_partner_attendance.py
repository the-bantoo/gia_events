# Copyright (c) 2013, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
    data = frappe.db.sql("""SELECT parent, COUNT(media_name), media_type FROM `tabMedia Table` GROUP BY media_type;""")
    return data

def get_columns():
    return [
        "Event: Data",
		"Number Of Media Partners: Data",
		"Type of Media: Data"
	]
