# SUMMARY · auto-2026-10-12-001 (noche autónoma)

Encargo: probar todas las funcionalidades disponibles sobre el candidato
vigente, mantener cobertura, cerrar lagunas acreditadas y dejar DEFECTS.md útil.
Sin funciones nuevas ni refactorizaciones. Corrección de producto intentada:
**ninguna** (no se encontró fallo evidente, mínimo y seguro con prueba fallida
previa; los defectos hallados requieren decisión de contrato o son de arnés).

## Candidato

- Checkout `fix/react-functional-continuation-20261007` HEAD
  `dfbc15a18ec7362bf832bf0cd6e564d89710f5c0` (producto `29df5ed`; solo cambios
  documentales desde entonces, verificado con `git diff --stat`).
- Instalado `%LOCALAPPDATA%\Programs\SLMEducator\SLMEducator.exe` SHA-256
  `12896871…C949` — coincide con el documentado; no se reinstaló ni se tocó.
- Fixture sintético desechable nuevo (`local_provider_server.py`, puerto 8092,
  base nueva en `%TEMP%\opencode\slm-auto-2026-10-12-001-r2`).
- Navegador: Chrome headless aislado propio (puerto 9223, perfil propio) tras
  perder el canal MCP a mitad de noche; todas las interacciones fueron eventos
  reales de teclado/ratón/DOM sobre la aplicación servida.

## Cobertura (COVERAGE.csv, 147 casos)

| Estado | Casos |
|---|---|
| PASS | 118 |
| PARTIAL | 8 |
| BLOCKED | 5 |
| NOT_RUN | 15 |
| FAIL (arnés) | 1 |

- 126 casos arrastrados desde `auto-2026-10-09-002` (mismo candidato de
  producto; estados conservados, no reejecutados salvo fila propia).
- 17 casos nuevos añadidos al denominador (jobs de generación, reintento,
  recuperación local, tarjeta legacy, semántica de archivado, búsqueda de
  mensajes, importación malformada, rotación de contraseña, borrador de aula,
  anotaciones, sesión completada, previa sin intento, recuperación local de
  intento, rúbrica en corrección, homónimos, perfil sin SW, restore por
  procedimiento) + 4 técnicas de esta noche.
- **No es aceptación completa**: 15 NOT_RUN (tiempo de la noche), 5 BLOCKED
  heredados, 8 PARTIAL. Los PASS heredados siguen siendo resultados
  comunicados, no reejecutados.

## Ejecutado esta noche (evidencia propia)

- **Suites completas**: pytest `15 failed, 1783 passed, 29 skipped` (clasificados
  en SLM-AUTO-016/017/018) · vitest `967 passed (967)`.
- **IA real por cuenta/proveedor**: teacher_a con lm_studio; proveedor real
  descubierto hoy (modelo cargado `gemma-4-12b-it-qat@q4_k_xl`, sustitución
  verificada). Generación real de lección/ejercicio/plan/estructura/paquete,
  lote con autoSave, tutor libre con respuesta útil. **Límite efectivo del
  tutor verificado: 1200 tokens** pese a 4000 configurados (captura de
  inferencia).
- **Lagunas acreditadas cerradas**: AUTO-GEN-02 (5 modos), AUTO-GEN-05 (jobs
  con estado Fallido honesto), AUTO-GEN-06 (reintento), AUTO-GEN-07
  (recuperación local), AUTO-MSG-02 (**parcial 1/3 sin duplicados**),
  AUTO-PORT-04 (**descarga abierta y verificada, sin secretos**), AUTO-SW-03
  (perfil nuevo sin SW), AUTO-VIS-03 (teclado real), AUTO-REG-03 (caducidad de
  sesión en vivo).
- **Parciales con diagnóstico**: AUTO-TUT-01 (libre PASS; contextual bloqueado
  por límite efectivo + modelo razonador, rechazo honesto), AUTO-GEN-03 (lote
  ejecutado y persistido; «parar tras el ítem» sin verificar por duración),
  AUTO-AI-02 (conexión PASS; catálogo roto por arnés SLM-AUTO-019).

## Defectos abiertos (DEFECTS.md)

| ID | Clase | Severidad | Resumen |
|---|---|---|---|
| SLM-AUTO-016 | producto | S3 | Objetivo diario con base de fechas distinta al día local |
| SLM-AUTO-017 | arnés | S4 | Limpieza de temporales en Windows (WinError 32) |
| SLM-AUTO-018 | entorno/proveedor | S3 | Tutor contextual y 11 AI e2e con modelo sustituto razonador |
| SLM-AUTO-019 | arnés | S3 | Hook de captura rompe catálogo (GET sin body) |
| SLM-AUTO-020 | producto (sin confirmar) | S3/S4 | NEEDS_REPRO: 403 con mensaje creado |

Sin pérdida de datos, exposición ni falso éxito observados en ningún camino.

## Bloqueos vigentes

- **BLK-LEGACY-SW**: sin fixture legacy autorizada → AUTO-SW-01/02 siguen
  BLOCKED (las pruebas mantenidas de retirada del worker son evidencia
  técnica, no la transición de dos pestañas).
- **BLK-LECTOR**: sin canal autorizado de lector de pantalla → AUTO-VIS-06.
- **BLK-ZOOM-NATIVO**: sin menú nativo de zoom del navegador por canal
  automatizado → AUTO-VIS-04 sigue PARTIAL.
- **BLK-INSTALL-DESTINATION / HANDOFF**: primera cuenta y ciclo de instalación
  nativos siguen bloqueados (instalación del propietario conservada intacta).

## Próxima acción concreta

1. Correcciones de arnés SLM-AUTO-017 y SLM-AUTO-019 (prueba fallida primero).
2. Decisión del propietario sobre SLM-AUTO-016 (¿día por zona horaria de la
   cuenta?) y SLM-AUTO-018 (modelo local no razonador o subir
   `TUTOR_MAX_OUTPUT_TOKENS`).
3. Reintentos de SLM-AUTO-020 con sonda autorizada.
4. Cerrar NOT_RUN por tiempo: MSG-03, PORT-05, SET-02, LEARN-05/06/07,
   EVA-06/07, GRADE-04, CRS-07, ADMIN-02, GEN-03 (parar tras el ítem con
   `exerciseCount=1`).

## Recursos propios abiertos

- Fixture server 127.0.0.1:8092 (PID de `venv\Scripts\python.exe` con
  `local_provider_server.py`) — detenible por su PID.
- Chrome headless aislado puerto 9223 (perfil propio en temp) — detenible.
- Credenciales del fixture solo en `fixture.json` local (nunca publicadas).
