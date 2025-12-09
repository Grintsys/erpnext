/* ============================================================================
   Historia Clinica Psicologia – Client Script
   ---------------------------------------------------------------------------
   - Muestra datos de Paciente en un campo HTML (pat_info_html).
   - Calcula y guarda pat_edadhoy = "X años Y meses".
   - Filtra el Link a Historia Clinica Psiquiatrica por paciente.
   - Copia campos simples + tablas (Eje I A/B/C, Eje III, EMNP) desde HCPsiq.
   ==========================================================================*/

frappe.ui.form.on('Historia Clinica Psicologia', {

  // Se ejecuta al cargar el formulario
  onload(frm) {
    set_hcpsiq_query(frm);      // filtro del Link a HCPsiq por patient

    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);
    } else {
      render_patient_html(frm); // deja la tabla vacía
    }
  },

  // Se ejecuta en cada refresh
  refresh(frm) {
    set_hcpsiq_query(frm);
    render_patient_html(frm);
    // Asegura que las tablas traídas queden solo lectura
    make_eje_tables_read_only(frm);
  },

  // Cuando cambia el Paciente
  patient(frm) {
    // limpia selección previa de HCPsiq
    frm.set_value('doctype_psiquiatria', null);

    if (frm.doc.patient) {
      hydrate_patient_side_fields(frm);
    } else {
      clear_patient_panel(frm);
    }

    set_hcpsiq_query(frm);
  },

  // Cuando cambia la fecha del documento, recalculamos la edad
  fecha(frm) {
    recalc_age_to_doc_date(frm);
  },

  // Cuando eliges una Historia Clinica Psiquiatrica
  doctype_psiquiatria(frm) {
    if (!frm.doc.doctype_psiquiatria) return;

    // === 1) CAMPOS SIMPLES: destino_en_Psicologia : origen_en_Psiquiatria ===
    const HCP_MAP = {
      hist_fecha: 'fecha',
      // Eje I-A/B/C y Eje III ahora vienen de tablas, NO van aquí
      hist_eje2a: 'cie_eje2a',
      hist_eje2b: 'cie_eje2b',
      hist_eje2c: 'cie_eje2c',
      // hist_emnp también viene de tabla, por eso ya no está en el mapa
      hist_farmacologico: 'est_lab_tratamiento',
      hist_rasgos: 'ant_rasgos',
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
      hist_dnfa: 'ant_dnfa'
    };

    const fields_to_fetch = Array.from(new Set(Object.values(HCP_MAP)));

    // 1) Traemos campos simples
    frappe.db
      .get_value(
        'Historia Clinica Psiquiatrica',
        frm.doc.doctype_psiquiatria,
        fields_to_fetch
      )
      .then(r => {
        const src = (r && r.message) || {};
        for (const [dest, origen] of Object.entries(HCP_MAP)) {
          safe_set(frm, dest, src[origen] ?? null);
        }
      });

    // 2) Traemos el doc completo para leer las TABLAS hijas
    frappe.db
      .get_doc('Historia Clinica Psiquiatrica', frm.doc.doctype_psiquiatria)
      .then(doc => {
        // TABLAS de diagnóstico que vienen de Psiquiatría:
        //   - e1a_diag_cie10  -> hist_eje1a
        //   - e1b_diag_cie10  -> hist_eje1b
        //   - e1c_diag_cie10  -> hist_eje1c
        //   - cie_eje3        -> hist_eje3
        //   - nopsiquiatricas -> hist_emnp

        copy_eje_table(frm, doc, 'e1a_diag_cie10', 'hist_eje1a'); // Eje I-A
        copy_eje_table(frm, doc, 'e1b_diag_cie10', 'hist_eje1b'); // Eje I-B
        copy_eje_table(frm, doc, 'e1c_diag_cie10', 'hist_eje1c'); // Eje I-C
        copy_eje_table(frm, doc, 'cie_eje3',       'hist_eje3');  // Eje III
        copy_eje_table(frm, doc, 'nopsiquiatricas','hist_emnp');  // Enf. médicas no psiq.

        frm.refresh_fields([
          'hist_eje1a',
          'hist_eje1b',
          'hist_eje1c',
          'hist_eje3',
          'hist_emnp'
        ]);

        make_eje_tables_read_only(frm);
      });
  }
});

/* ============================================================================
   Helpers: Copiar tablas de Psiquiatría a Psicología
   ==========================================================================*/

// Copia una tabla hija de Psiquiatría (src_field) a Psicología (dst_field)
// Copia todos los campos del child DocType excepto los meta (name, parent, etc.)
function copy_eje_table(frm, src_doc, src_field, dst_field) {
  if (!frm.fields_dict[dst_field]) return;

  // Limpiar tabla destino
  frm.clear_table(dst_field);

  const src_list = src_doc[src_field] || [];

  src_list.forEach(row_src => {
    const row = frm.add_child(dst_field);

    Object.keys(row_src).forEach(key => {
      // Campos meta que NO debemos copiar
      if ([
        'name', 'owner', 'creation', 'modified',
        'modified_by', 'doctype', 'idx',
        'parent', 'parenttype', 'parentfield'
      ].includes(key)) {
        return;
      }

      // Si el campo existe en el destino, lo copiamos
      row[key] = row_src[key];
    });
  });
}

