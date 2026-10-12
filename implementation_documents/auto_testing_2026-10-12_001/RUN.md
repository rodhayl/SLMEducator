# RUN · Campaña auto-2026-10-12-001 (noche autónoma)

Encargo del propietario (2026-10-12, noche): ejecutar autónomamente las pruebas
disponibles de SLMEducator sobre el candidato vigente, mantener cobertura,
cerrar las lagunas acreditadas y dejar DEFECTS.md útil para reparación
posterior. Sin funcionalidades nuevas ni refactorizaciones; única excepción de
corrección: fallo evidente, mínimo y seguro con prueba fallida primero y
regresión después.

## Candidato y procedencia (verificada al inicio)

| Elemento | Valor |
|---|---|
| Rama | `fix/react-functional-continuation-20261007` |
| HEAD local | `dfbc15a18ec7362bf832bf0cd6e564d89710f5c0` (árbol `f3b9ae8`) |
| Remoto | `origin` misma rama, up to date (git status) |
| Último commit de producto | `29df5ed6674f660f37337d8ea69616e31600a09f`; `29df5ed..HEAD` solo documentación/evidencia (verificado `git diff --stat`) |
| Instalado | `%LOCALAPPDATA%\Programs\SLMEducator\SLMEducator.exe`, SHA-256 `12896871AE081242211CE1D75D4C06137E657ECB46E71A1A64BFD4B0FD35C949`, 16.044.355 B, fecha 2026-10-09 19:09 — **coincide** con el documentado |
| Procedencia del candidato de esta noche | checkout de trabajo (mismo código de producto que el EXE instalado) servido por el fixture mantenido `tests/browser/local_provider_server.py` |
| Cambios locales | ninguno en ficheros versionados; worktrees ajenos sin seguimiento conservados sin tocar |

## Entorno

- Windows 10/11 (10.0.26200) x64, equipo del propietario, una sola sesión
  interactiva (`dhays`, console).
- LM Studio: `http://127.0.0.1:1234`, modelo **cargado** `gemma-4-12b-it-qat@q4_k_xl`
  (estado loaded; compartido con AAC — se usa, no se descarga ni se descarga otro).
  Catálogo actual: `gemma-4-12b-it-qat@q4_k_xl`, `text-embedding-nomic-embed-text-v1.5`,
  `gemma-4-12b-it-qat@q4_0`. El modelo histórico `slm-production-evaluation`
  **ya no existe** en el catálogo de hoy (hallazgo de reconciliación).
- Chrome aislado vía MCP chrome-devtools (perfil propio, sin tocar el Chrome del
  propietario). Las caminatas GUI de esta noche se ejecutan sobre ese canal con
  evidencia de snapshot/acciones; las comprobaciones técnicas auxiliares se
  marcan TÉCNICA y nunca se presentan como GUI nativa.
- Fixture sintética desechable:
  `C:\Users\dhays\AppData\Local\Temp\opencode\slm-auto-2026-10-12-001`
  (nueva, creada por el servidor de fixture; base `synthetic.db`, `env.properties`,
  credenciales en `fixture.json` — locales, nunca publicadas).

## Desvíos respecto al histórico (registrados, no ocultados)

1. **Modelo del proveedor local**: la configuración efectiva heredada apuntaba a
   `slm-production-evaluation`, ausente del catálogo actual. Para ejecutar IA
   real se reapunta la cuenta sintética al modelo local existente y autorizado
   `gemma-4-12b-it-qat@q4_k_xl` vía la propia pantalla de ajustes (flujo
   AUTO-AI-01). No se descarga nada, no hay proveedores de pago ni claves nuevas.
2. **Canal GUI**: sin acceso GUI nativo exclusivo esta noche, las caminatas se
   ejecutan por el navegador aislado del MCP (teclado/ratón reales de página,
   snapshots de accesibilidad, capturas). Los pasos que exigen lector de
   pantalla, menú nativo de zoom del navegador o fixture legacy de Service
   Worker se registran BLOCKED/PARTIAL con el requisito exacto, no se inventan.

## Alcance de esta noche

- Suites completas mantenidas: pytest (Python) y vitest (frontend).
- Cerrar lagunas acreditadas: AUTO-GEN-02 (cada modo con petición real),
  AUTO-GEN-03 (lote parcial, parar/reintentar, edición concurrente),
  AUTO-TUT-01 (tutor libre/contextual con respuesta útil real y límite
  efectivo verificado en la captura de inferencia), AUTO-MSG-02 (selección
  masiva y resultado parcial), AUTO-PORT-04 (descarga real abierta y
  comprobada), AUTO-SW-01/02, AUTO-VIS-04 (zoom), AUTO-VIS-06 (lector).
- Cadenas secuenciales reales: autoría (fuente→generación→borrador→revisión→
  publicación→vista estudiante) y evaluación (preparación→intento→envío→
  corrección→feedback).
- Todo dato sintético de personas adultas; sin credenciales reales en
  artefactos.
