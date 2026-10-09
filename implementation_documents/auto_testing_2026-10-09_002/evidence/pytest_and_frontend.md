# Evidencia técnica · frontend y suites Python (auto-2026-10-09-002)

## Frontend (`src/frontend`, candidato 19909e6)

| Paso | Resultado |
|---|---|
| `npm ci --ignore-scripts` | PASS — 319 paquetes, 0 vulnerabilidades |
| `npm run typecheck` | PASS (exit 0) |
| ESLint (`src/frontend/src` + `tests/frontend`) | PASS — ejecución directa del binario con ruta Windows; el script npm `lint` usa `cd ../.. && ruta/con/barras`, sintaxis que `cmd.exe` no ejecuta (y no hay `script-shell` configurado). Se registra como observación de entorno, no como fallo de lint. |
| `npm test` (vitest) | PASS — **953 pruebas en 52 ficheros**, 192.39s, 0 fallos |
| `npm run build` | PASS — 26 assets locales verificados, 29 registros de licencia |

Logs crudos locales (no publicados):

| Log | SHA-256 |
|---|---|
| `C:\builds\slm-fe-test2.log` | `7e2d47ec965a73e34d136d1deeda9f79b2d4a4c53d2fc3b8a650c6063b77f1f50` |
| `C:\builds\slm-fe-lint5.log` | `451ec9b8e9b24b8105c8f8a7eb23591600fcc323a79dfb09fc24848f8d6a1d13` |
| `C:\builds\slm-fe-build.log` | `7c51b1c8bbd78b8c14e3250736d7ce3827e2564225098e22e022b8d7824495ed` |

Los 953 incluyen los ficheros de regresión de los defectos devueltos:
`course-material-defects.test.tsx` (002/003/006/007/012/013 + casos 001), 
`assessments-workflows.test.tsx` / `assessments-contracts.test.ts` (008/009/010), 
`foundation-safety.test.tsx` (bordes de error), `people-flows.test.tsx` (001/PEO), 
`course-list-continuity.test.tsx`, `authoring-flows.test.tsx`.

## Suites Python (venv del repo, Python 3.14.7, Windows, locale cp1252)

Lote A (`test_build_package`, `test_seed_admin`, `test_first_run_setup`, 
`test_generation_diagnostics`, `test_lesson_visible_fields`, `test_frontend_delivery`, 
`test_launcher_lifecycle`, `trust/test_assessment_returned_ux`, 
`trust/test_private_note_retention`):

- **353 passed, 1 failed, 1 warning en 112.05s**
- El único fallo: `test_first_run_setup::test_native_errors_are_allowlisted_and_password_fields_are_masked` → `SLM-AUTO-014` (codificación del test, no del producto)

Lote B (`test_lesson_generation_contract`, `test_practice_option_contract`, 
`trust/test_provider_transport_contract`, `trust/test_ai_generation_boundaries`, 
`test_operational_documentation`):

- **153 passed, 1 failed, 1 warning en 22.12s**
- El único fallo: `test_operational_documentation::test_active_ui_guides_do_not_prescribe_removed_qt_modules` → `UnicodeDecodeError` por la misma causa → `SLM-AUTO-014`

Puerta AGENTS.md (`tests/test_build_package.py tests/test_seed_admin.py -q`): ambas dentro del lote A y **aprobadas**.

Logs crudos locales (no publicados):

| Log | SHA-256 |
|---|---|
| `C:\builds\slm-pytest-batchA.log` | `95d1f0a21a3953dda587962bc302c689494f89291234b590b3147f11704cca24` |
| `C:\builds\slm-pytest-batchB.log` | `525c608795b6c3c25a7bb818a9f50be3980c3a3569fc02899b7a7048eeaea71de` |