// Hace que las tablas de diagnóstico no permitan agregar/eliminar ni editar
function make_eje_tables_read_only(frm) {
  [
    'hist_eje1a',
    'hist_eje1b',
    'hist_eje1c',
    'hist_eje3',
    'hist_emnp'
  ].forEach(f => {
    const field = frm.get_field(f);
    if (!field || !field.grid) return;

    const grid = field.grid;

    // No permitir agregar ni borrar filas
    grid.cannot_add_rows = true;
    grid.cannot_delete_rows = true;
    grid.df.read_only = 1;

    // Ocultar botones de añadir / borrar
    grid.wrapper.find('.grid-add-row').hide();
    grid.wrapper.find('.grid-append-row').hide();
    grid.wrapper.find('.grid-remove-rows').hide();
    grid.wrapper.find('.grid-row-check').hide();

    // Bloquear edición de filas ya existentes
    (grid.grid_rows || []).forEach(row => {
      if (row && row.toggle_editable) {
        row.toggle_editable(false);
      }
    });

    grid.refresh();
  });
}

/* ============================================================================
   Helpers: Query a HCPsiq
   ==========================================================================*/

function set_hcpsiq_query(frm) {
  if (!frm.fields_dict.doctype_psiquiatria) return;

  frm.set_query('doctype_psiquiatria', () => {
    if (!frm.doc.patient) {
      return { filters: { name: '__never__' } };
    }
    return { filters: { patient: frm.doc.patient } };
  });

  // Formato bonito en el dropdown: "Paciente — Fecha"
  frappe.form.link_formatters['Historia Clinica Psiquiatrica'] = function(value, doc) {
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

/* ============================================================================
   Helpers: Paciente (carga de datos + edad + HTML)
   ==========================================================================*/

// Carga datos de Patient y actualiza cache + edad + HTML
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

    // Guarda cache para el HTML
    frm.__hc_patient_cache = p;

    // Si tienes un campo "patient_nombre" en Psicología, lo llenamos
    if (frm.get_field('patient_nombre')) {
      frm.set_value('patient_nombre', p.patient_name || null);
    }

    // Recalcular edad a la fecha del documento
    recalc_age_to_doc_date(frm, p.dob);

    // Renderizar tabla HTML
    render_patient_html(frm);
  });
}

// Limpia HTML y edad si se borra el paciente
function clear_patient_panel(frm) {
  frm.__hc_patient_cache = null;
  render_patient_html(frm, null);
  if (frm.get_field('pat_edadhoy')) {
    frm.set_value('pat_edadhoy', null);
  }
}

/* ============================================================================
   Cálculo de edad: "X años Y meses"
   ==========================================================================*/

function recalc_age_to_doc_date(frm, dobOpt) {
  const dob =
    dobOpt ||
    (frm.__hc_patient_cache && frm.__hc_patient_cache.dob) ||
    null;

  if (!dob) {
    if (frm.get_field('pat_edadhoy')) {
      frm.set_value('pat_edadhoy', null);
    }
    return;
  }

  const baseDate = frm.doc.fecha || frappe.datetime.get_today();
  const txt = age_text(dob, baseDate);

  if (frm.get_field('pat_edadhoy')) {
    frm.set_value('pat_edadhoy', txt);
  }
}

// Devuelve "X años Y meses"
function age_text(dob, baseYmd) {
  const parts = age_parts(dob, baseYmd);
  if (parts.years == null) return null;

  const y = `${parts.years} ${parts.years === 1 ? 'año' : 'años'}`;
  const m = `${parts.months} ${parts.months === 1 ? 'mes' : 'meses'}`;

  return `${y} ${m}`;
}

// Diferencia exacta en años y meses
function age_parts(dob, baseYmd) {
  if (!dob) return { years: null, months: null };

  try {
    const birth = frappe.datetime.str_to_obj(dob);
    const base = frappe.datetime.str_to_obj(
      baseYmd || frappe.datetime.get_today()
    );

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

    return { years, months };
  } catch (e) {
    console.warn('No se pudo calcular la edad:', e);
    return { years: null, months: null };
  }
}

/* ============================================================================
   Render HTML de datos del paciente
   ==========================================================================*/

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

/* ============================================================================
   Utilidad: set_value seguro
   ==========================================================================*/

function safe_set(frm, fieldname, value) {
  if (frm && frm.fields_dict && frm.fields_dict[fieldname]) {
    frm.set_value(fieldname, value);
  }
}
