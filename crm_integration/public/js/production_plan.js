frappe.ui.form.off("Production Plan", "get_sales_orders");

frappe.ui.form.on("Production Plan", {
	setup: function(frm) {
		apply_sales_order_query(frm);
	},

	refresh: function(frm) {
		apply_sales_order_query(frm);
	},

	get_sales_orders: function(frm) {
		frappe.call({
			method: "crm_integration.crm_integration.production_plan.get_open_sales_orders",
			args: {
				doc: frm.doc
			},
			freeze: true,
			freeze_message: __("正在获取销售订单..."),
			callback: function(r) {
				const sales_orders = r.message || [];
				frm.clear_table("sales_orders");

				if (!sales_orders.length) {
					frappe.msgprint(__("没有可用于生产计划的销售订单"));
				}

				sales_orders.forEach(function(row) {
					const child = frm.add_child("sales_orders");
					child.sales_order = row.name;
					child.sales_order_date = row.transaction_date;
					child.customer = row.customer;
					child.grand_total = row.base_grand_total;
				});

				frm.refresh_field("sales_orders");
			}
		});
	}
});

function apply_sales_order_query(frm) {
	frm.set_query("sales_order", "sales_orders", function() {
		return {
			query: "crm_integration.crm_integration.production_plan.sales_order_query",
			filters: {
				company: frm.doc.company,
				item_code: frm.doc.item_code
			}
		};
	});
}
