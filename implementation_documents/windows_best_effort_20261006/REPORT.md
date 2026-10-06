# Validación Windows best-effort

Fecha: 2026-10-06. Rama propia: `test/windows-best-effort-20261006`.
Base de aplicación: `e7152b3a801a003158261b87c7ecadc23a7fd2f7`, árbol
`4e2a5afa5985eb7ec72142c9b512789343ef20b7`.
Candidato congelado y probado: `3fdfe5bfa53dfc56b846df4e25d6e01a72ba6335`, árbol
`669e81ffd66053a6b44b6a231b694e8cc0d0f7a0`.
La diferencia contiene únicamente arnés/tests de aceptación; `src`, `scripts`,
traducciones y documentación previa conservan exactamente la base indicada.
El commit posterior de entrega añade solo este informe y evidencias saneadas.

## Resultado

| Control | Estado | Evidencia y alcance |
|---|---|---|
| Python afectado final | PASS | 291 tests, cero fallos; incluye packaging/bootstrap, tutor, parser/prosa, transporte, ciclo de solicitudes, asistencia, privacidad, recursos, revisión/publicación y notas provisionales |
| DOM final Windows | PASS | 197 tests, cero fallos |
| Chrome real EN/ES | PASS | Dos recorridos completos con servidor propio y proveedor sintético; lectura asignada y tutor/Q&A, sin sesión de navegador de profesor |
| Estructura y prosa | PASS | `_call_ai` simulado; parser, API y UI reales; respuesta `suggestion`, recibo `completed`, Markdown visible y aviso localizado de respuesta no verificada |
| Renderizado seguro | PASS | Respuestas con script/imagen hostiles no crean esos elementos ni ejecutan el marcador de prueba |
| Fallo de formato/proveedor | PASS | JSON incompleto sigue siendo fallo; excepción del proveedor sigue siendo fallo; recibos `failed`, motivo visible y pregunta conservada |
| Reintento explícito | PASS | Tutor y Q&A: conteo de peticiones estable durante espera, segunda petición solo por nuevo clic; tutor emite UUID nuevo tras fallo terminal |
| Lint/tipos/sintaxis | PASS | flake8 E9,F63,F7,F82 sobre ai_service y tres archivos de aceptación; mypy ai_service con follow-imports=silent; sintaxis dashboard.js; git diff --check; pip check |
| Build Windows nativo | PASS | BAT documentado, Python 3.13, PyInstaller real, `--prod` y salida nueva; staging aislado, sin SQLite de usuario |
| EXE: arranque/login/reinicio | PASS | Base admin incluida, CWD distinto, PATH solo System32, sin PYTHONPATH/PYTHONHOME/VIRTUAL_ENV; rotación, reinicio, contraseña inicial rechazada y token antiguo revocado |
| Inferencia real/selección de modelo | NOT RUN | Excluidas expresamente; ninguna inferencia ni descarga de modelos |
| Actions | NOT RUN | Ninguna consulta ni ejecución |
| X nativa, recuperación, zoom, SW, hardware | NOT RUN | No se repiten comprobaciones físicas históricas sin cambio relevante; X nativa sigue pendiente según el informe previo |
| Validación pedagógica/piloto humano | NOT RUN | Fuera de este encargo; no se declara eficacia educativa ni compatibilidad universal |

FAIL funcional final: ninguno. BLOCKED final: ninguno en los controles solicitados.
Una advertencia deprecada de Starlette/AnyIO no impide los tests.
Resumen verificable: [verification.json](verification.json); capturas EN/ES en
`screenshots/`. Los avisos de incertidumbre están localizados; los detalles de
fallo actuales de API permanecen en inglés también en ES, como límite visible.

## Aislamiento y ejecución

Checkout: `C:\Users\dhays\Github\SLMEducator\.windows-best-effort-worktree`.
Windows 11 10.0.26200, Python 3.13.15, PyInstaller 6.16.0,
Playwright 1.63.0 con Chrome instalado en contexto/perfil aislado,
Node 24.21.0, npm 11.19.0. Dependencias directas fijadas del proyecto;
`pip check` pasa. No se afirma pinning de todas las dependencias transitivas.

Cada suite utiliza bases sintéticas desechables. El navegador usa el arnés
`tests/browser/local_server.py`, puerto efímero, directorio nuevo y transporte
saliente bloqueado. Las cuentas docentes se usan por API solo para preparar
revisión/publicación/asignación antes de los recorridos; durante ellos solo
hay sesión de navegador de `learner_a`. No existe requisito de presencia
docente para lectura o tutor. La preferencia de idioma se guarda en esa cuenta.

