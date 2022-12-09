# Copyright (c) 2013, Bantoo Accounting Innovations and contributors
# For license information, please see license.txt


import frappe
from frappe import _

def execute(filters=None):
    return get_columns(), get_data(filters)

def get_data(filters):
    data = frappe.db.sql("""SELECT	te.event_start_date,
                                    ea.parent,
                                    ea.location,
                                    COUNT(ea.attendee_id),
                                    COUNT(CASE ea.payment_status WHEN 'Paid' THEN 1 ELSE NULL END), 
                                    COUNT(CASE ea.payment_status WHEN 'Free' THEN 1 ELSE NULL END),
                                    COUNT(CASE ea.attendance_type WHEN 'In-Person' THEN 1 ELSE NULL END),
                                    COUNT(CASE ea.attendance_type WHEN 'Online' THEN 1 ELSE NULL END),
                                    COUNT(CASE ea.attendance_status WHEN 'Present' THEN 1 ELSE null END),
                                    COUNT(CASE ea.attendance_status WHEN 'Absent' THEN 1 ELSE null END),
                                    COUNT(CASE WHEN ea.attendance_status <> 'Absent' AND  ea.attendance_status <> 'Present' THEN 1 ELSE NULL END),
                                    SUM(ea.paid_amount)
                            FROM `tabAttendee Table` AS ea
                            RIGHT JOIN `tabEvents` AS te
                            ON te.name = ea.parent
                            GROUP BY ea.location;
                        """)
    return data

def get_columns():
    return [
        "Date: Date",
        "Event: Data",
        "Country: Data",
        "Total: Data",
        "Paid: Data",
        "Free: Data",
        "In-Person: Data",
        "Online: Data",
        "Present: Data",
        "Absent: Data",
        "Unconfirmed Attendance: Data",
        "Paid Total: Currency"
    ]
