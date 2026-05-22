import frappe
import requests
from frappe import _
from frappe.utils import cint, flt, now
from frappe.utils.data import get_datetime

from crm_integration.crm_integration.integration_log import create_crm_log, update_crm_log


PENDING_CONFIRMATION = "Pending Confirmation"
REJECTED = "Rejected"
PENDING_DEPOSIT_CONFIRMATION = "Pending Deposit Confirmation"
PENDING_PRODUCTION = "Pending Production"
PENDING_FINAL_PAYMENT = "Pending Final Payment"
DELIVERABLE = "Deliverable"
CLOSED = "Closed"

CRM_STATUS_API_TIMEOUT = 15
CRM_STATUS_CONFIRMED_DEPOSIT_PUSH_PRODUCTION = "CONFIRMED_DEPOSIT_PUSH_PRODUCTION"
CRM_STATUS_FINANCE_REJECTED = "FINANCE_REJECTED"

CRM_STATUS_EVENTS = {
	CRM_STATUS_FINANCE_REJECTED: "Sales Order Rejected",
	CRM_STATUS_CONFIRMED_DEPOSIT_PUSH_PRODUCTION: "Confirmed Deposit Push Production",
}


def set_process_status(sales_order, process_status, status=None):
	"""Update process status without running the full Sales Order save cycle."""
	sales_order.db_set("custom_process_status", process_status, update_modified=True)
	if status:
		sales_order.db_set("status", status, update_modified=True)
	sales_order.notify_update()


def sync_closed_process_status(sales_order_name, status):
	"""Keep the custom process status aligned when ERPNext closes a Sales Order."""
	if status != CLOSED:
		return

	frappe.db.set_value(
		"Sales Order",
		sales_order_name,
		"custom_process_status",
		CLOSED,
		update_modified=True,
	)


@frappe.whitelist()
def update_status(status, name):
	"""Wrap ERPNext Sales Order status update so native Close also closes our flow."""
	from erpnext.selling.doctype.sales_order.sales_order import update_status as erpnext_update_status

	erpnext_update_status(status, name)
	sync_closed_process_status(name, status)


@frappe.whitelist()
def close_or_unclose_sales_orders(names, status):
	"""Wrap ERPNext bulk close so list actions also update the custom flow status."""
	from erpnext.selling.doctype.sales_order.sales_order import (
		close_or_unclose_sales_orders as erpnext_close_or_unclose_sales_orders,
	)

	erpnext_close_or_unclose_sales_orders(names, status)

	if status != CLOSED:
		return

	for name in frappe.parse_json(names):
		if frappe.db.get_value("Sales Order", name, "status") == CLOSED:
			sync_closed_process_status(name, status)


def get_crm_status_api_url():
	url = frappe.conf.get("crm_status_api_url")
	if not url:
		frappe.throw(_("缺少 CRM 状态推送接口配置：crm_status_api_url"))
	return url


def get_crm_status_api_key():
	api_key = frappe.conf.get("crm_status_api_key")
	if not api_key:
		frappe.throw(_("缺少 CRM 状态推送接口配置：crm_status_api_key"))
	return api_key


def get_crm_status_api_verify_ssl():
	return cint(frappe.conf.get("crm_status_api_verify_ssl", 1)) == 1


def get_crm_status_event(external_status):
	return CRM_STATUS_EVENTS.get(external_status) or "Sales Order Status Push"


