// Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Notas de Evolucion Medico Psiquiatrica', {

    onload(frm) {
        set_vital_signs_query(frm);
    },

    refresh(frm) {
        // Aseguramos filtro por paciente en Signos Vitales
        set_vital_signs_query(frm);

        // Si ya hay paciente pero aún no se han llenado nombre/edad, los rellenamos
        if (frm.doc.patient && (!frm.doc.pat_nombre || !frm.doc.pat_edadhoy)) {
            update_patient_info(frm);
        }

        // Si ya hay signos vitales cargados en un documento existente, rellenamos datos
        if (frm.doc.signos_vitales && !frm.doc.ant_sv_pa && !frm.doc.ant_sv_peso) {
            update_vital_signs_info(frm);
        }
    },

    patient(frm) {
        if (!frm.doc.patient) {
            frm.set_value('pat_nombre', '');
            frm.set_value('pat_edadhoy', '');
            frm.set_value('signos_vitales', '');
            clear_vital_signs(frm);
            return;
        }

        // Al cambiar de paciente, actualizamos nombre y edad
        update_patient_info(frm);

        // Limpiamos signos vitales para evitar mezclar paciente anterior con el nuevo
        frm.set_value('signos_vitales', '');
        clear_vital_signs(frm);
    },

    fecha_actual(frm) {
        // Si cambian la fecha actual, recalculamos la edad
        if (frm.doc.patient) {
            update_patient_info(frm);
        }
    },

    signos_vitales(frm) {
        if (frm.doc.signos_vitales) {
            update_vital_signs_info(frm);
        } else {
            clear_vital_signs(frm);
        }
    }
});

/**
 * Filtra el Link de Signos Vitales por paciente
 */
function set_vital_signs_query(frm) {
    frm.set_query('signos_vitales', function () {
        if (!frm.doc.patient) {
            return {};
        }
        return {
            filters: {
                patient: frm.doc.patient
            }
        };
    });
}

/**
 * Trae nombre y fecha de nacimiento del Paciente, y calcula edad al día de hoy o a fecha_actual
 */
function update_patient_info(frm) {
    if (!frm.doc.patient) return;

    frappe.db.get_value('Patient', frm.doc.patient, ['patient_name', 'dob'])
        .then(r => {
            if (!r || !r.message) return;
            const { patient_name, dob } = r.message;

            if (patient_name) {
                frm.set_value('pat_nombre', patient_name);
            }

            if (dob) {
                const as_of = frm.doc.fecha_actual || frappe.datetime.get_today();
                const age_str = get_age_string(dob, as_of);
                frm.set_value('pat_edadhoy', age_str);
            } else {
                frm.set_value('pat_edadhoy', '');
            }
        });
}

/**
 * Calcula edad como “X años Y meses” entre dob y una fecha de referencia
 */
function get_age_string(dob_str, as_of_str) {
    const dob = frappe.datetime.str_to_obj(dob_str);
    const as_of = frappe.datetime.str_to_obj(as_of_str || frappe.datetime.get_today());
    if (!dob || !as_of) return '';

    let years = as_of.getFullYear() - dob.getFullYear();
    let months = as_of.getMonth() - dob.getMonth();
    const days = as_of.getDate() - dob.getDate();

    if (days < 0) {
        months -= 1;
    }
    if (months < 0) {
        years -= 1;
        months += 12;
    }

    let partes = [];
    if (years >= 0) {
        partes.push(`${years} año${years === 1 ? '' : 's'}`);
    }
    if (months > 0) {
        partes.push(`${months} mes${months === 1 ? '' : 'es'}`);
    }

    return partes.join(' ');
}

/**
 * Carga los valores del DocType “Vital Signs” hacia los campos de solo lectura
 * OJO: ajusta los nombres de campos (vs.bp, vs.pulse, etc.) según tu Vital Signs real.
 */
function update_vital_signs_info(frm) {
    if (!frm.doc.signos_vitales) return;

    frappe.db.get_doc('Vital Signs', frm.doc.signos_vitales)
        .then(vs => {
            // Ajusta estos nombres según los campos reales de tu DocType Vital Signs
            frm.set_value('ant_sv_pa',   vs.bp || vs.bp_reading || '');
            frm.set_value('ant_sv_fr',   vs.respiratory_rate || vs.rr || '');
            frm.set_value('ant_sv_fc',   vs.pulse || vs.heart_rate || '');
            frm.set_value('ant_sv_peso', vs.weight || vs.weight_kg || '');
            frm.set_value('ant_sv_talla',vs.height || vs.height_cm || '');
            frm.set_value('ant_sv_imc',  vs.bmi || vs.bmi_value || '');
        });
}

/**
 * Limpia los campos de signos vitales en la nota
 */
function clear_vital_signs(frm) {
    frm.set_value('ant_sv_pa', '');
    frm.set_value('ant_sv_fr', '');
    frm.set_value('ant_sv_fc', '');
    frm.set_value('ant_sv_peso', '');
    frm.set_value('ant_sv_talla', '');
    frm.set_value('ant_sv_imc', '');
}

