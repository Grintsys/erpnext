/*
* LEAF ERP v14 - Share Sales Invoice PDF via Native OS Share Sheet
* Zero-Fork extension for Sales Invoice DocType
*/

frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			// Add Compartir action button
			frm.page.add_inner_button(__('Compartir PDF'), function() {
				leaf_share_sales_invoice(frm);
			});

			frm.add_custom_button(__('Compartir PDF'), function() {
				leaf_share_sales_invoice(frm);
			}, __('Acciones'));
		}
	}
});

function leaf_share_sales_invoice(frm) {
	// 1. Get available print formats
	let print_formats = frappe.meta.get_print_formats(frm.doctype) || ['Standard'];
	let default_format = (frm.meta && frm.meta.default_print_format) || print_formats[0] || 'Standard';

	if (print_formats.length > 1) {
		// Show dialog to select Print Format if multiple exist
		let d = new frappe.ui.Dialog({
			title: __('Compartir Factura - Seleccionar Formato'),
			fields: [
				{
					label: __('Formato de Impresión'),
					fieldname: 'print_format',
					fieldtype: 'Select',
					options: print_formats,
					default: default_format,
					reqd: 1
				},
				{
					label: __('Incluir Encabezado (Letterhead)'),
					fieldname: 'no_letterhead',
					fieldtype: 'Check',
					default: 0
				}
			],
			primary_action_label: __('Compartir'),
			primary_action: function(values) {
				d.hide();
				execute_pdf_share(frm, values.print_format, values.no_letterhead);
			}
		});
		d.show();
	} else {
		execute_pdf_share(frm, default_format, 0);
	}
}

async function execute_pdf_share(frm, print_format, no_letterhead) {
	frappe.show_progress(__('Generando PDF...'), 30, 100);

	try {
		// 2. Fetch PDF from LEAF robust PDF endpoint
		const params = $.param({
			doctype: frm.doctype,
			name: frm.doc.name,
			format: print_format,
			no_letterhead: no_letterhead ? 1 : 0
		});
		const pdf_url = frappe.urllib.get_full_url('/api/method/leaf.controllers.share_analytics.download_pdf?' + params);

		const response = await fetch(pdf_url);
		if (!response.ok) {
			throw new Error(__('No se pudo generar el PDF de la factura.'));
		}

		frappe.show_progress(__('Generando PDF...'), 80, 100);
		const blob = await response.blob();
		frappe.hide_progress();

		const file_name = `${frm.doc.name}.pdf`;
		const pdf_file = new File([blob], file_name, { type: 'application/pdf' });

		// 3. Check Native Web Share API with file support
		if (navigator.canShare && navigator.canShare({ files: [pdf_file] })) {
			try {
				await navigator.share({
					files: [pdf_file],
					title: frm.doc.name,
					text: __('Factura {0}', [frm.doc.name])
				});
				log_share_event(frm.doctype, frm.doc.name, print_format, 'native');
			} catch (shareErr) {
				if (shareErr.name !== 'AbortError') {
					console.warn('Share API error, fallback to download:', shareErr);
					trigger_fallback_download(blob, file_name, frm, print_format);
				}
			}
		} else {
			// 4. Fallback when Web Share API is unavailable
			trigger_fallback_download(blob, file_name, frm, print_format);
		}
	} catch (err) {
		frappe.hide_progress();
		frappe.msgprint({
			title: __('Error al Compartir'),
			message: err.message || __('Ocurrió un error al preparar la factura.'),
			indicator: 'red'
		});
	}
}

function trigger_fallback_download(blob, file_name, frm, print_format) {
	const link = document.createElement('a');
	link.href = URL.createObjectURL(blob);
	link.download = file_name;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);

	frappe.msgprint({
		title: __('Compartir Factura'),
		message: __('El dispositivo o navegador actual no permite compartir archivos directamente desde LEAF. La factura en formato PDF se ha descargado en su dispositivo para que pueda compartirla manualmente.'),
		indicator: 'orange'
	});

	log_share_event(frm.doctype, frm.doc.name, print_format, 'fallback');
}

function log_share_event(doctype, name, print_format, share_method) {
	frappe.call({
		method: 'leaf.controllers.share_analytics.log_share_event',
		args: {
			doctype: doctype,
			name: name,
			print_format: print_format,
			share_method: share_method
		},
		callback: function(r) {
			// Silent analytics callback
		}
	});
}
