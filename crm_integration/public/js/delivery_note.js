frappe.ui.form.on("Delivery Note", {
	refresh: function(frm) {
		restrict_sales_order_item_selection(frm);
	}
});

function restrict_sales_order_item_selection(frm) {
	const replace_sales_order_button = function() {
		frm.remove_custom_button(__("Sales Order"), __("Get Items From"));

		if (
			frm.doc.is_return ||
			frm.doc.status === "Closed" ||
			!frm.has_perm("write") ||
			!frappe.model.can_read("Sales Order") ||
			frm.doc.docstatus !== 0
		) {
			return;
		}

		frm.add_custom_button(
			__("Sales Order"),
			function() {
				if (!frm.doc.customer) {
					frappe.throw({
						title: __("Mandatory"),
						message: __("Please Select a Customer")
					});
				}

				erpnext.utils.map_current_doc({
					method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
					args: {
						for_reserved_stock: 1
					},
					source_doctype: "Sales Order",
					target: frm,
					setters: {
						customer: frm.doc.customer
					},
					get_query_filters: {
						docstatus: 1,
						custom_process_status: "Deliverable",
						status: ["not in", ["Closed", "On Hold"]],
						per_delivered: ["<", 99.99],
						company: frm.doc.company,
						project: frm.doc.project || undefined
					},
					allow_child_item_selection: true,
					child_fieldname: "items",
					child_columns: ["item_code", "item_name", "qty", "delivered_qty"]
				});
			},
			__("Get Items From")
		);
	};

	replace_sales_order_button();
	requestAnimationFrame(replace_sales_order_button);
	setTimeout(replace_sales_order_button, 300);
}
