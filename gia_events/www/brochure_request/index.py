import frappe
from frappe import _
from frappe.utils import today
from gia_events.api import process_brochure_request

def get_context(context):
        
    data = frappe.form_dict
    process_brochure_request(data)

    return context
