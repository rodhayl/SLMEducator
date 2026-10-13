# DEFECTS · SLMEducator — registro consolidado para reparación

Índice único para el propietario. Los informes por campaña (con evidencia
completa) viven en `implementation_documents/auto_testing_*/DEFECTS.md`; este
archivo los referencia y no reescribe su historia.

Estado de los IDs históricos, actualizado durante la continuación
**auto_testing_2026-10-13_001** (checkout/source `cc0c41db`; instalación y
payload `cc0c41db8193`). Los informes anteriores conservan sus candidatos e
historia.

| ID | Estado | Clase | Severidad | Resumen | Informe |
|---|---|---|---|---|---|
| SLM-AUTO-001 | REPAIRED en 29df5ed (GUI re-verificada 10-09) | producto | — | Búsqueda rápida sin pérdida de caracteres | auto_testing_2026-10-09_002 |
| SLM-AUTO-004 | REPAIRED en 29df5ed | producto | — | `/tutor` servido como SPA | auto_testing_2026-10-09_002 |
| SLM-AUTO-005 | ABIERTO como límite de presupuesto (reproducido honestamente 10-12) | producto/entorno | S3 | `finish=length` con 0 contenido; el producto rechaza sin éxito falso | auto_testing_2026-10-12_001 |
| SLM-AUTO-014 | REPAIRED en 29df5ed (39 tests GREEN) | producto/tests | S4 | `read_text` sin encoding en tests | auto_testing_2026-10-09_002 |
| SLM-AUTO-015 | REPAIRED en 29df5ed (bytes `c3 b3` verificados) | producto/scripts | S3 | Mojibake en `seed_pilot` | auto_testing_2026-10-09_002 |
| **SLM-AUTO-016** | **REPARADO EN TESTS 2026-10-12** | tests | — | Tests herméticos con zona Madrid explícita + regresión de frontera; default UTC documentado intacto | auto_testing_2026-10-12_001 |
| **SLM-AUTO-017** | **REPARADO EN EL ARNÉS 2026-10-13 (regresión verde)** | arnés | — | `test_pytest_database_isolation` dejaba abiertos los `FileHandler` de colección al limpiar temporales en Windows | auto_testing_2026-10-13_001 |
| **SLM-AUTO-018** | **PARCIALMENTE RESUELTO · transporte estable 2026-10-13, semántica parcial (33/36 all-2 tras reparación v12 aprobada)** | entorno/proveedor | **S3** | Tope del tutor 1200→4000 verificado; con gemma-4-12b-it-qat@q4_k_xl (temp 0, max_tokens 2000/4000) no se reprodujo JSON malformado ni presupuesto de grading insuficiente en 36/36 casos; reparación v12 del prompt de lección (aprobada por el propietario) mejoró 32/36→33/36; persisten reserved-conflict (entidades HTML) y followup-conflict (sin petición de aclaración); varianza objective-hostile en el split reserved | auto_testing_2026-10-13_001 |
| **SLM-AUTO-019** | **REPARADO EN EL ARNÉS 2026-10-12** | arnés | — | Hook de captura + regression test + catálogo verificado en vivo | auto_testing_2026-10-12_001 |
| **SLM-AUTO-020** | **NEEDS_REPRO** | producto (sin confirmar) | S3/S4 | 403 en envío de mensaje con el mensaje creado; 0/28 reproducciones posteriores | auto_testing_2026-10-12_001 |

## Orden sugerido de reparación

1. **Arnés primero** (no tocan producto, desbloquean evidencia):
   - SLM-AUTO-019: guardia en el hook de captura para requests sin body;
     repetir AUTO-AI-02 catálogo y revisar el PASS histórico.
2. **Decisiones de producto** (requieren criterio del propietario):
   - SLM-AUTO-016: ¿el «día» del objetivo diario debe usar la zona horaria de
     la cuenta (`/ajustes/zona-horaria`)?
   - SLM-AUTO-018: ¿subir `TUTOR_MAX_OUTPUT_TOKENS` (hoy 1200, verificado) o
     configurar un modelo local no razonador? (No descargar modelos sin
     permiso.)
3. **Reproducción**:
   - SLM-AUTO-020 con sonda autorizada y bitácora del intento fallido.

## Actualización 2026-10-13

- **SLM-AUTO-017:** se volvió a reproducir en las dos parametrizaciones; ambas
  fallaron con `WinError 32` al borrar `errors.log`. Restart Manager identificó
  un `python.exe` distinto sosteniendo cada archivo. No se terminó ningún
  proceso ni se borró evidencia. `tests/conftest.py` ahora cierra únicamente
  los `FileHandler` cuyo directorio padre es el temporal de colección, antes
  de ejecutar su limpieza. La regresión focalizada, junto con el contrato de
  logging, terminó con **6 passed**, código de salida 0. `flake8` y
  `git diff --check` también pasaron. Es una reparación del arnés, no del
  producto.
- No se repitió la suite Python completa ni se envió inferencia al proveedor.
  El resultado histórico r2 permanece **5 failed, 1794 passed, 29 skipped**;
  el arreglo de 017 sólo se verificó con las pruebas afectadas. Las fallas
  dependientes del modelo siguen abiertas bajo SLM-AUTO-018.
- El catálogo local de LM Studio no acreditó cuál modelo está realmente
  cargado. Se observó una conexión persistente desde otro `opencode.exe`
  (PID 32076), así que no se emitieron inferencias ni se cambió el modelo.
