import frappe
from frappe import _
from frappe.utils import today

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict
    print(data)
    
    if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
        request_status = True
    else:
        request_status = False

    if data['fields[acceptance][value]'] == "on":
        privacy_concent = True
    else:
        privacy_concent = False
    
    if data['fields[acceptance2][value]'] == "on":
        data_concent = True
    else:
        data_concent = False
    
    free_request = frappe.get_doc({
        "doctype": "Request",
        "request_type": "Free Guest Request",
        "event_name": data['fields[event_name][value]'],
        "already_exists": request_status,
        "source": "Online Registration",
        "first_name": data['fields[f_name][value]'],
        "last_name": data['fields[l_name][value]'],
        "full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
        "job_title": data['fields[job_title][value]'],
        "company": data['fields[company][value]'],
        "email_address": data['fields[email][value]'],
        "phone_number": data['fields[phone][value]'],
        "country": data['fields[country][value]'],
        "interest_type": "Attending",
        "attendance_type": "In-Person",
        "type": "Attendee",
        "industry": data['fields[industry][value]'],
        "terms_conditions": privacy_concent,
        "data_consent": data_concent,
        "payment_status": "Free"
        })
    free_request.insert(ignore_permissions=True)
    return context
