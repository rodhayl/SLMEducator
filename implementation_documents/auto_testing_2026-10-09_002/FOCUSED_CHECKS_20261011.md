# Comprobaciones focalizadas independientes · 2026-10-11

Fuente fijada: 386593bf6d40f444c2428423d7bb8163bd7fad50, producto 29df5ed6674f660f37337d8ea69616e31600a09f. Solo lectura de producto. Sin instalaciones de dependencias, llamadas reales de IA, navegador, GUI nativa ni cambios en el ordenador de David.

## Service Worker

- PASS técnico: `tests/frontend/foundation-worker-retirement.test.ts`, archivo existente sin modificar: 5/5 pruebas, Vitest 4.1.11, Node 24.19.0; 193 ms. Configuración mínima de revisión con alias `@` al árbol descargado y entorno Node; se reutilizó un runtime ya disponible. No equivale al check completo del frontend.
- El helper `requestLegacyWorkerUpdate` solicita actualización solo a registro con origen/scope raíz/script `/sw.js` exactos. No registra en origen nuevo, no adopta registro con worker ajeno, no elimina query de URL y no hace unregister/reload por su cuenta. Los cinco tests cubren estas ramas.
- PASS técnico: cuerpo existente y sin modificar de `test_retirement_only_deletes_recognized_caches_after_activation` ejecutado mediante AST, con constante `RETIREMENT_WORKER` extraída de la fuente real. Ejecuta Node, no un navegador. Comprueba ausencia de borrado antes de activate; borrado exclusivo de `slm-educator-v22-session-locale` y `slm-educator-v22-session-locale-auth-validation`; conservación de nombres desconocidos y `another-app`; unregister al finalizar. Código de salida 0.
- `src/frontend_delivery.py` confirma retirada únicamente tras activación normal, sin skipWaiting, clients.claim, navegación, recarga, acceso a localStorage/IndexedDB ni interceptación fetch.
- Sigue sin probarse aquí la migración real de dos pestañas/borradores/fixture legacy ni red interrumpida. Los casos GUI no se promueven por estos resultados.

## Tutor y presupuesto IA

- `src/core/services/ai_service.py` fija `TUTOR_MAX_OUTPUT_TOKENS = 1200`. `output_token_limit` toma el mínimo positivo entre presupuesto solicitado/configurado; tutor configurado a 4000 sigue limitado a 1200. `tests/trust/test_provider_transport_contract.py` lo especifica expresamente.
- `require_complete_response` rechaza finish_reason/done_reason `length` o `max_tokens` aunque el JSON parcial sea parseable. No se atribuye a un 200 HTTP éxito educativo.
- `_parse_tutoring_response` ya admite prosa ordinaria como answer; rechaza fragmentos estructurados, JSON escalar o respuestas sin campo utilizable. No se justifica relajar el parser por el simple argumento «el modelo devolvió texto en lugar de JSON».
- `useAIRequest.ts` requiere recibo válido, estado completed, política vigente y asistencia efectiva coincidente antes de aceptar resultado; cambios de identidad/contexto/política impiden entregar resultado obsoleto.
- INTENTO DE TESTS BLOQUEADO ANTES DE EJECUCIÓN: provider_transport_contract y tutor_text_fallback, copiados sin cambios y con imports del núcleo real, no alcanzaron tests porque el runtime disponible carece de `structlog`. No se instaló nada ni se sustituyó el módulo por mocks. Primer intento también carecía de variables efímeras de test y chocó con HOME no escribible; se corrigió usando las variables temporales equivalentes al conftest, sin crear credenciales persistentes, y el bloqueo final fue structlog. No hay un resultado FAIL del producto.
- Conclusión: ningún defecto simple nuevo demostrado. Hace falta recibo/log actual correlacionado y saneado para explicar el tutor no utilizable; subir configuración a 4000 no aumenta por sí solo el límite del tutor.

## G6

AUTO_TEST.md §13 define G6 como inventario/diagnóstico de deuda de código compartido, sin PASS GUI ni refactor de campaña. CONTINUITY_GAPS_20261007.md conserva consolidación más amplia como trabajo separado y explica qué adapters/hooks permanecieron sin cambio. Se corrige la asociación errónea de G6 a honestidad ante límites del proveedor; no se abre una refactorización ni se declara completada una auditoría semántica completa.

## Cierre del bloqueo offline · 2026-10-11 10:01 UTC

El intento inicial descrito arriba queda resuelto para los dos archivos de pruebas indicados. **79 PASS, 0 FAIL, 0 ERROR, 0 SKIP**, código de salida 0, duración comunicada por pytest 6,05 s:
- `tests/trust/test_provider_transport_contract.py`: 52 PASS.
- `tests/trust/test_tutor_text_fallback.py`: 27 PASS.

Fuente de esta ejecución: `dfbc15a18ec7362bf832bf0cd6e564d89710f5c0`, rama `fix/react-functional-continuation-20261007`. GitHub confirma que desde el producto `29df5ed6674f660f37337d8ea69616e31600a09f` solo hay cambios documentales y evidencia. Los 36 archivos de núcleo reutilizados y los dos tests coinciden byte por byte con sus blobs Git del SHA probado. Antes de ejecutar se eliminó exclusivamente un salto de línea final extra introducido por la materialización anterior; no se modificó comportamiento ni se sustituyeron imports del producto.

Preparación: Python 3.12.14 en Linux, entorno virtual aislado; requisitos de aplicación sin modificar de `requirements.txt` y `pytest==9.0.2` de `requirements-dev.txt`, obtenidos de `https://pypi.org/simple`. Esto incluye el requisito existente `structlog==25.5.0`, ausente en el intento inicial. `uv pip check --python .venv/bin/python`: 47 paquetes compatibles. No se cambiaron requisitos ni se añadieron dependencias al repositorio.

Comando de pruebas: `python -m pytest tests/trust/test_provider_transport_contract.py tests/trust/test_tutor_text_fallback.py -q -ra --strict-markers --basetemp=<temporal aislado> --junitxml=<evidencia local>`; ejecutado mediante `pytest.main` con esos mismos argumentos. Entorno: `SLM_OFFLINE_TESTS=1`, `USE_REAL_AI=0`, `SLM_TEST_MODE=1`, `PYTHONUTF8=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. HOME, configuración mínima, base de datos y logs fueron temporales y sintéticos; las claves efímeras se generaron en memoria, sin credenciales persistentes. Se utilizó el conftest existente, incluido su bloqueo de transporte HTTP, y las respuestas sintéticas ya definidas por los tests.

Resultado: se comprueban los adaptadores, límites de presupuesto y aceptación/rechazo del texto del tutor. No se demuestra un fallo nuevo de producto ni se explica por sí solo la respuesta no utilizable observada en la GUI. Sin inferencia real, llamadas pagadas, pruebas nativas, reconstrucción, reinstalación ni acceso a cuentas o datos del usuario. No se actualizan la matriz de aceptación ni GUIDED_TEST.md; esto no constituye aceptación GUI ni suite completa.
