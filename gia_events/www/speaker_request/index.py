import frappe
from frappe import _
from frappe.utils import today

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict
    
    if frappe.db.exists({'doctype': 'Lead', 'email_id': data['fields[email][value]']}):
        request_status = True
    else:
        request_status = False

    if data['fields[acceptance][value]'] == "on":
        acceptance = True
    else:
        acceptance = False
     
    speaker_request = frappe.get_doc({
        "doctype": "Request",
        "request_type": "Speaker Request",
        "event_name": data['fields[event_name][value]'],
        "already_exists": request_status,
        "first_name": data['fields[f_name][value]'],
        "newsletter": acceptance,
        "source": "Online Registration",
        "last_name": data['fields[l_name][value]'],
        "full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
        "job_title": data['fields[job_title][value]'],
        "company": data['fields[company][value]'],
        "email_address": data['fields[email][value]'],
        "phone_number": data['fields[phone][value]'],
        "country": data['fields[country][value]'],
        "interest_type": data['fields[more_about][value]'],
        "type": "Speaker",
        "speaker_bio": str(data['fields[speaker_bio][value]']),
        "topic": str(data['fields[topic][value]'])
        })
    speaker_request.insert(ignore_permissions=True)
    return context