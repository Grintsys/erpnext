# -*- coding: utf-8 -*-

import frappe
from frappe import _


@frappe.whitelist()
def get_appointments(appointment_date=None, status=None, search=None):

    # ==========================================================
    # USUARIO ACTUAL
    # ==========================================================

    user = frappe.session.user

    # ==========================================================
    # BUSCAR PROFESIONAL ASOCIADO AL USUARIO
    # ==========================================================

    professionals = frappe.get_all(
        "Healthcare Practitioner",
        filters={
            "user_id": user
        },
        fields=[
            "name"
        ]
    )

    if not professionals:
        frappe.throw(
            _("El usuario actual no está asociado a un profesional médico.")
        )

    professional = professionals[0]

    # ==========================================================
    # CONDICIONES
    # ==========================================================

    conditions = [
        "cm.profesional = %(professional)s"
    ]

    values = {
        "professional": professional.name
    }

    # ==========================================================
    # FILTRO FECHA
    # ==========================================================

    if appointment_date:

        conditions.append(
            "cm.appointment_date = %(appointment_date)s"
        )

        values["appointment_date"] = appointment_date

    # ==========================================================
    # FILTRO ESTADO
    # ==========================================================

    if status and status != "Todos":

        conditions.append(
            "cm.status = %(status)s"
        )

        values["status"] = status

    # ==========================================================
    # BUSQUEDA PACIENTE
    # ==========================================================

    if search:

        conditions.append(
            """
            (
                cm.patient LIKE %(search)s
                OR p.patient_name LIKE %(search)s
            )
            """
        )

        values["search"] = "%" + search + "%"

    # ==========================================================
    # CONSULTA
    # ==========================================================

    appointments = frappe.db.sql(
        """
        SELECT
            cm.name,
            cm.patient,
            p.patient_name,

            cm.branch,
            cm.service,
            cm.unit,

            cm.profesional,
            cm.appointment_type,

            cm.register_date,
            cm.appointment_date,

            cm.start_hour,
            cm.end_hour,

            cm.status,
            cm.observations,

            cm.start_datetime,
            cm.end_datetime

        FROM `tabCita Medica` cm

        LEFT JOIN `tabPatient` p
            ON p.name = cm.patient

        WHERE {conditions}

        ORDER BY
            cm.start_hour ASC,
            cm.appointment_date ASC
        """.format(
            conditions=" AND ".join(conditions)
        ),
        values,
        as_dict=True
    )

    # ==========================================================
    # RESPUESTA
    # ==========================================================

    return {
        "user": user,

        "professional": {
            "name": professional.name
        },

        "appointments": appointments,

        "total": len(appointments)
    }