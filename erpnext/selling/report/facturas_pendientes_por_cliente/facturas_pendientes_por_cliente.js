// Copyright (c) 2016, Frappe Technologies Pvt. Ltd.
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Facturas pendientes por cliente"] = {

    "tree": true,
    "name_field": "customer",
    "parent_field": "parent_customer",
    "initial_depth": 1,

    "filters": [

        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1
        },

        {
            fieldname: "prefix",
            label: __("Prefix"),
            fieldtype: "Link",
            options: "Prefix sales for days",
            reqd: 1
        },

        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1
        },

        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1
        }

    ]

};