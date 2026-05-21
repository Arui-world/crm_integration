import frappe
from frappe import _


DELIVERABLE = "Deliverable"
COMPLETED = "Completed"


def validate_sales_order_process_status(doc, method=None):
	sales_orders = {
		item.against_sales_order
		for item in doc.get("items", [])
		if item.get("against_sales_order")
	}

	if not sales_orders:
		return

	invalid_orders = frappe.get_all(
		"Sales Order",
		filters={
			"name": ["in", list(sales_orders)],
			"custom_process_status": ["!=", DELIVERABLE],
		},
		fields=["name", "custom_process_status"],
	)

	if invalid_orders:
		messages = [
			_("{0}: {1}").format(order.name, order.custom_process_status or "")
			for order in invalid_orders
		]
		frappe.throw(
			_("以下销售订单未放行发货，不能创建销售出库：<br>{0}").format(
				"<br>".join(messages)
			)
		)

def mark_sales_orders_completed_on_submit(doc, method=None):
	sales_orders = get_linked_sales_orders(doc)
	if not sales_orders:
		return

	for sales_order in sales_orders:
		frappe.db.set_value(
			"Sales Order",
			sales_order,
			"custom_process_status",
			COMPLETED,
			update_modified=True,
		)

	frappe.logger().info(
		f"Delivery Note {doc.name} submitted; marked Sales Orders completed: {', '.join(sales_orders)}"
	)


def get_linked_sales_orders(doc):
	return sorted(
		{
			item.against_sales_order
			for item in doc.get("items", [])
			if item.get("against_sales_order")
		}
	)

