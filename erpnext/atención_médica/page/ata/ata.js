frappe.pages['ata'].on_page_load = function(wrapper) {

	var page = frappe.ui.make_app_page({

		parent: wrapper,

		title: 'ATA',

		single_column: true

	});


	// ==========================================================
	// FECHA INICIAL
	// ==========================================================
	//
	// Se mantiene mañana porque actualmente tienes citas
	// para el 19/09/2026 y así podemos continuar probando.
	//
	// Cuando quieras regresar a hoy:
	//
	// frappe.datetime.get_today()
	//
	// ==========================================================

	var default_date = frappe.datetime.add_days(
		frappe.datetime.get_today(),
		1
	);


	// ==========================================================
	// ESTADO INICIAL
	// ==========================================================

	var default_status = 'Pendiente';


	// ==========================================================
	// HTML
	// ==========================================================

	$(wrapper).find('.layout-main-section').html(`

		<div class="ata-page">


			<!-- ================================================= -->
			<!-- HEADER                                            -->
			<!-- ================================================= -->

			<div class="ata-header">

				<div class="ata-header-left">

					<div class="ata-icon">
						<i class="fa fa-stethoscope"></i>
					</div>

					<div>

						<div class="ata-title">
							ATA
						</div>

						<div class="ata-subtitle">
							Agenda de Atención Médica
						</div>

					</div>

				</div>


				<div class="ata-doctor">

					<div class="ata-doctor-icon">
						<i class="fa fa-user-md"></i>
					</div>

					<div>

						<div class="ata-doctor-label">
							Profesional
						</div>

						<div
							id="ata-professional"
							class="ata-doctor-name"
						>
							Cargando...
						</div>

					</div>

				</div>

			</div>


			<!-- ================================================= -->
			<!-- FILTROS                                           -->
			<!-- ================================================= -->

			<div class="ata-filter-card">

				<div class="ata-filter-title">

					<i class="fa fa-filter"></i>

					<span>
						Filtrar citas
					</span>

				</div>


				<div class="ata-filters">


					<!-- ========================================= -->
					<!-- FECHA                                     -->
					<!-- ========================================= -->

					<div class="ata-filter">

						<label>
							Fecha de cita
						</label>

						<div class="ata-input-wrapper">

							<i class="fa fa-calendar"></i>

							<input
								type="date"
								id="ata-date"
								class="ata-input"
								value="${default_date}"
							>

						</div>

					</div>


					<!-- ========================================= -->
					<!-- ESTADO                                    -->
					<!-- ========================================= -->

					<div class="ata-filter">

						<label>
							Estado
						</label>

						<div class="ata-input-wrapper">

							<i class="fa fa-list"></i>

							<select
								id="ata-status"
								class="ata-input"
							>

								<option
									value="Pendiente"
									selected
								>
									Pendiente
								</option>

								<option
									value="Atendido"
								>
									Atendido
								</option>

							</select>

						</div>

					</div>


					<!-- ========================================= -->
					<!-- BUSCAR PACIENTE                            -->
					<!-- ========================================= -->

					<div class="ata-filter ata-filter-search">

						<label>
							Buscar paciente
						</label>

						<div class="ata-input-wrapper">

							<i class="fa fa-search"></i>

							<input
								type="text"
								id="ata-search"
								class="ata-input"
								placeholder="Nombre o código del paciente"
							>

						</div>

					</div>


					<!-- ========================================= -->
					<!-- BOTONES                                   -->
					<!-- ========================================= -->

					<div class="ata-filter-buttons">

						<button
							id="ata-search-button"
							class="btn btn-primary ata-btn-search"
						>

							<i class="fa fa-search"></i>

							Buscar

						</button>


						<button
							id="ata-clear-button"
							class="btn btn-default ata-btn-clear"
						>

							<i class="fa fa-refresh"></i>

							Limpiar

						</button>

					</div>

				</div>

			</div>


			<!-- ================================================= -->
			<!-- RESUMEN                                           -->
			<!-- ================================================= -->

			<div class="ata-summary">

				<div class="ata-summary-left">

					<div class="ata-summary-icon">

						<i class="fa fa-calendar-check-o"></i>

					</div>


					<div>

						<div class="ata-summary-title">
							Mis citas
						</div>

						<div
							id="ata-selected-date"
							class="ata-summary-date"
						>
							-
						</div>

					</div>

				</div>


				<div class="ata-counter">

					<span
						id="ata-total"
						class="ata-counter-number"
					>
						0
					</span>

					<span class="ata-counter-label">
						citas
					</span>

				</div>

			</div>


			<!-- ================================================= -->
			<!-- TABLA                                             -->
			<!-- ================================================= -->

			<div class="ata-table-card">

				<div class="ata-table-wrapper">

					<table class="ata-table">

						<thead>

							<tr>

								<th>
									Hora
								</th>

								<th>
									Paciente
								</th>

								<th>
									Servicio
								</th>

								<th>
									Unidad
								</th>

								<th>
									Tipo de cita
								</th>

								<th>
									Estado
								</th>

								<th class="ata-actions-header">
									Acciones
								</th>

							</tr>

						</thead>


						<tbody id="ata-appointments">

						</tbody>

					</table>

				</div>


				<!-- ================================================= -->
				<!-- FOOTER                                           -->
				<!-- ================================================= -->

				<div class="ata-table-footer">

					<div>

						<i class="fa fa-info-circle"></i>

						Mostrando las citas correspondientes
						al médico autenticado.

					</div>


					<div>

						Total:

						<strong id="ata-total-footer">
							0
						</strong>

					</div>

				</div>

			</div>

		</div>

	`);


	// ==========================================================
	// ESTILOS
	// ==========================================================

	var styles = `

		/* ======================================================
		   CONTENEDOR
		====================================================== */

		.ata-page {

			padding: 25px 30px 40px 30px;

			background: #f7f9fb;

			min-height: calc(100vh - 100px);

			font-family: Arial, Helvetica, sans-serif;

		}


		/* ======================================================
		   HEADER
		====================================================== */

		.ata-header {

			display: flex;

			align-items: center;

			justify-content: space-between;

			background: #ffffff;

			border-radius: 10px;

			padding: 20px 25px;

			margin-bottom: 20px;

			border: 1px solid #e4e9ee;

			box-shadow: 0 2px 8px rgba(0,0,0,0.04);

		}


		.ata-header-left {

			display: flex;

			align-items: center;

			gap: 15px;

		}


		.ata-icon {

			width: 48px;

			height: 48px;

			border-radius: 10px;

			background: #eaf3ff;

			color: #2878c8;

			display: flex;

			align-items: center;

			justify-content: center;

			font-size: 21px;

		}


		.ata-title {

			font-size: 24px;

			font-weight: 600;

			color: #263238;

			line-height: 1.2;

		}


		.ata-subtitle {

			font-size: 13px;

			color: #7b8794;

			margin-top: 3px;

		}


		/* ======================================================
		   DOCTOR
		====================================================== */

		.ata-doctor {

			display: flex;

			align-items: center;

			gap: 12px;

			padding-left: 20px;

			border-left: 1px solid #e5e9ed;

		}


		.ata-doctor-icon {

			width: 38px;

			height: 38px;

			border-radius: 50%;

			background: #edf8f2;

			color: #2e9b65;

			display: flex;

			align-items: center;

			justify-content: center;

		}


		.ata-doctor-label {

			font-size: 11px;

			text-transform: uppercase;

			color: #89949e;

			letter-spacing: .5px;

		}


		.ata-doctor-name {

			font-size: 14px;

			font-weight: 600;

			color: #36434d;

			margin-top: 2px;

		}


		/* ======================================================
		   FILTROS
		====================================================== */

		.ata-filter-card {

			background: #ffffff;

			border: 1px solid #e4e9ee;

			border-radius: 10px;

			padding: 20px 22px;

			margin-bottom: 18px;

			box-shadow: 0 2px 8px rgba(0,0,0,0.035);

		}


		.ata-filter-title {

			display: flex;

			align-items: center;

			gap: 8px;

			font-size: 14px;

			font-weight: 600;

			color: #3d4a54;

			margin-bottom: 16px;

		}


		.ata-filter-title i {

			color: #2878c8;

		}


		.ata-filters {

			display: flex;

			align-items: flex-end;

			gap: 15px;

			flex-wrap: wrap;

		}


		.ata-filter {

			flex: 1;

			min-width: 180px;

		}


		.ata-filter-search {

			flex: 1.6;

		}


		.ata-filter label {

			display: block;

			font-size: 12px;

			font-weight: 600;

			color: #65717c;

			margin-bottom: 7px;

		}


		.ata-input-wrapper {

			position: relative;

			display: flex;

			align-items: center;

		}


		.ata-input-wrapper > i {

			position: absolute;

			left: 12px;

			color: #89949e;

			z-index: 2;

		}


		.ata-input {

			width: 100%;

			height: 38px;

			border: 1px solid #d6dde3;

			border-radius: 6px;

			background: #ffffff;

			padding: 0 12px 0 34px;

			font-size: 13px;

			color: #36434d;

			outline: none;

			transition:
				border-color .15s,
				box-shadow .15s;

			box-sizing: border-box;

		}


		.ata-input:focus {

			border-color: #66afe9;

			box-shadow:
				0 0 0 2px rgba(102,175,233,.12);

		}


		select.ata-input {

			cursor: pointer;

		}


		.ata-filter-buttons {

			display: flex;

			gap: 8px;

			height: 38px;

		}


		.ata-btn-search {

			height: 38px;

			padding: 0 17px;

			border-radius: 6px;

			font-size: 13px;

		}


		.ata-btn-clear {

			height: 38px;

			padding: 0 14px;

			border-radius: 6px;

			font-size: 13px;

		}


		/* ======================================================
		   SUMMARY
		====================================================== */

		.ata-summary {

			display: flex;

			align-items: center;

			justify-content: space-between;

			margin-bottom: 12px;

		}


		.ata-summary-left {

			display: flex;

			align-items: center;

			gap: 10px;

		}


		.ata-summary-icon {

			width: 35px;

			height: 35px;

			border-radius: 7px;

			background: #eaf3ff;

			color: #2878c8;

			display: flex;

			align-items: center;

			justify-content: center;

		}


		.ata-summary-title {

			font-size: 15px;

			font-weight: 600;

			color: #36434d;

		}


		.ata-summary-date {

			font-size: 12px;

			color: #89949e;

			margin-top: 2px;

		}


		.ata-counter {

			background: #ffffff;

			border: 1px solid #e2e8ed;

			border-radius: 20px;

			padding: 5px 13px;

		}


		.ata-counter-number {

			font-weight: 700;

			color: #2878c8;

			font-size: 14px;

		}


		.ata-counter-label {

			font-size: 12px;

			color: #7c8791;

			margin-left: 3px;

		}


		/* ======================================================
		   TABLA
		====================================================== */

		.ata-table-card {

			background: #ffffff;

			border: 1px solid #e0e6eb;

			border-radius: 10px;

			overflow: hidden;

			box-shadow: 0 2px 8px rgba(0,0,0,0.035);

		}


		.ata-table-wrapper {

			width: 100%;

			overflow-x: auto;

		}


		.ata-table {

			width: 100%;

			border-collapse: collapse;

			margin: 0;

			font-size: 13px;

		}


		.ata-table thead th {

			background: #f5f7f9;

			color: #687580;

			font-size: 11px;

			text-transform: uppercase;

			letter-spacing: .3px;

			font-weight: 600;

			padding: 13px 12px;

			border-bottom: 1px solid #dfe5ea;

			white-space: nowrap;

		}


		.ata-table tbody td {

			padding: 13px 12px;

			border-bottom: 1px solid #edf0f2;

			color: #4d5963;

			vertical-align: middle;

		}


		.ata-table tbody tr {

			transition: background .12s;

		}


		.ata-table tbody tr:hover {

			background: #f8fbfe;

		}


		.ata-table tbody tr:last-child td {

			border-bottom: none;

		}


		.ata-time {

			font-weight: 600;

			color: #35424d;

			white-space: nowrap;

		}


		.ata-patient-name {

			font-weight: 600;

			color: #36434d;

		}


		.ata-patient-id {

			font-size: 11px;

			color: #9aa4ac;

			margin-top: 3px;

		}


		.ata-actions-header {

			text-align: center;

		}


		.ata-actions {

			text-align: center;

			white-space: nowrap;

		}


		/* ======================================================
		   BOTONES
		====================================================== */

		.ata-action-btn {

			width: 34px;

			height: 31px;

			padding: 0;

			margin: 0 2px;

			border-radius: 5px;

			border: 1px solid #d9e0e5;

			background: #ffffff;

			color: #66737d;

			transition: all .15s;

		}


		.ata-action-btn:hover {

			background: #f1f6fb;

			border-color: #b9cee0;

			color: #2878c8;

		}


		/* ======================================================
		   ESTADOS
		====================================================== */

		.ata-status {

			display: inline-block;

			padding: 5px 9px;

			border-radius: 12px;

			font-size: 11px;

			font-weight: 600;

			white-space: nowrap;

		}


		.ata-status-pendiente {

			background: #fff6df;

			color: #a27600;

		}


		.ata-status-atendido {

			background: #e9f7ef;

			color: #2c8b5b;

		}


		/* ======================================================
		   EMPTY
		====================================================== */

		.ata-empty {

			text-align: center;

			padding: 55px 20px;

		}


		.ata-empty-icon {

			width: 58px;

			height: 58px;

			border-radius: 50%;

			background: #f1f4f6;

			color: #9aa5ad;

			display: flex;

			align-items: center;

			justify-content: center;

			margin: 0 auto 14px;

			font-size: 22px;

		}


		.ata-empty-title {

			font-size: 14px;

			font-weight: 600;

			color: #5d6973;

		}


		.ata-empty-text {

			font-size: 12px;

			color: #9aa3aa;

			margin-top: 5px;

		}


		/* ======================================================
		   LOADING
		====================================================== */

		.ata-loading {

			text-align: center;

			padding: 45px 20px;

			color: #8c979f;

			font-size: 13px;

		}


		.ata-loading i {

			margin-right: 7px;

		}


		/* ======================================================
		   FOOTER
		====================================================== */

		.ata-table-footer {

			display: flex;

			justify-content: space-between;

			align-items: center;

			padding: 12px 15px;

			background: #fafbfc;

			border-top: 1px solid #edf0f2;

			color: #8b969e;

			font-size: 11px;

		}


		.ata-table-footer i {

			margin-right: 5px;

		}


		.ata-table-footer strong {

			color: #596670;

		}


		/* ======================================================
		   RESPONSIVE
		====================================================== */

		@media (max-width: 900px) {

			.ata-header {

				flex-direction: column;

				align-items: flex-start;

				gap: 18px;

			}


			.ata-doctor {

				border-left: none;

				border-top: 1px solid #e5e9ed;

				padding-left: 0;

				padding-top: 15px;

				width: 100%;

			}


			.ata-filter {

				min-width: 220px;

			}

		}


		@media (max-width: 600px) {

			.ata-page {

				padding: 15px;

			}


			.ata-filters {

				display: block;

			}


			.ata-filter {

				margin-bottom: 12px;

			}


			.ata-filter-buttons {

				margin-top: 5px;

			}


			.ata-table-footer {

				display: block;

			}

		}

	`;


	$('head').append(
		'<style id="ata-page-styles">' +
		styles +
		'</style>'
	);


	// ==========================================================
	// FUNCIONES AUXILIARES
	// ==========================================================


	function format_date(date) {

		if (!date) {
			return '-';
		}

		var parts = date.split('-');

		if (parts.length !== 3) {
			return date;
		}

		return parts[2] +
			'/' +
			parts[1] +
			'/' +
			parts[0];

	}


	function get_status_class(status) {

		if (status === 'Pendiente') {

			return 'ata-status ata-status-pendiente';

		}


		if (status === 'Atendido') {

			return 'ata-status ata-status-atendido';

		}


		return 'ata-status';

	}


	function update_selected_date() {

		var date =
			$('#ata-date').val();

		$('#ata-selected-date').text(
			'Fecha: ' + format_date(date)
		);

	}


	// ==========================================================
	// CARGAR CITAS
	// ==========================================================

	function load_appointments() {

		var appointment_date =
			$('#ata-date').val();


		var status =
			$('#ata-status').val();


		var search =
			$.trim(
				$('#ata-search').val()
			);


		update_selected_date();


		// ------------------------------------------------------
		// LOADING
		// ------------------------------------------------------

		$('#ata-appointments').html(`

			<tr>

				<td colspan="7">

					<div class="ata-loading">

						<i class="fa fa-spinner fa-spin"></i>

						Cargando citas...

					</div>

				</td>

			</tr>

		`);


		$('#ata-total').text('...');

		$('#ata-total-footer').text('...');


		// ------------------------------------------------------
		// REQUEST
		// ------------------------------------------------------

		frappe.call({

			method:
				'erpnext.atención_médica.page.ata.ata.get_appointments',

			args: {

				appointment_date:
					appointment_date,

				status:
					status,

				search:
					search

			},

			callback: function(r) {

				if (!r.message) {

					render_empty();

					return;

				}


				var data = r.message;


				// --------------------------------------------------
				// PROFESIONAL
				// --------------------------------------------------

				if (data.professional) {

					$('#ata-professional').text(
						data.professional
					);

				}


				// --------------------------------------------------
				// CITAS
				// --------------------------------------------------

				render_appointments(
					data.appointments || []
				);

			},


			error: function() {

				$('#ata-appointments').html(`

					<tr>

						<td colspan="7">

							<div class="ata-empty">

								<div class="ata-empty-icon">

									<i class="fa fa-exclamation-triangle"></i>

								</div>


								<div class="ata-empty-title">

									No fue posible cargar las citas

								</div>


								<div class="ata-empty-text">

									Verifica la conexión e intenta nuevamente.

								</div>

							</div>

						</td>

					</tr>

				`);


				$('#ata-total').text('0');

				$('#ata-total-footer').text('0');

			}

		});

	}


	// ==========================================================
	// RENDERIZAR CITAS
	// ==========================================================

	function render_appointments(appointments) {

		var tbody =
			$('#ata-appointments');


		tbody.empty();


		$('#ata-total').text(
			appointments.length
		);


		$('#ata-total-footer').text(
			appointments.length
		);


		// ------------------------------------------------------
		// SIN RESULTADOS
		// ------------------------------------------------------

		if (!appointments.length) {

			render_empty();

			return;

		}


		// ------------------------------------------------------
		// CITAS
		// ------------------------------------------------------

		appointments.forEach(
			function(appointment) {


				var patient_name =
					appointment.patient_name ||
					appointment.patient ||
					'Sin paciente';


				var status_class =
					get_status_class(
						appointment.status
					);


				var actions = '';


				// ==================================================
				// PENDIENTE
				// ==================================================

				if (
					appointment.status ===
					'Pendiente'
				) {

					actions = `

						<button

							class="ata-action-btn btn-ata"

							title="Agregar ATA al usuario"

							data-name="${appointment.name}"

						>

							<i class="fa fa-user-plus"></i>

						</button>

					`;

				}


				// ==================================================
				// ATENDIDO
				// ==================================================

				else if (
					appointment.status ===
					'Atendido'
				) {


					// ==============================================
					// YA EXISTE RECETA
					// ==============================================

					if (
						appointment.receta_name
					) {

						actions = `

							<button

								class="ata-action-btn btn-recipe"

								title="Editar receta"

								data-name="${appointment.receta_name}"

							>

								<i class="fa fa-pencil"></i>

							</button>

						`;

					}


					// ==============================================
					// NO EXISTE RECETA
					// ==============================================

					else {

						actions = `

							<button

								class="ata-action-btn btn-recipe-new"

								title="Crear receta"

								data-name="${appointment.name}"

								data-date="${appointment.appointment_date}"

							>

								<i class="fa fa-file-text-o"></i>

							</button>

						`;

					}

				}


				// ==================================================
				// FILA
				// ==================================================

				var row = $(`

					<tr>


						<!-- ====================================== -->
						<!-- HORA -->
						<!-- ====================================== -->

						<td>

							<div class="ata-time">

								${appointment.start_hour || '--:--'}

							</div>

							<div class="ata-patient-id">

								${appointment.end_hour || ''}

							</div>

						</td>


						<!-- ====================================== -->
						<!-- PACIENTE -->
						<!-- ====================================== -->

						<td>

							<div class="ata-patient-name">

								${patient_name}

							</div>

							<div class="ata-patient-id">

								${appointment.patient || ''}

							</div>

						</td>


						<!-- ====================================== -->
						<!-- SERVICIO -->
						<!-- ====================================== -->

						<td>

							${appointment.service || '-'}

						</td>


						<!-- ====================================== -->
						<!-- UNIDAD -->
						<!-- ====================================== -->

						<td>

							${appointment.unit || '-'}

						</td>


						<!-- ====================================== -->
						<!-- TIPO -->
						<!-- ====================================== -->

						<td>

							${appointment.appointment_type || '-'}

						</td>


						<!-- ====================================== -->
						<!-- ESTADO -->
						<!-- ====================================== -->

						<td>

							<span
								class="${status_class}"
							>

								${appointment.status || 'Sin estado'}

							</span>

						</td>


						<!-- ====================================== -->
						<!-- ACCIONES -->
						<!-- ====================================== -->

						<td class="ata-actions">

							${actions}

						</td>


					</tr>

				`);


				tbody.append(row);

			}
		);


		// ======================================================
		// PENDIENTE - AGREGAR ATA
		// ======================================================

		tbody.find('.btn-ata').on(
			'click',
			function() {

				var appointment =
					$(this).data('name');


				frappe.msgprint({

					title:
						'Agregar ATA al Usuario',

					message:
						'Esta funcionalidad está pendiente de desarrollo.',

					indicator:
						'orange'

				});

			}
		);


		// ======================================================
		// ATENDIDO - CREAR RECETA
		// ======================================================

		tbody.find('.btn-recipe-new').on(
			'click',
			function() {

				var appointment =
					$(this).data('name');


				var date =
					$(this).data('date');


				// ==============================================
				// CREAR NUEVO DOCUMENTO
				// ==============================================

				frappe.new_doc(
					'Receta Medica',
					{

						cita_medica:
							appointment,

						date:
							date

					}
				);

			}
		);


		// ======================================================
		// ATENDIDO - EDITAR RECETA
		// ======================================================

		tbody.find('.btn-recipe').on(
			'click',
			function() {

				var recipe =
					$(this).data('name');


				// ==============================================
				// ABRIR RECETA EXISTENTE
				// ==============================================

				frappe.set_route(
					'Form',
					'Receta Medica',
					recipe
				);

			}
		);

	}


	// ==========================================================
	// SIN RESULTADOS
	// ==========================================================

	function render_empty() {

		$('#ata-total').text('0');

		$('#ata-total-footer').text('0');


		$('#ata-appointments').html(`

			<tr>

				<td colspan="7">

					<div class="ata-empty">

						<div class="ata-empty-icon">

							<i class="fa fa-calendar-o"></i>

						</div>


						<div class="ata-empty-title">

							No se encontraron citas

						</div>


						<div class="ata-empty-text">

							No existen citas para los filtros seleccionados.

						</div>

					</div>

				</td>

			</tr>

		`);

	}


	// ==========================================================
	// BOTON BUSCAR
	// ==========================================================

	$('#ata-search-button').on(
		'click',
		function() {

			load_appointments();

		}
	);


	// ==========================================================
	// ENTER EN BUSQUEDA
	// ==========================================================

	$('#ata-search').on(
		'keypress',
		function(e) {

			if (e.which === 13) {

				load_appointments();

			}

		}
	);


	// ==========================================================
	// CAMBIO DE FECHA
	// ==========================================================

	$('#ata-date').on(
		'change',
		function() {

			load_appointments();

		}
	);


	// ==========================================================
	// CAMBIO DE ESTADO
	// ==========================================================

	$('#ata-status').on(
		'change',
		function() {

			load_appointments();

		}
	);


	// ==========================================================
	// LIMPIAR
	// ==========================================================

	$('#ata-clear-button').on(
		'click',
		function() {

			$('#ata-date').val(
				default_date
			);


			$('#ata-status').val(
				default_status
			);


			$('#ata-search').val(
				''
			);


			load_appointments();

		}
	);


	// ==========================================================
	// PRIMERA CARGA
	// ==========================================================

	load_appointments();

};