frappe.ui.form.on("Payment Entry", {
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
	const reference_sales_order = get_sales_order_from_references(frm);
	if (reference_sales_order) {
		return reference_sales_order;
	}

	return get_sales_order_from_session(frm);
}

function get_sales_order_from_references(frm) {
	const reference = (frm.doc.references || []).find(function(row) {
		return row.reference_doctype === "Sales Order" && row.reference_name;
	});

	return reference && reference.reference_name;
}

function get_sales_order_from_session(frm) {
	if (!window.sessionStorage) {
		return null;
	}

	try {
		const raw_value = sessionStorage.getItem("crm_integration_payment_entry_source");
		if (!raw_value) {
			return null;
		}

		const source = JSON.parse(raw_value);
		if (source.payment_entry === frm.doc.name && source.sales_order) {
			return source.sales_order;
		}
	} catch (e) {
		return null;
	}

	return null;
}
