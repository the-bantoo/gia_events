# Copyright (c) 2022, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt


import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

"""RIGHT JOIN `tabEvents` AS te
		ON te.name = ea.parent
"""

def get_data(filters):
	data = frappe.db.sql("""
		SELECT
			m.email_group,
			m.event,
			count(CASE m.unsubscribed WHEN '0' THEN 1 ELSE NULL END) as `currently subscribed`,
			count(CASE m.unsubscribed WHEN '1' THEN 1 ELSE NULL END) as `unsubscribed`,
			count(m.email) as `total`,
			count(CASE r.payment_status WHEN r.payment_status = 'Paid' OR r.payment_status = 'Sponsored' THEN 1 ELSE NULL END) as `converted`

		FROM `tabEmail Group Member` AS m
		LEFT JOIN `tabRequest` AS r
			ON m.email = r.email_address
			
		GROUP BY m.email_group;
	""")

	return data

def get_columns():
	return [
		{
			"fieldname": "Email List",
			"label": _("Email List"),
			"fieldtype": "Link",
			"options": "Email Group",
			"width": 350
		},
		{
			"fieldname": "Event",
			"label": _("Event"),
			"fieldtype": "Link",
			"options": "Event",
			"width": 250
		},
		{
			"fieldname": "Currently Subscribed",
			"label": _("Currently Subscribed"),
			"fieldtype": "Int",
			"width": 165
		},
		{
			"fieldname": "Unsubscribed",
			"label": _("Unsubscribed"),
			"fieldtype": "Int",
			"width": 120
		},
		{
			"fieldname": "Total",
			"label": _("Total"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "Converted to Customers",
			"label": _("Converted to Customers"),
			"fieldtype": "Int",
			"width": 200
		}
	]
