# Copyright (c) 2021, Bantoo Accounting and contributors
# For license information, please see license.txt

import frappe
#import pytracking
from frappe.model.document import Document
import re

class TestEmailCampaign(Document):
	def before_save(self):
		#open_tracking_url = pytracking.get_open_tracking_url(
		#{"customer_id": "chipohameja@gmail.com"}, base_open_tracking_url="https://giaevents.thebantoo.com/app/web-page/email-tracking/",
		#webhook_url="https://thebantoo.com/hello", include_webhook_url=True)
		
		#link = self.message.find("href=\"http")
		#frappe.msgprint(str(self.message[link:]))
		#frappe.msgprint(str(open_tracking_url))
		
		s = self.message
		pattern = "href=\"(.*?)\""
		
		links = re.findall(pattern, s)
		#substring = re.search(pattern, s).group(1)
		#self.message.replace(substring, tracking_link)
		#frappe.msgprint(str(self.message))
		#frappe.throw(str(self.name))
		
		"""tracking_link = "https://giaevents.thebantoo.com/email-tracking?link=" + substring
		
		doc = frappe.get_doc("Test Email Campaign", "Cmpaign001")
		row = doc.append("em_links", {
			"link_id": tracking_link,
			"original_url": substring
		})
		row.insert()"""
		for link in links:
			frappe.msgprint(str(link))