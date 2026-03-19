frappe.views.calendar["Cita Medica"] = {
	field_map: {
		start: "start_datetime",
		end: "end_datetime",
		title: "patient",
		id: "name",
		allDay: "all_day",
		color: "color"
	},

	filters: [
		{
			fieldtype: "Link",
			fieldname: "user_id",
			options: "User",
			label: __("Doctor"),
			default: frappe.session.user
		}
	],

	get_events_method: "frappe.desk.calendar.get_events"
};