import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_custom_fields():
    # Remove unwanted custom fields on CAI to restore standard look
    unwanted_fields = [
        "company", "branch", "pos_profile", "establishment",
        "emission_point", "doc_type_code", "current_sequence",
        "remaining_sequence", "days_before_expiry_alert", "remaining_qty_alert"
    ]
    for fieldname in unwanted_fields:
        if frappe.db.exists("Custom Field", f"CAI-{fieldname}"):
            frappe.delete_doc("Custom Field", f"CAI-{fieldname}", force=True)

    # Delete property setters created for CAI
    frappe.db.sql("DELETE FROM `tabProperty Setter` WHERE doc_type = 'CAI'")
    frappe.db.commit()

    # Add only the requested alert_email custom field with clean description
    custom_fields = {
        "CAI": [
            {
                "fieldname": "alert_email",
                "label": "Correo Electrónico de Alerta",
                "fieldtype": "Small Text",
                "insert_after": "status",
                "description": "Correo para informar el estatus del CAI según su fecha o numeración de aviso (ej: info@grintsys.com)."
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()
