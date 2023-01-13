// Copyright (c) 2021, Bantoo Accounting and contributors
// For license information, please see license.txt

frappe.ui.form.on('Events', {
	refresh: function(frm) {

        frm.add_custom_button(__("Pull Lead Data"), function(){
            
            frappe.call({
                method: "gia_events.api.create_participants_for_event_from_leads",
                args: {
                    "event": frm.doc.name
                }
            });
        });
	}
});
