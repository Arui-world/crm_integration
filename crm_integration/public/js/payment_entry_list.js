(function() {
	const existing_settings = frappe.listview_settings["Payment Entry"] || {};

	frappe.listview_settings["Payment Entry"] = Object.assign({}, existing_settings, {
		onload: function(listview) {
			if (existing_settings.onload) {
				existing_settings.onload(listview);
			}
			schedule_return_to_sales_order_button(listview);
		},

		refresh: function(listview) {
			if (existing_settings.refresh) {
				existing_settings.refresh(listview);
			}
			schedule_return_to_sales_order_button(listview);
		}
	});

	function schedule_return_to_sales_order_button(listview) {
		add_return_to_sales_order_button(listview);
		frappe.after_ajax(function() {
			add_return_to_sales_order_button(listview);
		});
		setTimeout(function() {
			add_return_to_sales_order_button(listview);
		}, 300);
	}

	function add_return_to_sales_order_button(listview) {
		const sales_order = get_sales_order_from_route();
		if (!sales_order || !listview || !listview.page || $(".crm-return-sales-order").length) {
			return;
		}

		const $button = listview.page.add_inner_button(__("返回销售订单"), function() {
			frappe.set_route("Form", "Sales Order", sales_order);
		});

		$button.addClass("crm-return-sales-order");
	}

	function get_sales_order_from_route() {
		return (
			get_sales_order_from_query_string(window.location.search) ||
			get_sales_order_from_query_string(window.location.href) ||
			get_sales_order_from_frappe_route() ||
			get_sales_order_from_route_options()
		);
	}

	function get_sales_order_from_query_string(value) {
		if (!value) {
			return null;
		}

		const query_string = value.includes("?") ? value.slice(value.indexOf("?") + 1) : value;
		const params = new URLSearchParams(query_string);
		return (
			params.get("Payment Entry Reference.reference_name") ||
			params.get("Payment+Entry+Reference.reference_name") ||
			params.get("reference_name")
		);
	}

	function get_sales_order_from_frappe_route() {
		const route = frappe.get_route ? frappe.get_route() : [];
		const route_string = route.join("/");
		const match = route_string.match(/SAL-ORD-[A-Za-z0-9-]+/);
		return match ? match[0] : null;
	}

	function get_sales_order_from_route_options() {
		const route_options = frappe.route_options || {};
		return (
			route_options["Payment Entry Reference.reference_name"] ||
			route_options.reference_name ||
			null
		);
	}
})();
