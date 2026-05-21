import frappe
from frappe import _
from frappe.utils import now


PENDING_CONFIRMATION = "Pending Confirmation"
REJECTED = "Rejected"
PENDING_DEPOSIT_CONFIRMATION = "Pending Deposit Confirmation"
PENDING_PRODUCTION = "Pending Production"


def set_process_status(sales_order, process_status, status=None):
	"""Update process status without running the full Sales Order save cycle."""
	sales_order.db_set("custom_process_status", process_status, update_modified=True)
	if status:
		sales_order.db_set("status", status, update_modified=True)
	sales_order.notify_update()


@frappe.whitelist()
def reject_sales_order(sales_order_name):
	"""Reject a CRM-created Sales Order while it is waiting for ERP confirmation."""
	sales_order = frappe.get_doc("Sales Order", sales_order_name)

	if sales_order.docstatus != 0:
		frappe.throw(_("只有草稿销售订单可以驳回。"))

	if sales_order.get("custom_process_status") != PENDING_CONFIRMATION:
		frappe.throw(_("只有待确认的销售订单可以驳回。"))

	set_process_status(sales_order, REJECTED, status="Cancelled")
	frappe.logger().info(f"Sales Order {sales_order_name} rejected from production flow")

	return {
		"status": "success",
		"message": _("销售订单已驳回。"),
		"process_status": REJECTED,
		"timestamp": now(),
	}


def set_pending_deposit_confirmation_on_submit(doc, method=None):
	"""Move the production flow forward after the native ERPNext submit succeeds."""
	if doc.get("custom_process_status") == REJECTED:
		return

	doc.db_set("custom_process_status", PENDING_DEPOSIT_CONFIRMATION, update_modified=True)
	doc.custom_process_status = PENDING_DEPOSIT_CONFIRMATION
	doc.notify_update()


def prevent_rejected_sales_order_submit(doc, method=None):
	"""Rejected CRM/MES flow orders must not be submitted later."""
	if doc.get("custom_process_status") == REJECTED:
		frappe.throw(_("已驳回的销售订单不能提交。"))


@frappe.whitelist()
def confirm_deposit_and_push_to_mes(sales_order_name):
	"""Simulate deposit confirmation and MES push for now."""
	sales_order = frappe.get_doc("Sales Order", sales_order_name)

	if sales_order.docstatus != 1:
		frappe.throw(_("销售订单必须提交后才能确认定金。"))

	if sales_order.get("custom_process_status") != PENDING_DEPOSIT_CONFIRMATION:
		frappe.throw(_("只有待确认定金的销售订单可以推送至MES。"))

	# MES push is simulated as successful for now.
	frappe.logger().info(f"Simulated MES push for Sales Order {sales_order_name}")
	set_process_status(sales_order, PENDING_PRODUCTION)

	return {
		"status": "success",
		"message": _("定金已确认，销售订单已推送至MES。"),
		"process_status": PENDING_PRODUCTION,
		"timestamp": now(),
	}
