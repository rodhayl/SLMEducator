# SESSION_LOG · auto-2026-10-12-001

Registro secuencial real de esta ejecución. Sin credenciales ni secretos.

- 2026-10-12 (noche) · Inicio. Reconciliación: HEAD `dfbc15a`, remoto al día,
  producto `29df5ed` sin cambios posteriores de código (`git diff --stat`),
  EXE instalado `12896871…` coincide. Worktrees ajenos conservados.
- Reconciliación de proveedor: catálogo LM Studio actual sin
  `slm-production-evaluation`; modelo cargado `gemma-4-12b-it-qat@q4_k_xl`
  (compartido con AAC — usado, no descargado ni modificado). Verificada la
  sustitución: LM Studio responde con el modelo cargado a cualquier nombre.
- Creación de `implementation_documents/auto_testing_2026-10-12_001/` y estado
  sintético nuevo en `%TEMP%\opencode\slm-auto-2026-10-12-001-r2`
  (puerto 8092).
- Suites lanzadas en background: pytest completo (sin PYTHONUTF8, gate real de
  Windows) y vitest completo.
- **00:48** Fixture server sembrando base sintética (docentes/estudiantes
  sintéticos, curso piloto con acentos correctos).
- **GUI**: login teacher_a por formulario → `/inicio` PASS.
- **AUTO-AI-01**: config efectiva observada (modelo histórico ausente hoy);
  guardado + recarga verificados; «Probar conexión» real (200, ~4,4 s ×2).
  Catálogo → 500 por defecto del arnés (SLM-AUTO-019); el producto sí recibió
  200 con JSON válido.
- **AUTO-GEN**: límite 1000 → `finish=length`, 0 contenido, rechazo honesto
  «No se guardó ninguna propuesta» (evidencia guardada). Subida verificada a
  4000 → lección generada (134 s) con contenido útil y editable. Ejercicio
  (4 opciones, clave C), plan (3 unidades × 2), estructura (adoptada y guardada
  como curso 2) y paquete (solo-vista, 0 de 2 guardados, propuestas editables).
- **Caducidad JWT (30 min)** observada 2 veces: «Hay que verificar tu sesión» +
  «El resultado es desconocido. Tu texto se conserva»; reautenticación limpia.
  Pérdida de propuestas temporales = contrato documentado en la UI.
- **AUTO-TUT-01**: libre PASS (respuesta real útil; límite efectivo **1200**
  verificado en la captura pese a 4000 configurados). Contextual: «No se
  confirmó una sugerencia utilizable»; diagnóstico con inference.jsonl:
  prompt 4215 chars + 1200 tokens → `finish=length`, 0 contenido.
- **Preparación de mensajería**: 20+ mensajes sintéticos creados vía API.
  Dos 403 con mensaje creado (SLM-AUTO-020, NEEDS_REPRO; 28/28 posteriores OK).
  Política verificada: `learner_b → teacher_a` 403 correcto (no es su docente).
- **AUTO-MSG-02**: selección múltiple (3) + borrado masivo con concurrencia →
  «Cambios confirmados: 1 de 3. No se confirmó el resto» + error 404 honesto +
  «Una operación podría haberse completado» + tercer mensaje NO reintentado.
- **AUTO-PORT-02/04**: preview docente (inclusiones/exclusiones, soluciones
  incluidas) → descarga real `course-1-teacher.json` (7566 B) abierta e
  inspeccionada: JSON válido, sin secretos.
- **AUTO-SW-03**: perfil nuevo → 0 registros SW, sin controller, sin caches.
- **AUTO-VIS-03**: recorrido por teclado real (Tab en orden, sin trampas).
- **AUTO-GEN-03/05**: lote ejecutado (esquema → curso 2 → «Generar temas
  elegidos»); recibos duraderos por ítem (Lección/Ejercicios, estado Listo y un
  Fallido honesto); 11 contenidos persistidos; estado incierto manejado honesto.
  «Parar tras el ítem» no verificado (cada paquete ≈10 min).
- **Cambio de canal**: el catálogo de herramientas retiró chrome-devtools a
  mitad de la noche; se reconstruyó el canal con un cliente CDP propio (stdlib)
  sobre un Chrome headless aislado (puerto 9223, perfil en temp). Sin foco
  robado ni interacción con aplicaciones ajenas.
- **Suites al cierre**: pytest 15 failed/1783 passed/29 skipped (clasificados:
  SLM-AUTO-016 base de fechas — pasan aislados; SLM-AUTO-017 limpieza Windows;
  SLM-AUTO-018 AI e2e con modelo sustituto). vitest 967/967 PASS.
- Documentación cerrada: COVERAGE (147 casos), DEFECTS (016–020), SUMMARY,
  RESUME, DEFECTS.md raíz. Commits normales en la rama de trabajo + push.
