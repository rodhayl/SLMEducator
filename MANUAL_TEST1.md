# SLMEducator: preparar un instalador nuevo para mi prueba manual

## Prompt para el agente de desarrollo en Windows

Trabaja en `rodhayl/SLMEducator`. Quiero un **instalador Windows real y recién construido**, listo para que yo, David, haga después la prueba guiada de `MANUAL_TEST2.md`. Este encargo es finito: prepara, comprueba, entrega y detente. No necesitas ser Codex ni usar comandos especiales de objetivos.

### Punto de partida y lectura obligatoria

1. Lee `AGENTS.md`, `README.md`, `docs/CONTRIBUTING.md`, `docs/FUNCTIONAL_REQUIREMENTS.md`, `docs/AI_REQUESTS_AND_OPERATIONS.md`, los scripts de packaging/bootstrap y este informe:
   https://github.com/rodhayl/SLMEducator/blob/5e839d2b0bc0bb89309f49eac648a6eee747cd79/implementation_documents/windows_best_effort_20261006/REPORT.md
2. Base de entrega documentada: commit `5e839d2b0bc0bb89309f49eac648a6eee747cd79`, árbol `673b386dc19f140c143859edfd8545640ae5bb6d`, rama `test/windows-best-effort-20261006`. Su candidato probado fue `3fdfe5bfa53dfc56b846df4e25d6e01a72ba6335`, árbol `669e81ffd66053a6b44b6a231b694e8cc0d0f7a0`. El commit posterior añadió documentación/evidencias. Verifica estos datos una vez; no rehagas su investigación histórica.
3. Conserva estos prompts aunque estén en una rama documental descendiente. Trabaja en una rama/worktree propia derivada de esa base, sin tocar `main`, descartar trabajo ajeno ni publicar automáticamente. Si el checkout contiene cambios posteriores de producto, identifica la diferencia y pide decisión antes de cambiar de base.
4. La evidencia anterior cubre 291 tests Python, 197 DOM, Chrome EN/ES con proveedor sintético y build/arranque/login/reinicio de EXE. No demuestra inferencia real ni un instalador. El ZIP histórico de 37.140.055 bytes, SHA-256 `87a5d1f08bc324b49c7a93ab6a92c94ea7763df7725c29287ad2d39f65b4004e`, contiene estado sintético **posterior al smoke**, base, logs y credenciales rotadas. No lo reutilices, distribuyas ni llames instalador.

### Límites de esta preparación

- Construye en Windows nativo. Comprueba entorno, permisos y herramientas antes de actuar. Si falta acceso a Windows o a un compilador permitido, informa del bloqueo concreto; no fabriques un `.exe` ni lo sustituyas silenciosamente por ZIP o ejecución desde fuente.
- Usa solo bases nuevas y desechables propias. No abras, copies, reinicialices, migres ni empaquetes bases, configuraciones privadas o claves de instalaciones existentes.
- No fuerces un LLM. No descargues modelos ni consultes proveedores cloud/de pago. No lances una nueva campaña semántica, búsqueda de modelos, auditoría global o repetición de suites históricas.
- No consultes ni ejecutes GitHub Actions; no publiques Releases, binarios, ramas o PR sin una instrucción adicional. Puedes preparar los cambios y un commit local revisable.
- No pares Gemma, Trading ni procesos preexistentes. Usa puertos disponibles y registra el URL real; no asumas un puerto libre ni mates su ocupante. Solo puedes cerrar procesos que hayas lanzado para esta prueba y cuya identidad/ruta hayas comprobado.
- No cambies requisitos para obtener resultados perfectos. La integridad de la aplicación, los errores honestos, los permisos, la revisión/publicación y las notas subjetivas provisionales sí se conservan. La calidad de un modelo se observará con incertidumbre explícita.

### 1. Añadir solo el empaquetado necesario

En la base indicada, `build_package.bat` delega en `scripts/build_package.py` y produce una carpeta portable PyInstaller `onedir`. No hay una receta de instalador Inno/MSI mantenida. Verifica si eso sigue siendo cierto en tu rama.

