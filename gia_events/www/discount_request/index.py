import frappe
from frappe import _
from frappe.utils import today
from gia_events.api import process_discount_request

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict

    process_discount_request(data)
    
    return context