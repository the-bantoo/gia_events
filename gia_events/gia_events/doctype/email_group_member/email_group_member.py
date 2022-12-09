# Copyright (c) 2022, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class EmailGroupMember(Document):
	pass

def on_doctype_update():
	frappe.db.add_unique("Email Group Member", ("email_group", "email"))
	
def after_doctype_insert():
	frappe.db.add_unique("Email Group Member", ("email_group", "email"))