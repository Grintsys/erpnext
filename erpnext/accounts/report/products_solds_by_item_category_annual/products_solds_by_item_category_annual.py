# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import datetime


def execute(filters=None):

	if not filters:
		filters = {}

	# ======================================================
	# COLUMNAS
	# ======================================================

	columns = [
		{
			"fieldname": "category",
			"fieldtype": "Data",
			"label": "Category",
			"width": 220
		},
		{
			"fieldname": "product",
			"fieldtype": "Data",
			"label": "Product",
			"width": 300
		},
		{
			"fieldname": "jan",
			"fieldtype": "Float",
			"label": "Enero",
			"width": 90
		},
		{
			"fieldname": "feb",
			"fieldtype": "Float",
			"label": "Febrero",
			"width": 90
		},
		{
			"fieldname": "mar",
			"fieldtype": "Float",
			"label": "Marzo",
			"width": 90
		},
		{
			"fieldname": "apr",
			"fieldtype": "Float",
			"label": "Abril",
			"width": 90
		},
		{
			"fieldname": "may",
			"fieldtype": "Float",
			"label": "Mayo",
			"width": 90
		},
		{
			"fieldname": "jun",
			"fieldtype": "Float",
			"label": "Junio",
			"width": 90
		},
		{
			"fieldname": "jul",
			"fieldtype": "Float",
			"label": "Julio",
			"width": 90
		},
		{
			"fieldname": "aug",
			"fieldtype": "Float",
			"label": "Agosto",
			"width": 90
		},
		{
			"fieldname": "sep",
			"fieldtype": "Float",
			"label": "Septiembre",
			"width": 90
		},
		{
			"fieldname": "oct",
			"fieldtype": "Float",
			"label": "Octubre",
			"width": 90
		},
		{
			"fieldname": "nov",
			"fieldtype": "Float",
			"label": "Noviembre",
			"width": 90
		},
		{
			"fieldname": "dec",
			"fieldtype": "Float",
			"label": "Diciembre",
			"width": 90
		},
		{
			"fieldname": "total",
			"fieldtype": "Float",
			"label": "Total",
			"width": 120
		}
	]

	data = []

	# ======================================================
	# FILTROS
	# ======================================================

	year = filters.get("year")

	from_date = f"{year}-01-01"
	to_date = f"{year}-12-31"

	conditions = [
		["posting_date", ">=", from_date],
		["posting_date", "<=", to_date],
		["naming_series", "=", filters.get("prefix")],
		["docstatus", "=", 0]
	]

	if filters.get("user"):
		conditions.append(
			["cashier", "=", filters.get("user")]
		)

	sales_invoices = frappe.get_all(
		"Sales Invoice",
		fields=["name", "posting_date"],
		filters=conditions
)

	# ======================================================
	# AGRUPAR DATA
	# Categoria -> Producto -> Mes
	# ======================================================

	grouped_data = {}

	month_fields = {
		1: "jan",
		2: "feb",
		3: "mar",
		4: "apr",
		5: "may",
		6: "jun",
		7: "jul",
		8: "aug",
		9: "sep",
		10: "oct",
		11: "nov",
		12: "dec"
	}

	# ======================================================
	# RECORRER FACTURAS
	# ======================================================

	for invoice in sales_invoices:

		month = invoice.posting_date.month

		products = frappe.get_all(
			"Sales Invoice Item",
			fields=[
				"item_group",
				"item_name",
				"qty"
			],
			filters={
				"parent": invoice.name
			}
		)

		for product in products:

			item_group = product.item_group or "NO CATEGORY"
			product_name = product.item_name or "NO PRODUCT"

			# ==============================================
			# CREAR CATEGORIA
			# ==============================================

			if item_group not in grouped_data:

				grouped_data[item_group] = {
					"products": {},
					"totals": init_months()
				}

			# ==============================================
			# CREAR PRODUCTO
			# ==============================================

			if product_name not in grouped_data[item_group]["products"]:

				grouped_data[item_group]["products"][product_name] = init_months()

			# ==============================================
			# ACUMULAR MES
			# ==============================================

			month_field = month_fields.get(month)

			qty = product.qty or 0

			grouped_data[item_group]["products"][product_name][month_field] += qty
			grouped_data[item_group]["products"][product_name]["total"] += qty

			grouped_data[item_group]["totals"][month_field] += qty
			grouped_data[item_group]["totals"]["total"] += qty

	# ======================================================
	# CONSTRUIR DATA
	# ======================================================

	grand_totals = init_months()

	for item_group in grouped_data:

		group = grouped_data[item_group]

		# ==============================================
		# FILA CATEGORIA
		# ==============================================

		category_row = {
			"indent": 0.0,
			"category": item_group,
			"bold": 1
		}

		category_row.update(group["totals"])

		data.append(category_row)

		# ==============================================
		# PRODUCTOS
		# ==============================================

		for product_name in group["products"]:

			product_data = group["products"][product_name]

			product_row = {
				"indent": 1.0,
				"category": "",
				"product": product_name
			}

			product_row.update(product_data)

			data.append(product_row)

		# ==============================================
		# GRAND TOTAL
		# ==============================================

		for key in grand_totals:
			grand_totals[key] += group["totals"][key]

	# ======================================================
	# FILA TOTAL GENERAL
	# ======================================================

	total_row = {
		"category": "GRAND TOTAL",
		"bold": 1
	}

	total_row.update(grand_totals)

	data.append(total_row)

	return columns, data


# ==========================================================
# INICIALIZAR MESES
# ==========================================================

def init_months():

	return {
		"jan": 0,
		"feb": 0,
		"mar": 0,
		"apr": 0,
		"may": 0,
		"jun": 0,
		"jul": 0,
		"aug": 0,
		"sep": 0,
		"oct": 0,
		"nov": 0,
		"dec": 0,
		"total": 0
	}