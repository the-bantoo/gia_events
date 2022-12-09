frappe.listview_settings['Request'] = {
    onload: function(listview) {
		frappe.call ({
			method: "gia_events.api.delete_spam",
		  });
    },
};
