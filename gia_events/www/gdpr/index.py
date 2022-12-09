import frappe
from frappe import _
from frappe.utils import today

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict
    
    request_dict = {"Data Rectification": "Rectification Request", "Data Erasure": "Erasure Request"}
    request_type = data['fields[request_for][value]']
    
    compliance_request = frappe.get_doc({
        "doctype": request_dict[str(request_type)],
        "first_name": data['fields[first_name][value]'],
        "last_name": data['fields[last_name][value]'],
        "full_name": data['fields[first_name][value]'] + " " + data['fields[last_name][value]'],
        "email_address": data['fields[email_address][value]'],
        "message": str(data['fields[message][value]'])
        })
    compliance_request.insert(ignore_permissions=True)
