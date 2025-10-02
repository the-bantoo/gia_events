// Copyright (c) 2021, Bantoo Accounting and contributors
// For license information, please see license.txt

frappe.ui.form.on('Request', {
	refresh: function(frm) {
		// 1. Listen for Blur on the input to catch new tags added via mouse click
        frm.page.wrapper.on('blur', '.tags-input.form-control', function() {
            setTimeout(update_lead_tags(frm), 300);
        });
		const update_lead_tags = (frm) => {
			frappe.call({
				method: "add_tags_to_lead",
				doc: frm.doc,
				callback: function(r) {

				}
			});
		};

	},
	validate(frm){
  
      if( frm.doc.type === "Attendee" && (frm.doc.payment_status === undefined || frm.doc.payment_status === "") ){
          frappe.throw('Payment Status is required to create a Lead');
          return false;
      }
      if( frm.doc.type === "Attendee" && (frm.doc.attendance_type === undefined || frm.doc.attendance_type === "") ){
          frappe.throw('Type of Attendance is required to create a Lead');
          return false;
      }
      if( frm.doc.payment_status !== "" && frm.doc.payment_status == "Paid" && frm.doc.paid_amount <= 0 ){
          frappe.throw('Paid amount should be more than 0');
          return false;
      }
      if( frm.doc.payment_status !== "" && frm.doc.payment_status == "Sponsored" && frm.doc.paid_amount <= 0){
          frappe.throw('Paid amount should be more than 0');
          return false; 
      }
  },
  first_name(frm) {
      //First and last name is undefined so set full name to empty string
      if(frm.doc.first_name === undefined && frm.doc.last_name === undefined){
          frm.set_value('full_name', "");
      }
      
      //First name is set and last name is not, set full name to first name only
      else if(frm.doc.first_name !== undefined && frm.doc.last_name === undefined){
          frm.set_value('full_name', frm.doc.first_name);
      }
      
      //Last name is set and first name is not, so det full name to last name
      else if(frm.doc.first_name === undefined && frm.doc.last_name !== undefined){
          frm.set_value('full_name', frm.doc.last_name);
      }
      
      //Both first and last names are set so set full name to first and last name
      else{
          frm.set_value('full_name', frm.doc.first_name + " " + frm.doc.last_name);
      }
      /*let person_name = frm.doc.first_name + " " + frm.doc.last_name;
    frm.set_value('lead_name', person_name);*/
  },
  
  last_name(frm) {
      //First and last name is undefined so set full name to empty string
      if(frm.doc.first_name === undefined && frm.doc.last_name === undefined){
          frm.set_value('full_name', "");
      }
      
      //First name is set and last name is not, set full name to first name only
      else if(frm.doc.first_name !== undefined && frm.doc.last_name === undefined){
          frm.set_value('full_name', frm.doc.first_name);
      }
      
      //Last name is set and first name is not, so det full name to last name
      else if(frm.doc.first_name === undefined && frm.doc.last_name !== undefined){
          frm.set_value('full_name', frm.doc.last_name);
      }
      
      //Both first and last names are set so set full name to first and last name
      else{
          frm.set_value('full_name', frm.doc.first_name + " " + frm.doc.last_name);
      }
  }
});
