import csv, pathlib

root = pathlib.Path(r"C:\Users\dhays\Github\SLMEducator\implementation_documents")
old = root / "auto_testing_2026-10-09_002" / "COVERAGE.csv"
run = root / "auto_testing_2026-10-12_001"
new_rows = [
    # case_id, manual_step, plan_id, historical_id, source_surface, role, candidate, variant, status, expected, observed, evidence_type, evidence_path, defect_id, timestamp, next_step
    ("AUTO-GEN-05.jobs_panel", "", "", "", "GEN", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Panel de trabajos guardados: lista por curso, refresco manual, cancelacion honesta (in_flight_call_may_finish)",
     "", "GUI", "", "", "2026-10-12T00:00:00", "Ejecutar tras el lote; comprobar estados por item"),
    ("AUTO-GEN-06.retry_same", "", "", "", "GEN", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Reintentar misma entrada tras error clasificado sin perder formulario ni ediciones",
     "", "GUI", "", "", "2026-10-12T00:00:00", "Provocar error real (limite de salida) y reintentar"),
    ("AUTO-GEN-07.local_draft_recovery", "", "", "", "GEN", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Recarga con borrador local de generacion: tarjeta de recuperacion, restaurar y descartar",
     "", "GUI", "", "", "2026-10-12T00:00:00", "Recargar /generar con formulario sucio"),
    ("AUTO-GEN-08.legacy_designer_card", "", "", "", "GEN", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Tarjeta de disenador legacy con borrador previo: instantanea, restaurar y descartar",
     "", "GUI", "", "", "2026-10-12T00:00:00", "Requiere borrador legacy en almacenamiento local"),
    ("AUTO-MSG-03.archive_semantics", "", "", "", "MSG", "teacher/student", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Archivar afecta a ambos participantes segun contrato; verificar desde las dos cuentas",
     "", "GUI", "", "", "2026-10-12T00:00:00", "Tras seleccion masiva"),
    ("AUTO-MSG-04.search_folders", "", "", "", "MSG", "student", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Busqueda y carpetas Enviados/Archivados; filtro, limpiar y conservacion de seleccion",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-PORT-05.import_malformed", "", "", "", "PORT", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Importar paquete vacio/malformado/tipo incorrecto: error legible sin importacion parcial silenciosa",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-SET-02.password_rotation", "", "", "", "SET", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Contrasena: validaciones, rotacion en cuenta sintetica desechable y reentrada con la nueva",
     "", "GUI", "", "", "2026-10-12T00:00:00", "Cierra el PARTIAL de AUTO-AUTH-02.password"),
    ("AUTO-LEARN-05.session_draft_recovery", "", "", "", "LEARN", "student", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Nota sin guardar en aula + recarga: dialogo de recuperacion de borrador local, restaurar y descartar",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-LEARN-06.annotations_panel", "", "", "", "LEARN", "student", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Panel de anotaciones sobre contenido: crear, asociar al material y persistir",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-LEARN-07.session_restore_readonly", "", "", "", "LEARN", "student", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Sesion completada: reabrir en solo lectura, duracion conocida vs desconocida y restauracion explícita",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-EVA-06.preview_no_attempt", "", "", "", "EVA", "student", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Vista previa de evaluacion por el alumno no inicia intento ni consume limite",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-EVA-07.attempt_local_recovery", "", "", "", "EVA", "student", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Respuestas y reloj persistidos localmente durante el intento; recarga reanuda sin duplicar",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-GRADE-04.rubric_in_grading", "", "", "", "GRADE", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Rubrica editable dentro del espacio de correccion; puntuacion coherente al guardar",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-CRS-07.homonymous_identity", "", "", "SLM-AUTO-001", "CRS", "teacher", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Cursos homonimos distinguidos por ID estable en lista, busqueda y detalle",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-SW-03.no_sw_fresh_profile", "", "", "", "SW", "", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Perfil nuevo: cero registros de Service Worker; la app no promete offline API",
     "", "GUI", "", "", "2026-10-12T00:00:00", ""),
    ("AUTO-ADMIN-02.restore_procedure_only", "", "", "", "PORT", "admin", "checkout-29df5ed+fixture-2026-10-12", "", "NOT_RUN",
     "Restauracion solo por procedimiento mantenido en destino nuevo; sin boton GUI de restore",
     "", "TECNICA", "", "", "2026-10-12T00:00:00", "Comprobar contrato por codigo/documentacion"),
]

with old.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.reader(handle))

header, carried = rows[0], rows[1:]
out = run / "COVERAGE.csv"
with out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(header)
    for row in carried:
        row = list(row)
        # Marcar procedencia: evidencia del run anterior, candidato identico.
        if row[7] == "":
            row[7] = "carried-2026-10-12-001"
        row[15] = (row[15] + " | " if row[15] else "") + "Arrastrado desde auto-2026-10-09-002 (revision 2026-10-11); mismo candidato de producto 29df5ed; no reejecutado salvo fila propia de este run."
        row[12] = "../auto_testing_2026-10-09_002/" + row[12] if row[12] else ""
        writer.writerow(row)
    for row in new_rows:
        writer.writerow(list(row))
print("carried:", len(carried), "new:", len(new_rows), "total:", len(carried) + len(new_rows) + 1)
