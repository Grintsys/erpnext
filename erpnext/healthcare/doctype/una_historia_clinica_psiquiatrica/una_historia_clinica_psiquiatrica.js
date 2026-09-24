// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('UNA Historia Clinica Psiquiatrica', {
	onload(frm) {
		set_vital_signs_query(frm);
		if (frm.doc.patient) {
			hydrate_patient_info(frm);
		}
	},

	refresh(frm) {
		set_vital_signs_query(frm);
		render_patient_info(frm);
		load_vital_signs(frm);
	},

	patient(frm) {
		frm.set_value('buscar', null);
		frm.__una_patient_cache = null;
		render_patient_info(frm);
		render_vital_signs(frm, null);
		frm.set_value('pat_edadhoy', null);

		if (frm.doc.patient) {
			hydrate_patient_info(frm);
		} else {
			return;
		}
	},

	buscar(frm) {
		load_vital_signs(frm);
	},

	fecha(frm) {
		recalculate_patient_age(frm);
	},

	before_save(frm) {
		recalculate_patient_age(frm);
	}
});

function set_vital_signs_query(frm) {
	frm.set_query('buscar', () => ({
		filters: {
			patient: frm.doc.patient || '__never__'
		}
	}));
}

function hydrate_patient_info(frm) {
	frappe.db.get_value('Patient', frm.doc.patient, [
		'patient_name',
		'nickname',
		'dob',
		'sex',
		'pac_estado',
		'pac_raza',
		'pac_religion',
		'pac_escolaridad',
		'pac_ocupacion',
		'pac_pais',
		'pac_departamento',
		'pac_ciudad',
		'pac_acompa',
		'pac_parentesco',
		'nacimiento',
		'cologne',
		'mobile'
	]).then(response => {
		frm.__una_patient_cache = (response && response.message) || {};
		recalculate_patient_age(frm);
		render_patient_info(frm);
	});
}

function load_vital_signs(frm) {
	if (!frm.doc.buscar) {
		render_vital_signs(frm, null);
		return;
	}

	frappe.db.get_value('Vital Signs', frm.doc.buscar, [
		'bp',
		'respiratory_rate',
		'pulse',
		'weight',
		'height',
		'bmi',
		'bp_systolic',
		'bp_diastolic',
		'signs_date',
		'signs_time',
		'patient'
	]).then(response => {
		const vital_signs = (response && response.message) || {};

		if (frm.doc.patient && vital_signs.patient && vital_signs.patient !== frm.doc.patient) {
			frappe.msgprint(__('El registro de Signos Vitales no corresponde al paciente seleccionado.'));
			frm.set_value('buscar', null);
			render_vital_signs(frm, null);
			return;
		}

		render_vital_signs(frm, vital_signs);
	});
}

function recalculate_patient_age(frm) {
	const patient = frm.__una_patient_cache || {};
	const dob = patient.dob;

	if (!dob) {
		frm.set_value('pat_edadhoy', null);
		return;
	}

	const birth = frappe.datetime.str_to_obj(dob);
	const base = frappe.datetime.str_to_obj(frm.doc.fecha || frappe.datetime.get_today());
	let years = base.getFullYear() - birth.getFullYear();
	let months = base.getMonth() - birth.getMonth();

	if (base.getDate() < birth.getDate()) {
		months -= 1;
	}
	if (months < 0) {
		years -= 1;
		months += 12;
	}
	if (years < 0) {
		years = 0;
		months = 0;
	}

	frm.set_value(
		'pat_edadhoy',
		`${years} ${years === 1 ? 'año' : 'años'} ${months} ${months === 1 ? 'mes' : 'meses'}`
	);
}

function render_patient_info(frm) {
	const field = frm.get_field('pat_info_html');
	if (!field) return;

	const patient = frm.__una_patient_cache || {};
	const rows = [
		['Nombre', patient.patient_name],
		['Dime', patient.nickname],
		['Sexo', patient.sex],
		['Estado civil', patient.pac_estado],
		['Raza', patient.pac_raza],
		['Religión', patient.pac_religion],
		['Escolaridad', patient.pac_escolaridad],
		['Ocupación', patient.pac_ocupacion],
		['País', patient.pac_pais],
		['Departamento', patient.pac_departamento],
		['Municipio', patient.pac_ciudad],
		['Acompañante', patient.pac_acompa],
		['Parentesco', patient.pac_parentesco],
		['Lugar de nacimiento', patient.nacimiento],
		['Dirección', patient.cologne],
		['Móvil', patient.mobile]
	];

	field.$wrapper.html(`
		<div class="form-grid">
			<table class="table table-bordered table-condensed">
				<tbody>
					${rows.map(([label, value]) => value ?
						`<tr><th style="width:30%">${label}</th><td>${frappe.utils.escape_html(String(value))}</td></tr>` :
						'').join('')}
				</tbody>
			</table>
		</div>`
	);
}

function render_vital_signs(frm, vital_signs) {
	const field = frm.get_field('pat_sv_html');
	if (!field) return;

	const data = vital_signs || {};
	let blood_pressure = data.bp;
	if (!blood_pressure && data.bp_systolic && data.bp_diastolic) {
		blood_pressure = `${data.bp_systolic}/${data.bp_diastolic} mmHg`;
	}

	const rows = [
		['Fecha', data.signs_date],
		['Hora', data.signs_time],
		['P/A', blood_pressure],
		['FR', data.respiratory_rate],
		['FC', data.pulse],
		['Peso', data.weight],
		['Talla', data.height],
		['IMC', data.bmi]
	];

	field.$wrapper.html(`
		<div class="form-grid">
			<table class="table table-bordered table-condensed">
				<tbody>
					${rows.map(([label, value]) => value ?
						`<tr><th style="width:30%">${label}</th><td>${frappe.utils.escape_html(String(value))}</td></tr>` :
						'').join('')}
				</tbody>
			</table>
		</div>`
	);
}
