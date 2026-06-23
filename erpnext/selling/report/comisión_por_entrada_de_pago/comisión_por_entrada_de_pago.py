# Copyright (c) 2013, Frappe Technologies Pvt. Ltd.
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):

	if not filters:
		filters = {}

	columns = [
		{
			"fieldname": "sales_partner",
			"label": "Socio de ventas",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"fieldname": "payment_entry",
			"label": "Entrada Pago",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 150
		},
		{
			"fieldname": "invoice",
			"label": "Factura",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150
		},
		{
			"fieldname": "posting_date",
			"label": "Fecha Pago",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "customer",
			"label": "Cliente",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"fieldname": "grand_total",
			"label": "Total Factura",
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "allocated_amount",
			"label": "Monto Pagado",
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "total_commission",
			"label": "Comisión",
			"fieldtype": "Currency",
			"width": 130
		}
	]

	data = []

	payment_entries = frappe.get_all(
		"Payment Entry",
		fields=[
			"name",
			"posting_date",
			"company"
		],
		filters={
			"company": filters.get("company"),
			"posting_date": [
				"between",
				[
					filters.get("from_date"),
					filters.get("to_date")
				]
			],
			"docstatus": 1
		},
		order_by="posting_date asc"
	)

	grouped_data = {}

	for payment in payment_entries:

		references = frappe.get_all(
			"Payment Entry Reference",
			fields=[
				"reference_doctype",
				"reference_name",
				"allocated_amount"
			],
			filters={
				"parent": payment.name
			}
		)

		for ref in references:

			if ref.reference_doctype != "Sales Invoice":
				continue

			invoice = frappe.db.get_value(
				"Sales Invoice",
				ref.reference_name,
				[
					"name",
					"customer",
					"sales_partner",
					"grand_total",
					"commission_rate",
					"naming_series"
				],
				as_dict=True
			)

			if not invoice:
				continue

			if invoice.naming_series != filters.get("prefix"):
				continue

			sales_partner = invoice.sales_partner or "SIN SOCIO DE VENTAS"

			commission_rate = invoice.commission_rate or 0

			payment_commission = (
				(ref.allocated_amount or 0)
				* commission_rate
				/ 100
			)

			if sales_partner not in grouped_data:

				grouped_data[sales_partner] = {
					"total_facturas": 0,
					"total_pagado": 0,
					"total_commission": 0,
					"details": [],
					"invoices_counted": set()
				}

			# =====================================
			# SOLO CONTAR UNA VEZ LA FACTURA
			# =====================================

			if invoice.name not in grouped_data[sales_partner]["invoices_counted"]:

				grouped_data[sales_partner]["total_facturas"] += (
					invoice.grand_total or 0
				)

				grouped_data[sales_partner]["invoices_counted"].add(
					invoice.name
				)

			# =====================================
			# ESTOS SIEMPRE SE ACUMULAN
			# =====================================

			grouped_data[sales_partner]["total_pagado"] += (
				ref.allocated_amount or 0
			)

			grouped_data[sales_partner]["total_commission"] += (
				payment_commission
			)

			grouped_data[sales_partner]["details"].append({
				"payment_entry": payment.name,
				"invoice": invoice.name,
				"posting_date": payment.posting_date,
				"customer": invoice.customer,
				"grand_total": invoice.grand_total,
				"allocated_amount": ref.allocated_amount,
				"total_commission": payment_commission
			})

	# =====================================
	# CONSTRUIR REPORTE
	# =====================================

	grand_total_facturas = 0
	grand_total_pagado = 0
	grand_total_commission = 0

	for sales_partner in sorted(grouped_data.keys()):

		group = grouped_data[sales_partner]

		data.append({
			"indent": 0,
			"is_group": 1,
			"sales_partner": sales_partner,
			"grand_total": group["total_facturas"],
			"allocated_amount": group["total_pagado"],
			"total_commission": group["total_commission"]
		})

		for detail in group["details"]:

			data.append({
				"indent": 1,
				"payment_entry": detail["payment_entry"],
				"invoice": detail["invoice"],
				"posting_date": detail["posting_date"],
				"customer": detail["customer"],
				"grand_total": detail["grand_total"],
				"allocated_amount": detail["allocated_amount"],
				"total_commission": detail["total_commission"]
			})

		grand_total_facturas += group["total_facturas"]
		grand_total_pagado += group["total_pagado"]
		grand_total_commission += group["total_commission"]

	data.append({
		"sales_partner": "TOTAL GENERAL",
		"grand_total": grand_total_facturas,
		"allocated_amount": grand_total_pagado,
		"total_commission": grand_total_commission,
		"bold": 1
	})

	return columns, data