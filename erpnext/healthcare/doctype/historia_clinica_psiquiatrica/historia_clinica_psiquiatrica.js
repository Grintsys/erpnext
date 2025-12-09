/* ============================================================================
   Historia Clinica Psiquiatrica – Client Script
   Versión: layout compacto con HTML + cálculo de edad
   ---------------------------------------------------------------------------
   - Muestra datos de Paciente en un campo HTML (pat_info_html).
   - Muestra el registro de Signos Vitales en un campo HTML (sv_info_html).
   - Filtra "buscar" (Link a Vital Signs) por paciente.
   - Calcula y guarda pat_edadhoy = "X años Y meses" (campo tipo Data).
   - Precarga filas por defecto en tablas hijas (si las usas luego).
   - Reordena el layout:
       * Tabla de datos del paciente a la izquierda (debajo de patient).
       * Campo "buscar" debajo de pat_edadhoy.
       * Tabla de signos vitales debajo de "buscar".
   ==========================================================================*/

frappe.ui.form.on('Historia Clinica Psiquiatrica', {

  // Se ejecuta al cargar el formulario (nuevo o existente)
  onload(frm) {
    // filtra el Link "buscar" por paciente
    set_vs_query(frm);

    // si ya viene con paciente, carga datos del paciente
    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);
    }

    // si quieres usar tablas hijas, aquí se precargan (solo en nuevo)
    ensure_default_rows(frm);
  },

  // Se ejecuta en cada refresh (abrir, guardar, cambiar estado)
  refresh(frm) {
    set_vs_query(frm);          // por si cambió el paciente
    render_patient_html(frm);   // repinta HTML de paciente

    // Si hay un Vital Signs seleccionado, lo recargamos;
    // si no, limpiamos la tabla de signos vitales.
    if (frm.doc.buscar) {
      load_vital_signs(frm);
    } else {
      render_sv_html(frm, null);
    }

    // Reordena la posición visual de los campos
    reflow_layout(frm);
  },

  // Cuando el usuario cambia de Paciente
  patient(frm) {
    // limpia el Link de signos vitales seleccionado
    frm.set_value('buscar', null);

    if (frm.doc.patient) {
      // vuelve a cargar los datos del paciente y recalcular edad
      hydrate_patient_side_fields(frm);
    } else {
      // si se borra el paciente, limpia HTML y edad
      frm.__hc_patient_cache = null;
      render_patient_html(frm, null);
      render_sv_html(frm, null);
      if (frm.get_field('pat_edadhoy')) {
        frm.set_value('pat_edadhoy', null);
      }
    }

    reflow_layout(frm);
  },

  // Cuando se cambia la fecha del documento, recalculamos la edad
  fecha(frm) {
    recalc_age_to_doc_date(frm);
  },

  // Cuando se selecciona un registro de Vital Signs en "buscar"
  buscar(frm) {
    load_vital_signs(frm);
  },

  // Antes de guardar, garantizamos que pat_edadhoy esté actualizado
  before_save(frm) {
    recalc_age_to_doc_date(frm);
  }
});

/* ============================================================================
   Helpers de queries y datos
   ==========================================================================*/

// Filtro del Link "buscar" para que solo muestre Signos Vitales de ese paciente
function set_vs_query(frm) {
  frm.set_query('buscar', () => {
    if (!frm.doc.patient) {
      // truco: devolver filtro imposible si no hay paciente
      return { filters: { name: '__never__' } };
    }
    return {
      filters: {
        patient: frm.doc.patient
      }
    };
  });
}

// Carga datos básicos del paciente y los guarda en un cache del form
function hydrate_patient_side_fields(frm) {
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
  ]).then(r => {
    const p = (r && r.message) || {};

    // dejamos el objeto del paciente en memoria del form
    frm.__hc_patient_cache = p;

    // recalculamos y guardamos la edad actual (texto) en pat_edadhoy
    recalc_age_to_doc_date(frm, p.dob);

    // repintamos el HTML del panel de paciente
    render_patient_html(frm);
  });
}

/* ============================================================================
   Carga de Signos Vitales (se usa en refresh y en buscar)
   ==========================================================================*/

