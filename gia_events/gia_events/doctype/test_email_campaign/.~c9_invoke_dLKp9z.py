# Copyright (c) 2021, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
#import pytracking
from frappe.model.document import Document

class TestEmailCampaign(Document):
	def before_save(self):
	    #open_tracking_url = pytracking.get_open_tracking_url(
        #{"customer_id": 1}, base_open_tracking_url="https://trackingdomain.com/path/",
        #webhook_url="https://thebantoo.com/hello", include_webhook_url=True)
	    
	    #link = self.message.find("href=")
	    #frappe.msgprint(str(self.message[link:]))
	    #frappe.msgprint(str(open_tracking_url))
	    s = self.message
	    pattern =
