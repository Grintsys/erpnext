frappe.views.calendar["Cita Medica"] = {
	field_map: {
		start: "appointment_date",
		end: "appointment_date",
		start_time: "start_hour",
		end_time: "end_hour",
		title: "patient",
		allDay: false
	},

	// Filtros visibles en el calendario
	filters: [
		{
			fieldtype: "Link",
			fieldname: "user_id",
			options: "User",
			label: __("Doctor"),
			default: frappe.session.user   // 👈 aquí la magia
		}
	]
};
