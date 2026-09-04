# Copyright (c) 2013, Frappe Technologies Pvt. Ltd.
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils import nowdate, date_diff


def execute(filters=None):
    if not filters:
        filters = {}

    columns = [
		{
			"fieldname": "customer",
			"label": "Cliente",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 220
		},
		{
			"fieldname": "sales_partner",
			"label": "Socio de Ventas",
			"fieldtype": "Link",
			"options": "Sales Partner",
			"width": 180
		},
		{
			"fieldname": "posting_date",
			"label": "Fecha de Factura",
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "invoice",
			"label": "Número de Comprobante",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 180
		},
		{
			"fieldname": "grand_total",
			"label": "Cantidad Facturada",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "paid_amount",
			"label": "Cantidad Pagada",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "outstanding_amount",
			"label": "Monto Pendiente",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "days",
			"label": "Días",
			"fieldtype": "Int",
			"width": 80
		}
	]

    invoice_filters = {
        "company": filters.get("company"),
        "posting_date": [
            "between",
            [
                filters.get("from_date"),
                filters.get("to_date")
            ]
        ],
        "docstatus": 1,
        "outstanding_amount": [">", 0]
    }

    invoices = frappe.get_all(
        "Sales Invoice",
        fields=[
            "name",
            "posting_date",
            "customer",
            "grand_total",
            "paid_amount",
            "outstanding_amount",
            "naming_series"
        ],
        filters=invoice_filters,
        order_by="customer asc, posting_date asc"
    )

    grouped_data = {}

    for invoice in invoices:

        if filters.get("prefix") and invoice.naming_series != filters.get("prefix"):
            continue

        sales_partner = frappe.db.get_value(
            "Customer",
            invoice.customer,
            "default_sales_partner"
        )

        customer = invoice.customer

        if customer not in grouped_data:
            grouped_data[customer] = {
                "sales_partner": sales_partner,
                "total_facturado": 0,
                "total_pagado": 0,
                "total_pendiente": 0,
                "details": []
            }

        grouped_data[customer]["total_facturado"] += invoice.grand_total or 0
        grouped_data[customer]["total_pagado"] += invoice.paid_amount or 0
        grouped_data[customer]["total_pendiente"] += invoice.outstanding_amount or 0

        grouped_data[customer]["details"].append({
            "posting_date": invoice.posting_date,
            "invoice": invoice.name,
            "grand_total": invoice.grand_total,
            "paid_amount": invoice.paid_amount,
            "outstanding_amount": invoice.outstanding_amount,
            "days": date_diff(nowdate(), invoice.posting_date)
        })

    data = []

    total_facturado = 0
    total_pagado = 0
    total_pendiente = 0

    for customer in sorted(grouped_data.keys()):

        group = grouped_data[customer]

        data.append({
            "indent": 0,
            "is_group": 1,
            "customer": customer,
            "sales_partner": group["sales_partner"],
            "grand_total": group["total_facturado"],
            "paid_amount": group["total_pagado"],
            "outstanding_amount": group["total_pendiente"]
        })

        for d in group["details"]:

            data.append({
                "indent": 1,
                "posting_date": d["posting_date"],
                "customer": customer,
                "sales_partner": group["sales_partner"],
                "invoice": d["invoice"],
                "grand_total": d["grand_total"],
                "paid_amount": d["paid_amount"],
                "outstanding_amount": d["outstanding_amount"],
                "days": d["days"]
            })

        total_facturado += group["total_facturado"]
        total_pagado += group["total_pagado"]
        total_pendiente += group["total_pendiente"]

    data.append({
        "customer": "TOTAL GENERAL",
        "grand_total": total_facturado,
        "paid_amount": total_pagado,
        "outstanding_amount": total_pendiente,
        "bold": 1
    })

    return columns, data