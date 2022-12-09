import frappe
from frappe import _
from frappe.utils import today

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict
    
    speaker_form = frappe.get_doc({
        "doctype": "Speaker Form",
        "event_name": data['fields[event_name][value]'],
        "data_consent": True,
        "full_name": data['fields[f_name][value]'] + " " + data['fields[l_name][value]'],
        "job_title": data['fields[job_title][value]'],
        "company": data['fields[company][value]'],
        "email_address": data['fields[email][value]'],
        "phone_number": data['fields[mobile_phone][value]'],
        "corporate_number": data['fields[phone][value]'],
        "country": data['fields[country][value]'],
        "speaker_bio": str(data['fields[biography][value]']),
        "topic": str(data['fields[presentation_title][value]']),
        "bullet_points": str(data['fields[bullet_points][value]']),
        "interested_session": data['fields[interested][value]'],
        "profile_image": data['fields[file][value]']
        })
    speaker_form.insert(ignore_permissions=True)
    return context
