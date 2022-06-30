# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Bankreconciliations(Document):
	def validate(self):
		if self.docstatus == 0:
			self.verificate_bank_account()
			self.delete_bank_transactions()
			self.add_bank_transactions()
			self.delete_payments()
			self.add_payments()

		if self.docstatus == 1:
			self.verificate_defference_amount()
			self.conciliation_transactions()
			self.create_reconciled_balance()
			self.modified_total_reconcilitiation_account()
			self.mark_reconciled_payment_entry()

	def on_update(self):
		self.update_amount()
		self.transit_check()
	
	def transit_check(self):
		transactions = frappe.get_all("Bank Transactions", ["*"], filters = {"status": "Transit", "check": 1})

		bank_check_transit_amount = 0

		for transaction in transactions:
			bank_check_transit_amount += transaction.amount_data

		payments = frappe.get_all("Payment Entry", ["*"], filters = {"prereconcilied": 0, "mode_of_payment": "Cheque", "company": self.company})

		for payment in payments:
			bank_check_transit_amount += payment.paid_amount
		
		self.db_set('bank_check_transit_amount', bank_check_transit_amount, update_modified=False)
	
	def update_amount(self):
		details = frappe.get_all("Bank reconciliations Table", ["amount"], filters = {"parent": self.name})

		details_payment = frappe.get_all("Bank reconciliations payment entry Table", ["amount"], filters = {"parent": self.name})

		self.transaction_amount = 0

		for detail in details:
			self.transaction_amount += detail.amount
		
		for detail_payment in details_payment:
			self.transaction_amount += detail_payment.amount

		if self.bank_amount == None:
			self.bank_amount = 0
			
		self.defference_amount = self.transaction_amount - self.bank_amount
	
	def delete_bank_transactions(self):
		transactions = frappe.get_all("Bank reconciliations Table", ["*"], filters = {"parent": self.name})

		for transaction in transactions:
			frappe.delete_doc("Bank reconciliations Table", transaction.name)

	def add_bank_transactions(self):
		transactions = frappe.get_all("Bank Transactions", ["*"], filters = {"status": "Pre-reconciled"})

		bank_check_amount = 0
		credit_note_amount = 0
		debit_note_amount = 0
		bank_deposit_amount = 0

		for transaction in transactions:
			no_document = ""	

			if transaction.check:
				no_document = transaction.no_bank_check
				bank_check_amount += transaction.amount_data
		
			if transaction.debit_note:
				no_document = transaction.next_note_nd
				debit_note_amount += transaction.amount_data

			if transaction.credit_note:
				no_document = transaction.next_note_nc
				credit_note_amount += transaction.amount_data
			
			if transaction.bank_deposit:
				no_document = transaction.document
				bank_deposit_amount += transaction.amount_data

			self.set_new_row_detail(transaction.name, no_document, transaction.transaction_data, transaction.date_data, "Pre-reconcilied", transaction.amount_data)
		
		self.db_set('bank_check_amount', bank_check_amount, update_modified=False)
		self.db_set('credit_note_amount', credit_note_amount, update_modified=False)
		self.db_set('debit_note_amount', debit_note_amount, update_modified=False)
		self.db_set('bank_deposit_amount', bank_deposit_amount, update_modified=False)

	def set_new_row_detail(self, bank_trasaction, no_document, type, date, mode, amount):
		row = self.append("detail", {})
		row.bank_trasaction = bank_trasaction
		row.no_document = no_document
		row.type = type
		row.date = date
		row.mode = mode
		row.amount = amount
	
	def delete_payments(self):
		transactions = frappe.get_all("Bank reconciliations payment entry Table", ["*"], filters = {"parent": self.name})

		for transaction in transactions:
			frappe.delete_doc("Bank reconciliations payment entry Table", transaction.name)
	
	def add_payments(self):
		payments = frappe.get_all("Payment Entry", ["*"], filters = {"prereconcilied": 1, "company": self.company})
		
		bank_check_amount = self.bank_check_amount
		wire_transfer_amount = 0

		for payment in payments:
			is_validate = False

			if payment.mode_of_payment == "Cheque":
				bank_check_amount += payment.paid_amount
				is_validate = True
			if payment.mode_of_payment == "Transferencia Bancaria":
				wire_transfer_amount += payment.paid_amount
				is_validate = True

			if is_validate:
				self.set_new_row_payments(payment.name, payment.payment_type, payment.posting_date, payment.paid_amount)
		
		self.db_set('bank_check_amount', bank_check_amount, update_modified=False)
		self.db_set('wire_transfer_amount', wire_transfer_amount, update_modified=False)
		
	def set_new_row_payments(self, payment_entry, type, date, amount):
		row = self.append("payment_entry_detail", {})
		row.payment_entry = payment_entry
		row.type = type
		row.date = date
		row.amount = amount

	def verificate_defference_amount(self):
		if self.defference_amount != 0:
			frappe.throw(_("Difference amount must be 0"))
	
	def conciliation_transactions(self):
		details = frappe.get_all("Bank reconciliations Table", ["bank_trasaction"], filters = {"parent": self.name})

		for detail in details:
			doc = frappe.get_doc("Bank Transactions", detail.bank_trasaction)
			doc.docstatus = 5
			doc.status = "Reconciled"
			doc.save()
	
	def mark_reconciled_payment_entry(self):
		details = frappe.get_all("Bank reconciliations payment entry Table", ["payment_entry"], filters = {"parent": self.name})

		for detail in details:
			doc = frappe.get_doc("Payment Entry", detail.payment_entry)
			doc.db_set('reconciled', 1, update_modified=False)
			doc.save()
	
	def create_reconciled_balance(self):
		details = frappe.get_all("Bank reconciliations Table", ["bank_trasaction", "amount"], filters = {"parent": self.name})

		transaction = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data"], filters = {"name": details[0].bank_trasaction})

		doc = frappe.new_doc("Reconciled balances")
		doc.reconciled_date = self.date
		doc.reconciled_balance = self.transaction_amount
		doc.docstatus = 1
		doc.bank_account = transaction[0].bank_account
		doc.insert()
	
	def on_cancel(self):
		frappe.throw(_("Bank reconciliation cannot be canceled"))
	
	def modified_total_reconcilitiation_account(self):
		details = frappe.get_all("Bank reconciliations Table", ["bank_trasaction", "amount"], filters = {"parent": self.name})

		transaction = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data"], filters = {"name": details[0].bank_trasaction})

		doc = frappe.get_doc("Bank Account", transaction[0].bank_account)
		doc.reconciliation_date = self.date
		doc.total_reconciliation = self.transaction_amount

		for detail in details:
			transac = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data", "amount_data"], filters = {"name": detail.bank_trasaction})
			if transac[0].transaction_data == "Bank Check" or transac[0].transaction_data== "Debit Note":
				doc.deferred_debits -= transac[0].amount_data
			else:
				doc.deferred_credits -= transac[0].amount_data
		
		doc.current_balance = doc.deferred_credits - doc.deferred_debits

		doc.save()
	
	def verificate_bank_account(self):
		details = frappe.get_all("Bank reconciliations Table", ["bank_trasaction", "amount"], filters = {"parent": self.name})

		for detail in details:
			transaction = frappe.get_all("Bank Transactions", ["bank_account", "transaction_data"], filters = {"name": detail.bank_trasaction})

			if transaction[0].bank_account != self.bank_account:
				frappe.throw(_("Bank transaction {} has a different bank account {} than the one selected".format(detail.bank_trasaction, transaction[0].bank_account)))
