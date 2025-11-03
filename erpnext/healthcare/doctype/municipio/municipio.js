// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Municipio', {
  setup(frm) {
    // Filtra "Departamento / Estado" (ciu_coddep) por el país seleccionado (ciu_pais)
    frm.set_query('ciu_coddep', () => {
      // Si no hay país seleccionado, puedes devolver {} (sin filtro) o un filtro imposible.
      if (!frm.doc.ciu_pais) {
        // Opción 1: no aplicar filtro ({}). Verás todos los departamentos.
        // return {};

        // Opción 2 (recomendada): no mostrar nada hasta que elija país
        return { filters: { name: ['is', 'set'], 'pais_dep': '___NO_MATCH___' } };
      }

      return {
        filters: {
          // En Doctype "Departamento", el campo Link a Pais se llama "pais_dep"
          'pais_dep': frm.doc.ciu_pais
        }
      };
    });
  },

  // Cuando cambie el país, limpia el departamento para evitar combinaciones inválidas
  ciu_pais(frm) {
    if (frm.doc.ciu_coddep) {
      frm.set_value('ciu_coddep', null);
      // si tienes un Data "ciu_departamento" de sólo lectura, también se limpiará solo
    }
  }
});

