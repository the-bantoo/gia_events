import frappe
from frappe import _
from frappe.utils import today

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict

    new_discount = frappe.get_doc({
        "doctype": "Discount Request",
        "full_name": data['fields[full_name][value]'],
        "company_name": data['fields[company_name][value]'],
        "corporate_email": data['fields[corporate_email][value]'],
        "event_name": data['fields[event_name][value]'],
        "newsletter": True
        })
    new_discount.insert(ignore_permissions=True)
    return context