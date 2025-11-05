// Historia Clinica Psiquiatrica - Client JS
// v4: usa 'buscar' (Link a Vital Signs) filtrado por patient,
//     copia signos vitales, y guarda 'pat_edadhoy' como "X años Y meses"
//     calculado respecto a la fecha del documento.

frappe.ui.form.on('Historia Clinica Psiquiatrica', {
  onload(frm) {
    set_vs_query(frm);          // filtra 'buscar' por paciente
    set_amg_asv_query(frm);     // tus filtros CIE
    set_cie_eje3_query(frm);

    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);   // nombre, DOB y edad a la fecha
    }
  },

  refresh(frm) {
    set_vs_query(frm);
    set_amg_asv_query(frm);
    set_cie_eje3_query(frm);
  },

  // Cuando cambie el paciente
  patient(frm) {
    frm.set_value('buscar', null);
    clear_vitals(frm);

    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);
    } else {
      // limpia campos derivados del paciente
      safe_set(frm, 'pat_nombre', null);
      safe_set(frm, 'pat_edad', null);
      safe_set(frm, 'pat_edadhoy', null);
    }

    set_vs_query(frm);
  },

  // Cuando cambie la fecha del documento, recalcula edad a esa fecha
  fecha(frm) {
    recalc_age_to_doc_date(frm);
  },

  // Cuando el usuario seleccione un registro en "buscar" (Vital Signs)
  buscar(frm) {
    if (!frm.doc.buscar) {
      clear_vitals(frm);
      return;
    }

    frappe.db.get_value('Vital Signs', frm.doc.buscar, [
      'bp', 'respiratory_rate', 'pulse', 'weight', 'height', 'bmi',
      'bp_systolic','bp_diastolic','signs_date','signs_time','patient'
    ]).then(r => {
      const v = (r && r.message) || {};

      // Seguridad: si no corresponde al paciente del form, lo vaciamos
      if (frm.doc.patient && v.patient && v.patient !== frm.doc.patient) {
        frappe.msgprint(__('El registro de Signos Vitales no corresponde al paciente seleccionado.'));
        frm.set_value('buscar', null);
        clear_vitals(frm);
        return;
      }

      let bp = v.bp;
      if (!bp && v.bp_systolic && v.bp_diastolic) {
        bp = `${v.bp_systolic}/${v.bp_diastolic} mmHg`;
      }

      safe_set(frm, 'ant_sv_pa',    bp || null);
      safe_set(frm, 'ant_sv_fr',    v.respiratory_rate || null);
      safe_set(frm, 'ant_sv_fc',    v.pulse || null);
      safe_set(frm, 'ant_sv_peso',  v.weight || null);
      safe_set(frm, 'ant_sv_talla', v.height || null);
      safe_set(frm, 'ant_sv_imc',   v.bmi || null);
    });
  },

  // Aseguramos que la edad quede guardada siempre
  before_save(frm) {
    recalc_age_to_doc_date(frm);
  }
});

/** ===== Helpers ===== */

// set_value protegido (evita warnings si el campo no existe)
function safe_set(frm, fieldname, value) {
  if (frm.get_field(fieldname)) {
    frm.set_value(fieldname, value);
  }
}

function clear_vitals(frm) {
  safe_set(frm, 'ant_sv_pa', null);
  safe_set(frm, 'ant_sv_fr', null);
  safe_set(frm, 'ant_sv_fc', null);
  safe_set(frm, 'ant_sv_peso', null);
  safe_set(frm, 'ant_sv_talla', null);
  safe_set(frm, 'ant_sv_imc', null);
}

function set_vs_query(frm) {
  // Filtra el LINK 'buscar' (Vital Signs) por el paciente del formulario
  frm.set_query('buscar', () => {
    if (!frm.doc.patient) {
      // evita que se liste todo cuando no hay paciente
      return { filters: { name: '__never__' } };
    }
    return {
      filters: { patient: frm.doc.patient }
    };
  });
}

function set_amg_asv_query(frm) {
  // Ajusta según tu catálogo real
  frm.set_query('amg_asv', () => {
    return {
      filters: {
        cod_grupo: ['in', ['Y4', 'Y6', 'Y09', 'AA175', 'AA207', 'AA208', 'AA210']]
      }
    };
  });
}

function set_cie_eje3_query(frm) {
  frm.set_query('cie_eje3', () => {
    return {
      filters: {
        cod_grupo: ['in', ['X60-X69','X70-X89','X85-X99','Y00-Y03','Y04','Y05','Y06','Y07','Y08','Y09','T74.1','T74.2','T74.3','AA206','AA207','AA208','AA175','AA210','Z00-Z13','Z20-Z29','Z30-Z39','Z40-Z54','Z55-Z65','Z70-Z76','Z80-Z99','NPP']]
      }
    };
  });
}

/** Carga nombre + DOB del Patient y calcula edad a la fecha del documento */
function hydrate_patient_side_fields(frm) {
  frappe.db.get_value('Patient', frm.doc.patient, [
    'patient_name', 'dob'
  ]).then(r => {
    const p = (r && r.message) || {};
    safe_set(frm, 'pat_nombre', p.patient_name || null);
    if (p.dob) safe_set(frm, 'pat_edad', p.dob); // guardas DOB en tu campo espejo si lo deseas

    // edad a la fecha del documento
    recalc_age_to_doc_date(frm, p.dob);
  });
}

/** Recalcula y guarda pat_edadhoy como "X años Y meses" usando la fecha del doc */
function recalc_age_to_doc_date(frm, dobOpt) {
  const dob = dobOpt || frm.doc.pat_edad || null; // pat_edad guarda DOB según tu JSON
  const baseDate = frm.doc.fecha || frappe.datetime.get_today(); // usa fecha del documento
  const txt = age_text(dob, baseDate);
  safe_set(frm, 'pat_edadhoy', txt);
}

/** Texto "X años Y meses" dado dob (YYYY-MM-DD) y fecha base (YYYY-MM-DD) */
function age_text(dob, baseYmd) {
  const parts = age_parts(dob, baseYmd);
  if (parts.years == null) return null;
  const y = `${parts.years} ${parts.years === 1 ? 'año' : 'años'}`;
  const m = `${parts.months} ${parts.months === 1 ? 'mes' : 'meses'}`;
  return `${y} ${m}`;
}

/** Devuelve {years, months} calculados a partir de DOB y una fecha base */
function age_parts(dob, baseYmd) {
  if (!dob) return { years: null, months: null };
  try {
    const birth = frappe.datetime.str_to_obj(dob);
    const base  = frappe.datetime.str_to_obj(baseYmd || frappe.datetime.get_today());

    let years  = base.getFullYear() - birth.getFullYear();
    let months = base.getMonth()    - birth.getMonth();

    // Si aún no cumple el día en el mes base, restamos 1 mes
    if (base.getDate() < birth.getDate()) months -= 1;

    if (months < 0) { years -= 1; months += 12; }
    if (years < 0)  { years = 0;  months = 0; }

    return { years, months };
  } catch (e) {
    console.warn('No se pudo calcular la edad:', e);
    return { years: null, months: null };
  }
}
