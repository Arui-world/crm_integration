// 为销售订单表单添加"推送至CRM"按钮
frappe.ui.form.on("Sales Order", {
	onload: function(frm) {
		// 在表单加载时添加按钮
		add_push_to_crm_button(frm);
		// 显示 CRM Status
		display_crm_status(frm);
	},
	
	refresh: function(frm) {
		// 在表单刷新时更新按钮状态
		add_push_to_crm_button(frm);
		// 显示 CRM Status
		display_crm_status(frm);
	},
	
	after_save: function(frm) {
		// 保存成功后，如果是已推送状态，重置为未推送
		if (frm.doc.custom_crm_status === "Pushed") {
			frappe.call({
				method: "crm_integration.crm_integration.sales_order.reset_crm_status",
				args: {
					sales_order_name: frm.doc.name
				},
				freeze: false,
				callback: function(r) {
					if (r.message && r.message.status === "success") {
						frm.reload_doc();
					}
				}
			});
		}
	}
});

// 页面加载时先移除所有旧的 CRM Status 标签
$(document).ready(function() {
	$('.crm-status-badge').remove();
});

// 监听 Frappe 页面变化（适用于 SPA 架构）
$(document).on('page-change', function() {
	// 每次页面变化时都清理旧的标签
	$('.crm-status-badge').remove();
});

function display_crm_status(frm) {
	// 通过 URL 判断当前页面是否是销售订单表单
	var currentUrl = window.location.pathname;
	
	// 列表页: /desk/sales-order（后面没有斜杠和参数）
	// 表单页: /desk/sales-order/SAL-ORD-xxx 或 /desk/sales-order/SAL-ORD-xxx/edit
	if (!currentUrl || currentUrl === '/desk/sales-order') {
		$('.crm-status-badge').remove();
		return;
	}
	
	// 验证当前页面是否是销售订单表单
	if (!frm || frm.doctype !== 'Sales Order' || !frm.doc || !frm.doc.name) {
		return;
	}
	
	// 验证页面是否有标题栏
	var $pageTitle = $('.page-title');
	if (!$pageTitle.length) {
		return;
	}
	
	// 获取 CRM Status 字段的值
	var crmStatus = frm.doc.custom_crm_status || "Unpushed";
	
	// 先移除已有的所有 CRM Status 标签
	$('.crm-status-badge').remove();
	
	// 构建状态标签的 HTML（使用 Frappe 原生的 indicator-pill 组件）
	var statusHtml = '';
	
	if (crmStatus === "Pushed") {
		// 已推送状态 - 蓝色
		statusHtml = '<span class="crm-status-badge indicator-pill no-indicator-dot whitespace-nowrap blue" style="margin-left: 12px;"><span>CRM: 已推送</span></span>';
	} else {
		// 未推送状态 - 红色
		statusHtml = '<span class="crm-status-badge indicator-pill no-indicator-dot whitespace-nowrap red" style="margin-left: 12px;"><span>CRM: 未推送</span></span>';
	}
	
	// 在页面顶部的工具栏区域添加（面包屑旁边）
	var $pageHead = $('.page-head');
	if ($pageHead.length) {
		var $target = $pageHead.find('.page-title').length ? $pageHead.find('.page-title') : $pageHead;
		$target.append(statusHtml);
	}
}

function add_push_to_crm_button(frm) {
	// 只在已提交的文档中显示按钮
	if (frm.doc.docstatus === 1) {
		// 检查是否已经添加过按钮，避免重复添加
		if (!frm.custom_buttons["推送至CRM"]) {
			frm.add_custom_button(__("推送至CRM"), function() {
				push_sales_order_to_crm(frm);
			}, __("CRM操作"));
			
			// 立即应用样式到 CRM操作 分组按钮
			apply_crm_button_style();
		}
	}
}

function apply_crm_button_style() {
	// 用最小延迟确保 DOM 已更新（使用 requestAnimationFrame 而不是固定延迟）
	requestAnimationFrame(function() {
		let $btns = $('.page-head').find('button');
		
		$btns.each(function() {
			const $this = $(this);
			const text = $this.text().trim();
			
			// 找到"CRM操作"分组按钮并应用黑色背景
			if (text === 'CRM操作') {
				$this.attr('style', 'background-color: #1f2937 !important; border-color: #1f2937 !important; color: #ffffff !important;')
					.removeClass('btn-default btn-light')
					.addClass('btn-primary');
			}
		});
	});
}

function push_sales_order_to_crm(frm) {
	// 获取按钮并禁用，防止重复点击
	const $btn = $('[data-label="推送至CRM"]');
	$btn.prop("disabled", true);
	
	frappe.call({
		method: "crm_integration.crm_integration.sales_order.push_to_crm",
		args: {
			sales_order_name: frm.doc.name
		},
		callback: function(r) {
			// 重新启用按钮
			$btn.prop("disabled", false);
			
			if (r.message) {
				frappe.msgprint({
					title: __("成功"),
					indicator: "green",
					message: r.message.message
				});
				
				// 刷新表单，更新 CRM Status 显示
				frm.reload_doc();
				frm.refresh_fields();
			}
		},
		error: function(err) {
			// 重新启用按钮
			$btn.prop("disabled", false);
			frappe.msgprint({
				title: __("错误"),
				indicator: "red",
				message: __("推送至CRM失败，请重试")
			});
		}
	});
}
