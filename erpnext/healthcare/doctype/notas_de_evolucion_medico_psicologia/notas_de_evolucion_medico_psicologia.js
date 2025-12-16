// Notas de Evolucion Medico Psicologia – Client Script
// ---------------------------------------------------
// - Calcula y muestra edad actual del paciente.
// - Filtra y carga Signos Vitales del paciente.
// - Permite elegir manualmente Historia Clinica Psicologia (doctype_psicologia)
//   y al seleccionar, carga los datos en las secciones de solo lectura (hist_*).
// - No sugiere automáticamente “la última” Historia Clínica.

frappe.ui.form.on('Notas de Evolucion Medico Psicologia', {

    onload(frm) {
        set_vital_signs_query(frm);
        set_hcpsico_query(frm);

        if (frm.doc.patient) {
            update_patient_info(frm);
        }
    },

    refresh(frm) {
        set_vital_signs_query(frm);
        set_hcpsico_query(frm);

        if (frm.doc.patient && (!frm.doc.pat_nombre || !frm.doc.pat_edadhoy)) {
            update_patient_info(frm);
        }

        // Si ya hay signos vitales y campos vacíos, rellenarlos
        if (frm.doc.signos_vitales && !frm.doc.ant_sv_pa && !frm.doc.ant_sv_peso) {
            update_vital_signs_info(frm);
        }

        // Tablas históricas (hist_*) solo lectura
        make_history_tables_read_only(frm);
    },

    patient(frm) {
        if (!frm.doc.patient) {
            // limpiar todo si se borra paciente
            frm.set_value('pat_nombre', '');
            frm.set_value('pat_edadhoy', '');
            frm.set_value('signos_vitales', '');
            clear_vital_signs(frm);

            clear_historia_clinica_section(frm);
            return;
        }

        // Datos del paciente (nombre + edad)
        update_patient_info(frm);

        // Limpiar signos vitales y sección histórica
        frm.set_value('signos_vitales', '');
        clear_vital_signs(frm);

        clear_historia_clinica_section(frm);
    },

    fecha_actual(frm) {
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
    },

    // Al elegir manualmente una Historia Clínica de Psicología
    doctype_psicologia(frm) {
        if (!frm.doc.doctype_psicologia) {
            clear_historia_clinica_section(frm);
            return;
        }
        load_hcpsico_into_fields(frm, frm.doc.doctype_psicologia);
    }
});

/* ============================================================================
 * QUERIES
 * ==========================================================================*/

// Filtra el Link de Signos Vitales por paciente
function set_vital_signs_query(frm) {
    frm.set_query('signos_vitales', function () {
        if (!frm.doc.patient) return {};
        return { filters: { patient: frm.doc.patient } };
    });
}

// Filtra Historia Clinica Psicologia por paciente
function set_hcpsico_query(frm) {
    if (!frm.fields_dict.doctype_psicologia) return;

    frm.set_query('doctype_psicologia', () => {
        if (!frm.doc.patient) {
            return { filters: { name: '__never__' } };
        }
        return { filters: { patient: frm.doc.patient } };
    });

    // Formato del Link: "HCP... — Paciente — Fecha"
    // (si tu doc tiene patient_name/fecha)
    frappe.form.link_formatters['Historia Clinica Psicologia'] = function (value, doc) {
        const parts = [];
        if (doc && (doc.patient_name || doc.patient)) {
            parts.push(doc.patient_name || doc.patient);
        }
        if (doc && (doc.fecha || doc.transaction_date)) {
            const raw = doc.fecha || doc.transaction_date;
            const f = (frappe.datetime && frappe.datetime.str_to_user)
                ? frappe.datetime.str_to_user(raw)
                : raw;
            parts.push(f);
        }
        return parts.length ? `${value} — ${parts.join(' — ')}` : value;
    };
}

/* ============================================================================
 * PACIENTE (NOMBRE + EDAD)
 * ==========================================================================*/

function update_patient_info(frm) {
    if (!frm.doc.patient) return;

    frappe.db.get_value('Patient', frm.doc.patient, ['patient_name', 'dob'])
        .then(r => {
            if (!r || !r.message) return;
            const { patient_name, dob } = r.message;

            frm.set_value('pat_nombre', patient_name || '');

            if (dob) {
                const as_of = frm.doc.fecha_actual || frappe.datetime.get_today();
                const age_str = get_age_string(dob, as_of);
                frm.set_value('pat_edadhoy', age_str);
            } else {
                frm.set_value('pat_edadhoy', '');
            }
        });
}

// Edad “X años Y meses”
function get_age_string(dob_str, as_of_str) {
    const dob = frappe.datetime.str_to_obj(dob_str);
    const as_of = frappe.datetime.str_to_obj(as_of_str || frappe.datetime.get_today());
    if (!dob || !as_of) return '';

    let years = as_of.getFullYear() - dob.getFullYear();
    let months = as_of.getMonth() - dob.getMonth();
    const days = as_of.getDate() - dob.getDate();

    if (days < 0) months -= 1;
    if (months < 0) { years -= 1; months += 12; }

    const partes = [];
    if (years >= 0) partes.push(`${years} año${years === 1 ? '' : 's'}`);
    partes.push(`${months} mes${months === 1 ? '' : 'es'}`);
    return partes.join(' ');
}

