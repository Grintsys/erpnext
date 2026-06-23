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
			"label": "Vendedor",
			"fieldtype": "Data",
			"width": 250
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
			"label": "Fecha",
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
			"width": 140
		},
		{
			"fieldname": "total_commission",
			"label": "Comisión",
			"fieldtype": "Currency",
			"width": 140
		}
	]

	data = []

	conditions = []

	if filters.get("company"):
		conditions.append(
			["company", "=", filters.get("company")]
		)

	if filters.get("prefix"):
		conditions.append(
			["naming_series", "=", filters.get("prefix")]
		)

	if filters.get("from_date"):
		conditions.append(
			["posting_date", ">=", filters.get("from_date")]
		)

	if filters.get("to_date"):
		conditions.append(
			["posting_date", "<=", filters.get("to_date")]
		)

	conditions.append(
		["docstatus", "=", 1]
	)

	invoices = frappe.get_all(
		"Sales Invoice",
		fields=[
			"name",
			"posting_date",
			"customer",
			"sales_partner",
			"grand_total",
			"total_commission"
		],
		filters=conditions,
		order_by="sales_partner asc, posting_date asc"
	)

	# =====================================================
	# AGRUPAR POR VENDEDOR
	# =====================================================

	grouped_data = {}

	for invoice in invoices:

		sales_partner = invoice.sales_partner or "SIN VENDEDOR"

		if sales_partner not in grouped_data:

			grouped_data[sales_partner] = {
				"total_sales": 0,
				"total_commission": 0,
				"invoices": []
			}

		grouped_data[sales_partner]["total_sales"] += (
			invoice.grand_total or 0
		)

		grouped_data[sales_partner]["total_commission"] += (
			invoice.total_commission or 0
		)

		grouped_data[sales_partner]["invoices"].append(invoice)

	# =====================================================
	# CONSTRUIR ÁRBOL
	# =====================================================

	grand_total_sales = 0
	grand_total_commission = 0

	for sales_partner in grouped_data:

		group = grouped_data[sales_partner]

		# -----------------------------
		# FILA PADRE
		# -----------------------------

		data.append({
			"indent": 0.0,
			"sales_partner": sales_partner,
			"grand_total": group["total_sales"],
			"total_commission": group["total_commission"],
			"bold": 1
		})

		# -----------------------------
		# FACTURAS HIJAS
		# -----------------------------

		for invoice in group["invoices"]:

			data.append({
				"indent": 1.0,
				"invoice": invoice.name,
				"posting_date": invoice.posting_date,
				"customer": invoice.customer,
				"grand_total": invoice.grand_total,
				"total_commission": invoice.total_commission
			})

		grand_total_sales += group["total_sales"]
		grand_total_commission += group["total_commission"]

	# =====================================================
	# TOTAL GENERAL
	# =====================================================

	data.append({
		"sales_partner": "TOTAL GENERAL",
		"grand_total": grand_total_sales,
		"total_commission": grand_total_commission,
		"bold": 1
	})

	return columns, data