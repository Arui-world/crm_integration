frappe.ui.form.on("Payment Entry", {
	refresh: function(frm) {
		add_return_to_sales_order_button(frm);
		add_save_and_submit_button(frm);
	}
});

function add_save_and_submit_button(frm) {
	if (!frm || !frm.doc || frm.doc.docstatus !== 0) {
		return;
	}

	frm.remove_custom_button(__("保存并提交"));
	frm.add_custom_button(__("保存并提交"), function() {
		save_and_submit_payment_entry(frm);
	});

	apply_save_and_submit_button_style(frm);
}

function save_and_submit_payment_entry(frm) {
	frappe.confirm(
		__("确认保存并提交此收付款凭证？"),
		function() {
			frm.save("Submit");
		}
	);
}

function apply_save_and_submit_button_style(frm) {
	requestAnimationFrame(function() {
		const labels = [...new Set(["保存并提交", __("保存并提交")])];
		const selector = labels
			.map((label) => `.page-actions button[data-label="${encodeURIComponent(label)}"]`)
			.join(", ");

		$(frm.page.wrapper)
			.find(selector)
			.removeClass("btn-default btn-secondary btn-xs")
			.addClass("btn-primary btn-sm primary-action crm-save-submit-button");
	});
}

function add_return_to_sales_order_button(frm) {
	const sales_order = get_source_sales_order(frm);
	if (!sales_order) {
		return;
	}

	frm.remove_custom_button(__("返回销售订单"));
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
