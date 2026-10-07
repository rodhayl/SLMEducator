# Informe de sesión manual parcial — instalador SLMEducator (2026-10-07)

Sesión guiada según `MANUAL_TEST2.md`, **parada por el operador** al bloquearse
el tramo B. Este informe registra lo observado; no corrige producto ni certifica
eficacia educativa, adecuación para menores, cumplimiento normativo ni calidad
de modelo.

## Artefacto y entorno usados

| Elemento | Valor |
|---|---|
| Instalador | `SLMEducator-Setup-2.0.0-fe954cab4655.exe` (build `fe954cab4655`) |
| Tamaño / SHA-256 | 31.456.307 bytes · `c02c79e21e6d04d327ed11223203c85ef95fd5b796fbc6a2c771ed5f952a1531` |
| Origen | Rama `feature/windows-installer-inno-20261006`, base `5e839d2`, construido en commit `fe954cab4655` (sin reconstruir durante la sesión) |
| Entorno | Windows 11 10.0.26200, instalación nueva en `%LOCALAPPDATA%\Programs\SLMEducator`, sin elevación, perfil del operador sin colisiones previas |
| Verificación de identidad | Registro HKCU «SLMEducator 2.0.0 (build fe954cab4655)»; EXE instalado con hash idéntico al payload verificado |

## Resultados (observado por el operador + comprobaciones del agente)

| Control | Estado | Evidencia |
|---|---|---|
| A.1 Instalación (asistente, destino nuevo, sin SmartScreen) | PASS | Operador + registro HKCU y hash del EXE instalado (agente) |
| A.2 Arranque sin Python/venv del repo | PASS | `http://localhost:8000/`; PID 3640 `SLMEducator.exe` desde la carpeta instalada (agente) |
| A.3 Login admin + rotación de contraseña en UI + re-login | PASS | Operador («¡Contraseña cambiada con éxito!», «Cerrar Sesión», re-entrada); contraseñas nunca compartidas |
| A.4 **X nativa del launcher** (pendiente histórico de la entrega) | **PASS** | Operador pulsó la X de «SLM Educator - Server Control» y aceptó «Stop the server and exit?»; agente verificó: 0 procesos `SLMEducator.exe`, puerto 8000 sin LISTENING, curl rechazado |
| A.5 Reapertura por acceso directo + persistencia | PASS | Login con la nueva contraseña tras reinicio (sin resembrado); PID 12712 desde la carpeta instalada, sin instancias/puertos inesperados |
| B.1 Crear «Docente Demo» desde la UI | **FAIL → BLOQUEA B** | Error visible `[object Object]`; log de la instancia: `POST /api/auth/register 422`. Ver `DEFICIENCIAS.md` (D3) |
| C–F (IA opcional, alumna autónoma, evaluación, privacidad) | NOT RUN | La sesión se paró al bloquearse B; la pregunta de IA nunca se hizo (inferencia real: NOT RUN) |

## Cuentas y material

- `admin`: creada por el instalador; contraseña inicial rotada por el operador
  en la UI (privada, no registrada aquí). Sigue siendo la única cuenta.
- «Docente Demo» (`docente_demo`): **no creada** (B.1 FAIL). Sin alumnos,
  cursos, evaluaciones ni prácticas: nada se llegó a crear.

## Incidencias accionables

Las tres deficiencias comunicadas por el operador — **incluida su exigencia de
rehacer y reestilar la GUI completa** — y el bug de registro con reproducción
mínima están en `DEFICIENCIAS.md` (D1 menú sin secciones, D2 estilos, D3
`[object Object]` al crear docente por `POST /api/auth/register` 422 cuya causa
la UI oculta). Registro de paso a paso en `SESSION_LOG.md`.

## Conclusión

El instalador `fe954cab4655` permitió instalar, arrancar, autenticar, rotar
contraseña, cerrar con la **X nativa** (verificado el fin del proceso y del
puerto) y reabrir con persistencia de la cuenta: **tramo A completo, 5/5 PASS**.
La creación de cuentas de personal desde la UI está **rota** (422 con error
ilegible), lo que paró la sesión: B bloqueado y C/D/E/F sin recorrer; la
inferencia real queda **NOT RUN** y no se mezcla con evidencia sintética previa.

## Handoff para el agente revisor

- Revisar la rama `feature/windows-installer-inno-20261006` (este commit;
  PR #3 hacia `test/windows-best-effort-20261006`, base documentada `5e839d2`).
- Entrada principal: `DEFICIENCIAS.md` (con la exigencia de rehacer la GUI
  completa) y `SESSION_LOG.md` (pasos y comprobaciones con sus evidencias).
- Límites: no tratar PASS de esta sesión como certificación general; no reusar
  el ZIP histórico; toda contraseña de la sesión es privada del operador y no
  está en el repositorio; la instancia instalada y sus datos sintéticos se
  conservan para el operador (no desinstalar ni limpiar automáticamente).
