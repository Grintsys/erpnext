// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Products Solds By Item Category Annual"] = {
	"filters": [
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Int",
			"default": new Date().getFullYear(),
			"reqd": 1
		},
		{
			"fieldname":"prefix",
			"label": __("Prefix"),
			"fieldtype": "Link",
			"options": "Prefix sales for days",
			"reqd": 1
		},
		{
			"fieldname":"user",
			"label": __("User"),
			"fieldtype": "Link",
			"options": "User"
		}
	]
};