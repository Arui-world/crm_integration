frappe.listview_settings["Sales Order"] = frappe.listview_settings["Sales Order"] || {};

frappe.listview_settings["Sales Order"].add_fields = [
	...(frappe.listview_settings["Sales Order"].add_fields || []),
	"`tabSales Order`.`custom_crm_status`",
];

frappe.listview_settings["Sales Order"].formatters = {
	...(frappe.listview_settings["Sales Order"].formatters || {}),
	custom_crm_status: function(value) {
		const status = value || "Unpushed";
		const color = status === "Pushed" ? "blue" : "red";

		return `<span class="indicator-pill ${color} no-indicator-dot">${__(status)}</span>`;
	},
};
