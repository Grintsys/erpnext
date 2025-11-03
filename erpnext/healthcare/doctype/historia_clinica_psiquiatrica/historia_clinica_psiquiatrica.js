// Historia Clinica Psiquiatrica - Client JS
// v3: filtra Vital Signs por patient, calcula edad, filtra amg_asv por grupos

frappe.ui.form.on('Historia Clinica Psiquiatrica', {
  onload(frm) {
    set_vs_query(frm);
    set_amg_asv_query(frm);
    set_cie_eje3_query(frm);
    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);   // DOB + edad hoy (y pat_nombre si lo agregas)
    }
  },

  refresh(frm) {
    set_vs_query(frm);
    set_amg_asv_query(frm);
    set_cie_eje3_query(frm);
  },

  patient(frm) {
    frm.set_value('vital_signs', null);
    clear_vitals(frm);

    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);
    } else {
      // limpia campos derivados del paciente
      frm.set_value('pat_nombre', null);
      frm.set_value('pat_edad', null);
      frm.set_value('pat_edadhoy', null);
    }

    set_vs_query(frm);
  },

  vital_signs(frm) {
    if (!frm.doc.vital_signs) {
      clear_vitals(frm);
      return;
    }

    frappe.db.get_value('Vital Signs', frm.doc.vital_signs, [
      'bp', 'respiratory_rate', 'pulse', 'weight', 'height', 'bmi',
      'bp_systolic','bp_diastolic','signs_date','signs_time'
    ]).then(r => {
      const v = (r && r.message) || {};
      let bp = v.bp;
      if (!bp && v.bp_systolic && v.bp_diastolic) {
        bp = `${v.bp_systolic}/${v.bp_diastolic} mmHg`;
      }
      frm.set_value('ant_sv_pa', bp || null);
      frm.set_value('ant_sv_fr', v.respiratory_rate || null);
      frm.set_value('ant_sv_fc', v.pulse || null);
      frm.set_value('ant_sv_peso', v.weight || null);
      frm.set_value('ant_sv_talla', v.height || null);
      frm.set_value('ant_sv_imc', v.bmi || null);
      // Fecha y hora de signos Vitales
      // frm.set_value('vital_sigms_date', v.signs_date || null);
      // frm.set_value('vital_sigms_time', v.signs_time || null);
    });
  }
});

/** ===== Helpers ===== */

function clear_vitals(frm) {
  frm.set_value('ant_sv_pa', null);
  frm.set_value('ant_sv_fr', null);
  frm.set_value('ant_sv_fc', null);
  frm.set_value('ant_sv_peso', null);
  frm.set_value('ant_sv_talla', null);
  frm.set_value('ant_sv_imc', null);
}

function set_vs_query(frm) {
  frm.set_query('vital_signs', () => {
    if (!frm.doc.patient) {
      return { filters: { name: '__never__' } };
    }
    return { filters: { patient: frm.doc.patient } };
  });
}

function set_amg_asv_query(frm) {
  // Filtra el Link 'amg_asv' por los grupos indicados (ajústalo a tu DocType/campo reales)
  frm.set_query('amg_asv', () => {
    return {
      filters: {
        cod_grupo: ['in', ['Y4', 'Y6', 'Y09', 'AA175', 'AA207', 'AA208', 'AA210']]
      }
    };
  });
}

function set_cie_eje3_query(frm) {
  // Filtra el Link 'cie_eje3' por los grupos indicados (ajústalo a tu DocType/campo reales)
  frm.set_query('cie_eje3', () => {
    return {
      filters: {
        cod_grupo: ['in', ['X60-X69',	'X70-X89',	'X85-X99',	'Y00-Y03',	'Y04',	'Y05',	'Y06',	'Y07',	'Y08',	'Y09',	'T74.1',	'T74.2',	'T74.3',	'AA206',	'AA207',	'AA208',	'AA175',	'AA210',	'Z00-Z13',	'Z20-Z29',	'Z30-Z39',	'Z40-Z54',	'Z55-Z65',	'Z70-Z76',	'Z80-Z99',	'NPP']]
      }
    };
  });
}

function hydrate_patient_side_fields(frm) {
  frappe.db.get_value('Patient', frm.doc.patient, ['patient_name', 'dob']).then(r => {
    const p = (r && r.message) || {};
    if (frm.get_field('pat_nombre')) {
      frm.set_value('pat_nombre', p.patient_name || null);
    }
    if (p.dob) frm.set_value('pat_edad', p.dob);
    const years = calc_age(p.dob);
    frm.set_value('pat_edadhoy', years != null ? `${years}` : null);
  });
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
