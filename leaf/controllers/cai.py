import frappe
from frappe.utils import getdate, nowdate, date_diff, cint

def check_cai_expiry_alerts():
    """
    Daily scheduled task to check all CAIs and send email alerts
    from leaf@grintsys.com to alert_email (e.g. info@grintsys.com).
    Evaluates both Expired Days (date deadline) and Expired Amount (correlative count).
    """
    today = getdate(nowdate())
    cais = frappe.get_all("CAI", filters={"docstatus": ["!=", 2]}, fields=["name"])

    for cai_entry in cais:
        doc = frappe.get_doc("CAI", cai_entry.name)
        if not getattr(doc, "alert_email", None):
            continue

        # 1. Días restantes por fecha límite de emisión
        deadline = getdate(doc.issue_deadline) if doc.issue_deadline else None
        days_left = date_diff(deadline, today) if deadline else 999
        expired_days_limit = cint(getattr(doc, "expired_days", 30) or 30)

        # 2. Correlativos restantes por rango autorizado
        series_prefix = (doc.prefix or "").split(".")[0]
        current_seq = 0
        if series_prefix:
            res = frappe.db.sql("SELECT current FROM tabSeries WHERE name = %s", series_prefix)
            if res:
                current_seq = cint(res[0][0])
        final_num = cint(doc.final_number or 0)
        remaining_qty = max(0, final_num - current_seq)
        expired_qty_limit = cint(getattr(doc, "expired_amount", 100) or 100)

        # Trigger alert condition if days left <= expired_days OR remaining qty <= expired_amount
        if days_left <= expired_days_limit or (final_num > 0 and remaining_qty <= expired_qty_limit):
            send_cai_alert_email(doc, days_left, remaining_qty)

    frappe.db.commit()


def send_cai_alert_email(doc, days_left=0, remaining_qty=0):
    recipients = [e.strip() for e in (getattr(doc, "alert_email", "") or "").replace("\n", ",").split(",") if e.strip()]
    if not recipients:
        return

    subject = f"[ALERTA LEAF CAI] Notificación de CAI ({doc.status}): {getattr(doc, 'name_cai', doc.name)}"
    
    html_message = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; max-width: 600px;">
        <h2 style="color: #d9534f;">Alerta de Vencimiento / Agotamiento de CAI (SAR Honduras)</h2>
        <p>Se ha detectado una notificación para el documento de autorización fiscal registrado en <strong>LEAF ERP</strong>:</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Nombre CAI:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{getattr(doc, 'name_cai', doc.name)}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Código CAI (SAR):</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{doc.cai or 'N/A'}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Prefijo / Serie:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{doc.prefix or 'N/A'}</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Fecha Límite de Emisión:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{doc.issue_deadline or 'N/A'} (Días restantes: <strong>{days_left}</strong> | Límite aviso: {getattr(doc, 'expired_days', 30)} días)</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Rango Autorizado:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;">{doc.initial_number} al {doc.final_number} (Restantes: <strong style="color: #d9534f;">{remaining_qty}</strong> | Límite aviso: {getattr(doc, 'expired_amount', 100)})</td></tr>
            <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Estado Actual:</strong></td><td style="padding: 8px; border-bottom: 1px solid #eee;"><span style="background-color: #f0ad4e; color: white; padding: 3px 8px; border-radius: 4px;">{doc.status}</span></td></tr>
        </table>
        <p style="margin-top: 20px;"><strong>Acción Requerida:</strong> Iniciar el trámite de la nueva resolución de autorización CAI ante la SAR Honduras para evitar la interrupción de la facturación.</p>
        <hr style="margin-top: 20px; border: 0; border-top: 1px solid #e0e0e0;" />
        <p style="font-size: 12px; color: #777;">Mensaje generado automáticamente por LEAF ERP desde <code>leaf@grintsys.com</code>.</p>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=html_message,
        sender="leaf@grintsys.com"
    )
