# Registro de sesión — MANUAL_TEST2 (prueba manual guiada)

Fecha de inicio: 2026-10-07. Guía: agente. Operador: David.
Informe final previsto en esta carpeta al terminar (o sesión parcial si se para).

## Artefacto verificado al inicio de sesión

- Instalador: `C:\Users\dhays\Github\SLMEducator\.manual-windows-worktree\dist\SLMEducator-installer-fe954cab4655\SLMEducator-Setup-2.0.0-fe954cab4655.exe`
- 31.456.307 bytes · SHA-256 `c02c79e21e6d04d327ed11223203c85ef95fd5b796fbc6a2c771ed5f952a1531` · versión 2.0.0 · build `fe954cab4655`
- Handoff: `implementation_documents/manual_windows_20261006/MANUAL_TEST_HANDOFF.md` (corresponde a este artefacto)
- Destino por defecto `%LOCALAPPDATA%\Programs\SLMEducator`: no existe (nuevo)
- Registro HKCU y accesos Inicio/Escritorio: sin colisiones previas
- Credencial admin inicial: archivo privado presente, no leído por el agente

## Estado del recorrido

| Tramo | Estado |
|---|---|
| A. Instalación, primer acceso y persistencia | COMPLETO (A.1–A.5 PASS) |
| B. Cuentas y materiales | BLOQUEADO (B.1 FAIL: crear docente → POST 422, la UI muestra «[object Object]») |
| C. IA opcional (pregunta única) | NOT RUN (no se llegó a preguntar) |
| D. Alumna autónoma | NOT RUN |
| E. Evaluación y revisión | NOT RUN |
| F. Privacidad y cierre | NOT RUN (sesión parada por el operador) |

## Observaciones e incidencias

- A.1 (David): instalador abierto sin advertencia de firma ni SmartScreen; asistente completado. Verificación técnica propia: registro HKCU `{40301115-8D29-4D37-A067-F025278BCDC0}_is1` con DisplayName «SLMEducator 2.0.0 (build fe954cab4655)», InstallLocation `%LOCALAPPDATA%\Programs\SLMEducator`; EXE instalado con hash idéntico al payload verificado (`e60912db…f3c230`); accesos Inicio/Escritorio creados; `slm_educator.db` y `env.properties` presentes. PASS instalación (identidad y destino confirmados).
- A.2 (David): el instalador lanzó `http://localhost:8000/`; página con «Listo para Iniciar sesión» y botón «iniciar Sesión». Verificación técnica propia: puerto 8000 en LISTENING con PID 3640, proceso `SLMEducator.exe` con ruta ejecutable `C:\Users\dhays\AppData\Local\Programs\SLMEducator\SLMEducator.exe` (instalación, no repo/venv); respuesta HTTP con título «SLM Educator». PASS arranque sin Python/venv del repo.
- A.3 (David): login `admin` correcto con la credencial del archivo privado (no compartida). Ve el «Panel»/«Resumen» con contadores a 0 (base recién creada) y menú lateral completo (Bandeja de Entrada, Mi Aprendizaje, Evaluaciones, Calificaciones, Estudiantes, Profesores, Administradores, Clasificación, Cola de Ayuda, Crear Contenido, Tutor IA, Configuración; pie «Administrator User» + «Cerrar Sesión»). PASS login admin.
- Sugerencia del operador (sin acción esta sesión): prefiere el tema claro por defecto («modo oscuro» por defecto); se registra como observación de producto, no se corrige durante la evaluación.
- A.3 rotación (David): cambio de contraseña del admin en la UI («Configuración» → «Perfil» → tarjeta «🔐 Seguridad» → «🔑 Cambiar Contraseña»); el operador vio «Contraseña cambiada con éxito». PASS rotación en UI; la nueva contraseña no se compartió.
- A.3 re-login (David): primer intento falló («no funciona»), luego confirmó que fue un error suyo y que la nueva contraseña sí entra. PASS logout («Cerrar Sesión») + re-login con la nueva; el Panel volvió a cargar. Pendiente de rigor: rechazo de la contraseña antigua se verificará tras la X nativa.
- A.4 X NATIVA (David + agente): el operador pulsó la X de «SLM Educator - Server Control», vio el diálogo «Exit — Stop the server and exit?» y aceptó con «Sí». Verificación técnica dirigida propia: sin procesos `SLMEducator.exe` (tasklist), puerto 8000 sin LISTENING (solo TIME_WAIT residuales) y `curl` rechazado (http_code=000). **PASS X nativa** — cierre humano acreditado por el operador + terminación verificada por el agente.
- A.5 reapertura (David + agente): reabrió por el acceso directo instalado y entró con la contraseña nueva (el Panel cargó). Verificación técnica propia: puerto 8000 LISTENING con PID 12712, `ExecutablePath` en la carpeta instalada; dos procesos del mismo exe (launcher 1208 + servidor 12712), sin instancias ni puertos inesperados; la cuenta no se resembra (la contraseña nueva sigue válida tras reinicio). **PASS A.5 — tramo A completo.**
- B.1 FAIL (David + agente): crear «Docente Demo» desde «Profesores» → «Crear» → «Crear cuenta» falló. La UI mostró el error literal `[object Object]` (captura del operador; el campo Rol mostraba «Docente»). Evidencia del log de la instancia instalada (`%LOCALAPPDATA%\Programs\SLMEducator\logs\slm_educator.log`): `POST /api/auth/register HTTP/1.1" 422`. Diagnóstico desde el código (sin modificar producto): `AuthService.register` (static/js/auth.js) hace `throw new Error(err.detail || 'Registration failed')`; con `detail` estructurado de un 422 (FastAPI) el mensaje se stringifica como `[object Object]`, ocultando el motivo real. Sin reintento automático; la cuenta no se creó (comprobado: solo un POST 422 en el log).
- Cierre de sesión: el operador decidió parar aquí. Sesión parcial; los tramos dependientes de B quedan sin recorrer. Inferencia real: NOT RUN.
