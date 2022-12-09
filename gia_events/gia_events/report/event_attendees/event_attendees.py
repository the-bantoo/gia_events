# Copyright (c) 2022, Bantoo Accounting and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_data(filters):
	#status = filters.get("pay_status")
	#status = "Free"
	data = frappe.db.sql("""SELECT full_name, parent, payment_status, attendance_type FROM `tabAttendee Table`;""")
	return data

def get_columns():
	return [
		{
			"fieldname": "full_name",
			"label": _("Full Name"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "event_name",
			"label": _("Event Name"),
			"fieldtype": "Link",
			"options": "Events",
			"width": 200
		},
		{
			"fieldname": "payment_status",
			"label": _("Payment Status"),
			"width": 200
		},
		{
			"fieldname": "attendance_type",
			"label": _("Type of Attendance"),
			"width": 200
		}
		]
