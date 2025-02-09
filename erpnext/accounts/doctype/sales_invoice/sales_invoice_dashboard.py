from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'fieldname': 'sales_invoice',
		'non_standard_fieldnames': {
			'Delivery Note': 'against_sales_invoice',
			'Journal Entry': 'reference_name',
			'Payment Entry': 'reference_name',
			'Credit Note CXC': 'reference_name',
			'Customer Retention': 'reference_name',
			'Payment Request': 'reference_name',
			'Sales Invoice': 'return_against',
			'Auto Repeat': 'reference_document',
		},
		'internal_links': {
			'Sales Order': ['items', 'sales_order']
		},
		'transactions': [
			{
				'label': _('Payment'),
				'items': ['Payment Entry', 'Payment Request', 'Journal Entry', 'Invoice Discounting']
			},
			{
				'label': _('Reference'),
				'items': ['Timesheet', 'Delivery Note', 'Sales Order', 'Work Order Invoice']
			},
			{
				'label': _('Returns'),
				'items': ['Sales Invoice', 'Credit Note CXC']
			},
			{
				'label': _('Subscription'),
				'items': ['Auto Repeat']
			},
			{
				'label': _('Retention'),
				'items': ['Customer Retention']
			},
		]
	}