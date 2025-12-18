from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
            "label": _("Atención Médica"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Sucursal",
                    "description": _("Sucursales de clínicas.")
                },
                {
                    "type": "doctype",
                    "name": "Servicio",
                    "description": _("Servicio en clínica"),
                    "dependencies": ["Sucursal"]
                },
                {
                    "type": "doctype",
                    "name": "Unidad",
                    "description": _("Unidad que pertenece un médico."),
                    "dependencies": ["Servicio"]
                },
                {
                    "type": "doctype",
                    "name": "Profesional de salud",
                    "description": _("Lista de médicos, Enfermeros, Psicologos, entre otros."),
                    "dependencies": ["Unidad"]
                },
                {
                    "type": "doctype",
                    "name": "Cita Medica",
                    "description": _("Lista, crea y edita las citas médicas."),
                    "dependencies": ["Profesional de salud"]
                },
                {
                    "type": "doctype",
                    "name": "Preclinica",
                    "description": _("Registro de signos vitales."),
                    "dependencies": ["Cita Medica"]
                },
                {
                    "type": "doctype",
                    "name": "Posclinica",
                    "description": _("Registro de comentarios del médico."),
                    "dependencies": ["Cita Medica"]
                },
                {
                    "type": "doctype",
                    "name": "Clinica de deposito",
                    "description": _("Registro de materiales y productos utilizados o recetados en la cita médica."),
                    "dependencies": ["Cita Medica"]
                }
            ]
        },
        {
            "label": _("Configuraciones"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Tipo de cita",
                    "description": _("Lista de tipos de citas médicas.")
                },
                {
                    "type": "doctype",
                    "name": "Bloqueo de disponibilidad medica",
                    "description": _("Manejo de Bloqueo de disponibilidad medica."),
                    "dependencies": ["Profesional de salud"]
                },
            ]
        }
	]