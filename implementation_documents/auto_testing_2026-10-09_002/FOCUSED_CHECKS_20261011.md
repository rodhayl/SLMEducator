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