/* ============================================================================
 * SIGNOS VITALES
 * ==========================================================================*/

function update_vital_signs_info(frm) {
    if (!frm.doc.signos_vitales) return;

    frappe.db.get_doc('Vital Signs', frm.doc.signos_vitales)
        .then(vs => {
            frm.set_value('ant_sv_pa',    vs.bp || vs.bp_reading || '');
            frm.set_value('ant_sv_fr',    vs.respiratory_rate || vs.rr || '');
            frm.set_value('ant_sv_fc',    vs.pulse || vs.heart_rate || '');
            frm.set_value('ant_sv_peso',  vs.weight || vs.weight_kg || '');
            frm.set_value('ant_sv_talla', vs.height || vs.height_cm || '');
            frm.set_value('ant_sv_imc',   vs.bmi || vs.bmi_value || '');
        });
}

function clear_vital_signs(frm) {
    frm.set_value('ant_sv_pa', '');
    frm.set_value('ant_sv_fr', '');
    frm.set_value('ant_sv_fc', '');
    frm.set_value('ant_sv_peso', '');
    frm.set_value('ant_sv_talla', '');
    frm.set_value('ant_sv_imc', '');
}

/* ============================================================================
 * HISTORIA CLÍNICA PSICOLOGÍA – SECCIÓN LECTURA (hist_*)
 * ==========================================================================*/

function load_hcpsico_into_fields(frm, hc_name) {
    if (!hc_name) return;

    // 1) Campos simples
    // Nota: en tu Historia Clinica Psicologia el campo de fecha normalmente es "fecha".
    // Si en tu DocType se llama diferente, cámbialo aquí.
    const HCP_MAP = {
        hist_fecha: 'fecha',
        hist_eje2a: 'cie_eje2a',
        hist_eje2b: 'cie_eje2b',
        hist_eje2c: 'cie_eje2c'
    };

    const fields_to_fetch = Object.values(HCP_MAP);

    frappe.db.get_value('Historia Clinica Psicologia', hc_name, fields_to_fetch)
        .then(r => {
            const src = (r && r.message) || {};
            for (const [dest, origen] of Object.entries(HCP_MAP)) {
                if (frm.fields_dict[dest]) {
                    frm.set_value(dest, src[origen] || '');
                }
            }
        });

    // 2) Tablas hijas (Eje I A/B/C + Eje III)
    frappe.db.get_doc('Historia Clinica Psicologia', hc_name)
        .then(doc => {
            // En Historia Clinica Psicologia, normalmente estas tablas se llaman igual:
            // e1a_diag_cie10, e1b_diag_cie10, e1c_diag_cie10, cie_eje3
            copy_child_table(frm, doc, 'e1a_diag_cie10', 'hist_eje1a');
            copy_child_table(frm, doc, 'e1b_diag_cie10', 'hist_eje1b');
            copy_child_table(frm, doc, 'e1c_diag_cie10', 'hist_eje1c');
            copy_child_table(frm, doc, 'cie_eje3',       'hist_eje3');

            frm.refresh_fields(['hist_eje1a', 'hist_eje1b', 'hist_eje1c', 'hist_eje3']);
            make_history_tables_read_only(frm);
        });
}

function clear_historia_clinica_section(frm) {
    frm.set_value('doctype_psicologia', '');
    frm.set_value('hist_fecha', '');
    frm.set_value('hist_eje2a', '');
    frm.set_value('hist_eje2b', '');
    frm.set_value('hist_eje2c', '');

    ['hist_eje1a', 'hist_eje1b', 'hist_eje1c', 'hist_eje3'].forEach(f => {
        if (frm.fields_dict[f]) frm.clear_table(f);
    });

    frm.refresh_fields(['hist_eje1a', 'hist_eje1b', 'hist_eje1c', 'hist_eje3']);
}

/* ============================================================================
 * UTILIDADES: copiar tablas + hacerlas solo lectura
 * ==========================================================================*/

function copy_child_table(frm, src_doc, src_field, dst_field) {
    if (!frm.fields_dict[dst_field]) return;

    frm.clear_table(dst_field);
    const src_list = src_doc[src_field] || [];

    src_list.forEach(row_src => {
        const row = frm.add_child(dst_field);

        Object.keys(row_src).forEach(key => {
            if ([
                'name', 'owner', 'creation', 'modified',
                'modified_by', 'doctype', 'idx',
                'parent', 'parenttype', 'parentfield'
            ].includes(key)) return;

            row[key] = row_src[key];
        });
    });
}

function make_history_tables_read_only(frm) {
    [
        'hist_eje1a',
        'hist_eje1b',
        'hist_eje1c',
        'hist_eje3'
    ].forEach(f => {
        const field = frm.get_field(f);
        if (!field || !field.grid) return;

        const grid = field.grid;

        grid.cannot_add_rows = true;
        grid.cannot_delete_rows = true;
        grid.df.read_only = 1;

        grid.wrapper.find('.grid-add-row').hide();
        grid.wrapper.find('.grid-append-row').hide();
        grid.wrapper.find('.grid-remove-rows').hide();
        grid.wrapper.find('.grid-row-check').hide();

        (grid.grid_rows || []).forEach(row => {
            if (row && row.toggle_editable) row.toggle_editable(false);
        });

        grid.refresh();
    });
}