Si no existe, implementa la **mínima receta mantenida de Inno Setup** y su invocación documentada para envolver la salida de producción nueva. Reutiliza el builder y `scripts/seed_admin.py`; no inventes otro seeder ni un framework de migraciones. Mantén cualquier ajuste de producto estrictamente limitado a un impedimento demostrado de instalación/arranque y añade la regresión correspondiente.

Requisitos del instalador:

- Instalación por usuario, sin privilegios de administrador, en una carpeta nueva escribible bajo `LOCALAPPDATA`. El launcher congelado resuelve actualmente rutas relativas desde su EXE; respeta ese contrato o justifica y prueba el ajuste mínimo. No instales la base junto a un EXE en una carpeta de solo lectura.
- Identidad propia de SLMEducator, independiente de AAC; nombre/versión/identificador de build trazables al commit. Carpeta de salida nueva. Acceso directo y entrada de desinstalación coherentes con la instalación real.
- Payload completo del `onedir`; nunca el EXE aislado. Solo binarios/recursos necesarios, configuración generada desde valores públicos y la base **recién creada** con su administrador exclusivo para esta entrega privada. No incluyas alumnos, cursos, fixtures, conversaciones, logs del smoke, credenciales en texto, claves locales ni datos anteriores.
- Diferencia los archivos del programa de los datos mutables. La base y configuración inicial solo se crean si no existen; nunca se sobrescriben al reinstalar. La desinstalación conserva datos/configuración del usuario y no borra carpetas genéricas con comodines. Si actualizar una instalación existente no puede hacerse con garantías, recházalo con un mensaje claro y usa un destino nuevo; no improvises una migración.
- No incluyas cierre forzado genérico por nombre de proceso, ejecución oculta de servicios, descargas de dependencias/modelos ni llamadas externas al instalar. Si un archivo de una instalación está ocupado, pide cerrar esa instancia o cancela limpiamente.
- Usa Inno Setup ya instalado si está disponible. Si falta, identifica la herramienta oficial y solicita la autorización necesaria para instalarla. No eludas permisos, protecciones de Windows o avisos de seguridad.

### 2. Crear un payload limpio y credenciales privadas

1. Usa el Python/Tcl-Tk que realmente permite el build; la combinación documentada es Python 3.13 y PyInstaller 6.16.0. Comprueba las versiones presentes y el preflight Tcl/Tk; no lo saltes para usar el layout zipfs de Python 3.14. Instala dependencias explícitamente en un entorno aislado cuando esté autorizado; el arranque de la aplicación nunca debe instalarlas.
2. Construye con el modo `--prod` y un `--output-dir` nuevo y absoluto. No uses `--test --database` para el instalador. El builder debe fallar si ya existe la salida.
3. Conserva el bootstrap create-only. Para esta instalación, genera una contraseña aleatoria única de al menos 12 caracteres y entrégala por un mecanismo **local privado** que yo pueda consultar; por ejemplo, la salida privada del terminal o un archivo fuera del repo con acceso restringido a mi cuenta. Si no puedes mantenerla privada, para y pídeme que la introduzca localmente. No la escribas en el chat, comandos compartidos, historial, capturas, logs publicables, manifiestos o Git. No uses una contraseña de ejemplo.
4. El usuario inicial es `admin`; informa de cómo obtener la contraseña de manera privada y de la rotación en el primer acceso. No pruebes credenciales de otras instalaciones ni uses variables bootstrap para recuperar cuentas existentes.
5. Conserva una fuente prístina del payload antes de cualquier ejecución. Compila el instalador desde esa fuente nueva. Nunca reconstruyas el instalador desde el directorio ya ejecutado por el smoke. El instalador está destinado a mi instalación privada de evaluación; no es un paquete universal reutilizable con un mismo hash de contraseña.

### 3. Verificar antes de pasarme trabajo técnico

Haz tú estas comprobaciones de ingeniería, con evidencia saneada y alcance limitado:

