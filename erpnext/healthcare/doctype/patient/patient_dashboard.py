from __future__ import unicode_literals
from frappe import _

def get_data():
	return {
		'heatmap': True,
		'heatmap_message': _('This is based on transactions against this Patient. See timeline below for details'),
		'fieldname': 'patient',
		'transactions': [
			{
				'label': _('Appointments and Patient Encounters'),
				'items': ['Patient Appointment', 'Patient Encounter']
			},
			{
				'label': _('Lab Tests and Vital Signs'),
 				'items': ['Lab Test', 'Sample Collection', 'Vital Signs']
			},
			{
				'label': _('Billing'),
				'items': ['Sales Invoice']
			},
			{
				'label': _('Pastoral de la salud'),
				'items': ['General Patient Interview']
			},
			{
				'label': _('Historial Psicología'),
				'items': ['Historia Clinica Psicologia', 'Notas de Evolucion Medico Psicologia', 'Psychology Test Sheet', 'Reference and Response', 'Scanned Contracts Psycology']
			},
			{
				'label': _('Historial de Psiquiatria'),
				'items': ['Historia Clinica Psiquiatrica', 'Notas de Evolucion Medico Psiquiatrica', 'Psychiatric Examination Sheet', 'Reference and Answers Psychiatric', 'Clinical Deposit Registration']
			},
			{
				'label': _('Trabajo Social'),
				'items': ['Social Work Interview', 'Economic Social Study', 'Follow up Notes']
			},
			{
				'label': _('Enfermeria'),
				'items': ['Notes Patient', 'Deposit Registration', 'Applied medication sheet']
			}
		]
	}
