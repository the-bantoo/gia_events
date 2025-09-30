// Copyright (c) 2021, Bantoo Accounting and contributors
// For license information, please see license.txt

frappe.ui.form.on('Discount Request', {
	refresh: function(frm) {

		if(!frm.doc.lead){
			frm.set_intro('Could not find any related Lead or Request', 'yellow');
			frappe.call({
				method: 'set_lead_n_request',
				doc: frm.doc,
				callback(r){
					if (r.message==true){
						frm.reload_doc()
					}
				}
			})
			
		}
		else{
			frm.set_intro('');
		}

	}
});