function load_vital_signs(frm) {
  if (!frm.doc.buscar) {
    // si se limpia el campo, se borra el panel de SV
    render_sv_html(frm, null);
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
  ]).then(r => {
    const v = (r && r.message) || {};

    // seguridad: que el registro de SV sea del mismo paciente
    if (frm.doc.patient && v.patient && v.patient !== frm.doc.patient) {
      frappe.msgprint(__('El registro de Signos Vitales no corresponde al paciente seleccionado.'));
      frm.set_value('buscar', null);
      render_sv_html(frm, null);
      return;
    }

    // pinta el panel HTML de signos vitales
    render_sv_html(frm, v);
  });
}

/* ============================================================================
   Cálculo de edad
   ==========================================================================*/

// Calcula y setea pat_edadhoy = "X años Y meses"
function recalc_age_to_doc_date(frm, dobOpt) {
  // dobOpt se usa cuando lo tenemos fresquito del Patient
  const dob = dobOpt || (frm.__hc_patient_cache && frm.__hc_patient_cache.dob) || null;

  if (!dob) {
    if (frm.get_field('pat_edadhoy')) {
      frm.set_value('pat_edadhoy', null);
    }
    return;
  }

  // fecha base = fecha del documento, o hoy si no está
  const baseDate = frm.doc.fecha || frappe.datetime.get_today();
  const txt = age_text(dob, baseDate);

  if (frm.get_field('pat_edadhoy')) {
    frm.set_value('pat_edadhoy', txt);
  }
}

// Construye el texto "X años Y meses"
function age_text(dob, baseYmd) {
  const parts = age_parts(dob, baseYmd);
  if (parts.years == null) return null;

  const y = `${parts.years} ${parts.years === 1 ? 'año' : 'años'}`;
  const m = `${parts.months} ${parts.months === 1 ? 'mes' : 'meses'}`;

  return `${y} ${m}`;
}

// Calcula la diferencia exacta en años y meses
function age_parts(dob, baseYmd) {
  if (!dob) return { years: null, months: null };

  try {
    const birth = frappe.datetime.str_to_obj(dob);
    const base = frappe.datetime.str_to_obj(baseYmd || frappe.datetime.get_today());

    let years = base.getFullYear() - birth.getFullYear();
    let months = base.getMonth() - birth.getMonth();

    // si aún no ha pasado el día del mes, restamos un mes
    if (base.getDate() < birth.getDate()) {
      months -= 1;
    }

    // normalizamos si quedan meses negativos
    if (months < 0) {
      years -= 1;
      months += 12;
    }

    if (years < 0) {
      years = 0;
      months = 0;
    }

    return { years, months };
  } catch (e) {
    console.warn('No se pudo calcular la edad:', e);
    return { years: null, months: null };
  }
}

/* ============================================================================
   Render de HTML (paciente y signos vitales)
   ==========================================================================*/

// Pinta la tabla HTML de datos del paciente en pat_info_html
function render_patient_html(frm) {
  const t = frm.get_field('pat_info_html');
  if (!t) return;

  const p = frm.__hc_patient_cache || {};

  const rows = [
    ['Nombre', p.patient_name],
    ['Dime', p.nickname],
    ['Sexo', p.sex],
    ['Estado civil', p.pac_estado],
    ['Raza', p.pac_raza],
    ['Religión', p.pac_religion],
    ['Escolaridad', p.pac_escolaridad],
    ['Ocupación', p.pac_ocupacion],
    ['País', p.pac_pais],
    ['Departamento', p.pac_departamento],
    ['Municipio', p.pac_ciudad],
    ['Acompañante', p.pac_acompa],
    ['Parentesco', p.pac_parentesco],
    ['Lugar de nacimiento', p.nacimiento],
    ['Dirección', p.cologne],
    ['Móvil', p.mobile]
  ];

  const html = `
    <div class="form-grid">
      <table class="table table-bordered table-condensed">
        <tbody>
          ${rows
            .map(([k, v]) =>
              v
                ? `<tr><th style="width:30%">${k}</th><td>${frappe.utils.escape_html(
                    String(v)
                  )}</td></tr>`
                : ''
            )
            .join('')}
        </tbody>
      </table>
    </div>`;

  t.$wrapper.html(html);
}

