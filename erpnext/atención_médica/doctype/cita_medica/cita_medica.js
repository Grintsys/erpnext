frappe.ui.form.on('Cita Medica', {
	validate(frm) {
		if (frm.doc.appointment_date && frm.doc.start_hour) {
			frm.doc.start_datetime = frappe.datetime.get_datetime_as_string(
				`${frm.doc.appointment_date} ${frm.doc.start_hour}`
			);
		}

		if (frm.doc.appointment_date && frm.doc.end_hour) {
			frm.doc.end_datetime = frappe.datetime.get_datetime_as_string(
				`${frm.doc.appointment_date} ${frm.doc.end_hour}`
			);
		}
	}
});