frappe.listview_settings["Sales Order"] = frappe.listview_settings["Sales Order"] || {};

frappe.listview_settings["Sales Order"].add_fields = [
	...(frappe.listview_settings["Sales Order"].add_fields || []),
	"`tabSales Order`.`custom_process_status`",
];

frappe.listview_settings["Sales Order"].formatters = {
	...(frappe.listview_settings["Sales Order"].formatters || {}),
	custom_process_status: function(value) {
		const status = value || "Pending Confirmation";
		const colors = {
			"Pending Confirmation": "orange",
			"Rejected": "red",
			"Pending Deposit Confirmation": "yellow",
			"Pending Production": "blue",
			"Pending Final Payment": "yellow",
			"Deliverable": "blue",
			"Completed": "green",
		};

		return `<span class="indicator-pill ${colors[status] || "gray"} no-indicator-dot">${__(status)}</span>`;
	},
};
