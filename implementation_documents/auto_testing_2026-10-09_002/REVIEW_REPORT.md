# REVIEW REPORT · SLMEducator · campaña auto-2026-10-09-002

Informe de hechos de ESTA ejecución. No renumera ni sobrescribe la campaña histórica
`auto-2026-10-08-001` (117 filas intactas) ni su DEFECTS.md.

- Campaña: `AUTO_TEST.md` (con la Actualización 2026-10-08 sobre primer administrador y
  evidencia sin credenciales), run `auto-2026-10-09-002`
- Directorio: `implementation_documents/auto_testing_2026-10-09_002/`
- Fecha: 2026-10-09
- Estado: **EN CURSO** — bloqueos de exclusividad/destino/handoff abiertos

## 1. Candidato

| Elemento | Valor |
|---|---|
| Rama / HEAD | `fix/react-functional-continuation-20261007` · `19909e6038c180ce15f5e987928934d34dfc797e` (árbol `e13ba124…`) |
| Delta integrado al inicio | `e55e618` (redacción de credenciales) + `19909e6` (reparación de defectos devueltos y primer arranque), fast-forward desde `16a2dd9` con los worktrees locales intactos |
| Setup | `SLMEducator-Setup-2.0.0-19909e6038c1.exe` · SHA-256 `66839a07…6115b6` · Python 3.13.15 + Inno 6 según `docs/WINDOWS_INSTALLER.md` |
| Payload prod | 27 tablas, **0 usuarios** (cuenta-free, apto para primer arranque), hash EXE `38b7fe64…5b8697` |
| Frontend | reconstruido en esta ejecución: typecheck/lint/953 pruebas/build PASS |
| Instalado / portable | NO instalado todavía: bloqueos §7 |

Candidato construido solo con staging/salida nuevos. No se leyó ni empaquetó base ni
configuración privada. El checkout NO acredita Setup ni el EXE instalado (§1); esa
evidencia sigue pendiente.

## 2. Entorno y modo de evidencia

| Elemento | Observado |
|---|---|
| Sistema | Windows 10/11 (10.0.26200), 64 bits — ordenador del usuario |
| Visión nativa | DISPONIBLE y verificada: captura `System.Drawing.CopyFromScreen` (2560×1440) + inspección directa de la imagen |
| Entrada nativa (ratón/teclado) | Herramienta disponible (Win32 SendKeys/mouse_event) pero **NO usada**: el escritorio muestra otra sesión activa (conversación ChatGPT con actividad reciente y terminal de otro proyecto) → sin exclusividad → §1 exige suspender |
| Exclusividad | NO concedida todavía → todos los recorridos GUI con entrada quedan BLOCKED, no PASS |
| Navegador/headless | Sin Playwright/CDP/DOM para simular recorridos; la evidencia API/DOM existente es solo complementaria (pruebas ofline) |
| Lector de pantalla / zoom nativo / audio | No usados (requieren exclusividad) |
| LM Studio | `http://localhost:1234`, catálogo de 4 modelos, `slm-production-evaluation` — runtime local ya autorizado; sin proveedores de pago ni descargas |

## 3. Cobertura (124 filas; denominador explícito)

| Estado | Filas |
|---|---|
| PASS | 4 (todas `TECH-*`, alcance técnico declarado) |
| PARTIAL | 1 (`AUTO-GEN-01.leccion`, solo API) |
| FAIL | 1 (`TECH-PYTEST-AFFECTED`, por SLM-AUTO-014) |
| BLOCKED | 2 (`TECH-SETUP-INSTALL`, `AUTO-BOOT-06`) |
| NOT_RUN | 116 |
| Históricas conservadas | 117 filas de `auto-2026-10-08_001` re-listadas en NOT_RUN para este candidato; sus estados originales no se tocaron |

Las 23 filas PLAN-E/D/A/X y los recorridos GUI arrancan cuando haya exclusividad.

## 4. Defectos

### Nuevo en esta campaña

| ID | Sev | Hecho observado |
|---|---|---|
| `SLM-AUTO-014` | S4 | Dos tests Python leen con `Path.read_text()` sin `encoding='utf-8'` y en Windows cp1252 fallan: `test_first_run_setup…password_fields_are_masked` (assert silencioso) y `test_operational_documentation…removed_qt_modules` (`UnicodeDecodeError` en `docs/CONTRIBUTING.md`). Producto intacto; reproducción, diagnóstico por decodificación dual y mitigación (`PYTHONUTF8=1`) en DEFECTS.md. La verificación publicada fue en Linux y no lo reproduce. |

### Históricos 001–013 · estado en ESTE candidato (evidencia técnica; GUI pendiente)

