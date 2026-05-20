import frappe
from frappe.utils import now


@frappe.whitelist()
def push_to_crm(sales_order_name):
	"""
	推送销售订单到 CRM 系统
	"""
	# 获取销售订单
	sales_order = frappe.get_doc("Sales Order", sales_order_name)
	
	# 验证销售订单是否已提交
	if sales_order.docstatus != 1:
		frappe.throw(frappe._("销售订单必须已提交才能推送到 CRM"))
	
	# 检查是否已经推送
	if sales_order.get("custom_crm_status") == "Pushed":
		frappe.throw(frappe._("此销售订单已推送至 CRM，无需重复推送"))
	
	# 这里是将销售订单推送至 CRM 的业务逻辑
	# 目前只是模拟推送成功
	frappe.logger().info(f"推送销售订单 {sales_order_name} 到 CRM")
	
	# 更新 CRM Status 为已推送
	sales_order.db_set("custom_crm_status", "Pushed")
	
	return {
		"status": "success",
		"message": f"销售订单 {sales_order_name} 已成功推送到 CRM",
		"crm_status": "Pushed",
		"timestamp": now()
	}


@frappe.whitelist()
def reset_crm_status(sales_order_name):
	"""
	重置销售订单的 CRM Status 为 Unpushed（当已推送的订单被修改时）
	"""
	# 获取销售订单
	sales_order = frappe.get_doc("Sales Order", sales_order_name)
	
	# 只重置已推送的订单
	if sales_order.get("custom_crm_status") == "Pushed":
		sales_order.db_set("custom_crm_status", "Unpushed")
		frappe.logger().info(f"销售订单 {sales_order_name} 已修改，CRM 状态重置为 Unpushed")
		
		return {
			"status": "success",
			"message": f"销售订单 {sales_order_name} 的 CRM 状态已重置为未推送",
			"crm_status": "Unpushed"
		}
	
	return {
		"status": "skipped",
		"message": "无需重置"
	}
