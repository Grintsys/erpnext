# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
import frappe.defaults
from frappe.utils import cint, flt, add_months, today, date_diff, getdate, add_days, cstr, nowdate
from frappe import _, msgprint, throw
from erpnext.accounts.party import get_party_account, get_due_date
from erpnext.controllers.stock_controller import update_gl_entries_after
from frappe.model.mapper import get_mapped_doc
from erpnext.accounts.doctype.sales_invoice.pos import update_multi_mode_option

from erpnext.controllers.selling_controller import SellingController
from erpnext.accounts.utils import get_account_currency
from erpnext.stock.doctype.delivery_note.delivery_note import update_billed_amount_based_on_so
from erpnext.projects.doctype.timesheet.timesheet import get_projectwise_timesheet_data
from erpnext.assets.doctype.asset.depreciation \
	import get_disposal_account_and_cost_center, get_gl_entries_on_asset_disposal
from erpnext.stock.doctype.batch.batch import set_batch_nos
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos, get_delivery_note_serial_no
from erpnext.setup.doctype.company.company import update_company_current_month_sales
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.doctype.loyalty_program.loyalty_program import \
	get_loyalty_program_details_with_points, get_loyalty_details, validate_loyalty_points
from erpnext.accounts.deferred_revenue import validate_service_stop_date

from erpnext.healthcare.utils import manage_invoice_submit_cancel

