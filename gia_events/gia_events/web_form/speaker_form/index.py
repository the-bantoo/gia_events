import frappe

def get_context(context):
    context.name = "Administrator"
    #print(f"\n\n\n{frappe.form_dict}\n\n\n")
    frappe.errprint("Hello")
    return context
    