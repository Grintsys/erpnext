# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class PriceListSchedule(Document):
	def validate(self):
		price_list_schedule = frappe.get_all("Price List Schedule", ["name"])

		if len(price_list_schedule) > 0 and price_list_schedule[0].name != self.name:
			frappe.throw(_("A price list schedule already exists."))