def push_sales_order_status_to_crm(sales_order, external_status):
	external_order_id = sales_order.get("custom_crm_order_no") or sales_order.name
	if not external_order_id:
		frappe.throw(_("缺少 CRM 订单编号，无法推送状态到 CRM。"))

	payload = {
		"sourceSystem": "ERP",
		"externalStatus": external_status,
		"externalOrderId": external_order_id,
		"remark": sales_order.get("custom_remark") or "",
		"traceId": make_crm_trace_id(sales_order.name, external_status),
		"attachments": [],
	}
	request_url = get_crm_status_api_url()
	headers = {
		"Content-Type": "application/json",
		"X-API-Key": get_crm_status_api_key(),
	}
	crm_log = create_crm_log(
		direction="Outbound",
		event=get_crm_status_event(external_status),
		status="Pending",
		reference_doctype="Sales Order",
		reference_name=sales_order.name,
		source="ERPNext",
		request_url=request_url,
		request_payload=payload,
		trace_id=payload["traceId"],
		external_status=external_status,
	)

	try:
		response = requests.post(
			request_url,
			json=payload,
			headers=headers,
			timeout=CRM_STATUS_API_TIMEOUT,
			verify=get_crm_status_api_verify_ssl(),
		)
		response_payload = parse_crm_response(response)
		response.raise_for_status()
	except requests.RequestException as exc:
		response = getattr(exc, "response", None)
		update_crm_log(
			crm_log,
			status="Failed",
			response_payload=parse_crm_response(response) if response else None,
			error_message=frappe.get_traceback(),
			http_status_code=getattr(response, "status_code", None),
		)
		frappe.log_error(
			title=_("CRM 状态推送失败"),
			message=frappe.get_traceback(),
		)
		frappe.throw(_("CRM 状态推送失败：{0}").format(str(exc)))

	update_crm_log(
		crm_log,
		status="Success",
		response_payload=response_payload,
		http_status_code=response.status_code,
	)
	frappe.logger().info(
		f"Pushed Sales Order {sales_order.name} status {external_status} to CRM with traceId {payload['traceId']}"
	)
	return response_payload


def make_crm_trace_id(sales_order_name, external_status):
	timestamp = get_datetime().strftime("%Y%m%d%H%M%S")
	return f"erp-{sales_order_name}-{external_status}-{timestamp}"


def parse_crm_response(response):
	if not response:
		return None

	content_type = response.headers.get("content-type") or ""
	if content_type.startswith("application/json"):
		try:
			return response.json()
		except ValueError:
			return response.text
	return response.text


@frappe.whitelist()
def reject_sales_order(sales_order_name):
	"""Reject a CRM-created Sales Order while it is waiting for ERP confirmation."""
	sales_order = frappe.get_doc("Sales Order", sales_order_name)

	if sales_order.docstatus != 0:
		frappe.throw(_("只有草稿销售订单可以驳回。"))

	if sales_order.get("custom_process_status") != PENDING_CONFIRMATION:
		frappe.throw(_("只有待确认的销售订单可以驳回。"))

	push_sales_order_status_to_crm(sales_order, CRM_STATUS_FINANCE_REJECTED)

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

	push_sales_order_status_to_crm(sales_order, CRM_STATUS_CONFIRMED_DEPOSIT_PUSH_PRODUCTION)

	# MES push is simulated as successful for now.
	frappe.logger().info(f"Simulated MES push for Sales Order {sales_order_name}")
	set_process_status(sales_order, PENDING_PRODUCTION)

	return {
		"status": "success",
		"message": _("定金已确认，销售订单已推送至MES。"),
		"process_status": PENDING_PRODUCTION,
		"timestamp": now(),
	}


@frappe.whitelist()
def reconcile_final_payment(sales_order_name):
	"""Release Sales Order for delivery after final payment is fully covered by advances."""
	sales_order = frappe.get_doc("Sales Order", sales_order_name)

	if sales_order.docstatus != 1:
		frappe.throw(_("销售订单必须提交后才能核销尾款。"))

	if sales_order.get("custom_process_status") != PENDING_FINAL_PAYMENT:
		frappe.throw(_("只有待核销尾款的销售订单可以执行此操作。"))

	grand_total = flt(sales_order.get("grand_total"), sales_order.precision("grand_total"))
	advance_paid = flt(sales_order.get("advance_paid"), sales_order.precision("advance_paid"))

	if advance_paid < grand_total:
		return {
			"status": "failed",
			"message": _("尾款核销失败：预付款 {0} 小于总计 {1}。").format(
				frappe.format_value(advance_paid, {"fieldtype": "Currency", "options": "currency"}, sales_order),
				frappe.format_value(grand_total, {"fieldtype": "Currency", "options": "currency"}, sales_order),
			),
			"process_status": PENDING_FINAL_PAYMENT,
			"advance_paid": advance_paid,
			"grand_total": grand_total,
			"timestamp": now(),
		}

	set_process_status(sales_order, DELIVERABLE)
	frappe.logger().info(f"Sales Order {sales_order_name} final payment reconciled")

	return {
		"status": "success",
		"message": _("尾款已核销，销售订单已放行发货。"),
		"process_status": DELIVERABLE,
		"advance_paid": advance_paid,
		"grand_total": grand_total,
		"timestamp": now(),
	}

