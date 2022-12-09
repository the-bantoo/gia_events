import frappe
from frappe import _

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict
    print(data)
    call_log = frappe.get_doc({
        "doctype": "GIA Call Log",
        "status": data.CallStatus
    })
    call_log.insert(ignore_permissions=True)
    return context