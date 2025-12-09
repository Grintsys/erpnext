// Notas de Evolucion Medico Psiquiatrica – Client Script
// ------------------------------------------------------
// - Calcula y muestra edad actual del paciente.
// - Filtra y carga Signos Vitales del paciente.
// - Permite elegir manualmente:
//      * Historia Clinica Psiquiatrica (doctype_psiquiatria)
//      * Nota de Evolucion histórica (nevhist)
//   y al seleccionar, carga los datos en las secciones de solo lectura.
// - No sugiere automáticamente “la última” HCP ni NEV.

frappe.ui.form.on('Notas de Evolucion Medico Psiquiatrica', {

    onload(frm) {
        set_vital_signs_query(frm);
        set_hcpsiq_query(frm);
        set_nev_hist_query(frm);

        if (frm.doc.patient) {
            update_patient_info(frm);
        }
    },

    refresh(frm) {
        set_vital_signs_query(frm);
        set_hcpsiq_query(frm);
        set_nev_hist_query(frm);

        if (frm.doc.patient && (!frm.doc.pat_nombre || !frm.doc.pat_edadhoy)) {
            update_patient_info(frm);
        }

        // Si ya hay signos vitales y campos vacíos, rellenarlos
        if (frm.doc.signos_vitales && !frm.doc.ant_sv_pa && !frm.doc.ant_sv_peso) {
            update_vital_signs_info(frm);
        }

        // Tablas históricas siguen siendo solo lectura
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
            clear_nevhist_section(frm);
            return;
        }

        // Datos del paciente (nombre + edad)
        update_patient_info(frm);

        // Limpiar signos vitales y secciones históricas
        frm.set_value('signos_vitales', '');
        clear_vital_signs(frm);

        clear_historia_clinica_section(frm);
        clear_nevhist_section(frm);
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

    // Al elegir manualmente una Historia Clínica Psiquiátrica
    doctype_psiquiatria(frm) {
        if (!frm.doc.doctype_psiquiatria) {
            clear_historia_clinica_section(frm);
            return;
        }
        load_hcpsiq_into_fields(frm, frm.doc.doctype_psiquiatria);
    },

    // Al elegir manualmente una Nota de Evolución histórica
    nevhist(frm) {
        if (!frm.doc.nevhist) {
            clear_nevhist_section(frm);
            return;
        }
        load_evol_hist_from_doc(frm, frm.doc.nevhist);
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

// Filtra Historia Clínica Psiquiátrica por paciente
function set_hcpsiq_query(frm) {
    if (!frm.fields_dict.doctype_psiquiatria) return;

    frm.set_query('doctype_psiquiatria', () => {
        if (!frm.doc.patient) {
            return { filters: { name: '__never__' } };
        }
        return { filters: { patient: frm.doc.patient } };
    });

    // Formato del Link: "HCP... — Paciente — Fecha"
    frappe.form.link_formatters['Historia Clinica Psiquiatrica'] = function (value, doc) {
        const parts = [];
        if (doc && (doc.patient_name || doc.patient)) {
            parts.push(doc.patient_name || doc.patient);
        }
        if (doc && doc.fecha) {
            const f = (frappe.datetime && frappe.datetime.str_to_user)
                ? frappe.datetime.str_to_user(doc.fecha)
                : doc.fecha;
            parts.push(f);
        }
        return parts.length ? `${value} — ${parts.join(' — ')}` : value;
    };
}

// Filtra Notas de Evolución históricas por paciente
function set_nev_hist_query(frm) {
    if (!frm.fields_dict.nevhist) return;

    frm.set_query('nevhist', () => {
        if (!frm.doc.patient) {
            return { filters: { name: '__never__' } };
        }
        const filters = { patient: frm.doc.patient };
        if (frm.doc.name) {
            // Evitar que se seleccione a sí misma como "histórico"
            filters.name = ['!=', frm.doc.name];
        }
        return { filters };
    });
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

// Edad “X años Y meses”
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

    const partes = [];
    if (years >= 0) {
        partes.push(`${years} año${years === 1 ? '' : 's'}`);
    }
    if (months > 0) {
        partes.push(`${months} mes${months === 1 ? '' : 'es'}`);
    }

    return partes.join(' ');
}

/* ============================================================================
 * SIGNOS VITALES
 * ==========================================================================*/

function update_vital_signs_info(frm) {
    if (!frm.doc.signos_vitales) return;

    frappe.db.get_doc('Vital Signs', frm.doc.signos_vitales)
        .then(vs => {
            // Ajusta estos nombres según tu DocType "Vital Signs"
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
 * HISTORIA CLÍNICA PSIQUIÁTRICA – SECCIÓN LECTURA
 * ==========================================================================*/

// Copia campos y tablas de una Historia Clínica específica
function load_hcpsiq_into_fields(frm, hc_name) {
    if (!hc_name) return;

    // 1) Campos simples
    const HCP_MAP = {
        hist_fecha: 'fecha',
        hist_eje2a: 'cie_eje2a',
        hist_eje2b: 'cie_eje2b',
        hist_eje2c: 'cie_eje2c'
        // Eje III se maneja abajo como tabla
    };

    const fields_to_fetch = Object.values(HCP_MAP);

    frappe.db.get_value('Historia Clinica Psiquiatrica', hc_name, fields_to_fetch)
        .then(r => {
            const src = (r && r.message) || {};
            for (const [dest, origen] of Object.entries(HCP_MAP)) {
                if (frm.fields_dict[dest]) {
                    frm.set_value(dest, src[origen] || '');
                }
            }
        });

    // 2) Tablas hijas (Eje I A/B/C + Eje III)
    frappe.db.get_doc('Historia Clinica Psiquiatrica', hc_name)
        .then(doc => {
            copy_child_table(frm, doc, 'e1a_diag_cie10', 'hist_eje1a');
            copy_child_table(frm, doc, 'e1b_diag_cie10', 'hist_eje1b');
            copy_child_table(frm, doc, 'e1c_diag_cie10', 'hist_eje1c');
            copy_child_table(frm, doc, 'cie_eje3',       'hist_eje3');

            frm.refresh_fields(['hist_eje1a', 'hist_eje1b', 'hist_eje1c', 'hist_eje3']);
            make_history_tables_read_only(frm);
        });
}

function clear_historia_clinica_section(frm) {
    frm.set_value('doctype_psiquiatria', '');
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
 * HISTORIA DE NOTAS DE EVOLUCIÓN – SECCIÓN LECTURA
 * ==========================================================================*/

// Copia campos y tablas desde otra Nota de Evolución a la sección nevhist_*
function load_evol_hist_from_doc(frm, nev_name) {
    if (!nev_name) return;

    // 1) Campos simples
    const NEV_MAP = {
        nevhist_fecha:        'fecha_actual',
        nevhist_e2a:          'cie_eje2a',
        nevhist_e2b:          'cie_eje2b',
        nevhist_e2c:          'cie_eje2c',
        nevhist_satisfactoria:'evolucion_sat',
        nevhist_nota:         'evolucion_texto',
        nevhist_tratamiento:  'tratamiento'
    };

    const fields = Object.values(NEV_MAP);

    frappe.db.get_value('Notas de Evolucion Medico Psiquiatrica', nev_name, fields)
        .then(r => {
            const src = (r && r.message) || {};
            for (const [dest, origen] of Object.entries(NEV_MAP)) {
                if (frm.fields_dict[dest]) {
                    frm.set_value(dest, src[origen] || '');
                }
            }
        });

    // 2) Tablas hijas (Eje I A/B/C + Eje III)
    frappe.db.get_doc('Notas de Evolucion Medico Psiquiatrica', nev_name)
        .then(doc => {
            copy_child_table(frm, doc, 'e1a_diag_cie10', 'nevhist_e1a');
            copy_child_table(frm, doc, 'e1b_diag_cie10', 'nevhist_e1b');
            copy_child_table(frm, doc, 'e1c_diag_cie10', 'nevhist_e1c');
            copy_child_table(frm, doc, 'cie_eje3',       'nevhist_e3');

            frm.refresh_fields(['nevhist_e1a', 'nevhist_e1b', 'nevhist_e1c', 'nevhist_e3']);
            make_history_tables_read_only(frm);
        });
}

function clear_nevhist_section(frm) {
    frm.set_value('nevhist', '');
    frm.set_value('nevhist_fecha', '');
    frm.set_value('nevhist_e2a', '');
    frm.set_value('nevhist_e2b', '');
    frm.set_value('nevhist_e2c', '');
    frm.set_value('nevhist_satisfactoria', '');
    frm.set_value('nevhist_nota', '');
    frm.set_value('nevhist_tratamiento', '');

    ['nevhist_e1a', 'nevhist_e1b', 'nevhist_e1c', 'nevhist_e3'].forEach(f => {
        if (frm.fields_dict[f]) frm.clear_table(f);
    });

    frm.refresh_fields(['nevhist_e1a', 'nevhist_e1b', 'nevhist_e1c', 'nevhist_e3']);
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
            // Campos meta que no copiamos
            if ([
                'name', 'owner', 'creation', 'modified',
                'modified_by', 'doctype', 'idx',
                'parent', 'parenttype', 'parentfield'
            ].includes(key)) {
                return;
            }
            row[key] = row_src[key];
        });
    });
}

// Hace que las tablas históricas no se puedan editar
function make_history_tables_read_only(frm) {
    [
        'hist_eje1a',
        'hist_eje1b',
        'hist_eje1c',
        'hist_eje3',
        'nevhist_e1a',
        'nevhist_e1b',
        'nevhist_e1c',
        'nevhist_e3'
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
            if (row && row.toggle_editable) {
                row.toggle_editable(false);
            }
        });

        grid.refresh();
    });
}