El arnés añade cuatro marcadores explícitos de pregunta, sin cambiar la
aplicación: estructura válida, prosa, formato inválido y excepción del proveedor.
No sustituye las salidas históricas ni puntúa contenido semántico. Las pruebas
Python mantienen los controles de autoría, acceso ajeno, publicación revisada,
asistencia durante evaluaciones y calificación provisional. Los tests de parser
siguen rechazando JSON roto y escalares; authoring/grading no reciben fallback.

Fallo inicial conservado: Node y flake8 multiproceso fallaron por restricciones
del sandbox antes de ejecutar tests. Node pasa con ejecución permitida;
flake8 pasa serial. La creación del entorno requirió ejecución permitida por
fallo inicial de ensurepip. El primer recorrido EN falló porque localStorage
no sustituye la preferencia ES guardada en el servidor; se corrigió el arnés
para guardar EN en la cuenta sintética. ES ya pasaba. Luego EN/ES pasan y la
comprobación ampliada de reintento Q&A pasa. No se reprodujo defecto de producto.

El candidato quedó congelado antes de la última pasada Python/DOM. Los tests
Chrome y EXE corresponden a los mismos archivos congelados. No se repiten
arranques físicos posteriores para generar más evidencia. Se cerraron solo
procesos hijos de prueba y árboles de EXE lanzados por su PID; no se detuvieron
Gemma, Trading ni aplicaciones preexistentes. No se inspeccionaron bases,
configuración privada o credenciales del usuario.

## Reproducción

En entorno nuevo, instalar `requirements-dev.txt` y `pyinstaller==6.16.0` con
Python 3.13. Ejecutar las rutas afectadas enumeradas en `verification.json` con
`SLM_OFFLINE_TESTS=1`, `USE_REAL_AI=0`, `--basetemp` nuevo y `-q`.
Packaging/bootstrap están incluidos:
`python -m pytest tests/test_build_package.py tests/test_seed_admin.py -q`.
DOM: `npm ci --ignore-scripts --prefix tests/ui` y `npm test --prefix tests/ui`.

Chrome: `SLM_BROWSER_ACCEPTANCE=1`, `SLM_BROWSER_EXECUTABLE` al Chrome local,
`SLM_BROWSER_ARTIFACTS` a una carpeta nueva; ejecutar
`python -m pytest tests/browser/test_best_effort_journey.py -q --basetemp=RUTA_NUEVA`.
No activar `SLM_OFFLINE_TESTS` para ese recorrido porque necesita HTTP loopback;
el arnés bloquea los transportes de proveedores y las rutas externas del browser.

Build realizado:
`build_package.bat --prod --output-dir "dist\SLMEducator Best Effort Windows 20261006"`.
Contraseña inicial aleatoria proporcionada únicamente al entorno del proceso.
Smoke opt-in: `SLM_PACKAGED_EXE` al EXE nuevo y `SLM_PACKAGED_INITIAL_PASSWORD`
privada; ejecutar `tests/windows/test_packaged_bootstrap.py` una sola vez contra
un paquete sintético nuevo (rota la contraseña).

## Artefacto local y límites

Carpeta portable completa:
`C:\Users\dhays\Github\SLMEducator\.windows-best-effort-worktree\dist\SLMEducator Best Effort Windows 20261006`.
Archivo local de esa carpeta tras el smoke, sin cambios de binarios:
`C:\Users\dhays\Github\SLMEducator\.windows-best-effort-worktree\dist\SLMEducator Best Effort Windows 20261006.zip`.

- ZIP: 37.140.055 bytes; SHA-256 `87a5d1f08bc324b49c7a93ab6a92c94ea7763df7725c29287ad2d39f65b4004e`.
- EXE: 15.960.120 bytes; SHA-256 `d04e76ebd8a4807c69d9a0ff883eeb2b9e14509d0be8860a5275f578357f066c`.

El ZIP identifica el artefacto sintético local posterior al smoke: incluye la
base sintética y estado/logs de esa prueba. No se distribuye ni se sube a Git.
La prueba rota una contraseña aleatoria; no se ofrece como paquete de instalación
con credencial compartida. Registros locales, bases, configuración y secretos
quedan fuera del commit. Solo se publican tests, resultados resumidos y capturas
sin credenciales/tokens. El paquete es portable, no un instalador universal.

Pendientes concretos conservados: X nativa del launcher, piloto humano y
validación pedagógica; proveedores/modelos alternativos y otras plataformas
sin certificar. Los resultados semánticos históricos permanecen inalterados.
Se entrega este cierre funcional y se detiene el trabajo sin otra auditoría.
