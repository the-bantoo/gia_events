import frappe
from frappe import _
from frappe.utils import today

def get_context(context):
    context.name = "Administrator"
    data = frappe.form_dict

    if frappe.db.exists({'doctype': 'Email Group Member', 'email': data['fields[email][value]']}):
        members = frappe.db.get_all("Email Group Member", filters={"email": data['fields[email][value]']}, fields=["name"])
        list_size = len(members)
        i = 0
        while i < list_size:
            frappe.db.set_value("Email Group Member", members[i]["name"], "unsubscribed", True)
            i = i + 1
