// Historia Clinica Psicologia - Client JS
// Reutiliza lógica de HCPsiq: hidratar datos de paciente, filtrar HCPsiq por paciente,
// y mapear campos seleccionados (ej: hist_fecha <- fecha).

frappe.ui.form.on('Historia Clinica Psicologia', {
  onload(frm) {
    set_hcpsiq_query(frm);      // filtro del Link a HCPsiq por patient
    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);
    }
  },

  refresh(frm) {
    set_hcpsiq_query(frm);
  },

  // cuando cambia el patient
  patient(frm) {
    frm.set_value('doctype_psiquiatria', null); // limpia selección previa
    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);
    } else {
      clear_patient_side_fields(frm);
    }
    set_hcpsiq_query(frm);
  },

  // cuando eliges una Historia Clinica Psiquiatrica
  doctype_psiquiatria(frm) {
    if (!frm.doc.doctype_psiquiatria) return;

    // === MAPEOS: destino_en_Psicologia : origen_en_Psiquiatria ===
    const HCP_MAP = {
      // Asi se agregan los campos a rellenarce por la seleccion de doctype.
      // agrega más así:
      // 'campo_destino_psico': 'campo_origen_psiquiatria',
      // 'psico_otro': 'exmen_contenido',
      // etc.
	  hist_fecha: 'fecha',
	  hist_eje1a: 'cie_a',
	  hist_eje1b: 'cie_b',
	  hist_eje1c: 'cie_c',
	  hist_eje2a: 'cie_eje2a',
	  hist_eje2b: 'cie_eje2b',
	  hist_eje2c: 'cie_eje2c',
	  hist_eje3: 'cie_eje3',
	  hist_farmacologico: 'est_lab_tratamiento',
	  hist_rasgos: 'ant_rasgos',
	  hist_emnp: 'ant_medsqui',
	  hist_perprevia: 'fla_per',
	  hist_ant_medicos: 'ant_medicos',
	  hist_esp_pp: 'fla_esp',
	  hist_ant_afpp: 'ant_afpp',
	  hist_depresion: 'ant_sel_depresion',
	  hist_ansiedad: 'ant_sel_ansiedad',
	  hist_bipolaridad: 'ant_sel_bipolaridad',
	  hist_esquizofrenia: 'ant_lab_esquizofrenia',
	  hist_ant_otrosms03: 'ant_otrosms03',
	  hist_abuso: 'ant_lab_abuso',
	  hist_suicidas: 'ant_lab_suicidas',
	  hist_demencias: 'ant_lab_demencias',
	  hist_epilepsia: 'ant_lab_epilepsia',
	  hist_dnfa: 'ant_dnfa',

    };

    // Trae en un solo get_value todos los campos origen del map
    const fields_to_fetch = Array.from(new Set(Object.values(HCP_MAP)));
    frappe.db.get_value('Historia Clinica Psiquiatrica', frm.doc.doctype_psiquiatria, fields_to_fetch)
      .then(r => {
        const src = (r && r.message) || {};
        for (const [dest, origen] of Object.entries(HCP_MAP)) {
          safe_set(frm, dest, src[origen] ?? null);
        }
      });
  }
});

/* ---------------- Helpers ---------------- */

function set_hcpsiq_query(frm) {
  if (!frm.fields_dict.doctype_psiquiatria) return;

  frm.set_query('doctype_psiquiatria', () => {
    if (!frm.doc.patient) {
      return { filters: { name: '__never__' } };
    }
    // Filtra por el mismo paciente
    return { filters: { patient: frm.doc.patient } };
  });

  // Formato bonito en el dropdown: "Paciente — Fecha"
  // (mejor si en HCPsiq agregas search_fields = "patient, fecha")
  frappe.form.link_formatters['Historia Clinica Psiquiatrica'] = function(value, doc) {
    // `doc` trae campos usados en la búsqueda si están en search_fields
    // fallback: muestra solo el name si no vienen
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

// Hidrata laterales desde Patient (igual que en Psiquiatría)
function hydrate_patient_side_fields(frm) {
  frappe.db.get_value('Patient', frm.doc.patient, [
    'patient_name', 'dob', 'sex',
    'pac_estado', 'pac_raza', 'pac_religion',
    'pac_escolaridad', 'pac_ocupacion',
    'pac_pais', 'pac_departamento', 'pac_ciudad',
    'pac_acompa', 'pac_parentesco', 'nacimiento',
    'cologne', 'mobile'
  ]).then(r => {
    const p = (r && r.message) || {};
    safe_set(frm, 'patient_nombre', p.patient_name || null);

    if (p.dob) safe_set(frm, 'pat_edad', p.dob);
    const years = calc_age(p.dob);
    safe_set(frm, 'pat_edadhoy', years != null ? `${years}` : null);

    safe_set(frm, 'pat_sex', p.sex || null);
    safe_set(frm, 'pat_estado', p.pac_estado || null);
    safe_set(frm, 'pat_raza', p.pac_raza || null);
    safe_set(frm, 'pat_religion', p.pac_religion || null);
    safe_set(frm, 'pat_escolaridad', p.pac_escolaridad || null);
    safe_set(frm, 'pat_ocupacion', p.pac_ocupacion || null);
    safe_set(frm, 'pat_pais', p.pac_pais || null);
    safe_set(frm, 'pat_departamento', p.pac_departamento || null);
    safe_set(frm, 'pat_ciudad', p.pac_ciudad || null);
    safe_set(frm, 'pat_acompa', p.pac_acompa || null);
    safe_set(frm, 'pat_parentesco', p.pac_parentesco || null);
    safe_set(frm, 'pat_nacimiento', p.nacimiento || null);
    safe_set(frm, 'pat_direccion', p.cologne || null);
    safe_set(frm, 'pat_mobile', p.mobile || null);
  });
}

function clear_patient_side_fields(frm) {
  const fields = [
    'patient_nombre', 'pat_edad', 'pat_edadhoy', 'pat_sex', 'pat_estado',
    'pat_raza', 'pat_religion', 'pat_escolaridad', 'pat_ocupacion',
    'pat_pais', 'pat_departamento', 'pat_ciudad', 'pat_direccion',
    'pat_mobile', 'pat_acompa', 'pat_parentesco', 'pat_nacimiento'
  ];
  fields.forEach(f => safe_set(frm, f, null));
}

function calc_age(dob) {
  if (!dob) return null;
  try {
    const d = frappe.datetime.str_to_obj(dob);
    const today = frappe.datetime.str_to_obj(frappe.datetime.get_today());
    let age = today.getFullYear() - d.getFullYear();
    const m = today.getMonth() - d.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age -= 1;
    return age;
  } catch (e) {
    console.warn('No se pudo calcular edad:', e);
    return null;
  }
}

function safe_set(frm, fieldname, value) {
  if (frm && frm.fields_dict && frm.fields_dict[fieldname]) {
    frm.set_value(fieldname, value);
  }
}