// Pinta la tabla HTML de signos vitales en sv_info_html
function render_sv_html(frm, v) {
  const t = frm.get_field('sv_info_html');
  if (!t) return;

  const d = v || {};

  // si no viene bp directo, lo armamos con sistólica/diastólica
  let bp = d.bp;
  if (!bp && d.bp_systolic && d.bp_diastolic) {
    bp = `${d.bp_systolic}/${d.bp_diastolic} mmHg`;
  }

  const rows = [
    ['Fecha', d.signs_date],
    ['Hora', d.signs_time],
    ['P/A', bp],
    ['FR', d.respiratory_rate],
    ['FC', d.pulse],
    ['Peso', d.weight],
    ['Talla', d.height],
    ['IMC', d.bmi]
  ];

  const html = `
    <div class="form-grid">
      <table class="table table-bordered table-condensed">
        <tbody>
          ${rows
            .map(([k, v]) =>
              v
                ? `<tr><th style="width:30%">${k}</th><td>${frappe.utils.escape_html(
                    String(v)
                  )}</td></tr>`
                : ''
            )
            .join('')}
        </tbody>
      </table>
    </div>`;

  t.$wrapper.html(html);
}

/* ============================================================================
   Precarga de filas de tablas hijas (si las usas)
   ==========================================================================*/

function ensure_default_rows(frm) {
  if (!frm.is_new()) return;

  // Si no estás usando aún las tablas hijas, puedes comentar todo este bloque.
  // Ejemplo para Examen Físico:
  if (!(frm.doc.exf_items || []).length && frm.fields_dict.exf_items) {
    ['Cabeza', 'Cuello', 'ORL', 'Cardiopulmonar', 'Gastrointestinal', 'Músculo-esquelético', 'Piel y faneras', 'Neurológico']
      .forEach(parte => {
        const r = frm.add_child('exf_items');
        r.parte = parte;
        r.resultado = 'None';
      });
  }

  // Examen Mental
  if (!(frm.doc.exm_items || []).length && frm.fields_dict.exm_items) {
    ['Aspecto y actitud', 'Edad aparente', 'Colabora', 'Higiene/vestimenta', 'Contacto visual', 'Conciencia', 'Atención', 'Orientación', 'Sensopercepción', 'Conducta motora', 'Afecto', 'Memoria', 'Pensamiento-Forma', 'Pensamiento-Curso', 'Pensamiento-Contenido', 'Funciones corticales', 'Insight', 'Juicio']
      .forEach(aspecto => {
        const r = frm.add_child('exm_items');
        r.aspecto = aspecto;
        r.valor = 'None';
      });
  }

  // FOG
  if (!(frm.doc.fog_items || []).length && frm.fields_dict.fog_items) {
    ['Sueño', 'Apetito', 'Sed', 'Micción', 'Defecación']
      .forEach(funcion => {
        const r = frm.add_child('fog_items');
        r.funcion = funcion;
        r.valor = 'none';
      });
  }

  frm.refresh_fields(['exf_items', 'exm_items', 'fog_items']);
}

/* ============================================================================
   Reordenar layout en el DOM
   ==========================================================================*/

function reflow_layout(frm) {
  // Mover tabla de datos del paciente debajo de "patient" (lado izquierdo)
  try {
    const pat_html = frm.fields_dict.pat_info_html && frm.fields_dict.pat_info_html.$wrapper;
    const patient = frm.fields_dict.patient && frm.fields_dict.patient.$wrapper;

    if (pat_html && patient && pat_html.prev()[0] !== patient[0]) {
      pat_html.insertAfter(patient);
    }

    // Mover campo "buscar" debajo de "pat_edadhoy" (Edad hoy – lado derecho)
    const buscar = frm.fields_dict.buscar && frm.fields_dict.buscar.$wrapper;
    const edad = frm.fields_dict.pat_edadhoy && frm.fields_dict.pat_edadhoy.$wrapper;

    if (buscar && edad && buscar.prev()[0] !== edad[0]) {
      buscar.insertAfter(edad);
    }

    // Mover tabla de signos vitales debajo de "buscar"
    const sv_html = frm.fields_dict.sv_info_html && frm.fields_dict.sv_info_html.$wrapper;
    if (sv_html && buscar && sv_html.prev()[0] !== buscar[0]) {
      sv_html.insertAfter(buscar);
    }
  } catch (e) {
    console.warn('No se pudo reordenar el layout de Historia Clinica Psiquiatrica:', e);
  }
}