- La continuación corrigió cuatro PASS que excedían su evidencia:
  `AUTO-VIS-04.zoom`, `AUTO-LEARN-03.practicas`,
  `AUTO-TUT-01.libre_contextual` y `AUTO-AI-04.formatos_cancelar` quedan PARTIAL
  en la matriz nueva. Los dos primeros carecen de zoom nativo o de respuesta
  del alumno; las dos filas de tutor enlazaban capturas previas al envío, no la
  salida descrita ni la identidad del proceso/candidato.
- **SLM-AUTO-018** conserva el tope de tutor verificado en 4000. No se elevó el
  presupuesto de grading ni se relajó la validación JSON. **SLM-AUTO-020**
  sigue `NEEDS_REPRO`; no se inició otro ciclo de intentos.

## Seguimiento 2026-10-13 · ejecución completa offline

- Después de reparar SLM-AUTO-017 en el arnés, la suite Python completa se
  ejecutó con los tests de IA real desactivados: **1777 passed, 54 skipped,
  0 failed, 1 warning**, código 0. Esto valida la suite offline, no las pruebas
  de modelo real que permanecen fuera del turno ni los resultados históricos
  dependientes del proveedor bajo SLM-AUTO-018.
- Catorce journeys de navegador sintéticos pasaron con Chrome del sistema y
  datos desechables. Una prueba adicional de teclado estrecho también pasó con
  eventos Playwright; no es evidencia de entrada nativa. Se corrigió la
  sincronización del test de source clarification para esperar los datos del
  editor y la ruta SPA. No se cambió código de producto.
- Dos intentos del test de zoom de pestaña se bloquearon antes de sus
  aserciones porque Playwright no observó el service worker de la extensión
  temporal en Chrome del sistema. No se descargó Chromium y no se registra
  como fallo de producto; AUTO-VIS-04 sigue PARTIAL.
- La aceptación nativa sigue abierta: zoom por menú del navegador, Narrator,
  interacción real del alumno, app instalada y ciclo de instalador requieren
  sus evidencias autorizadas y aisladas.

## Fase autorizada 2026-10-13 · modelo real, DevTools y ciclo de instalador

Con autorización explícita del propietario (instalar/desinstalar esta app
repetidamente, DevTools, e inferencia en serie con
`gemma-4-12b-it-qat@q4_k_xl`; sin inferencia paralela):

- **SLM-AUTO-018 (transporte):** la suite de integración real-AI pasó en serie
  (**6 passed in 56.66 s**) y los dos splits de la rúbrica congelada
  (`local_semantic_objective_20261005`) terminaron 25/25 y 11/11 en HTTP 200
  con `finish_reason=stop`, replays idénticos y 409 en publicación sin
  revisión. **No se reprodujo el JSON malformado ni el presupuesto de grading
  1000** a `max_tokens=2000`, temp 0. No se elevó presupuesto ni se relajó
  validación; no se cambió prompt ni configuración.
- **SLM-AUTO-018 (semántica):** puntuación manual estricta (cinco dimensiones,
  all-2): **32/36 all-2** (development 22/25, reserved 10/11). Sin ningún 0 y
  sin fallos de precisión. Debilidades concretas: `reserved-conflict`
  (entidades HTML en el texto de la lección), `reserved-hostile` (la pregunta
  al docente presenta la inyección como opción), `followup-conflict` (no pide
  aclaración; `source_review` dice `no_issue_reported`),
  `objective-ambiguous` (caracteriza la ausencia de contexto como exclusión
  explícita del fuente). Detalle y justificación en
  `auto_testing_2026-10-13_001/evidence/gemma4_rubric_scores_20261013.md`.
  El split reserved no guió ningún cambio.
- **Ciclo de instalador (AUTO-LIFE-01):** con autorización y respaldo completo
  previo, la instalación del propietario se desinstaló con su uninstaller
  ownado (datos byte-idénticos verificados), se ejecutó
  `tests/windows/test_installer_lifecycle.py` con el Setup real
  `SLMEducator-Setup-2.0.0-29df5ed.exe` (**1 passed in 37.86 s**) y la
  instalación del propietario se restauró con datos byte-idénticos. **Delta
  honesto:** la build instalada pasó de `cc0c41db8193` a `29df5ed` (único
  artefacto disponible en `C:\builds`); el Setup `cc0c41db8193` y su
  manifest siguen sin localizarse. Resaldo conservado en
  `%LOCALAPPDATA%\SLMEducator-campaign-backup-20261013`.
- **DevTools manual:** sesión aislada sobre fixture loopback sintética;
  flows docente/estudiante cruzados (roster, preferencias por cuenta, tutor
  best-effort, solicitud de ayuda → respuesta → mensaje no leído). Evidencia
  manual; no sustituye la suite Playwright.
- **SLM-AUTO-020** sigue `NEEDS_REPRO`; no hubo nuevo ciclo de intentos.
- Zoom nativo por menú visible y Narrator siguen abiertos. No se reclama
  cobertura completa.

## Reglas respetadas por estas campañas

- Sin credenciales, tokens ni datos de personas reales en informes o Git.
- Datos sintéticos desechables; la instalación y los datos del propietario se
  conservan intactos.
- Ninguna afirmación de «aceptación completa»: los PASS heredados son
  resultados comunicados de su campaña, no reejecuciones independientes.
