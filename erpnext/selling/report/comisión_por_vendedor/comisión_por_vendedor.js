// Copyright (c) 2016, Frappe Technologies Pvt. Ltd.
// For license information, please see license.txt

frappe.query_reports["Comisión por vendedor"] = {
	"filters": [
		{
			fieldname:"company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1
		},
		{
			fieldname:"prefix",
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
			fieldname:"to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1
		}
	]
};