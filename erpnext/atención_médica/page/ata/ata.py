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

    professional = frappe.get_value(
        "Healthcare Practitioner",
        {
            "user_id": user
        },
        "name"
    )

    if not professional:
        frappe.throw(
            _(
                "El usuario actual no está asociado "
                "a un profesional médico."
            )
        )

    # ==========================================================
    # CONDICIONES
    # ==========================================================

    conditions = [
        "cm.profesional = %(professional)s"
    ]

    values = {
        "professional": professional
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
    # ATA SOLO MANEJA:
    # Pendiente
    # Atendido
    # ==========================================================

    if status:

        if status not in ["Pendiente", "Atendido"]:

            frappe.throw(
                _("Estado no válido para ATA.")
            )

        conditions.append(
            "cm.status = %(status)s"
        )

        values["status"] = status

    # ==========================================================
    # BUSQUEDA DE PACIENTE
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
    #
    # Usamos una subconsulta para obtener solamente una receta
    # asociada a la cita y evitar duplicar la cita en caso de que
    # existan varias recetas.
    #
    # La lógica de ATA considera:
    #
    # 1 Cita -> 0 o 1 receta activa
    #
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

            cm.end_datetime,

            (
                SELECT rm.name
                FROM `tabReceta Medica` rm
                WHERE rm.cita_medica = cm.name
                  AND rm.docstatus < 2
                ORDER BY rm.creation DESC
                LIMIT 1
            ) AS receta_name

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

        "professional": professional,

        "appointments": appointments,

        "total": len(appointments)

    }