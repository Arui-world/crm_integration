import json

import frappe
from frappe import _
from pypika.terms import ExistsCriterion

from erpnext.selling.doctype.sales_order.sales_order import make_production_plan as native_make_production_plan


PENDING_PRODUCTION = "Pending Production"


@frappe.whitelist()
def make_production_plan(source_name, target_doc=None):
	validate_single_sales_order_for_production(source_name)
	return native_make_production_plan(source_name, target_doc)


@frappe.whitelist()
def get_open_sales_orders(doc):
	frappe.has_permission("Production Plan", throw=True)

	if isinstance(doc, str):
		doc = json.loads(doc)

	production_plan = frappe.get_doc(doc)
	return get_sales_orders(production_plan)


@frappe.whitelist()
def sales_order_query(doctype=None, txt=None, searchfield=None, start=None, page_len=None, filters=None):
	frappe.has_permission("Production Plan", throw=True)
	filters = frappe._dict(filters or {})

	so_table = frappe.qb.DocType("Sales Order")
	table = frappe.qb.DocType("Sales Order Item")

	query = (
		frappe.qb.from_(so_table)
		.join(table)
		.on(table.parent == so_table.name)
		.select(table.parent)
		.distinct()
		.where(
			(table.qty > table.production_plan_qty)
			& (table.docstatus == 1)
			& (so_table.custom_process_status == PENDING_PRODUCTION)
		)
	)

	if filters.get("company"):
		query = query.where(so_table.company == filters.get("company"))

	if filters.get("sales_orders"):
		query = query.where(so_table.name.isin(filters.get("sales_orders")))

	if filters.get("item_code"):
		query = query.where(table.item_code == filters.get("item_code"))

	if txt:
		query = query.where(table.parent.like(f"%{txt}%"))

	if page_len:
		query = query.limit(page_len)

	if start:
		query = query.offset(start)

	return query.run()


def get_sales_orders(doc):
	bom = frappe.qb.DocType("BOM")
	pi = frappe.qb.DocType("Packed Item")
	so = frappe.qb.DocType("Sales Order")
	so_item = frappe.qb.DocType("Sales Order Item")

	open_so_subquery1 = frappe.qb.from_(bom).select(bom.name).where(bom.is_active == 1)

	open_so_subquery2 = (
		frappe.qb.from_(pi)
		.select(pi.name)
		.where(
			(pi.parent == so.name)
			& (pi.parent_item == so_item.item_code)
			& (
				ExistsCriterion(
					frappe.qb.from_(bom)
					.select(bom.name)
					.where((bom.item == pi.item_code) & (bom.is_active == 1))
				)
			)
		)
	)

	open_so_query = (
		frappe.qb.from_(so)
		.from_(so_item)
		.select(so.name, so.transaction_date, so.customer, so.base_grand_total)
		.distinct()
		.where(
			(so_item.parent == so.name)
			& (so.docstatus == 1)
			& (so.status.notin(["Stopped", "Closed"]))
			& (so.custom_process_status == PENDING_PRODUCTION)
			& (so.company == doc.company)
			& (so_item.qty > so_item.production_plan_qty)
		)
	)

	date_field_mapper = {
		"from_date": so.transaction_date >= doc.from_date,
		"to_date": so.transaction_date <= doc.to_date,
		"from_delivery_date": so_item.delivery_date >= doc.from_delivery_date,
		"to_delivery_date": so_item.delivery_date <= doc.to_delivery_date,
	}

	for field, value in date_field_mapper.items():
		if doc.get(field):
			open_so_query = open_so_query.where(value)

	for field in ("customer", "project", "sales_order_status"):
		if doc.get(field):
			so_field = "status" if field == "sales_order_status" else field
			open_so_query = open_so_query.where(so[so_field] == doc.get(field))

	if doc.item_code and frappe.db.exists("Item", doc.item_code):
		open_so_query = open_so_query.where(so_item.item_code == doc.item_code)
		open_so_subquery1 = open_so_subquery1.where(
			doc.get_bom_item_condition() or bom.item == so_item.item_code
		)

	open_so_query = open_so_query.where(
		ExistsCriterion(open_so_subquery1) | ExistsCriterion(open_so_subquery2)
	)

	return open_so_query.run(as_dict=True)


def validate_sales_order_process_status(doc, method=None):
	sales_orders = set()

	for row in doc.get("sales_orders", []):
		if row.sales_order:
			sales_orders.add(row.sales_order)

	for row in doc.get("po_items", []):
		if row.sales_order:
			sales_orders.add(row.sales_order)

	invalid_sales_orders = get_invalid_sales_orders(sales_orders)
	if invalid_sales_orders:
		frappe.throw(
			_("以下销售订单未放行生产，不能创建或保存生产计划：{0}").format(
				", ".join(invalid_sales_orders)
			)
		)


def validate_single_sales_order_for_production(sales_order):
	invalid_sales_orders = get_invalid_sales_orders([sales_order])
	if invalid_sales_orders:
		process_status = frappe.db.get_value("Sales Order", sales_order, "custom_process_status")
		frappe.throw(
			_("销售订单 {0} 未放行生产，当前流程状态：{1}").format(
				sales_order, process_status or ""
			)
		)


def get_invalid_sales_orders(sales_orders):
	if not sales_orders:
		return []

	return frappe.get_all(
		"Sales Order",
		filters={
			"name": ["in", list(sales_orders)],
			"custom_process_status": ["!=", PENDING_PRODUCTION],
		},
		pluck="name",
	)
