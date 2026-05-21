frappe.ui.form.on("Sales Invoice", {
	refresh: function(frm) {
		add_return_to_sales_order_button(frm);
	}
});

function add_return_to_sales_order_button(frm) {
	const sales_order = get_source_sales_order(frm);
	if (!sales_order) {
		return;
	}

	frm.add_custom_button(__("返回销售订单"), function() {
		frappe.set_route("Form", "Sales Order", sales_order);
	});
}

function get_source_sales_order(frm) {
	const item_sales_order = get_sales_order_from_items(frm);
	if (item_sales_order) {
		return item_sales_order;
	}

	return get_sales_order_from_session(frm);
}

function get_sales_order_from_items(frm) {
	const item = (frm.doc.items || []).find(function(row) {
		return row.sales_order;
	});

	return item && item.sales_order;
}

function get_sales_order_from_session(frm) {
	if (!window.sessionStorage) {
		return null;
	}

	try {
		const raw_value = sessionStorage.getItem("crm_integration_sales_invoice_source");
		if (!raw_value) {
			return null;
		}

		const source = JSON.parse(raw_value);
		if (source.sales_order && (frm.doc.__islocal || source.sales_invoice === frm.doc.name)) {
			return source.sales_order;
		}
	} catch (e) {
		return null;
	}

	return null;
}