1. Ejecuta `python -m pytest tests/test_build_package.py tests/test_seed_admin.py -q` con base temporal nueva. Añade y ejecuta únicamente los tests afectados por la nueva receta y por cualquier corrección necesaria. Usa el modo offline/sintético adecuado para esos tests; identifica siempre los mocks como mocks. No sustituyas una prueba Windows por freezer simulado de Linux.
2. Congela los archivos de producto/packaging y registra commit, estado del árbol y versiones. Construye un instalador Windows real. Calcula su tamaño y SHA-256; conserva el hash del EXE instalado para identificarlo.
3. Instala **ese mismo archivo** en una ubicación desechable propia y comprueba que la instalación termina, crea los accesos esperados y arranca sin Python del checkout, entorno virtual o CWD del repo. No dependas del PATH de desarrollo. Comprueba que se usa la base nueva y la configuración del destino correcto.
4. En esta copia de smoke, verifica login de `admin`, rotación de contraseña, cierre/reinicio y persistencia del cambio. El test existente `tests/windows/test_packaged_bootstrap.py` puede reutilizarse únicamente si su contrato corresponde a esta copia; rota credenciales y no debe ejecutarse sobre la fuente prístina ni sobre la futura sesión manual de David. Una credencial ya rotada en el smoke no es la credencial inicial de la instalación nueva desde el instalador.
5. Verifica una vez en la instalación sintética que la preservación de datos/configuración funciona en el recorrido de reinstalación/desinstalación que anuncias. No borres datos reales; no anuncies compatibilidad general de actualizaciones si solo has probado instalación nueva. Tras finalizar, limpia solo tus procesos y archivos desechables conforme a los permisos disponibles.
6. El cierre mediante la **X nativa del launcher** está pendiente en la evidencia histórica. `MANUAL_TEST2.md` incluye una observación humana de ese recorrido. No lo marques PASS usando `terminate`, un cierre por API o el cierre de la pestaña web. Puedes detectar y corregir un bloqueo evidente durante tu smoke, pero conserva el paso humano y distingue ambas evidencias.
7. Si corriges un fallo reproducible de instalación, bootstrap o arranque, repite solo lo afectado y vuelve a generar/hashar el instalador. No me entregues un binario anterior al cambio. Si el arreglo excede este alcance, para y presenta el bloqueo y la decisión necesaria.

El instalador original debe permanecer inalterado y limpio después del smoke. Las bases, contraseñas rotadas y logs de la copia instalada no vuelven a su payload. Los cursos y alumnos de `MANUAL_TEST2.md` los crearé yo durante la sesión, no se precargan en la entrega.

### 4. Entrega concreta y fin del encargo

Guarda un informe breve y un handoff sin secretos en una carpeta nueva bajo `implementation_documents/manual_windows_<fecha>/`. El handoff debe permitir que otro agente continúe con `MANUAL_TEST2.md` y contener:

- Rama, commit/árbol de origen y de construcción, cambios locales pendientes y comando de build reproducible sin contraseñas.
- **Ruta absoluta del instalador real**, nombre, tamaño, SHA-256 y versión; ruta de su payload prístino y hash del EXE. Diferencia instalador, EXE instalado y carpeta portable.
- Un enlace de descarga únicamente si ya existe una ubicación privada autorizada y has comprobado que apunta al archivo correcto y que yo puedo abrirlo. Si no existe, di «sin URL de descarga; disponible en esta ruta local» y no inventes un enlace ni publiques el binario. Incluye el enlace verificable al commit/informe de fuente por separado.
- Destino nuevo propuesto para mi prueba y ubicación de sus datos/configuración. La ruta/URL de la aplicación se confirmará al arrancar; no fijes un puerto sin verificarlo.
- Cuenta inicial `admin`, dónde puedo consultar **privadamente** su credencial y cómo cambiarla en la UI. No incluyas la contraseña, tokens, claves o una copia de la base en el informe.
- Resultado de cada smoke: PASS, FAIL, BLOCKED o NOT RUN; entorno y prueba realmente ejecutada. Explica firma digital ausente o advertencias observadas sin afirmar confianza universal ni instruirme a eludir seguridad.
- Preparación de un documento local `MANUAL_TEST_HANDOFF.md` con estos datos, la ubicación de `MANUAL_TEST2.md` y las incidencias que condicionan la sesión. No uses logs sin sanear como handoff.

Termina con un resumen corto: instalador listo o bloqueo real, ruta, hash, resultados y primer paso de la sesión. **No empieces la prueba humana, no sigas auditando, no publiques y no selecciones un modelo. Detente y espera a que yo lance `MANUAL_TEST2.md`.**
