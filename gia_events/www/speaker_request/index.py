import frappe
from frappe import _
from frappe.utils import today
from gia_events.api import process_speaker_request

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict

    frappe.errprint(data)

    process_speaker_request(data)

    return context