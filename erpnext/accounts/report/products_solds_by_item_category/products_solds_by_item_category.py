# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):

	if not filters:
		filters = {}

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
			"fieldname": "total_product",
			"fieldtype": "Currency",
			"label": "Unit Price",
			"width": 120
		},
		{
			"fieldname": "product_description",
			"fieldtype": "Data",
			"label": "Description",
			"width": 180
		},
		{
			"fieldname": "quantity",
			"fieldtype": "Float",
			"label": "Quantity",
			"width": 120
		},
		{
			"fieldname": "total_price",
			"fieldtype": "Currency",
			"label": "TOTAL",
			"width": 140
		}
	]

	data = []

	# ======================================================
	# FILTROS
	# ======================================================

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")

	conditions = get_conditions(filters, from_date, to_date)

	# ======================================================
	# FACTURAS
	# ======================================================

	sales_invoices = frappe.get_all(
		"Sales Invoice",
		fields=["name"],
		filters=conditions
	)

	# ======================================================
	# OBTENER ITEMS
	# ======================================================

	products = []

	for sale_invoice in sales_invoices:

		products_list = frappe.get_all(
			"Sales Invoice Item",
			fields=[
				"item_group",
				"item_name",
				"rate",
				"description",
				"qty"
			],
			filters={
				"parent": sale_invoice.name
			}
		)

		products.extend(products_list)

	# ======================================================
	# AGRUPAR
	# Categoria -> Producto
	# ======================================================

	grouped_data = {}

	for product in products:

		item_group = product.item_group or "NO CATEGORY"
		product_name = product.item_name or "NO PRODUCT"

		# Crear categoria
		if item_group not in grouped_data:

			grouped_data[item_group] = {
				"products": {},
				"total_qty": 0,
				"total_amount": 0
			}

		# Crear producto
		if product_name not in grouped_data[item_group]["products"]:

			grouped_data[item_group]["products"][product_name] = {
				"item_name": product.item_name,
				"description": product.description,
				"rate": product.rate,
				"qty": 0,
				"amount": 0
			}

		# ==================================================
		# ACUMULAR
		# ==================================================

		grouped_data[item_group]["products"][product_name]["qty"] += product.qty or 0

		# recalcular total
		total_qty = grouped_data[item_group]["products"][product_name]["qty"]
		rate = grouped_data[item_group]["products"][product_name]["rate"]

		grouped_data[item_group]["products"][product_name]["amount"] = total_qty * rate

	# ======================================================
	# CALCULAR TOTALES POR CATEGORIA
	# ======================================================

	for item_group in grouped_data:

		total_qty = 0
		total_amount = 0

		for product_name in grouped_data[item_group]["products"]:

			product = grouped_data[item_group]["products"][product_name]

			total_qty += product["qty"]
			total_amount += product["amount"]

		grouped_data[item_group]["total_qty"] = total_qty
		grouped_data[item_group]["total_amount"] = total_amount

	# ======================================================
	# CONSTRUIR REPORTE
	# ======================================================

	grand_total_qty = 0
	grand_total_amount = 0

	for item_group in grouped_data:

		group = grouped_data[item_group]

		# ==================================================
		# LINEA CATEGORIA
		# ==================================================

		data.append({
			"indent": 0.0,
			"category": item_group,
			"quantity": group["total_qty"],
			"total_price": group["total_amount"],
			"bold": 1
		})

		# ==================================================
		# PRODUCTOS
		# ==================================================

		for product_name in group["products"]:

			product = group["products"][product_name]

			data.append({
				"indent": 1.0,
				"category": "",
				"product": product["item_name"],
				"total_product": product["rate"],
				"product_description": product["description"],
				"quantity": product["qty"],
				"total_price": product["amount"]
			})

		grand_total_qty += group["total_qty"]
		grand_total_amount += group["total_amount"]

	# ======================================================
	# GRAND TOTAL
	# ======================================================

	data.append({
		"category": "GRAND TOTAL",
		"quantity": grand_total_qty,
		"total_price": grand_total_amount,
		"bold": 1
	})

	return columns, data


def get_conditions(filters, from_date, to_date):

	conditions = {
		"posting_date": ["between", [from_date, to_date]],
		"naming_series": filters.get("prefix")
	}

	if filters.get("user"):
		conditions["cashier"] = filters.get("user")

	return conditions