| ID | Estado técnico aquí | Evidencia |
|---|---|---|
| 001 búsqueda rápida | Sin reproducción en los tests DOM (casos dentro de los 953) | frontend vitest |
| 002 biblioteca vacía | Reparación aprobada en tests (16 casos) | `course-material-defects.test.tsx` PASS |
| 003 claves duplicadas | Reparación aprobada en tests | idem PASS |
| 004 `/tutor` | **No reproducido**: `GET /tutor` → 200 HTML SPA | `evidence/tech_probes_002.json` |
| 005 generación 500 | Camino nuevo verificado en vivo: 502 `generation_output_limit`+`saved:false` (83.4s, log sin valores) con presupuesto 1000; **200 completo en 131.9s** con 4000. El 500 original sigue **sin causa demostrada** (su log citado no está publicado); no se inventa diagnóstico | sondas API + log del runtime sintético |
| 006 cursos homónimos | Reparación aprobada en tests | vitest PASS |
| 007 encabezados vacíos | Reparación aprobada en tests + `test_lesson_visible_fields` PASS | lote A/vitest |
| 008 rúbrica | Reparación aprobada: `trust/test_assessment_returned_ux` + workflows PASS | lote A/vitest |
| 009 vínculos autores | Reparación aprobada (mismas suites) | lote A/vitest |
| 010 avisos traducidos | Reparación aprobada (mismas suites) | lote A/vitest |
| 011 traspaso de matrícula | **Política conservada**: `trust/test_private_note_retention` PASS; sin ampliación de permisos; la decisión de retención sigue abierta | lote A |
| 012 archivos inválidos | Reparación aprobada en tests (rechazo antes de petición) | vitest PASS |
| 013 títulos históricos | Reparación aprobada; **no se reescriben títulos históricos** | vitest + `test_lesson_visible_fields` |

Ninguno de estos estados es PASS GUI: los recorridos de pantalla con entrada siguen
suspendidos por exclusividad.

## 5. Primer arranque (AUTO-BOOT-06)

- Payload verificado **sin cuentas precreadas** (0 usuarios, solo-lectura).
- El diálogo nativo del propietario **no se ha mostrado ni interactuado**: requiere
  instalación nueva + exclusividad + handoff de credenciales. El propietario introducirá
  y enviará sus credenciales; el agente nunca las teclea ni las recibe por chat.
- `tests/windows/test_packaged_bootstrap.py` sin ejecutar (solo acredita lo posterior al
  setup; además lanzaría el EXE empaquetado con ventana en escritorio compartido).

## 6. IA real (LM Studio, runtime local autorizado)

- Ajustes por cuenta guardados vía API (200): `lm_studio` + `slm-production-evaluation`.
- Truncado/limitado → **502 `generation_output_limit`, `saved:false`** con categorías
  fijas y frames en el log, sin valores de prompt/respuesta; sin reintento automático.
- Presupuesto suficiente → **200 con estructura completa** (título, 2 secciones,
  vocabulario 3, objetivos, resumen, preguntas) en 131.9s.
- Alcance: evidencia técnica API. La utilidad visible en GUI y la causa del 500
  histórico siguen abiertas. No se confundió la configuración de ejemplo (`env.properties`
  del repo, que además falla con `MissingSectionHeaderError` en el fallback y **no se
  leyó ni modificó**) con la efectiva de la cuenta.

## 7. Bloqueos pendientes

| ID | Bloqueo | Acción mínima |
|---|---|---|
| `BLK-SHARED-SCREEN` | Escritorio con otra sesión activa; sin exclusividad para ratón/teclado/foco | Que el propietario confirme escritorio libre o aisle sesión/VM |
| `BLK-INSTALL-DESTINATION` | Instalación per-user existente `fe954cab4655` con datos del usuario; prohibido in-place/desinstalar al usuario | El propietario desinstala (datos conservados) y acepta instalar el candidato, o perfil desechable |
| `BLK-HANDOFF-CREDENTIALS` | Credenciales del primer admin y logins: solo el propietario las teclea | Handoff nativo cuando se limpien los otros dos |
| `BLK-AI-GENERATION-ORIGINAL-500` | Causa del 500 original no demostrada (log citado ausente) | Repetición visible en GUI; mantener «sin causa demostrada» |

Con exclusividad concedida quedan libres: instalación, BOOT-06, los 13 defectos en GUI,
pasadas I–III, teclado/foco, zoom/DPI, lector, service worker y descargas.

## 8. Límites de este informe

- Ningún PASS de GUI nativa; ninguna aceptación nativa declarada; ninguna resolución del
  fallo original de generación por extrapolar pruebas offline.
- Sin Actions, sin `main`, sin Releases, sin binarios publicados, sin PR.
- Ninguna credencial, token, hash de credencial, base o configuración privada en estos
  artefactos ni en las evidencias; la imagen de prueba de pantalla contiene contenido de
  otra sesión y **no se publica**.
