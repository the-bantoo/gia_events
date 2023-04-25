// Copyright (c) 2021, Bantoo Accounting and contributors
// For license information, please see license.txt

function create_new() {
	console.log('create new');
}

frappe.ui.form.on('Discount Request', {
	refresh: function(frm) {
		cur_page.set_primary_action('Create Request', () => {
			console.log('create new');
		}, 'octicon octicon-plus');
	}
});


