import frappe
from frappe import _


PENDING_PRODUCTION = "Pending Production"


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def query_sales_order(doctype, txt, searchfield, start, page_len, filters):
	"""Return only Sales Orders released for production."""
	filters = frappe._dict(filters or {})
	production_item = filters.get("production_item")

	if not production_item:
		return []

	return frappe.get_list(
		"Sales Order",
		fields=["name"],
		filters=[
			["Sales Order", "docstatus", "=", 1],
			["Sales Order", "custom_process_status", "=", PENDING_PRODUCTION],
		],
		or_filters=[
			["Sales Order Item", "item_code", "=", production_item],
			["Packed Item", "item_code", "=", production_item],
		],
		as_list=True,
		distinct=True,
	)


def validate_sales_order_process_status(doc, method=None):
	if not doc.sales_order:
		return

	process_status = frappe.db.get_value("Sales Order", doc.sales_order, "custom_process_status")
	if process_status != PENDING_PRODUCTION:
		frappe.throw(
			_("销售订单 {0} 未放行生产，当前流程状态：{1}").format(
				doc.sales_order, process_status or ""
			)
		)