from six import iteritems
from datetime import datetime, timedelta, date
from frappe.model.naming import parse_naming_series
from frappe.utils.data import money_in_words
from datetime import datetime
import math

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class SalesInvoice(SellingController):
	def __init__(self, *args, **kwargs):
		super(SalesInvoice, self).__init__(*args, **kwargs)
		self.status_updater = [{
			'source_dt': 'Sales Invoice Item',
			'target_field': 'billed_amt',
			'target_ref_field': 'amount',
			'target_dt': 'Sales Order Item',
			'join_field': 'so_detail',
			'target_parent_dt': 'Sales Order',
			'target_parent_field': 'per_billed',
			'source_field': 'amount',
			'join_field': 'so_detail',
			'percent_join_field': 'sales_order',
			'status_field': 'billing_status',
			'keyword': 'Billed',
			'overflow_type': 'billing'
		}]

	def set_indicator(self):
		"""Set indicator for portal"""
		if self.outstanding_amount < 0:
			self.indicator_title = _("Credit Note Issued")
			self.indicator_color = "darkgrey"
		elif self.outstanding_amount > 0 and getdate(self.due_date) >= getdate(nowdate()):
			self.indicator_color = "orange"
			self.indicator_title = _("Unpaid")
		elif self.outstanding_amount > 0 and getdate(self.due_date) < getdate(nowdate()):
			self.indicator_color = "red"
			self.indicator_title = _("Overdue")
		elif cint(self.is_return) == 1:
			self.indicator_title = _("Return")
			self.indicator_color = "darkgrey"
		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def set_cost_center(self):
		company = frappe.get_all("Company", ["cost_center"], filters = {"name": self.company})

		self.db_set('cost_center', company[0].cost_center, update_modified=False)

	def set_new_row_item(self, item, rate, taxed_sales, is_exonerated):
		d_amount = item.price_list_rate * item.qty * (item.discount_percentage/100)
		row = self.append("items", {})
		row.item_code = item.item_code
		row.qty = item.qty
		row.rate = rate
		row.amount = taxed_sales
		row.parent = self.name
		row.uom = item.uom
		row.description = item.description
		row.item_name = item.item_name
		row.conversion_factor = item.conversion_factor
		row.base_rate = item.base_rate
		row.base_amount = item.base_amount
		row.income_account = item.income_account
		row.cost_center = item.cost_center
		row.tax_detail = item.tax_detail
		row.barcode = item.barcode
		row.is_exonerated = is_exonerated
		row.category_for_sale = item.category_for_sale
		row.customer_item_code = item.customer_item_code
		row.description_section = item.description_section
		row.item_group = item.item_group
		row.brand = item.brand
		row.image = item.image
		row.image_view = item.image_view
		row.stock_uom = item.stock_uom
		row.stock_qty = item.stock_qty
		row.purchase_rate = item.purchase_rate
		row.price_list_rate = item.price_list_rate
		row.base_price_list_rate = item.base_price_list_rate
		row.discount_and_margin = item.discount_and_margin
		row.discount_reason = item.discount_reason
		row.margin_type = item.margin_type
		row.margin_rate_or_amount = item.margin_rate_or_amount
		row.rate_with_margin = item.rate_with_margin
		row.discount_percentage = item.discount_percentage
		row.discount_amount = d_amount
		row.base_rate_with_margin = item.base_rate_with_margin
		row.item_tax_template = item.item_tax_template
		row.tax_detail = item.tax_detail
		row.pricing_rules = item.pricing_rules
		row.is_free_item = item.is_free_item
		row.net_rate = item.net_rate
		row.net_amount = item.net_amount
		row.base_net_rate = item.base_net_rate
		row.base_net_amount = item.base_net_amount
		row.is_fixed_asset = item.is_fixed_asset
		row.asset = item.asset
		row.finance_book = item.finance_book
		row.expense_account = item.expense_account
		row.deferred_revenue_account = item.deferred_revenue_account
		row.service_stop_date = item.service_stop_date
		row.enable_deferred_revenue = item.enable_deferred_revenue
		row.service_start_date = item.service_start_date
		row.service_end_date = item.service_end_date
		row.weight_per_unit = item.weight_per_unit
		row.total_weight = item.total_weight
		row.weight_uom = item.weight_uom
		row.warehouse = item.warehouse
		row.target_warehouse = item.target_warehouse
		row.quality_inspection = item.quality_inspection
		row.batch_no = item.batch_no
		row.allow_zero_valuation_rate = item.allow_zero_valuation_rate
		row.serial_no = item.serial_no
		row.item_tax_rate = item.item_tax_rate
		row.actual_batch_qty = item.actual_batch_qty
		row.actual_qty = item.actual_qty
		row.edit_references = item.edit_references
		row.sales_order = item.sales_order
		row.so_detail = item.so_detail
		row.delivery_note = item.delivery_note
		row.dn_detail = item.dn_detail
		row.delivered_qty = item.delivered_qty
		row.cost_center = item.cost_center
		row.page_break = item.page_break

	def update_item_discount_amount(self):
		items = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.name})

		for item in items:
			d_amount = item.price_list_rate * item.qty * (item.discount_percentage/100)

			doc = frappe.get_doc("Sales Invoice Item", item.name)
			doc.discount_amount = d_amount
			doc.db_set("discount_amount", d_amount, update_modified=False)
	
	def caculate_items_amount(self):
		items = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.name})

		if self.exonerated:
			for item in items:
				if item.is_exonerated != 1:
					item_taxes = frappe.get_all("Item Tax", ['name', "item_tax_template"], filters = {"parent": item.item_code})
					if len(item_taxes) >0:
						for item_tax in item_taxes:
							tax_tamplates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": item_tax.item_tax_template})
								
							for tax_tamplate in tax_tamplates:

								tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate", "tax_type"], filters = {"parent": tax_tamplate.name})
									
								for tax_detail in tax_details:

									if tax_detail.tax_rate == 15:
										self.account15 = tax_detail.tax_type
										taxed_sales15 = item.amount/1.15
										rate = taxed_sales15/item.qty

										self.set_new_row_item(item, rate, taxed_sales15, 1)										
									
									if tax_detail.tax_rate == 18:
										self.account18 = tax_detail.tax_type
										taxed_sales18 = item.amount/1.18
										rate = taxed_sales18/item.qty
										
										self.set_new_row_item(item, rate, taxed_sales18, 1)
									
									frappe.delete_doc('Sales Invoice Item', item.name)
		else:
			for item in items:
				if item.is_exonerated == 1:
					product_price = frappe.get_all("Item Price", ["price_list_rate"], filters = {"item_code": item.item_code, "price_list": self.selling_price_list})

					amount = item.qty * product_price[0].price_list_rate

					self.set_new_row_item(item, product_price[0].price_list_rate, amount, 0)
					frappe.delete_doc('Sales Invoice Item', item.name)
	
	def work_order_create(self):
		if self.is_work_order == 1:
			if self.work_order == None:
				frappe.throw(_("Select Work Order Invoice."))
			else:
				order = frappe.get_doc("Work Order Invoice", self.work_order)
				order.sales_invoice = self.name
				order.company = self.company
				order.save()
		else:
			order = frappe.new_doc("Work Order Invoice")
			order.sales_invoice = self.name
			order.company = self.company
			order.insert()
		
		self.verificate_work_order()
		
	def verificate_work_order(self):
		orders = frappe.get_all("Work Order Invoice", ["name"], filters = {"sales_invoice": self.name})

		if len(orders) > 0:
			order = frappe.get_doc("Work Order Invoice", orders[0].name)

			items = frappe.get_all("Work Order Items", ["*"], filters = {"parent": order.name})

			if len(items) == 0:
				frappe.delete_doc("Work Order Invoice", order.name)

	def calculate_insurance(self):
		if self.excesses != None and self.excesses != None and self.excesses != None and self.excesses != None:
			self.total_insurance_deduction = self.excesses + self.deductible + self.ineligible_expenses + self.co_pay20
		else:
			self.total_insurance_deduction = 0
			
		self.deduction_grand_total = self.grand_total - self.total_insurance_deduction
		self.db_set('deduction_grand_total', self.deduction_grand_total, update_modified=False)

	def veificate_enrolled_student(self):		
		# enrolled = frappe.get_doc('Enrolled Student', self.enrolled_students)

		details = frappe.get_all("details of quotas", ["*"], filters = {"parent": self.enrolled_students, "paid": 0, "pay": 1}, order_by='date asc')

		graduation_exp = True

		details_graduations = frappe.get_all("details of graduation expenses", ["*"], filters = {"parent": self.enrolled_students, "paid": 0, "pay": 1}, order_by='date asc')

		for detail in details_graduations:
			products_verificate = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.name, "description": str(detail.date ) + " " + detail.item})

			if len(products_verificate) == 0:
				frappe.throw(_("The product {} with relation to Enrolled Student {} no exist in this invoice.".format(detail.item, self.enrolled_students)))
			
			doc = frappe.get_doc("details of graduation expenses", detail.name)
			doc.paid = 1
			doc.db_set('paid', 1, update_modified=False)
			doc.db_set('coments', "PAID", update_modified=False)
			doc.save()

			graduation_exp = False
		
		if len(details) == 0 and graduation_exp:
			frappe.throw(_("You don´t have pending payments for Enrolled Student {}.".format(self.enrolled_students)))

		products_verificate = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.name})

		# if len(products_verificate) == 0:
		# 		frappe.throw(_("The product {} with relation to Enrolled Student {} no exist in this invoice.".format(detail.item, self.enrolled_students)))

		for detail in details:
			product_verificate = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.name, "item_code": detail.item})

			if len(product_verificate) == 0:
				frappe.throw(_("The product {} with relation to Enrolled Student {} no exist in this invoice.".format(detail.item, self.enrolled_students)))
			
			for product in product_verificate:

				detailsItem = frappe.get_all("details of quotas", ["*"], filters = {"parent": self.enrolled_students, "paid": 0, "pay": 1, "item": detail.item}, order_by='date asc')

				if len(detailsItem) > 0:
					if int(product.qty) > len(detailsItem):
						frappe.throw(_("You have only {} pending payments and you pay {} in this invoice.".format(len(detailsItem), int(product.qty))))
					
					rangeInt = product.qty
					
					for i in range(0,int(rangeInt), 1):
						# if len(products_verificate) > 1:
						# 	frappe.throw(_("Only can exist one product {} in this invoice.".format(detail.item, self.enrolled_students)))
						
									
						doc = frappe.get_doc("details of quotas", detailsItem[i].name)
						doc.paid = 1
						doc.db_set('paid', 1, update_modified=False)
						doc.db_set('coments', "PAID", update_modified=False)
						doc.save()

	def validate(self):
		super(SalesInvoice, self).validate()
		self.validate_auto_set_posting_time()
		self.discount_product()
		self.calculate_insurance()
		if self.round_off_discount == 1 and self.update_stock == 0:
			frappe.throw(_("When selecting a discount reason check the field to update inventory."))
			
		if self.docstatus == 0:
			self.caculate_items_amount()
			# self.set_cost_center()

		if not self.is_pos:
			self.so_dn_required()
		
		if not self.creation_date:
			self.creation_date = datetime.now()

		self.validate_proj_cust()
		self.validate_pos_return()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("stock_uom", "stock_qty")
		self.validate_uom_is_integer("uom", "qty")
		self.check_sales_order_on_hold_or_close("sales_order")
		self.validate_debit_to_acc()
		self.clear_unallocated_advances("Sales Invoice Advance", "advances")
		self.add_remarks()
		self.validate_write_off_account()
		self.validate_account_for_change_amount()
		self.validate_fixed_asset()
		self.set_income_account_for_fixed_assets()
		validate_inter_company_party(self.doctype, self.customer, self.company, self.inter_company_invoice_reference)

		if cint(self.is_pos):
			self.validate_pos()

		if cint(self.update_stock):
			self.validate_dropship_item()
			self.validate_item_code()
			self.validate_warehouse()
			self.update_current_stock()
			self.validate_delivery_note()

		# validate service stop date to lie in between start and end date
		validate_service_stop_date(self)

		if not self.is_opening:
			self.is_opening = 'No'

		if self._action != 'submit' and self.update_stock and not self.is_return:
			set_batch_nos(self, 'warehouse', True)

		if self.redeem_loyalty_points:
			lp = frappe.get_doc('Loyalty Program', self.loyalty_program)
			self.loyalty_redemption_account = lp.expense_account if not self.loyalty_redemption_account else self.loyalty_redemption_account
			self.loyalty_redemption_cost_center = lp.cost_center if not self.loyalty_redemption_cost_center else self.loyalty_redemption_cost_center

		self.set_against_income_account()
		self.validate_c_form()
		self.validate_time_sheets_are_submitted()
		self.validate_multiple_billing("Delivery Note", "dn_detail", "amount", "items")
		if not self.is_return:
			self.validate_serial_numbers()
		self.update_packing_list()
		self.set_billing_hours_and_amount()
		self.update_timesheet_billing_for_project()
		self.set_status()
		if self.is_pos and not self.is_return:
			self.verify_payment_amount_is_positive()

		#validate amount in mode of payments for returned invoices for pos must be negative
		if self.is_pos and self.is_return:
			self.verify_payment_amount_is_negative()

		if self.redeem_loyalty_points and self.loyalty_program and self.loyalty_points:
			validate_loyalty_points(self, self.loyalty_points)

		self.exonerated_value()

		if self.grand_total == self.paid_amount:
			outstanding_amount = 0
			self.db_set('outstanding_amount', outstanding_amount, update_modified=False)
			
		if self.docstatus == 1:
			self.update_accounts_status()
			company = frappe.get_doc('Company', self.company)
			if company.isv_by_item_amount:
				self.calculated_taxes_by_item_amount()
			else:
				self.calculated_taxes()
			if self.is_pos:
				self.allow_credit_pos()
			
			if self.enrolled_students != None:
				self.veificate_enrolled_student()

			self.update_dashboard_customer()
			# self.create_dispatch_control()
			# if self.grand_total == self.paid_amount:
			# 	self.db_set('outstanding_amount', 0, update_modified=False)	
			# else:
			# 	outstanding_amount = self.rounded_total

			# 	if self.total_advance > 0:
			# 		outstanding_amount = self.rounded_total - self.total_advance

			# 	if self.paid_amount > 0:
			# 		outstanding_amount = self.rounded_total - self.paid_amount

		# if self.docstatus == 0:
		# 	self.validate_camps()
		# if self.round_off_discount == 1
		# if self.docstatus == 0:
		# 	self.assign_cai()
	
	# def apply_advances(self):
	# 	for advance in self.get("advances"):
	# 		self.outstanding_amount -= advance.allocated_amount
	# 		self.db_set('outstanding_amount', self.outstanding_amount, update_modified=False)	
	
	def update_dashboard_customer(self):
		customers = frappe.get_all("Dashboard Customer",["*"], filters = {"customer": self.customer, "company": self.company})

		if len(customers) > 0:
			customer = frappe.get_doc("Dashboard Customer", customers[0].name)
			customer.billing_this_year += self.grand_total

			outstanding_amount = self.outstanding_amount

			if self.grand_total == self.paid_amount:
				outstanding_amount = 0
				self.db_set('outstanding_amount', outstanding_amount, update_modified=False)

			customer.total_unpaid += outstanding_amount
			customer.save()
		else:
			new_doc = frappe.new_doc("Dashboard Customer")
			new_doc.customer = self.customer
			new_doc.company = self.company
			new_doc.billing_this_year = self.grand_total
			outstanding_amount = self.outstanding_amount

			if self.grand_total == self.paid_amount:
				outstanding_amount = 0
				self.db_set('outstanding_amount', outstanding_amount, update_modified=False)

			new_doc.total_unpaid = outstanding_amount
			new_doc.insert()
	
	def update_dashboard_customer_cancel(self):
		customers = frappe.get_all("Dashboard Customer",["*"], filters = {"customer": self.customer, "company": self.company})

		if len(customers) > 0:
			customer = frappe.get_doc("Dashboard Customer", customers[0].name)
			customer.billing_this_year -= self.grand_total
			customer.total_unpaid -= self.outstanding_amount
			customer.save()
	
	def allow_credit_pos(self):
		pos_profile = frappe.get_all("POS Profile", ["allow_credit"], filters = {"name": self.pos_profile})

		if self.outstanding_amount > 0:
			if pos_profile[0].allow_credit == 0:
				if self.grand_total > self.paid_amount:
					frappe.throw(_("It is not allowed to give credit at this point of sale"))

	def create_dispatch_control(self):
		products = frappe.get_all("Sales Invoice Item", ["item_code", "qty"], filters = {"parent": self.name})

		areas = frappe.get_all("Delivery Area", ["name"])

		for area in areas:
			products_dispatch = []
			area_details = frappe.get_all("Delivery Area Detail", ["item"], filters = {"parent": area.name})
			for product in products:
				for areadetail in area_details:
					if product.item_code == areadetail.item:
						pro = [product.item_code, product.qty]
						products_dispatch.append(pro)
			
			if len(products_dispatch) > 0:
				doc = frappe.new_doc('Dispatch Control')
				doc.sale_invoice = self.name
				doc.delivery_area = area.name
				doc.creation_date = datetime.now()
				for list_product in products_dispatch:
					row = doc.append("items", {
					'item': list_product[0],
					'qty': list_product[1]
					})
				doc.insert()

	def assing_price_list(self):
		day_in = datetime.today().weekday()
		day = ""

		if day_in == 0:
			day = "Lunes"
		elif day_in == 1:
			day = "Martes"
		elif day_in == 2:
			day = "Miercoles"
		elif day_in == 3:
			day = "Jueves"
		elif day_in == 4:
			day = "Viernes"
		elif day_in == 5:
			day = "Sábado"
		elif day_in == 6:
			day = "Domingo"

		price_list_schedule_detail = frappe.get_all("Price List Schedule Detail", ["price_list"], filters = {"day": day, "start_time": ["<=", self.posting_time], "final_hour": [">=", self.posting_time], "company":self.company})

		if len(price_list_schedule_detail) > 0:
			self.set('selling_price_list', price_list_schedule_detail[0].price_list)
	
	def assing_price_list_pos(self):
		day_in = datetime.today().weekday()
		day = ""
		price_list = ""

		if day_in == 0:
			day = "Lunes"
		elif day_in == 1:
			day = "Martes"
		elif day_in == 2:
			day = "Miercoles"
		elif day_in == 3:
			day = "Jueves"
		elif day_in == 4:
			day = "Viernes"
		elif day_in == 5:
			day = "Sábado"
		elif day_in == 6:
			day = "Domingo"

		company = self.company

		price_list_schedule_detail = frappe.get_all("Price List Schedule Detail", ["price_list"], filters = {"day": day, "start_time": ["<=", self.posting_time], "final_hour": [">=", self.posting_time], "company":self.company})

		if len(price_list_schedule_detail) > 0:
			price_list = price_list_schedule_detail[0].price_list

		return price_list

	def calculated_taxes(self):
		taxed15 = 0
		taxed18 = 0
		exempt = 0
		exonerated = 0
		taxed_sales15 = 0
		taxed_sales18 = 0
		outstanding_amount = 0
		grand_total = 0

		if self.taxes_and_charges:
					if self.exonerated == 1:
						exonerated += self.total
					else:
						invoice_table_taxes = frappe.get_all("Sales Taxes and Charges", ["name", "rate", "tax_amount"], filters = {"parent": self.name})

						for invoice_tax in invoice_table_taxes:

							if invoice_tax.rate == 15:
								taxed15 += invoice_tax.tax_amount							
							
							if invoice_tax.rate == 18:
								taxed18 += invoice_tax.tax_amount
		else:
			items = frappe.get_all("Sales Invoice Item", ["name", "item_code", "amount"], filters = {"parent": self.name})

			for item in items:
				itUp = frappe.get_doc("Sales Invoice Item", item.name)
				item_taxes = frappe.get_all("Item Tax", ['name', "item_tax_template"], filters = {"parent": item.item_code})
				if len(item_taxes) >0:
					for item_tax in item_taxes:
						tax_tamplates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": item_tax.item_tax_template})
							
						for tax_tamplate in tax_tamplates:

							tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate", "tax_type"], filters = {"parent": tax_tamplate.name})
								
							for tax_detail in tax_details:
								# frappe.msgprint("tax detail {}".format(tax_detail))
								if tax_detail.tax_rate == 15:
									# frappe.msgprint("cuenta tax 15 {}".format(tax_detail.tax_type))
									self.account15 = tax_detail.tax_type
									if self.exonerated == 1:
										taxed_sales15 += item.amount
										taxed15 += item.amount * 0.15
										exonerated += taxed_sales15 + taxed15

										itUp.db_set('taxed_sales15', item.amount, update_modified=False)
										itUp.db_set('taxed15', item.amount * 0.15, update_modified=False)
										itUp.db_set('taxed_sales18', 0, update_modified=False)
										itUp.db_set('taxed18', 0, update_modified=False)
									else:
										taxed_sales15 += item.amount/1.15
										taxed15 += item.amount - (item.amount/1.15)
										itUp.db_set('taxed_sales15', item.amount, update_modified=False)
										itUp.db_set('taxed15', item.amount - (item.amount/1.15), update_modified=False)
										itUp.db_set('taxed_sales18', 0, update_modified=False)
										itUp.db_set('taxed18', 0, update_modified=False)
								
								if tax_detail.tax_rate == 18:
									self.account18 = tax_detail.tax_type
									if self.exonerated == 1:
										taxed_sales18 += item.amount
										taxed18 += item.amount * 0.18
										exonerated += taxed_sales18 + taxed18

										itUp.db_set('taxed_sales15', 0, update_modified=False)
										itUp.db_set('taxed15', 0, update_modified=False)
										itUp.db_set('taxed_sales18', item.amount, update_modified=False)
										itUp.db_set('taxed18', item.amount * 0.18, update_modified=False)
									else:
										taxed_sales18 += item.amount/1.18
										taxed18 += item.amount - (item.amount/1.18)

										itUp.db_set('taxed_sales15', 0, update_modified=False)
										itUp.db_set('taxed15', 0, update_modified=False)
										itUp.db_set('taxed_sales18', item.amount, update_modified=False)
										itUp.db_set('taxed18', item.amount - (item.amount/1.18), update_modified=False)
				else:
					exempt += item.amount
	
		self.isv15 = taxed15
		self.isv18 = taxed18
		self.total_exonerated = exonerated
		self.total_exempt = exempt
		self.total_taxes_and_charges = taxed15 + taxed18
		self.taxed_sales15 = taxed_sales15
		self.taxed_sales18 = taxed_sales18

		if self.is_pos:
			pos = frappe.get_doc("POS Profile", self.pos_profile)

			if pos.round_off_discount == 1:
				discount_amount = math.ceil(self.discount_amount)

				net_total = math.floor(self.net_total)
				self.db_set('net_total', net_total, update_modified=False)

				# rounding_adjustment = math.floor(self.rounding_adjustment)
				self.db_set('rounding_adjustment', 0, update_modified=False)

				self.discount_amount = discount_amount
				self.db_set('discount_amount', discount_amount, update_modified=False)

				change_amount = self.paid_amount - self.rounded_total
				self.db_set('change_amount', change_amount, update_modified=False)
		else:
			if self.round_off_discount == 1:
				discount_amount = math.ceil(self.discount_amount)

				net_total = math.floor(self.net_total)
				self.db_set('net_total', net_total, update_modified=False)

				# rounding_adjustment = math.floor(self.rounding_adjustment)
				self.db_set('rounding_adjustment', 0, update_modified=False)

				self.discount_amount = discount_amount
				self.db_set('discount_amount', discount_amount, update_modified=False)

		if self.exonerated == 1:
			if self.discount_amount:
				self.grand_total = self.total - self.discount_amount
			else:
				self.grand_total = self.total			
		else:
			if self.discount_amount:
				self.grand_total = self.total - self.discount_amount
			else:
				self.grand_total = self.total
		
		# if self.exonerated != 1:
		# 	self.grand_total += self.isv15 + self.isv18
		
		grand_total = self.grand_total
		
		if self.is_pos and self.change_amount > 0:
			outstanding_amount = 0
			self.db_set('outstanding_amount', outstanding_amount, update_modified=False)
		else:
			if self.round_off_discount:
				if self.grand_total != self.outstanding_amount:
					outstanding_amount = self.grand_total
					self.db_set('outstanding_amount', outstanding_amount, update_modified=False)
			else:
				outstanding_amount = 0
				if self.paid_amount > 0:
					outstanding_amount = self.grand_total - self.paid_amount
				else:
					outstanding_amount = self.grand_total

				self.db_set('outstanding_amount', outstanding_amount, update_modified=False)
		
		self.rounded_total = self.grand_total

		# if self.status == 'Draft' or self.docstatus == 1:
		self.db_set('grand_total', grand_total, update_modified=False)
		self.db_set('isv15', taxed15, update_modified=False)
		self.db_set('isv18', taxed18, update_modified=False)
		self.db_set('total_exonerated', exonerated, update_modified=False)
		self.db_set('taxed_sales15', taxed_sales15, update_modified=False)
		self.db_set('total_exempt', exempt, update_modified=False)
		self.db_set('taxed_sales18', taxed_sales18, update_modified=False)
		self.db_set('total_taxes_and_charges', taxed15 + taxed18, update_modified=False)

		if self.is_pos:
			pos = frappe.get_doc("POS Profile", self.pos_profile)

			if pos.round_off_discount == 1:
				self.db_set('rounded_total', self.rounded_total, update_modified=False)

				if self.grand_total == self.paid_amount:
					self.db_set('outstanding_amount', 0, update_modified=False)	
		else:
			if self.round_off_discount == 1:
				self.db_set('rounded_total', self.rounded_total, update_modified=False)

				if self.grand_total == self.paid_amount:
					self.db_set('outstanding_amount', 0, update_modified=False)		
		
		self.db_set('rounded_total', self.rounded_total, update_modified=False)

		self.in_words = money_in_words(self.rounded_total)
		self.db_set('in_words', self.in_words, update_modified=False)		
		self.calculate_insurance()

		self.subtotal = self.grand_total - self.isv15 - self.isv18
		self.db_set('subtotal', self.subtotal, update_modified=False)

	def calculated_taxes_by_item_amount(self):
		taxed15 = 0
		taxed18 = 0
		exempt = 0
		exonerated = 0
		taxed_sales15 = 0
		taxed_sales18 = 0
		outstanding_amount = 0
		grand_total = 0

		if self.taxes_and_charges:
					if self.exonerated == 1:
						exonerated += self.total
					else:
						invoice_table_taxes = frappe.get_all("Sales Taxes and Charges", ["name", "rate", "tax_amount"], filters = {"parent": self.name})

						for invoice_tax in invoice_table_taxes:

							if invoice_tax.rate == 15:
								taxed15 += invoice_tax.tax_amount							
							
							if invoice_tax.rate == 18:
								taxed18 += invoice_tax.tax_amount
		else:
			items = frappe.get_all("Sales Invoice Item", ["item_code", "amount", "discount_amount"], filters = {"parent": self.name})

			for item in items:
				item_taxes = frappe.get_all("Item Tax", ['name', "item_tax_template"], filters = {"parent": item.item_code})
				if len(item_taxes) >0:
					for item_tax in item_taxes:
						tax_tamplates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": item_tax.item_tax_template})
							
						for tax_tamplate in tax_tamplates:

							tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate", "tax_type"], filters = {"parent": tax_tamplate.name})
								
							for tax_detail in tax_details:
								# frappe.msgprint("tax detail {}".format(tax_detail))
								if tax_detail.tax_rate == 15:
									# frappe.msgprint("cuenta tax 15 {}".format(tax_detail.tax_type))
									self.account15 = tax_detail.tax_type
									if self.exonerated == 1:
										taxed_sales15 += item.amount + item.discount_amount
										taxed15 += (item.amount + item.discount_amount) * 0.15
										exonerated += taxed_sales15 + taxed15
									else:
										taxed_sales15 += (item.amount+ item.discount_amount)/1.15
										taxed15 += (item.amount + item.discount_amount) - ((item.amount + item.discount_amount)/1.15)
								
								if tax_detail.tax_rate == 18:
									self.account18 = tax_detail.tax_type
									if self.exonerated == 1:
										taxed_sales18 += (item.amount + item.discount_amount) + item.discount_amount
										taxed18 += (item.amount + item.discount_amount) * 0.18
										exonerated += taxed_sales18 + taxed18
									else:
										taxed_sales18 += item.amount/1.18
										taxed18 += (item.amount + item.discount_amount) - ((item.amount + item.discount_amount)/1.18)
				else:
					exempt += item.amount
	
		self.isv15 = taxed15
		self.isv18 = taxed18
		self.total_exonerated = exonerated
		self.total_exempt = exempt
		self.total_taxes_and_charges = taxed15 + taxed18
		self.taxed_sales15 = taxed_sales15
		self.taxed_sales18 = taxed_sales18

		if self.is_pos:
			pos = frappe.get_doc("POS Profile", self.pos_profile)

			if pos.round_off_discount == 1:
				discount_amount = math.ceil(self.discount_amount)

				net_total = math.floor(self.net_total)
				self.db_set('net_total', net_total, update_modified=False)

				# rounding_adjustment = math.floor(self.rounding_adjustment)
				self.db_set('rounding_adjustment', 0, update_modified=False)

				self.discount_amount = discount_amount
				self.db_set('discount_amount', discount_amount, update_modified=False)

				change_amount = self.paid_amount - self.rounded_total
				self.db_set('change_amount', change_amount, update_modified=False)
		else:
			if self.round_off_discount == 1:
				discount_amount = math.ceil(self.discount_amount)

				net_total = math.floor(self.net_total)
				self.db_set('net_total', net_total, update_modified=False)

				# rounding_adjustment = math.floor(self.rounding_adjustment)
				self.db_set('rounding_adjustment', 0, update_modified=False)

				self.discount_amount = discount_amount
				self.db_set('discount_amount', discount_amount, update_modified=False)

		if self.exonerated == 1:
			if self.discount_amount:
				self.grand_total = self.total - self.discount_amount
			else:
				self.grand_total = self.total			
		else:
			if self.discount_amount:
				self.grand_total = self.total - self.discount_amount
			else:
				self.grand_total = self.total
		
		# if self.exonerated != 1:
		# 	self.grand_total += self.isv15 + self.isv18
		
		grand_total = self.grand_total
		
		if self.is_pos and self.change_amount > 0:
			outstanding_amount = 0
			self.db_set('outstanding_amount', outstanding_amount, update_modified=False)
		else:
			if self.round_off_discount:
				if self.grand_total != self.outstanding_amount:
					outstanding_amount = self.grand_total
					self.db_set('outstanding_amount', outstanding_amount, update_modified=False)
			else:
				outstanding_amount = 0
				if self.paid_amount > 0:
					outstanding_amount = self.grand_total - self.paid_amount
				else:
					outstanding_amount = self.grand_total

				self.db_set('outstanding_amount', outstanding_amount, update_modified=False)
		
		self.rounded_total = self.grand_total

		# if self.status == 'Draft' or self.docstatus == 1:
		self.db_set('grand_total', grand_total, update_modified=False)
		self.db_set('isv15', taxed15, update_modified=False)
		self.db_set('isv18', taxed18, update_modified=False)
		self.db_set('total_exonerated', exonerated, update_modified=False)
		self.db_set('taxed_sales15', taxed_sales15, update_modified=False)
		self.db_set('total_exempt', exempt, update_modified=False)
		self.db_set('taxed_sales18', taxed_sales18, update_modified=False)
		self.db_set('total_taxes_and_charges', taxed15 + taxed18, update_modified=False)

		if self.is_pos:
			pos = frappe.get_doc("POS Profile", self.pos_profile)

			if pos.round_off_discount == 1:
				self.db_set('rounded_total', self.rounded_total, update_modified=False)

				if self.grand_total == self.paid_amount:
					self.db_set('outstanding_amount', 0, update_modified=False)	
		else:
			if self.round_off_discount == 1:
				self.db_set('rounded_total', self.rounded_total, update_modified=False)

				if self.grand_total == self.paid_amount:
					self.db_set('outstanding_amount', 0, update_modified=False)		
		
		self.db_set('rounded_total', self.rounded_total, update_modified=False)

		self.in_words = money_in_words(self.rounded_total)
		self.db_set('in_words', self.in_words, update_modified=False)		
		self.calculate_insurance()

		self.subtotal = self.grand_total - self.isv15 - self.isv18
		self.db_set('subtotal', self.subtotal, update_modified=False)

	# def validate_camps(self):
	# 	if not self.type_document:
	# 		frappe.throw(_("Type Document is required."))
	
	def exonerated_value(self):
		if self.exonerated == 1:
			if self.grand_total < self.total:
				self.grand_total -= self.total_taxes_and_charges
				self.outstanding_amount -= self.total_taxes_and_charges

				payment_schedule = frappe.get_all("Payment Schedule", ["name", "payment_amount"], filters = {"parent": self.name})
				
				for payment in payment_schedule:
					doc = frappe.get_doc("Payment Schedule", payment.name)
					doc.payment_amount -= self.total_taxes_and_charges
					doc.save()
		else:
			if self.grand_total == self.total: 
				self.grand_total += self.total_taxes_and_charges
				self.outstanding_amount += self.total_taxes_and_charges

				payment_schedule = frappe.get_all("Payment Schedule", ["name"], filters = {"parent": self.name})

				for payment in payment_schedule:
					doc = frappe.get_doc("Payment Schedule", payment.name)
					doc.payment_amount += self.total_taxes_and_charges
					doc.save()

	def update_accounts_status(self):
		customer = frappe.get_doc("Customer", self.customer)
		if customer:
			customer.debit += self.grand_total
			customer.credit += self.paid_amount
			customer.remaining_balance += self.grand_total - self.paid_amount
			customer.save()
			
	def discount_product(self):
		total_discount = 0
		for d in self.get('items'):
			total_discount += d.qty * d.discount_amount
			self.partial_discount = total_discount

	def assign_cai(self):
		user = frappe.session.user

		# user_name = frappe.get_all("User", ["first_name"], filters = {"email": user})

		cai = frappe.get_all("CAI", ["initial_number", "final_number", "name_cai", "cai", "issue_deadline", "prefix"], filters = { "status": "Active", "prefix": self.naming_series})

		if len(cai) == 0:
			cai_secondary = frappe.get_all("CAI", ["initial_number", "final_number", "name_cai", "cai", "issue_deadline", "prefix"], filters = { "status": "Pending", "prefix": self.naming_series})
			
			if len(cai_secondary) > 0:
				self.assing_data(cai_secondary[0].cai, cai_secondary[0].issue_deadline, cai_secondary[0].initial_number, cai_secondary[0].final_number, user, cai_secondary[0].prefix)
				# doc = frappe.get_doc("CAI", cai[0].name_cai)
				# doc.status = "Inactive"
				# doc.save()

				doc_sec = frappe.get_doc("CAI", cai_secondary[0].name_cai)
				doc_sec.status = "Active"
				doc_sec.save()

				new_current = int(cai_secondary[0].initial_number) - 1
				name = self.parse_naming_series(cai_secondary[0].prefix)

				frappe.db.sql("""
				UPDATE `tabSeries`
				SET `current` = %s
				WHERE `name` = %s
				""", (new_current, name))
			else:
				# self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, user, cai[0].prefix)
				frappe.throw("The CAI you are using is expired.")
			# frappe.throw(_("This secuence no assign cai"))

		current_value = self.get_current(cai[0].prefix)

		now = datetime.now()

		date = now.date()

		if current_value == None:
			current_value = 0

		number_final = current_value + 1

		if number_final <= int(cai[0].final_number) and str(date) <= str(cai[0].issue_deadline):
			self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, user, cai[0].prefix)

			amount = int(cai[0].final_number) - current_value

			self.alerts(cai[0].issue_deadline, amount)
		else:
			cai_secondary = frappe.get_all("CAI", ["initial_number", "final_number", "name_cai", "cai", "issue_deadline", "prefix"], filters = { "status": "Pending", "prefix": self.naming_series})
			
			if len(cai_secondary) > 0:
				final = int(cai[0].final_number) + 1
				initial = int(cai_secondary[0].initial_number)
				if final <= initial:
					self.assing_data(cai_secondary[0].cai, cai_secondary[0].issue_deadline, cai_secondary[0].initial_number, cai_secondary[0].final_number, user, cai_secondary[0].prefix)
					doc = frappe.get_doc("CAI", cai[0].name_cai)
					doc.status = "Inactive"
					doc.save()

					doc_sec = frappe.get_doc("CAI", cai_secondary[0].name_cai)
					doc_sec.status = "Active"
					doc_sec.save()

					new_current = int(cai_secondary[0].initial_number) - 1
					name = self.parse_naming_series(cai_secondary[0].prefix)

					frappe.db.sql("""
					UPDATE `tabSeries`
					SET `current` = %s
					WHERE `name` = %s
					""", (new_current, name))
				else:
					self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, user, cai[0].prefix)
					frappe.throw("The CAI you are using is expired.")
			else:
				self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, user, cai[0].prefix)
				frappe.throw("The CAI you are using is expired.")
	
	def get_current(self, prefix):
		pre = self.parse_naming_series(prefix)
		current_value = frappe.db.get_value("Series",
		pre, "current", order_by = "name")
		return current_value

	def parse_naming_series(self, prefix):
		parts = prefix.split('.')
		if parts[-1] == "#" * len(parts[-1]):
			del parts[-1]

		pre = parse_naming_series(parts)
		return pre
	
	def assing_data(self, cai, issue_deadline, initial_number, final_number, user, prefix):
		pre = self.parse_naming_series(prefix)

		self.cai = cai

		self.due_date_cai = issue_deadline

		self.authorized_range = "{}{} al {}{}".format(pre, self.serie_number(int(initial_number)), pre, self.serie_number(int(final_number)))

		self.cashier = user
	
	def serie_number(self, number):

		if number >= 1 and number < 10:
			return("0000000" + str(number))
		elif number >= 10 and number < 100:
			return("000000" + str(number))
		elif number >= 100 and number < 1000:
			return("00000" + str(number))
		elif number >= 1000 and number < 10000:
			return("0000" + str(number))
		elif number >= 10000 and number < 100000:
			return("000" + str(number))
		elif number >= 100000 and number < 1000000:
			return("00" + str(number))
		elif number >= 1000000 and number < 10000000:
			return("0" + str(number))
		elif number >= 10000000:
			return(str(number))
	
	def alerts(self, date, amount):
		gcai_setting = frappe.get_all("Cai Settings", ["expired_days", "expired_amount"])

		if len(gcai_setting) > 0:
			if amount <= gcai_setting[0].expired_amount:
				amount_rest = amount - 1
				frappe.msgprint(_("There are only {} numbers available for this CAI.".format(amount_rest)))
		
			now = date.today()
			days = timedelta(days=int(gcai_setting[0].expired_days))

			sum_dates = now+days

			if str(date) <= str(sum_dates):
				for i in range(int(gcai_setting[0].expired_days)):		
					now1 = date.today()
					days1 = timedelta(days=i)

					sum_dates1 = now1+days1
					if str(date) == str(sum_dates1):
						frappe.msgprint(_("This CAI expires in {} days.".format(i)))
						break		
					
	def validate_cai(self, name):
		doc_duedate = frappe.get_doc("GCAI", name)
		doc_duedate.state = "{}".format("Expired")
		doc_duedate.save()

	def validate_fixed_asset(self):
		for d in self.get("items"):
			if d.is_fixed_asset and d.meta.get_field("asset") and d.asset:
				asset = frappe.get_doc("Asset", d.asset)
				if self.doctype == "Sales Invoice" and self.docstatus == 1:
					if self.update_stock:
						frappe.throw(_("'Update Stock' cannot be checked for fixed asset sale"))

					elif asset.status in ("Scrapped", "Cancelled", "Sold"):
						frappe.throw(_("Row #{0}: Asset {1} cannot be submitted, it is already {2}").format(d.idx, d.asset, asset.status))

	def before_save(self):
		set_account_for_mode_of_payment(self)
	
	# def calculate_taxes_items:
	# 	items = frappe.get_all("Sales Invoice Item") 

	def before_naming(self):
		if self.docstatus == 0:
			self.assign_cai()
			self.create_prefix_for_days()
			self.create_daily_summary_series()

		if self.status == 'Draft' and self.cai == None:
			self.assign_cai()
			self.create_prefix_for_days()
			self.create_daily_summary_series()

	def create_prefix_for_days(self):
		prefix = cai = frappe.get_all("Prefix sales for days", ["name_prefix"], filters = {"name_prefix": self.naming_series})

		if len(prefix) == 0:
			doc = frappe.new_doc('Prefix sales for days')
			doc.name_prefix = self.naming_series
			doc.insert()
	
	def create_daily_summary_series(self):
		split_serie = self.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])
		prefix = frappe.get_all("Daily summary series", ["name_serie"], filters = {"name_serie": serie})

		if len(prefix) == 0:
			doc = frappe.new_doc('Daily summary series')
			doc.name_serie = serie
			doc.insert()

	def on_submit(self):
		self.validate_pos_paid_amount()

		if not self.auto_repeat:
			frappe.get_doc('Authorization Control').validate_approving_authority(self.doctype,
				self.company, self.base_grand_total, self)

		self.check_prev_docstatus()

		if self.is_return and not self.update_billed_amount_in_sales_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_in_dn()
		self.clear_unallocated_mode_of_payments()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		if self.update_stock == 1:
			self.update_stock_ledger()

		# this sequence because outstanding may get -ve
		self.make_gl_entries()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Delivery Note")
			self.update_billing_status_for_zero_amount_refdoc("Sales Order")
			self.check_credit_limit()

		self.update_serial_no()

		if not cint(self.is_pos) == 1 and not self.is_return:
			self.update_against_document_in_jv()

		self.update_time_sheet(self.name)

		if frappe.db.get_single_value('Selling Settings', 'sales_update_frequency') == "Each Transaction":
			update_company_current_month_sales(self.company)
			self.update_project()
		update_linked_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		# create the loyalty point ledger entry if the customer is enrolled in any loyalty program
		if not self.is_return and self.loyalty_program:
			self.make_loyalty_point_entry()
		elif self.is_return and self.return_against and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			against_si_doc.delete_loyalty_point_entry()
			against_si_doc.make_loyalty_point_entry()
		if self.redeem_loyalty_points and self.loyalty_points:
			self.apply_loyalty_points()

		# Healthcare Service Invoice.
		domain_settings = frappe.get_doc('Domain Settings')
		active_domains = [d.domain for d in domain_settings.active_domains]

		if "Healthcare" in active_domains:
			manage_invoice_submit_cancel(self, "on_submit")
		
		if self.docstatus == 1:
			self.update_item_discount_amount()

	def validate_pos_return(self):

		if self.is_pos and self.is_return:
			total_amount_in_payments = 0
			for payment in self.payments:
				total_amount_in_payments += payment.amount
			invoice_total = self.rounded_total or self.grand_total
			if total_amount_in_payments < invoice_total:
				frappe.throw(_("Total payments amount can't be greater than {}".format(-invoice_total)))

	def validate_pos_paid_amount(self):
		if len(self.payments) == 0 and self.is_pos:
			frappe.throw(_("At least one mode of payment is required for POS invoice."))

	def before_cancel(self):
		self.update_time_sheet(None)


	def on_cancel(self):
		super(SalesInvoice, self).on_cancel()

		if self.enrolled_students != None:
			frappe.throw(_("You can´t cancel pay for Enrolled Student: {}".format(self.enrolled_students)))

		self.update_dashboard_customer_cancel()
 
		self.check_sales_order_on_hold_or_close("sales_order")

		if self.is_return and not self.update_billed_amount_in_sales_order:
			# NOTE status updating bypassed for is_return
			self.status_updater = []

		self.update_status_updater_args()
		self.update_prevdoc_status()
		self.update_billing_status_in_dn()

		if not self.is_return:
			self.update_billing_status_for_zero_amount_refdoc("Delivery Note")
			self.update_billing_status_for_zero_amount_refdoc("Sales Order")
			self.update_serial_no(in_cancel=True)

		self.validate_c_form_on_cancel()

		# Updating stock ledger should always be called after updating prevdoc status,
		# because updating reserved qty in bin depends upon updated delivered qty in SO
		if self.update_stock == 1:
			self.update_stock_ledger()

		self.make_gl_entries_on_cancel()
		frappe.db.set(self, 'status', 'Cancelled')

		if frappe.db.get_single_value('Selling Settings', 'sales_update_frequency') == "Each Transaction":
			update_company_current_month_sales(self.company)
			self.update_project()
		if not self.is_return and self.loyalty_program:
			self.delete_loyalty_point_entry()
		elif self.is_return and self.return_against and self.loyalty_program:
			against_si_doc = frappe.get_doc("Sales Invoice", self.return_against)
			against_si_doc.delete_loyalty_point_entry()
			against_si_doc.make_loyalty_point_entry()

		unlink_inter_company_doc(self.doctype, self.name, self.inter_company_invoice_reference)

		# Healthcare Service Invoice.
		domain_settings = frappe.get_doc('Domain Settings')
		active_domains = [d.domain for d in domain_settings.active_domains]

		if "Healthcare" in active_domains:
			manage_invoice_submit_cancel(self, "on_cancel")

	def update_status_updater_args(self):
		if cint(self.update_stock):
			self.status_updater.append({
				'source_dt':'Sales Invoice Item',
				'target_dt':'Sales Order Item',
				'target_parent_dt':'Sales Order',
				'target_parent_field':'per_delivered',
				'target_field':'delivered_qty',
				'target_ref_field':'qty',
				'source_field':'qty',
				'join_field':'so_detail',
				'percent_join_field':'sales_order',
				'status_field':'delivery_status',
				'keyword':'Delivered',
				'second_source_dt': 'Delivery Note Item',
				'second_source_field': 'qty',
				'second_join_field': 'so_detail',
				'overflow_type': 'delivery',
				'extra_cond': """ and exists(select name from `tabSales Invoice`
					where name=`tabSales Invoice Item`.parent and update_stock = 1)"""
			})
			if cint(self.is_return):
				self.status_updater.append({
					'source_dt': 'Sales Invoice Item',
					'target_dt': 'Sales Order Item',
					'join_field': 'so_detail',
					'target_field': 'returned_qty',
					'target_parent_dt': 'Sales Order',
					'source_field': '-1 * qty',
					'second_source_dt': 'Delivery Note Item',
					'second_source_field': '-1 * qty',
					'second_join_field': 'so_detail',
					'extra_cond': """ and exists (select name from `tabSales Invoice` where name=`tabSales Invoice Item`.parent and update_stock=1 and is_return=1)"""
				})

	def check_credit_limit(self):
		from erpnext.selling.doctype.customer.customer import check_credit_limit

		validate_against_credit_limit = False
		bypass_credit_limit_check_at_sales_order = frappe.db.get_value("Customer Credit Limit",
			filters={'parent': self.customer, 'parenttype': 'Customer', 'company': self.company},
			fieldname=["bypass_credit_limit_check"])

		if bypass_credit_limit_check_at_sales_order:
			validate_against_credit_limit = True

		for d in self.get("items"):
			if not (d.sales_order or d.delivery_note):
				validate_against_credit_limit = True
				break
		if validate_against_credit_limit:
			check_credit_limit(self.customer, self.company, bypass_credit_limit_check_at_sales_order)

	def set_missing_values(self, for_validate=False):
		pos = self.set_pos_fields(for_validate)

		if not self.debit_to:
			self.debit_to = get_party_account("Customer", self.customer, self.company)
			self.party_account_currency = frappe.db.get_value("Account", self.debit_to, "account_currency", cache=True)
		if not self.due_date and self.customer:
			self.due_date = get_due_date(self.posting_date, "Customer", self.customer, self.company)

		super(SalesInvoice, self).set_missing_values(for_validate)

		print_format = pos.get("print_format_for_online") if pos else None
		if not print_format and not cint(frappe.db.get_value('Print Format', 'POS Invoice', 'disabled')):
			print_format = 'POS Invoice'

		if pos:
			return {
				"print_format": print_format,
				"allow_edit_rate": pos.get("allow_user_to_edit_rate"),
				"allow_edit_discount": pos.get("allow_user_to_edit_discount"),
				"campaign": pos.get("campaign")
			}

	def update_time_sheet(self, sales_invoice):
		for d in self.timesheets:
			if d.time_sheet:
				timesheet = frappe.get_doc("Timesheet", d.time_sheet)
				self.update_time_sheet_detail(timesheet, d, sales_invoice)
				timesheet.calculate_total_amounts()
				timesheet.calculate_percentage_billed()
				timesheet.flags.ignore_validate_update_after_submit = True
				timesheet.set_status()
				timesheet.save()

	def update_time_sheet_detail(self, timesheet, args, sales_invoice):
		for data in timesheet.time_logs:
			if (self.project and args.timesheet_detail == data.name) or \
				(not self.project and not data.sales_invoice) or \
				(not sales_invoice and data.sales_invoice == self.name):
				data.sales_invoice = sales_invoice

	def on_update(self):
		self.set_paid_amount()
		if self.docstatus == 0:
			self.update_item_discount_amount()
		# self.exonerated_value()
		company = frappe.get_doc('Company', self.company)
		if company.isv_by_item_amount:
			self.calculated_taxes_by_item_amount()
		else:
			self.calculated_taxes()
		if self.docstatus == 1:
			self.create_dispatch_control()
			self.verificate_work_order()
			self.work_order_create()
		
		self.reload()

		# if self.grand_total == self.paid_amount:
		# 		self.db_set('outstanding_amount', 0, update_modified=False)	
		# else:
		# 	outstanding_amount = self.rounded_total

		# 	if self.total_advance > 0:
		# 		outstanding_amount = self.rounded_total - self.total_advance

		# 	if self.paid_amount > 0:
		# 		outstanding_amount = self.rounded_total - self.paid_amount
				
		# 	self.db_set('outstanding_amount', outstanding_amount, update_modified=False)

	def set_paid_amount(self):
		paid_amount = 0.0
		base_paid_amount = 0.0
		for data in self.payments:
			data.base_amount = flt(data.amount*self.conversion_rate, self.precision("base_paid_amount"))
			paid_amount += data.amount
			base_paid_amount += data.base_amount

		self.paid_amount = paid_amount
		self.base_paid_amount = base_paid_amount

	def validate_time_sheets_are_submitted(self):
		for data in self.timesheets:
			if data.time_sheet:
				status = frappe.db.get_value("Timesheet", data.time_sheet, "status")
				if status not in ['Submitted', 'Payslip']:
					frappe.throw(_("Timesheet {0} is already completed or cancelled").format(data.time_sheet))

	def set_pos_fields(self, for_validate=False):
		"""Set retail related fields from POS Profiles"""
		if cint(self.is_pos) != 1:
			return

		from erpnext.stock.get_item_details import get_pos_profile_item_details, get_pos_profile
		if not self.pos_profile:
			pos_profile = get_pos_profile(self.company) or {}
			self.pos_profile = pos_profile.get('name')

		pos = {}
		if self.pos_profile:
			pos = frappe.get_doc('POS Profile', self.pos_profile)

		if not self.get('payments') and not for_validate:
			update_multi_mode_option(self, pos)

		if not self.account_for_change_amount:
			self.account_for_change_amount = frappe.get_cached_value('Company',  self.company,  'default_cash_account')

		if pos:
			self.allow_print_before_pay = pos.allow_print_before_pay

			if not for_validate and not self.customer:
				self.customer = pos.customer

			self.ignore_pricing_rule = pos.ignore_pricing_rule
			if pos.get('account_for_change_amount'):
				self.account_for_change_amount = pos.get('account_for_change_amount')

			for fieldname in ('territory', 'naming_series', 'currency', 'letter_head', 'tc_name',
				'company', 'select_print_heading', 'cash_bank_account', 'write_off_account', 'taxes_and_charges',
				'write_off_cost_center', 'apply_discount_on', 'cost_center'):
					if (not for_validate) or (for_validate and not self.get(fieldname)):
						self.set(fieldname, pos.get(fieldname))

			customer_price_list = frappe.get_value("Customer", self.customer, 'default_price_list')

			if pos.get("company_address"):
				self.company_address = pos.get("company_address")

			if not customer_price_list:
				price_list = self.assing_price_list_pos()

				if price_list != "":
					doc = frappe.get_doc('POS Profile', pos.get('name'))
					doc.selling_price_list = price_list
					doc.save()
					self.set('selling_price_list', price_list)
				else:
					self.set('selling_price_list', pos.get("selling_price_list"))

			if not for_validate:
				self.update_stock = cint(pos.get("update_stock"))

			# set pos values in items
			for item in self.get("items"):
				if item.get('item_code'):
					profile_details = get_pos_profile_item_details(pos, frappe._dict(item.as_dict()), pos)
					for fname, val in iteritems(profile_details):
						if (not for_validate) or (for_validate and not item.get(fname)):
							item.set(fname, val)

			# fetch terms
			if self.tc_name and not self.terms:
				self.terms = frappe.db.get_value("Terms and Conditions", self.tc_name, "terms")

			# fetch charges
			if self.taxes_and_charges and not len(self.get("taxes")):
				self.set_taxes()

		return pos

	def get_company_abbr(self):
		return frappe.db.sql("select abbr from tabCompany where name=%s", self.company)[0][0]

	def validate_debit_to_acc(self):
		account = frappe.get_cached_value("Account", self.debit_to,
			["account_type", "report_type", "account_currency"], as_dict=True)

		if not account:
			frappe.throw(_("Debit To is required"))

		if account.report_type != "Balance Sheet":
			frappe.throw(_("Debit To account must be a Balance Sheet account"))

		if self.customer and account.account_type != "Receivable":
			frappe.throw(_("Debit To account must be a Receivable account"))

		self.party_account_currency = account.account_currency

	def clear_unallocated_mode_of_payments(self):
		self.set("payments", self.get("payments", {"amount": ["not in", [0, None, ""]]}))

		frappe.db.sql("""delete from `tabSales Invoice Payment` where parent = %s
			and amount = 0""", self.name)

	def validate_with_previous_doc(self):
		super(SalesInvoice, self).validate_with_previous_doc({
			"Sales Order": {
				"ref_dn_field": "sales_order",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Sales Order Item": {
				"ref_dn_field": "so_detail",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
			"Delivery Note": {
				"ref_dn_field": "delivery_note",
				"compare_fields": [["customer", "="], ["company", "="], ["project", "="], ["currency", "="]]
			},
			"Delivery Note Item": {
				"ref_dn_field": "dn_detail",
				"compare_fields": [["item_code", "="], ["uom", "="], ["conversion_factor", "="]],
				"is_child_table": True,
				"allow_duplicate_prev_row_id": True
			},
		})

		if cint(frappe.db.get_single_value('Selling Settings', 'maintain_same_sales_rate')) and not self.is_return:
			self.validate_rate_with_reference_doc([
				["Sales Order", "sales_order", "so_detail"],
				["Delivery Note", "delivery_note", "dn_detail"]
			])

	def set_against_income_account(self):
		"""Set against account for debit to account"""
		against_acc = []
		for d in self.get('items'):
			if d.income_account and d.income_account not in against_acc:
				against_acc.append(d.income_account)
		self.against_income_account = ','.join(against_acc)

	def add_remarks(self):
		if not self.remarks: self.remarks = 'No Remarks'

	def validate_auto_set_posting_time(self):
		# Don't auto set the posting date and time if invoice is amended
		if self.is_new() and self.amended_from:
			self.set_posting_time = 1

		self.validate_posting_time()

	def so_dn_required(self):
		"""check in manage account if sales order / delivery note required or not."""
		if self.is_return:
			return
		dic = {'Sales Order':['so_required', 'is_pos'],'Delivery Note':['dn_required', 'update_stock']}
		for i in dic:
			if frappe.db.get_single_value('Selling Settings', dic[i][0]) == 'Yes':
				for d in self.get('items'):
					is_stock_item = frappe.get_cached_value('Item', d.item_code, 'is_stock_item')
					if  (d.item_code and is_stock_item == 1\
						and not d.get(i.lower().replace(' ','_')) and not self.get(dic[i][1])):
						msgprint(_("{0} is mandatory for Item {1}").format(i,d.item_code), raise_exception=1)


	def validate_proj_cust(self):
		"""check for does customer belong to same project as entered.."""
		if self.project and self.customer:
			res = frappe.db.sql("""select name from `tabProject`
				where name = %s and (customer = %s or customer is null or customer = '')""",
				(self.project, self.customer))
			if not res:
				throw(_("Customer {0} does not belong to project {1}").format(self.customer,self.project))

	def validate_pos(self):
		if self.is_return:
			if flt(self.paid_amount) + flt(self.write_off_amount) - flt(self.grand_total) > \
				1.0/(10.0**(self.precision("grand_total") + 1.0)):
					frappe.throw(_("Paid amount + Write Off Amount can not be greater than Grand Total"))

	def validate_item_code(self):
		for d in self.get('items'):
			if not d.item_code:
				msgprint(_("Item Code required at Row No {0}").format(d.idx), raise_exception=True)

	def validate_warehouse(self):
		super(SalesInvoice, self).validate_warehouse()

		for d in self.get_item_list():
			if not d.warehouse and frappe.get_cached_value("Item", d.item_code, "is_stock_item"):
				frappe.throw(_("Warehouse required for stock Item {0}").format(d.item_code))

	def validate_delivery_note(self):
		for d in self.get("items"):
			if d.delivery_note:
				msgprint(_("Stock cannot be updated against Delivery Note {0}").format(d.delivery_note), raise_exception=1)

	def validate_write_off_account(self):
		if flt(self.write_off_amount) and not self.write_off_account:
			self.write_off_account = frappe.get_cached_value('Company',  self.company,  'write_off_account')

		if flt(self.write_off_amount) and not self.write_off_account:
			msgprint(_("Please enter Write Off Account"), raise_exception=1)

	def validate_account_for_change_amount(self):
		if flt(self.change_amount) and not self.account_for_change_amount:
			msgprint(_("Please enter Account for Change Amount"), raise_exception=1)

	def validate_c_form(self):
		""" Blank C-form no if C-form applicable marked as 'No'"""
		if self.amended_from and self.c_form_applicable == 'No' and self.c_form_no:
			frappe.db.sql("""delete from `tabC-Form Invoice Detail` where invoice_no = %s
					and parent = %s""", (self.amended_from,	self.c_form_no))

			frappe.db.set(self, 'c_form_no', '')

	def validate_c_form_on_cancel(self):
		""" Display message if C-Form no exists on cancellation of Sales Invoice"""
		if self.c_form_applicable == 'Yes' and self.c_form_no:
			msgprint(_("Please remove this Invoice {0} from C-Form {1}")
				.format(self.name, self.c_form_no), raise_exception = 1)

	def validate_dropship_item(self):
		for item in self.items:
			if item.sales_order:
				if frappe.db.get_value("Sales Order Item", item.so_detail, "delivered_by_supplier"):
					frappe.throw(_("Could not update stock, invoice contains drop shipping item."))

	def update_current_stock(self):
		for d in self.get('items'):
			if d.item_code and d.warehouse:
				bin = frappe.db.sql("select actual_qty from `tabBin` where item_code = %s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
				d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0

		for d in self.get('packed_items'):
			bin = frappe.db.sql("select actual_qty, projected_qty from `tabBin` where item_code =	%s and warehouse = %s", (d.item_code, d.warehouse), as_dict = 1)
			d.actual_qty = bin and flt(bin[0]['actual_qty']) or 0
			d.projected_qty = bin and flt(bin[0]['projected_qty']) or 0

	def update_packing_list(self):
		if cint(self.update_stock) == 1:
			from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
			make_packing_list(self)
		else:
			self.set('packed_items', [])

	def set_billing_hours_and_amount(self):
		if not self.project:
			for timesheet in self.timesheets:
				ts_doc = frappe.get_doc('Timesheet', timesheet.time_sheet)
				if not timesheet.billing_hours and ts_doc.total_billable_hours:
					timesheet.billing_hours = ts_doc.total_billable_hours

				if not timesheet.billing_amount and ts_doc.total_billable_amount:
					timesheet.billing_amount = ts_doc.total_billable_amount

	def update_timesheet_billing_for_project(self):
		if not self.timesheets and self.project:
			self.add_timesheet_data()
		else:
			self.calculate_billing_amount_for_timesheet()

	def add_timesheet_data(self):
		self.set('timesheets', [])
		if self.project:
			for data in get_projectwise_timesheet_data(self.project):
				self.append('timesheets', {
						'time_sheet': data.parent,
						'billing_hours': data.billing_hours,
						'billing_amount': data.billing_amt,
						'timesheet_detail': data.name
					})

			self.calculate_billing_amount_for_timesheet()

	def calculate_billing_amount_for_timesheet(self):
		total_billing_amount = 0.0
		for data in self.timesheets:
			if data.billing_amount:
				total_billing_amount += data.billing_amount

		self.total_billing_amount = total_billing_amount

	def get_warehouse(self):
		user_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
			where ifnull(user,'') = %s and company = %s""", (frappe.session['user'], self.company))
		warehouse = user_pos_profile[0][1] if user_pos_profile else None

		if not warehouse:
			global_pos_profile = frappe.db.sql("""select name, warehouse from `tabPOS Profile`
				where (user is null or user = '') and company = %s""", self.company)

			if global_pos_profile:
				warehouse = global_pos_profile[0][1]
			elif not user_pos_profile:
				msgprint(_("POS Profile required to make POS Entry"), raise_exception=True)

		return warehouse

	def set_income_account_for_fixed_assets(self):
		disposal_account = depreciation_cost_center = None
		for d in self.get("items"):
			if d.is_fixed_asset:
				if not disposal_account:
					disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(self.company)

				d.income_account = disposal_account
				if not d.cost_center:
					d.cost_center = depreciation_cost_center

	def check_prev_docstatus(self):
		for d in self.get('items'):
			if d.sales_order and frappe.db.get_value("Sales Order", d.sales_order, "docstatus") != 1:
				frappe.throw(_("Sales Order {0} is not submitted").format(d.sales_order))

			if d.delivery_note and frappe.db.get_value("Delivery Note", d.delivery_note, "docstatus") != 1:
				throw(_("Delivery Note {0} is not submitted").format(d.delivery_note))

	def make_gl_entries(self, gl_entries=None, repost_future_gle=True, from_repost=False):
		auto_accounting_for_stock = erpnext.is_perpetual_inventory_enabled(self.company)
		
		if not gl_entries:
			gl_entries = self.get_gl_entries()

		if gl_entries:
			from erpnext.accounts.general_ledger import make_gl_entries

			# if POS and amount is written off, updating outstanding amt after posting all gl entries
			update_outstanding = "No" if (cint(self.is_pos) or self.write_off_account or
				cint(self.redeem_loyalty_points)) else "Yes"

			# if self.exonerated == 1:
			# 	gl_entries.pop(1)

			make_gl_entries(gl_entries, cancel=(self.docstatus == 2),
				update_outstanding=update_outstanding, merge_entries=False, from_repost=from_repost)

			if update_outstanding == "No":
				from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt
				update_outstanding_amt(self.debit_to, "Customer", self.customer,
					self.doctype, self.return_against if cint(self.is_return) and self.return_against else self.name)

			if repost_future_gle and cint(self.update_stock) \
				and cint(auto_accounting_for_stock):
					items, warehouses = self.get_items_and_warehouses()
					update_gl_entries_after(self.posting_date, self.posting_time,
						warehouses, items, company = self.company)
		elif self.docstatus == 2 and cint(self.update_stock) \
			and cint(auto_accounting_for_stock):
				from erpnext.accounts.general_ledger import delete_gl_entries
				delete_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def get_gl_entries(self, warehouse_account=None):
		from erpnext.accounts.general_ledger import merge_similar_entries

		gl_entries = []

		self.make_customer_gl_entry(gl_entries)

		if self.discount_reason != None:
			self.make_discount_gl_entries(gl_entries)
		
		if self.isv15 > 0:
			self.make_isv15_gl_entries(gl_entries)
		
		if self.isv18 > 0:
			self.make_isv18_gl_entries(gl_entries)
		
		self.make_discount_Reason_GL_Entries(gl_entries)

		# if self.exonerated and self.account_head == None:
		# 	frappe.throw(_("You need to fill the account head field"))

		self.make_tax_gl_entries(gl_entries)

		self.make_item_gl_entries(gl_entries)

		# merge gl entries before adding pos entries
		gl_entries = merge_similar_entries(gl_entries)

		self.make_loyalty_point_redemption_gle(gl_entries)
		self.make_pos_gl_entries(gl_entries)
		# self.make_gle_for_change_amount(gl_entries)

		self.make_write_off_gl_entry(gl_entries)
		self.make_gle_for_rounding_adjustment(gl_entries)

		# frappe.msgprint("{}".format(gl_entries))

		return gl_entries

	def make_customer_gl_entry(self, gl_entries):
		# Checked both rounding_adjustment and rounded_total
		# because rounded_total had value even before introcution of posting GLE based on rounded total
		grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
		if grand_total:

			# Didnot use base_grand_total to book rounding loss gle
			grand_total_in_company_currency = flt(grand_total * self.conversion_rate,
				self.precision("grand_total"))

			company = frappe.get_doc("Company", self.company)

			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"due_date": self.due_date,
					"against": self.against_income_account,
					"debit": grand_total_in_company_currency,
					"debit_in_account_currency": grand_total_in_company_currency \
						if self.party_account_currency==self.company_currency else grand_total,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.cost_center
				}, self.party_account_currency)
			)
	def make_isv15_gl_entries(self, gl_entries):
		self.calculated_taxes_by_item_amount()
		company = frappe.get_doc("Company", self.company)

		account = self.account15

		# if account == None:
		# 	account = company.account_isv15
		
		if account == None:
			frappe.throw(_("Assign a account to product for ISV 15"))

		account_currency = get_account_currency(account)

		# frappe.msgprint("cuenta factrura {}".format(account))

		gl_entries.append(
				self.get_gl_dict({
					"account": account,
					"party_type": "Customer",
					"party": self.customer,
					"against": self.customer,
			 		"credit": self.isv15,
			 		"credit_in_account_currency": self.isv15,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.round_off_cost_center
			}, account_currency)
		)
	
	def make_isv18_gl_entries(self, gl_entries):
		company = frappe.get_doc("Company", self.company)

		account = self.account18

		if account == None:
			account = company.account_isv18
		
		if account == None:
			frappe.throw(_("Assign a account to product and company for ISV 18"))

		account_currency = get_account_currency(account)

		# frappe.msgprint("cuenta factrura 18 {}".format(account))

		gl_entries.append(
				self.get_gl_dict({
					"account": account,
					"party_type": "Customer",
					"party": self.customer,
					"against": self.customer,
			 		"credit": self.isv18,
			 		"credit_in_account_currency": self.isv18,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.round_off_cost_center
			}, account_currency)
		)

	def make_discount_Reason_GL_Entries(self, gl_entries):
		items = frappe.get_all("Sales Invoice Item", ["name", "discount_reason", "discount_amount", "price_list_rate", "qty", "discount_percentage"], filters = {"parent": self.name})

		totalDiscount = 0

		accountCredit = self.against_income_account

		isPos = False

		if(self.pos_profile  != None):
			pos_profile = frappe.get_doc("POS Profile", self.pos_profile)

			if(pos_profile.income_account != None):
				isPos = True
				accountCredit = pos_profile.income_account
		
		company = frappe.get_doc("Company", self.company)

		if(isPos == False):
			if(company.default_expense_account != None):
				accountCredit = company.default_expense_account
		
		for item in items:
			d_amount = item.price_list_rate * item.qty * (item.discount_percentage/100)

			if(item.sales_default_values != None):
				gl_entries.append(
				self.get_gl_dict({
					"account": item.sales_default_values,
					"party_type": "Customer",
					"party": self.customer,
			 		"credit": d_amount,
			 		"credit_in_account_currency": d_amount,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.round_off_cost_center
					}, account_currency)
				)
			else:
				totalDiscount += d_amount

			mode_of_payment = frappe.get_all("Mode of Payment Account", "default_account", filters = {"parent": item.discount_reason})

			if(len(mode_of_payment) == 0):
				frappe.throw(_("This mode of payment no have a account"))

			account_currency = get_account_currency(mode_of_payment[0].default_account)

			gl_entries.append(
				self.get_gl_dict({
					"account": mode_of_payment[0].default_account,
					"party_type": "Customer",
					"party": self.customer,
					"due_date": self.due_date,
					# "against": self.against_income_account,
					"debit": d_amount,
					"debit_in_account_currency": d_amount,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.round_off_cost_center
				}, account_currency)
			)

		account_currency_default = get_account_currency(accountCredit)
		
		if(totalDiscount > 0):
			gl_entries.append(
				self.get_gl_dict({
					"account": accountCredit,
					"party_type": "Customer",
					"party": self.customer,
					"credit": totalDiscount,
					"credit_in_account_currency": totalDiscount,
					"against_voucher": self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.round_off_cost_center
				}, account_currency_default)
			)

	def make_discount_gl_entries(self, gl_entries):
		account = frappe.get_all("Mode of Payment Account", ["*"], filters = {"company": self.company, "parent": self.discount_reason})

		if len(account) == 0:
			frappe.throw(_("The discount reason does not have a ledger account assigned for this company."))

		account_currency = get_account_currency(account[0].default_account)

		# gl_entries.append(
		# 	self.get_gl_dict({
		# 		"account": account[0].default_account,
		# 		"against": self.customer,
		# 		"credit": self.discount_amount,
		# 		"credit_in_account_currency": self.discount_amount,
		# 		"cost_center": self.cost_center
		# 	}, account_currency)
		# )
		company = frappe.get_doc("Company", self.company)
		gl_entries.append(
				self.get_gl_dict({
					"account": account[0].default_account,
					"party_type": "Customer",
					"party": self.customer,
					"due_date": self.due_date,
					"against": self.against_income_account,
					"debit": self.discount_amount,
					"debit_in_account_currency": self.discount_amount,
					"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.round_off_cost_center
			}, account_currency)
		)

	def make_tax_gl_entries(self, gl_entries):
		for tax in self.get("taxes"):
			if flt(tax.base_tax_amount_after_discount_amount):
				account_currency = get_account_currency(tax.account_head)
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"against": self.customer,
						"credit": flt(tax.base_tax_amount_after_discount_amount,
							tax.precision("tax_amount_after_discount_amount")),
						"credit_in_account_currency": (flt(tax.base_tax_amount_after_discount_amount,
							tax.precision("base_tax_amount_after_discount_amount")) if account_currency==self.company_currency else
							flt(tax.tax_amount_after_discount_amount, tax.precision("tax_amount_after_discount_amount"))),
						"cost_center": tax.cost_center
					}, account_currency)
				)

	def make_item_gl_entries(self, gl_entries):
		# income account gl entries
		total_amount = 0
		cont = 0
		for item in self.get("items"):
			base_net_amount = 0

			if self.is_pos:
				pos = frappe.get_doc("POS Profile", self.pos_profile)

				if pos.round_off_discount == 1:
					base_net_amount = math.floor(item.base_net_amount)
					total_amount += base_net_amount
					items = self.get("items")
					last = items[-1]
					
					if last.item_code == item.item_code:
						if total_amount < gl_entries[0].debit:
							total_amount -= base_net_amount
							base_net_amount = math.ceil(item.base_net_amount)
							total_amount += base_net_amount

							if total_amount < gl_entries[0].debit:
								sum_amount = gl_entries[0].debit - total_amount
								base_net_amount += sum_amount
								total_amount += sum_amount
					
					if item.is_exonerated != 1:
						item_taxes = frappe.get_all("Item Tax", ['name', "item_tax_template"], filters = {"parent": item.item_code})
						if len(item_taxes) >0:
							for item_tax in item_taxes:
								tax_tamplates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": item_tax.item_tax_template})
									
								for tax_tamplate in tax_tamplates:

									tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate", "tax_type"], filters = {"parent": tax_tamplate.name})
												
									for tax_detail in tax_details:

										if tax_detail.tax_rate == 15:
											taxed_sales15 = item.amount/1.15
											rate = taxed_sales15
											base_net_amount -= item.amount - rate					
												
										if tax_detail.tax_rate == 18:
											taxed_sales18 = item.amount/1.18
											rate = taxed_sales18
													
											base_net_amount += item.amount - rate
				else:
					base_net_amount = item.base_net_amount

					if item.is_exonerated != 1:
						item_taxes = frappe.get_all("Item Tax", ['name', "item_tax_template"], filters = {"parent": item.item_code})
						if len(item_taxes) >0:
							for item_tax in item_taxes:
								tax_tamplates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": item_tax.item_tax_template})
									
								for tax_tamplate in tax_tamplates:

									tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate", "tax_type"], filters = {"parent": tax_tamplate.name})
												
									for tax_detail in tax_details:

										if tax_detail.tax_rate == 15:
											taxed_sales15 = item.amount/1.15
											rate = taxed_sales15
											base_net_amount -= item.amount - rate						
												
										if tax_detail.tax_rate == 18:
											taxed_sales18 = item.amount/1.18
											rate = taxed_sales18
													
											base_net_amount -= item.amount - rate
			else:
				if self.round_off_discount:
					base_net_amount = math.floor(item.base_net_amount)
					total_amount += base_net_amount
					items = self.get("items")
					last = items[-1]
						
					if last.item_code == item.item_code:
						if total_amount < gl_entries[0].debit:
							total_amount -= base_net_amount
							base_net_amount = math.ceil(item.base_net_amount)
							total_amount += base_net_amount

							if total_amount < gl_entries[0].debit:
								sum_amount = gl_entries[0].debit - total_amount
								base_net_amount += sum_amount
								total_amount += sum_amount
					
					if item.is_exonerated != 1:
						item_taxes = frappe.get_all("Item Tax", ['name', "item_tax_template"], filters = {"parent": item.item_code})
						if len(item_taxes) >0:
							for item_tax in item_taxes:
								tax_tamplates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": item_tax.item_tax_template})
									
								for tax_tamplate in tax_tamplates:

									tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate", "tax_type"], filters = {"parent": tax_tamplate.name})
												
									for tax_detail in tax_details:

										if tax_detail.tax_rate == 15:
											taxed_sales15 = item.amount/1.15
											rate = taxed_sales15
											base_net_amount -= item.amount - rate						
												
										if tax_detail.tax_rate == 18:
											taxed_sales18 = item.amount/1.18
											rate = taxed_sales18
													
											base_net_amount -= item.amount - rate
				else:
					base_net_amount = item.base_net_amount

					if item.is_exonerated != 1:
						item_taxes = frappe.get_all("Item Tax", ['name', "item_tax_template"], filters = {"parent": item.item_code})
						if len(item_taxes) >0:
							for item_tax in item_taxes:
								tax_tamplates = frappe.get_all("Item Tax Template", ["name"], filters = {"name": item_tax.item_tax_template})
									
								for tax_tamplate in tax_tamplates:

									tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate", "tax_type"], filters = {"parent": tax_tamplate.name})
												
									for tax_detail in tax_details:

										if tax_detail.tax_rate == 15:
											taxed_sales15 = item.amount/1.15
											rate = taxed_sales15
											base_net_amount -= item.amount - rate						
												
										if tax_detail.tax_rate == 18:
											taxed_sales18 = item.amount/1.18
											rate = taxed_sales18
													
											base_net_amount -= item.amount - rate

			if flt(base_net_amount, item.precision("base_net_amount")):
				if item.is_fixed_asset:
					asset = frappe.get_doc("Asset", item.asset)

					if (len(asset.finance_books) > 1 and not item.finance_book
						and asset.finance_books[0].finance_book):
						frappe.throw(_("Select finance book for the item {0} at row {1}")
							.format(item.item_code, item.idx))

					fixed_asset_gl_entries = get_gl_entries_on_asset_disposal(asset,
						base_net_amount, item.finance_book)

					for gle in fixed_asset_gl_entries:
						gle["against"] = self.customer
						gl_entries.append(self.get_gl_dict(gle))

					asset.db_set("disposal_date", self.posting_date)
					asset.set_status("Sold" if self.docstatus==1 else None)
				else:
					income_account = (item.income_account
						if (not item.enable_deferred_revenue or self.is_return) else item.deferred_revenue_account)
					
					company = frappe.get_doc("Company", self.company)
					if self.outstanding_amount > 0:						
						if company.default_credit_account == None:
							frappe.throw(_("Assign Credit Account by default in the company"))
						else:
							income_account = company.default_credit_account
					
					paid_amount = 0

					for advance in self.get("advances"):
						paid_amount += advance.allocated_amount
					
					if paid_amount > 0:
						if paid_amount == self.grand_total:
							income_account = company.default_income_account
					
					account_currency = get_account_currency(income_account)
					gl_entries.append(
						self.get_gl_dict({
							"account": income_account,
							"against": self.customer,
							"credit": flt(base_net_amount, item.precision("base_net_amount")),
							"credit_in_account_currency": (flt(base_net_amount, item.precision("base_net_amount"))
								if account_currency==self.company_currency
								else flt(item.net_amount, item.precision("net_amount"))),
							"cost_center": item.cost_center
						}, account_currency, item=item)
					)

		# expense account gl entries
		if cint(self.update_stock) and \
			erpnext.is_perpetual_inventory_enabled(self.company):
			gl_entries += super(SalesInvoice, self).get_gl_entries()
		
		if self.discount_reason != None:				
				
				company = frappe.get_doc("Company", self.company)
				income_account = company.default_income_account

				if self.outstanding_amount > 0:						
					if company.default_credit_account == None:
						frappe.throw(_("Assign Credit Account by default in the company"))
					else:
						income_account = company.default_credit_account
					
				paid_amount = 0

				for advance in self.get("advances"):
					paid_amount += advance.allocated_amount
					
				if paid_amount > 0:
					if paid_amount == self.grand_total:
						income_account = company.default_income_account

				account_currency = get_account_currency(income_account)

				gl_entries.append(self.get_gl_dict({
					"account": income_account,
					"against": self.customer,
					"cost_center": company.cost_center,
					"remarks": self.get("remarks") or "Accounting Entry for Stock",
					"credit": self.discount_amount,
					"credit_in_account_currency": self.discount_amount
				}, account_currency))

	def make_loyalty_point_redemption_gle(self, gl_entries):
		company = frappe.get_doc("Company", self.company)
		if cint(self.redeem_loyalty_points):
			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"against": "Expense account - " + cstr(self.loyalty_redemption_account) + " for the Loyalty Program",
					"credit": self.loyalty_amount,
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.cost_center
				})
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.loyalty_redemption_account,
					"cost_center": company.cost_center or self.loyalty_redemption_cost_center,
					"against": self.customer,
					"debit": self.loyalty_amount,
					"remark": "Loyalty Points redeemed by the customer"
				})
			)

	def make_pos_gl_entries(self, gl_entries):
		if cint(self.is_pos):
			for payment_mode in self.payments:
				if payment_mode.amount:
					# POS, make payment entries
					if payment_mode.mode_of_payment == "Efectivo":
						amount = payment_mode.base_amount - self.change_amount
					else:
						amount = payment_mode.base_amount
					
					company = frappe.get_doc("Company", self.company)
					
					gl_entries.append(
						self.get_gl_dict({
							"account": self.debit_to,
							"party_type": "Customer",
							"party": self.customer,
							"against": payment_mode.account,
							"credit": amount,
							"credit_in_account_currency": amount \
								if self.party_account_currency==self.company_currency \
								else payment_mode.amount,
							"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
							"against_voucher_type": self.doctype,
							"cost_center": company.cost_center
						}, self.party_account_currency)
					)

					payment_mode_account_currency = get_account_currency(payment_mode.account)
					gl_entries.append(
						self.get_gl_dict({
							"account": payment_mode.account,
							"against": self.customer,
							"debit": amount,
							"debit_in_account_currency": amount \
								if payment_mode_account_currency==self.company_currency \
								else payment_mode.amount,
							"cost_center": company.cost_center
						}, payment_mode_account_currency)
					)

	def make_gle_for_change_amount(self, gl_entries):
		if cint(self.is_pos) and self.change_amount:
			company = frappe.get_doc("Company", self.company)
			if self.account_for_change_amount:
				gl_entries.append(
					self.get_gl_dict({
						"account": self.debit_to,
						"party_type": "Customer",
						"party": self.customer,
						"against": self.account_for_change_amount,
						"debit": flt(self.base_change_amount),
						"debit_in_account_currency": flt(self.base_change_amount) \
							if self.party_account_currency==self.company_currency else flt(self.change_amount),
						"against_voucher": self.return_against if cint(self.is_return) and self.return_against else self.name,
						"against_voucher_type": self.doctype,
						"cost_center": company.cost_center
					}, self.party_account_currency)
				)

				gl_entries.append(
					self.get_gl_dict({
						"account": self.account_for_change_amount,
						"against": self.customer,
						"credit": self.base_change_amount,
						"cost_center": company.cost_center
					})
				)
			else:
				frappe.throw(_("Select change amount account"), title="Mandatory Field")

	def make_write_off_gl_entry(self, gl_entries):
		# write off entries, applicable if only pos
		if self.write_off_account and flt(self.write_off_amount, self.precision("write_off_amount")):
			write_off_account_currency = get_account_currency(self.write_off_account)
			default_cost_center = frappe.get_cached_value('Company',  self.company,  'cost_center')

			company = frappe.get_doc("Company", self.company)

			gl_entries.append(
				self.get_gl_dict({
					"account": self.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"against": self.write_off_account,
					"credit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
					"credit_in_account_currency": (flt(self.base_write_off_amount,
						self.precision("base_write_off_amount")) if self.party_account_currency==self.company_currency
						else flt(self.write_off_amount, self.precision("write_off_amount"))),
					"against_voucher": self.return_against if cint(self.is_return) else self.name,
					"against_voucher_type": self.doctype,
					"cost_center": company.cost_center
				}, self.party_account_currency)
			)
			gl_entries.append(
				self.get_gl_dict({
					"account": self.write_off_account,
					"against": self.customer,
					"debit": flt(self.base_write_off_amount, self.precision("base_write_off_amount")),
					"debit_in_account_currency": (flt(self.base_write_off_amount,
						self.precision("base_write_off_amount")) if write_off_account_currency==self.company_currency
						else flt(self.write_off_amount, self.precision("write_off_amount"))),
					"cost_center": company.cost_center or self.write_off_cost_center or default_cost_center
				}, write_off_account_currency)
			)

	def make_gle_for_rounding_adjustment(self, gl_entries):
		if flt(self.rounding_adjustment, self.precision("rounding_adjustment")) and self.base_rounding_adjustment:
			round_off_account, round_off_cost_center = \
				get_round_off_account_and_cost_center(self.company)

			company = frappe.get_doc("Company", self.company)

			gl_entries.append(
				self.get_gl_dict({
					"account": round_off_account,
					"against": self.customer,
					"credit_in_account_currency": flt(self.rounding_adjustment,
						self.precision("rounding_adjustment")),
					"credit": flt(self.base_rounding_adjustment,
						self.precision("base_rounding_adjustment")),
					"cost_center": company.cost_center or round_off_cost_center,
				}
			))

	def update_billing_status_in_dn(self, update_modified=True):
		updated_delivery_notes = []
		for d in self.get("items"):
			if d.dn_detail:
				billed_amt = frappe.db.sql("""select sum(amount) from `tabSales Invoice Item`
					where dn_detail=%s and docstatus=1""", d.dn_detail)
				billed_amt = billed_amt and billed_amt[0][0] or 0
				frappe.db.set_value("Delivery Note Item", d.dn_detail, "billed_amt", billed_amt, update_modified=update_modified)
				updated_delivery_notes.append(d.delivery_note)
			elif d.so_detail:
				updated_delivery_notes += update_billed_amount_based_on_so(d.so_detail, update_modified)

		for dn in set(updated_delivery_notes):
			frappe.get_doc("Delivery Note", dn).update_billing_percentage(update_modified=update_modified)

	def on_recurring(self, reference_doc, auto_repeat_doc):
		for fieldname in ("c_form_applicable", "c_form_no", "write_off_amount"):
			self.set(fieldname, reference_doc.get(fieldname))

		self.due_date = None

	def update_serial_no(self, in_cancel=False):
		""" update Sales Invoice refrence in Serial No """
		invoice = None if (in_cancel or self.is_return) else self.name
		if in_cancel and self.is_return:
			invoice = self.return_against

		for item in self.items:
			if not item.serial_no:
				continue

			for serial_no in item.serial_no.split("\n"):
				if serial_no and frappe.db.get_value('Serial No', serial_no, 'item_code') == item.item_code:
					frappe.db.set_value('Serial No', serial_no, 'sales_invoice', invoice)

	def validate_serial_numbers(self):
		"""
			validate serial number agains Delivery Note and Sales Invoice
		"""
		self.set_serial_no_against_delivery_note()
		self.validate_serial_against_delivery_note()
		self.validate_serial_against_sales_invoice()

	def set_serial_no_against_delivery_note(self):
		for item in self.items:
			if item.serial_no and item.delivery_note and \
				item.qty != len(get_serial_nos(item.serial_no)):
				item.serial_no = get_delivery_note_serial_no(item.item_code, item.qty, item.delivery_note)

	def validate_serial_against_delivery_note(self):
		"""
			validate if the serial numbers in Sales Invoice Items are same as in
			Delivery Note Item
		"""

		for item in self.items:
			if not item.delivery_note or not item.dn_detail:
				continue

			serial_nos = frappe.db.get_value("Delivery Note Item", item.dn_detail, "serial_no") or ""
			dn_serial_nos = set(get_serial_nos(serial_nos))

			serial_nos = item.serial_no or ""
			si_serial_nos = set(get_serial_nos(serial_nos))

			if si_serial_nos - dn_serial_nos:
				frappe.throw(_("Serial Numbers in row {0} does not match with Delivery Note".format(item.idx)))

			if item.serial_no and cint(item.qty) != len(si_serial_nos):
				frappe.throw(_("Row {0}: {1} Serial numbers required for Item {2}. You have provided {3}.".format(
					item.idx, item.qty, item.item_code, len(si_serial_nos))))

	def validate_serial_against_sales_invoice(self):
		""" check if serial number is already used in other sales invoice """
		for item in self.items:
			if not item.serial_no:
				continue

			for serial_no in item.serial_no.split("\n"):
				serial_no_details = frappe.db.get_value("Serial No", serial_no,
					["sales_invoice", "item_code"], as_dict=1)

				if not serial_no_details:
					continue

				if serial_no_details.sales_invoice and serial_no_details.item_code == item.item_code \
					and self.name != serial_no_details.sales_invoice:
					sales_invoice_company = frappe.db.get_value("Sales Invoice", serial_no_details.sales_invoice, "company")
					if sales_invoice_company == self.company:
						frappe.throw(_("Serial Number: {0} is already referenced in Sales Invoice: {1}"
							.format(serial_no, serial_no_details.sales_invoice)))

	def update_project(self):
		if self.project:
			project = frappe.get_doc("Project", self.project)
			project.update_billed_amount()
			project.db_update()


	def verify_payment_amount_is_positive(self):
		for entry in self.payments:
			if entry.amount < 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be positive").format(entry.idx))

	def verify_payment_amount_is_negative(self):
		for entry in self.payments:
			if entry.amount > 0:
				frappe.throw(_("Row #{0} (Payment Table): Amount must be negative").format(entry.idx))

	# collection of the loyalty points, create the ledger entry for that.
	def make_loyalty_point_entry(self):
		returned_amount = self.get_returned_amount()
		current_amount = flt(self.grand_total) - cint(self.loyalty_amount)
		eligible_amount = current_amount - returned_amount
		lp_details = get_loyalty_program_details_with_points(self.customer, company=self.company,
			current_transaction_amount=current_amount, loyalty_program=self.loyalty_program,
			expiry_date=self.posting_date, include_expired_entry=True)
		if lp_details and getdate(lp_details.from_date) <= getdate(self.posting_date) and \
			(not lp_details.to_date or getdate(lp_details.to_date) >= getdate(self.posting_date)):
			points_earned = cint(eligible_amount/lp_details.collection_factor)
			doc = frappe.get_doc({
				"doctype": "Loyalty Point Entry",
				"company": self.company,
				"loyalty_program": lp_details.loyalty_program,
				"loyalty_program_tier": lp_details.tier_name,
				"customer": self.customer,
				"sales_invoice": self.name,
				"loyalty_points": points_earned,
				"purchase_amount": eligible_amount,
				"expiry_date": add_days(self.posting_date, lp_details.expiry_duration),
				"posting_date": self.posting_date
			})
			doc.flags.ignore_permissions = 1
			doc.save()
			self.set_loyalty_program_tier()

	# valdite the redemption and then delete the loyalty points earned on cancel of the invoice
	def delete_loyalty_point_entry(self):
		lp_entry = frappe.db.sql("select name from `tabLoyalty Point Entry` where sales_invoice=%s",
			(self.name), as_dict=1)

		if not lp_entry: return
		against_lp_entry = frappe.db.sql('''select name, sales_invoice from `tabLoyalty Point Entry`
			where redeem_against=%s''', (lp_entry[0].name), as_dict=1)
		if against_lp_entry:
			invoice_list = ", ".join([d.sales_invoice for d in against_lp_entry])
			frappe.throw(_('''Sales Invoice can't be cancelled since the Loyalty Points earned has been redeemed.
				First cancel the Sales Invoice No {0}''').format(invoice_list))
		else:
			frappe.db.sql('''delete from `tabLoyalty Point Entry` where sales_invoice=%s''', (self.name))
			# Set loyalty program
			self.set_loyalty_program_tier()

	def set_loyalty_program_tier(self):
		lp_details = get_loyalty_program_details_with_points(self.customer, company=self.company,
				loyalty_program=self.loyalty_program, include_expired_entry=True)
		frappe.db.set_value("Customer", self.customer, "loyalty_program_tier", lp_details.tier_name)

	def get_returned_amount(self):
		returned_amount = frappe.db.sql("""
			select sum(grand_total)
			from `tabSales Invoice`
			where docstatus=1 and is_return=1 and ifnull(return_against, '')=%s
		""", self.name)
		return abs(flt(returned_amount[0][0])) if returned_amount else 0

	# redeem the loyalty points.
	def apply_loyalty_points(self):
		from erpnext.accounts.doctype.loyalty_point_entry.loyalty_point_entry \
			import get_loyalty_point_entries, get_redemption_details
		loyalty_point_entries = get_loyalty_point_entries(self.customer, self.loyalty_program, self.company, self.posting_date)
		redemption_details = get_redemption_details(self.customer, self.loyalty_program, self.company)

		points_to_redeem = self.loyalty_points
		for lp_entry in loyalty_point_entries:
			if lp_entry.sales_invoice == self.name:
				continue
			available_points = lp_entry.loyalty_points - flt(redemption_details.get(lp_entry.name))
			if available_points > points_to_redeem:
				redeemed_points = points_to_redeem
			else:
				redeemed_points = available_points
			doc = frappe.get_doc({
				"doctype": "Loyalty Point Entry",
				"company": self.company,
				"loyalty_program": self.loyalty_program,
				"loyalty_program_tier": lp_entry.loyalty_program_tier,
				"customer": self.customer,
				"sales_invoice": self.name,
				"redeem_against": lp_entry.name,
				"loyalty_points": -1*redeemed_points,
				"purchase_amount": self.grand_total,
				"expiry_date": lp_entry.expiry_date,
				"posting_date": self.posting_date
			})
			doc.flags.ignore_permissions = 1
			doc.save()
			points_to_redeem -= redeemed_points
			if points_to_redeem < 1: # since points_to_redeem is integer
				break

	# Healthcare
	def set_healthcare_services(self, checked_values):
		self.set("items", [])
		from erpnext.stock.get_item_details import get_item_details
		for checked_item in checked_values:
			item_line = self.append("items", {})
			price_list, price_list_currency = frappe.db.get_values("Price List", {"selling": 1}, ['name', 'currency'])[0]
			args = {
				'doctype': "Sales Invoice",
				'item_code': checked_item['item'],
				'company': self.company,
				'customer': frappe.db.get_value("Patient", self.patient, "customer"),
				'selling_price_list': price_list,
				'price_list_currency': price_list_currency,
				'plc_conversion_rate': 1.0,
				'conversion_rate': 1.0
			}
			item_details = get_item_details(args)
			item_line.item_code = checked_item['item']
			item_line.qty = 1
			if checked_item['qty']:
				item_line.qty = checked_item['qty']
			if checked_item['rate']:
				item_line.rate = checked_item['rate']
			else:
				item_line.rate = item_details.price_list_rate
			item_line.amount = float(item_line.rate) * float(item_line.qty)
			if checked_item['income_account']:
				item_line.income_account = checked_item['income_account']
			if checked_item['dt']:
				item_line.reference_dt = checked_item['dt']
			if checked_item['dn']:
				item_line.reference_dn = checked_item['dn']
			if checked_item['description']:
				item_line.description = checked_item['description']

		self.set_missing_values(for_validate = True)

	def get_discounting_status(self):
		status = None
		if self.is_discounted:
			invoice_discounting_list = frappe.db.sql("""
				select status
				from `tabInvoice Discounting` id, `tabDiscounted Invoice` d
				where
					id.name = d.parent
					and d.sales_invoice=%s
					and id.docstatus=1
					and status in ('Disbursed', 'Settled')
			""", self.name)
			for d in invoice_discounting_list:
				status = d[0]
				if status == "Disbursed":
					break
		return status

	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if flt(self.outstanding_amount) > 0 and getdate(self.due_date) < getdate(nowdate()) and self.is_discounted and self.get_discounting_status()=='Disbursed':
					self.status = "Overdue and Discounted"
				elif flt(self.outstanding_amount) > 0 and getdate(self.due_date) < getdate(nowdate()):
					self.status = "Overdue"
				elif flt(self.outstanding_amount) > 0 and getdate(self.due_date) >= getdate(nowdate()) and self.is_discounted and self.get_discounting_status()=='Disbursed':
					self.status = "Unpaid and Discounted"
				elif flt(self.outstanding_amount) > 0 and getdate(self.due_date) >= getdate(nowdate()):
					self.status = "Unpaid"
				#Check if outstanding amount is 0 due to credit note issued against invoice
				elif flt(self.outstanding_amount) <= 0 and self.is_return == 0 and frappe.db.get_value('Sales Invoice', {'is_return': 1, 'return_against': self.name, 'docstatus': 1}):
					self.status = "Credit Note Issued"
				elif self.is_return == 1:
					self.status = "Return"
				elif flt(self.outstanding_amount)<=0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set('status', self.status, update_modified = update_modified)

def validate_inter_company_party(doctype, party, company, inter_company_reference):
	if not party:
		return

	if doctype in ["Sales Invoice", "Sales Order"]:
		partytype, ref_partytype, internal = "Customer", "Supplier", "is_internal_customer"

		if doctype == "Sales Invoice":
			ref_doc = "Purchase Invoice"
		else:
			ref_doc = "Purchase Order"
	else:
		partytype, ref_partytype, internal = "Supplier", "Customer", "is_internal_supplier"

		if doctype == "Purchase Invoice":
			ref_doc = "Sales Invoice"
		else:
			ref_doc = "Sales Order"

	if inter_company_reference:
		doc = frappe.get_doc(ref_doc, inter_company_reference)
		ref_party = doc.supplier if doctype in ["Sales Invoice", "Sales Order"] else doc.customer
		if not frappe.db.get_value(partytype, {"represents_company": doc.company}, "name") == party:
			frappe.throw(_("Invalid {0} for Inter Company Transaction.").format(partytype))
		if not frappe.get_cached_value(ref_partytype, ref_party, "represents_company") == company:
			frappe.throw(_("Invalid Company for Inter Company Transaction."))

	elif frappe.db.get_value(partytype, {"name": party, internal: 1}, "name") == party:
		companies = frappe.get_all("Allowed To Transact With", fields=["company"], filters={"parenttype": partytype, "parent": party})
		companies = [d.company for d in companies]
		if not company in companies:
			frappe.throw(_("{0} not allowed to transact with {1}. Please change the Company.").format(partytype, company))

def update_linked_doc(doctype, name, inter_company_reference):

	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_field = "inter_company_invoice_reference"
	else:
		ref_field = "inter_company_order_reference"

	if inter_company_reference:
		frappe.db.set_value(doctype, inter_company_reference,\
			ref_field, name)

def unlink_inter_company_doc(doctype, name, inter_company_reference):

	if doctype in ["Sales Invoice", "Purchase Invoice"]:
		ref_doc = "Purchase Invoice" if doctype == "Sales Invoice" else "Sales Invoice"
		ref_field = "inter_company_invoice_reference"
	else:
		ref_doc = "Purchase Order" if doctype == "Sales Order" else "Sales Order"
		ref_field = "inter_company_order_reference"

	if inter_company_reference:
		frappe.db.set_value(doctype, name, ref_field, "")
		frappe.db.set_value(ref_doc, inter_company_reference, ref_field, "")

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Invoices'),
	})
	return list_context

@frappe.whitelist()
def get_bank_cash_account(mode_of_payment, company):
	account = frappe.db.get_value("Mode of Payment Account",
		{"parent": mode_of_payment, "company": company}, "default_account")
	if not account:
		frappe.throw(_("Please set default Cash or Bank account in Mode of Payment {0}")
			.format(mode_of_payment))
	return {
		"account": account
	}

@frappe.whitelist()
def make_maintenance_schedule(source_name, target_doc=None):
	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
		"Sales Invoice": {
			"doctype": "Maintenance Schedule",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Invoice Item": {
			"doctype": "Maintenance Schedule Item",
		},
	}, target_doc)

	return doclist

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = flt(source_doc.qty) - flt(source_doc.delivered_qty)
		target_doc.stock_qty = target_doc.qty * flt(source_doc.conversion_factor)

		target_doc.base_amount = target_doc.qty * flt(source_doc.base_rate)
		target_doc.amount = target_doc.qty * flt(source_doc.rate)

	doclist = get_mapped_doc("Sales Invoice", source_name, 	{
		"Sales Invoice": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Invoice Item": {
			"doctype": "Delivery Note Item",
			"field_map": {
				"name": "si_detail",
				"parent": "against_sales_invoice",
				"serial_no": "serial_no",
				"sales_order": "against_sales_order",
				"so_detail": "so_detail",
				"cost_center": "cost_center"
			},
			"postprocess": update_item,
			"condition": lambda doc: doc.delivered_by_supplier!=1
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"field_map": {
				"incentives": "incentives"
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_sales_return(source_name, target_doc=None):
	from erpnext.controllers.sales_and_purchase_return import make_return_doc
	return make_return_doc("Sales Invoice", source_name, target_doc)

def set_account_for_mode_of_payment(self):
	for data in self.payments:
		if not data.account:
			data.account = get_bank_cash_account(data.mode_of_payment, self.company).get("account")

def get_inter_company_details(doc, doctype):
	if doctype in ["Sales Invoice", "Sales Order"]:
		party = frappe.db.get_value("Supplier", {"disabled": 0, "is_internal_supplier": 1, "represents_company": doc.company}, "name")
		company = frappe.get_cached_value("Customer", doc.customer, "represents_company")
	else:
		party = frappe.db.get_value("Customer", {"disabled": 0, "is_internal_customer": 1, "represents_company": doc.company}, "name")
		company = frappe.get_cached_value("Supplier", doc.supplier, "represents_company")

	return {
		"party": party,
		"company": company
	}


def validate_inter_company_transaction(doc, doctype):

	details = get_inter_company_details(doc, doctype)
	price_list = doc.selling_price_list if doctype in ["Sales Invoice", "Sales Order"] else doc.buying_price_list
	valid_price_list = frappe.db.get_value("Price List", {"name": price_list, "buying": 1, "selling": 1})
	if not valid_price_list:
		frappe.throw(_("Selected Price List should have buying and selling fields checked."))

	party = details.get("party")
	if not party:
		partytype = "Supplier" if doctype in ["Sales Invoice", "Sales Order"] else "Customer"
		frappe.throw(_("No {0} found for Inter Company Transactions.").format(partytype))

	company = details.get("company")
	default_currency = frappe.get_cached_value('Company', company, "default_currency")
	if default_currency != doc.currency:
		frappe.throw(_("Company currencies of both the companies should match for Inter Company Transactions."))

	return

@frappe.whitelist()
def make_inter_company_purchase_invoice(source_name, target_doc=None):
	return make_inter_company_transaction("Sales Invoice", source_name, target_doc)

def make_inter_company_transaction(doctype, source_name, target_doc=None):
	if doctype in ["Sales Invoice", "Sales Order"]:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Invoice" if doctype == "Sales Invoice" else "Purchase Order"
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Sales Invoice" if doctype == "Purchase Invoice" else "Sales Order"

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")

	def update_details(source_doc, target_doc, source_parent):
		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype in ["Purchase Invoice", "Purchase Order"]:
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.buying_price_list = source_doc.selling_price_list
		else:
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.selling_price_list = source_doc.buying_price_list

	doclist = get_mapped_doc(doctype, source_name,	{
		doctype: {
			"doctype": target_doctype,
			"postprocess": update_details,
			"field_no_map": [
				"taxes_and_charges"
			]
		},
		doctype +" Item": {
			"doctype": target_doctype + " Item",
			"field_no_map": [
				"income_account",
				"expense_account",
				"cost_center",
				"warehouse"
			]
		}

	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def get_loyalty_programs(customer):
	''' sets applicable loyalty program to the customer or returns a list of applicable programs '''
	from erpnext.selling.doctype.customer.customer import get_loyalty_programs

	customer = frappe.get_doc('Customer', customer)
	if customer.loyalty_program: return

	lp_details = get_loyalty_programs(customer)

	if len(lp_details) == 1:
		frappe.db.set(customer, 'loyalty_program', lp_details[0])
		return []
	else:
		return lp_details

@frappe.whitelist()
def create_invoice_discounting(source_name, target_doc=None):
	invoice = frappe.get_doc("Sales Invoice", source_name)
	invoice_discounting = frappe.new_doc("Invoice Discounting")
	invoice_discounting.company = invoice.company
	invoice_discounting.append("invoices", {
		"sales_invoice": source_name,
		"customer": invoice.customer,
		"posting_date": invoice.posting_date,
		"outstanding_amount": invoice.outstanding_amount
	})

	return invoice_discounting
