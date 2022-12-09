import frappe
from frappe import _
from frappe.utils import today

"""def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict

    if frappe.db.exists({'doctype': 'Lead', 'email_id': data["paymentEmail"]}):
        request_status = True
    else:
        request_status = False

    paid_request = frappe.get_doc({
        "doctype": "Request",
        "request_type": "Paid Request",
        #"event_name": data["eventTitle"],
        "event_name": "World Data Summit 2022",
        "already_exists": request_status,
        "first_name": data["paymentFirstName"],
        "last_name": data["paymentLastName"],
        "full_name": data["paymentFirstName"] + " " + data["paymentLastName"],
        "email_address": data["paymentEmail"],
        "number_of_tickets": data["numberOfTickets"],
        "payment_fee": data["paymentFee"],
        "currency": data["paymentCurrency"],
        "language":data["paymentLanguage"],
        "tax": data["paymentSalesTax"],
        "interest_type": "Attending",
        "type": "Attendee",
        "payment_type": data["paymentType"],
        "payment_status": "Paid",
        "source": "Xing Registration"
        })
    paid_request.insert(ignore_permissions=True)"""

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict
    number_of_tickets = data["numberOfTickets"]
    
    i = 0
    while i < int(number_of_tickets):
        if frappe.db.exists({'doctype': 'Attendee', 'email_address': data["ticketEmail"+str(i)]}):
            attendee = frappe.get_doc('Attendee', data["ticketEmail"+str(i)])
            row = attendee.append("tickets", {
                "ticket_id": data["ticketId"+str(i)],
                "ticket_category": data["ticketCategory"+str(i)],
                "event_name": data["eventTitle"]
                })
            row.insert()

            event = frappe.db.get_list("Events", filters={'status':'Registration'}, fields=['event_name'])
            row = event.append("attendees", {
                "attendee_id": data["ticketEmail"+str(i)],
                "payment_status": "Paid",
                })
            row.insert()
            i+=1
        else:
            new_attendee = frappe.get_doc({
                "doctype": "Attendee",
                "first_name": data["ticketFirstName"+str(i)],
                "last_name": data["ticketLastName"+str(i)],
                "full_name": data["ticketFirstName"+str(i)] + " " + data["ticketLastName"+str(i)],
                "email_address": data["ticketEmail"+str(i)],
                "country": "Unknown",
                "tickets": [
                    {
                        "ticket_id": data["ticketId"+str(i)],
                        "ticket_category": data["ticketCategory"+str(i)],
                        "event_name": data["eventTitle"]
                    }
                    ]
                })
            new_attendee.insert(ignore_permissions=True)

            event = frappe.db.get_list("Events", filters={'status':'Registration'}, fields=['event_name'])
            row = event.append("attendees", {
                "attendee_id": data["ticketEmail"+str(i)],
                "payment_status": "Paid",
                })
            row.insert()
            i+=1
