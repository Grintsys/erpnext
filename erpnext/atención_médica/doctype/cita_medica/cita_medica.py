# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, msgprint, throw

class CitaMedica(Document):
	def validate(self):
		self.checkDoctorBlock()

	def checkDoctorBlock(self):
		blocks = frappe.get_all("Bloqueo de disponibilidad medica",["*"], filters = {"profesional": self.profesional, "date": self.appointment_date})

		if(len(blocks) > 0):
			frappe.throw(_("El doctor no esta disponible en esta fecha."))

		blocks = frappe.get_all(
			"Holiday List",
			fields=["*"],
			filters=[
				["from_date", "<=", self.appointment_date],
				["to_date", ">=", self.appointment_date],
			]
		)
		
		if(len(blocks) > 0):
			frappe.throw(_("Esa fecha es festiva ({})".format(blocks[0].name)))
