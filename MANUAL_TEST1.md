# MANUAL_TEST1 — preparar el instalador de la GUI React actual

Fase 1: trabajo técnico del agente. Fase 2: David usa la aplicación con
`MANUAL_TEST2.md`. Leer o editar estas guías no ordena construir ni instalar.
Si David te pide ejecutar `MANUAL_TEST1.md`, ejecuta este encargo: no hace falta
copiar el texto ni pedir una segunda orden. También puede copiar INICIO–FIN.

INICIO

Trabaja en `rodhayl/SLMEducator`. Prepara un instalador Windows nuevo, limpio y
trazable para que David pruebe después la GUI React. Haz la preparación técnica,
entrega el handoff y detente. No empieces la sesión humana. No uses `/goal`, un
bucle autónomo indefinido, campañas de modelos ni una arquitectura nueva.

## Punto de partida: no construir ni probar la versión antigua

1. Lee `AGENTS.md`, `README.md`, `docs/CONTRIBUTING.md`,
   `src/frontend/CONTRACTS.md`, `docs/FUNCTIONAL_REQUIREMENTS.md`,
   `docs/WINDOWS_INSTALLER.md`, `docs/BROWSER_TEST.md` y los dos manuales.
   Para intención y cambios recientes, lee
   `implementation_documents/gui_redesign_20261007_plan.md` y
   `implementation_documents/react_redesign_20261007/CONTINUITY_GAPS_20261007.md`.
   El plan describe objetivos; las etiquetas y contratos vigentes se verifican
   en el código actual, no se deducen de sus maquetas.
2. Base de producto de esta revisión:
   `642966a93e7e9c9f9c5e93cce0bc842f538846fb`, árbol
   `e0a3966bddc8bbd4cfc2ab4041668c3162ce86f7`, rama
   `fix/react-functional-continuation-20261007`.
   [Fuente identificada](https://github.com/rodhayl/SLMEducator/commit/642966a93e7e9c9f9c5e93cce0bc842f538846fb).
   Incluye la GUI React y los arreglos G1–G5 de continuidad, navegación y
   movimiento guardado. Comprueba HEAD, árbol y archivos modificados. Puedes
   usar un descendiente cuya diferencia respecto a esa base sea únicamente
   estas guías; registra su SHA real. Si hay otros cambios de producto, para y
   pide elegir el candidato. No cambies a `main` ni a otra rama por costumbre.
3. Trabaja en una rama/worktree aislada derivada del candidato verificado. No
   descartes cambios ajenos. Los manuales 1 y 2 procedían de
   `docs/manual-tests-windows-20261006`; sus antiguas referencias a `5e839d2…`
   no seleccionan el producto actual. El handoff de
   `implementation_documents/manual_windows_20261006/MANUAL_TEST_HANDOFF.md`
   conserva el instalador histórico `fe954cab4655`: NO contiene esta GUI ni
   sus arreglos. No lo abras como primer paso ni reutilices su payload, hash o
   credencial. Tampoco uses un ZIP posterior al smoke como instalador limpio.
4. La verificación de fuente G1–G5 comunicó 825 pruebas DOM, 249 Python y
   8 diagnósticos sintéticos, además de tipos, lint y build. Es evidencia
   histórica con alcance declarado; no prueba un nuevo instalador, navegador,
   Windows, accesibilidad real, service worker o inferencia. No la copies como
   PASS de esta preparación ni de la futura sesión humana.

## Quién hace qué y límites

- Agente: comprueba fuentes y herramientas; construye y verifica copias
  sintéticas desechables; calcula identidades; prepara evidencia saneada y
  handoff. Explica solo bloqueos o decisiones que necesiten a David.
- David: autoriza lo que exija confirmación; introduce, confirma y envía
  contraseñas o credenciales cuando requieran intervención humana; instala y
  maneja la GUI en la fase 2. No le pases comandos de ingeniería como tareas
  manuales ordinarias.
- Construcción nativa Windows 10/11, sin elevación. Si no tienes ese entorno,
  conserva el trabajo y declara BLOCKED. No simules un EXE, no sustituyas Setup
  por ZIP, `start.bat` o Linux, ni afirmes que un freezer simulado probó Windows.
- No abras, copies, reinicialices, migres ni empaquetes bases/configuraciones de
  instalaciones existentes. Usa una base nueva creada por el builder. No mates
  procesos ajenos; un puerto ocupado obliga a elegir uno libre,
  no a parar su ocupante. Solo limpia procesos de tu prueba con identidad
  comprobada y autorización aplicable.
- Conserva instalaciones antiguas. La receta rechaza actualizar in-place; otra
  carpeta no evita un registro HKCU existente. No desinstales, borres registros,
  accesos directos o datos para quitar ese bloqueo. Usa un perfil Windows de
  evaluación desechable ya autorizado, o pide la decisión concreta necesaria.
- No descargues modelos, no exijas uno nuevo/segundo ni llames a proveedores de
  pago. IA configurable y ayuda best effort no significan respuestas perfectas.
  Los errores deben ser honestos y los permisos/revisión/notas provisionales
  siguen siendo obligatorios.
- No consultes ni ejecutes Actions; no publiques binarios, Releases, ramas o PR
  por este prompt. No eludas restricciones previas de navegador/localhost,
  seguridad o autenticación mediante otra ruta o un script. Una herramienta
  denegada deja ese control BLOCKED; no deja toda la fuente aprobada.

## 1. Reutilizar el empaquetado mantenido

La receta YA existe: `build_installer.bat` → `scripts/build_installer.py` →
`scripts/build_package.py --prod` + `installer/SLMEducator.iss`.
Reutilízala. No añadas otro instalador, seeder ni framework de migraciones.

1. Verifica Python 3.13, dependencias del repo, PyInstaller 6.16.0, Tcl/Tk
   compatible, Node 22.22+ para construir y el compilador Inno Setup 6. No
   saltes el preflight Tcl/Tk para usar el layout zipfs de Python 3.14. Si falta
   una herramienta, comprueba la vía oficial y solicita la autorización que
   corresponda; no la instales silenciosamente.
2. Prepara dependencias explícitamente y ejecuta desde la raíz:

   ```powershell
   npm ci --ignore-scripts --prefix src/frontend
   npm run check --prefix src/frontend
   python -m pytest tests/test_build_package.py tests/test_seed_admin.py tests/test_build_installer.py tests/test_installer_lifecycle_contract.py -q
   ```

   Usa el Python del entorno preparado y temporales sintéticos nuevos conforme
   a las instrucciones del repo. El primer comando requiere acceso permitido
   al registro. `check` incluye tipos, lint, DOM y build; registra el resultado
   real. Consulta `docs/BROWSER_TEST.md` para verificaciones separadas. No lances
   suites de proveedor real para completar esta preparación.
3. El dist debe coincidir con las fuentes y lockfile congelados. El builder
   valida inventario/hashes y digest de entradas; no instala npm ni recompila.
   Si falla, corrige la preparación y reconstruye explícitamente. No copies
   dist de otro SHA ni reactives `src/web` como fallback. Node no se requiere
   en la máquina donde después se instale el producto.
4. Conserva las garantías actuales: instalación por usuario en destino nuevo
   escribible, payload `onedir` completo, sin descargas/servicios ocultos ni
   cierre genérico de procesos. Base y `env.properties` solo se colocan si no
   existen y se conservan al desinstalar. Un portable no registrado también
   debe quedar intacto: nunca usar su directorio como destino.

## 2. Crear payload limpio y credencial privada

1. Antes del build, acuerda un mecanismo privado local para la credencial
   inicial. Si David aporta `SLM_INITIAL_ADMIN_PASSWORD`, debe introducirla
   localmente en el entorno de proceso, nunca en chat ni comandos compartidos.
   Debe ser única y de al menos 12 caracteres. Sin override, el seeder imprime
   una contraseña aleatoria una vez: NO captures esa salida en logs publicables.
   Si no puedes mantenerla privada, para antes de construir y solicita entrada
   local segura. No inventes una contraseña de ejemplo.
2. El bootstrap mantenido crea `admin` solo cuando falta; no sirve para recuperar
   ni cambiar una cuenta existente. Cambios de contraseña y nuevos accesos
   persistentes respetan la política de aprobación/handoff de la herramienta.
   No ejecutes un arnés como forma de saltarte esa política.
3. Define dos rutas absolutas nuevas, bajo un directorio de builds autorizado,
   y verifica que no existen. El siguiente es un patrón: sustituye las rutas
   por las que acabas de comprobar, no pidas al usuario que copie el ejemplo:

   ```powershell
   .\build_installer.bat --payload-dir "C:\builds\SLM-<build>-payload" --output-dir "C:\builds\SLM-<build>-setup" --version 2.0.0
   ```

   No uses `--test --database`. El build-id por defecto viene de Git; no
   aceptes `unknown`. Registra el SHA completo/árbol que representa. El resultado
   esperado es `SLMEducator-Setup-<version>-<build-id>.exe`, no el EXE aislado.
4. Congela el payload prístino y calcula SHA-256 del Setup y de
   `SLMEducator.exe`, tamaño y nombre de cada artefacto, e identidad del dist.
   El payload contiene solo base nueva/admin y configuración pública generada,
   sin alumnos, cursos, claves, archivos personales ni logs del smoke.
   Guarda el mecanismo de acceso privado fuera del repo; el handoff describe
   cómo consultarlo, nunca incluye el secreto ni lo adjunta.
5. Ejecuta los smokes sobre una COPIA instalada desechable. La rotación, los
   cursos o logs de esa copia jamás vuelven al payload ni al instalador.
   Construye por instalación de evaluación: copiar un paquete sembrado copia
   también el hash y la cuenta de administrador; no es un binario universal.

## 3. Verificar antes de entregar

1. Registra las comprobaciones sintéticas anteriores separadas del build
   Windows real. Conserva salida saneada, versiones, SHA y resultado. Un skip
   o una prueba no ejecutada no es PASS. Si cambias producto/packaging, ejecuta
   las regresiones afectadas, vuelve a construir y cambia la identidad del
   candidato antes de continuar. Si requiere rediseño, pausa y pide decisión.
2. Instala exactamente el Setup hasheado en un perfil/destino desechable
   autorizado, no en la instalación de David. Comprueba accesos y registro,
   arranque desde fuera del repo sin Python/venv/Node del desarrollo, uso de
   datos de esa copia y servicio listo. Anota la URL que expone SU launcher;
   no supongas 8000, 8080, `localhost` ni `127.0.0.1` como origen de la sesión.
3. Comprueba login, cambio de contraseña autorizado en copia sintética y
   reinicio/persistencia según `tests/windows/test_packaged_bootstrap.py`.
   Lee su contrato y variables antes de invocarlo: no inventes sus argumentos,
   no lo apuntes a la copia prístina ni a datos del usuario. Si una intervención
   de autenticación requiere handoff, pausa esa parte. Terminar un PID no prueba
   la X del launcher ni `Detener`.
4. La prueba opt-in `tests/windows/test_installer_lifecycle.py` necesita
   `SLM_INSTALLER_SETUP` con la ruta del Setup; admite
   `SLM_INSTALLER_PAYLOAD_SHA256` para el EXE prístino. Sigue
   `docs/WINDOWS_INSTALLER.md`: cuenta no elevada desechable, ningún instalador
   simultáneo ni registro/acceso existente. Afecta HKCU y carpetas reales de
   Inicio/escritorio del perfil aunque el payload esté en un temporal. Usa un
   perfil desechable limpio DISTINTO del smoke de §3.2, o retira únicamente esa
   instalación sintética propia mediante su desinstalador autorizado y verifica
   su limpieza antes del lifecycle. Nunca retires la instalación de David.
   Comprueba rechazo in-place y preservación de datos/config sintéticos
   distintos del seed tras desinstalar/reinstalar. No ejecutes el ciclo sobre
   la instalación conservada de David. Si se bloquea, registra BLOCKED.
5. Timeout, descendientes inciertos o limpieza fallida: conserva destino,
   desinstalador y evidencia privada; no borres mientras puedan seguir activos.
   Investiga solo los procesos propios. No repitas para hacer desaparecer el
   fallo. No registres PASS si quedó pendiente la limpieza o identidad.
6. Conserva como aceptación humana separada de `MANUAL_TEST2.md`: X nativa,
   `Detener`/reabrir, GUI de los tres roles, etiquetas/foco/zoom, SW e IA real.
   Una prueba automática puede aportar evidencia, nunca la observación de David.
   Tampoco los resultados del instalador viejo certifican este candidato.
7. Recalcula los hashes del Setup y payload prístino tras el smoke: deben
   coincidir. Si no coinciden, no entregues esa preparación como lista.

## 4. Handoff concreto y fin del encargo

Crea una carpeta de evidencia nueva, por ejemplo
`implementation_documents/manual_windows_<fecha>_<build>/`, sin sobrescribir
los informes históricos. Escribe allí `MANUAL_TEST_HANDOFF.md` y un informe
breve; el nombre del nuevo handoff no renumera los manuales 1/2.

El handoff debe permitir decidir LISTO o BLOCKED sin investigación adicional:

- Fecha, rama, SHA/árbol de origen y construcción, estado del checkout, diferencia
  documental permitida respecto a `642966a…`, versiones y comandos sin secretos.
- Ruta absoluta real del Setup, nombre, versión/build, tamaño, SHA-256; payload
  prístino, hash del EXE e identidad del dist. Separa instalador, programa
  instalado y portable. Nunca llames «instalador» a una carpeta o ZIP.
- Destino de evaluación nuevo y ubicación de datos/configuración. Inventario
  no sensible de registros/accesos preexistentes que bloqueen instalar. Di
  expresamente que no se desinstaló ni reemplazó una instalación anterior.
- Cómo consultar privadamente la cuenta `admin` inicial. Sin contraseñas, tokens,
  claves API ni base adjunta. Ruta GUI de rotación: «Cuenta y ajustes» →
  «Contraseña»; verifica en `features/settings/locales.ts` del candidato sus
  etiquetas antes de guiar. El usuario introduce y envía sus credenciales.
- Cada control con PASS / FAIL / BLOCKED / NOT RUN, evidencia y alcance: build,
  smokes sintéticos/nativos, instalación, login, persistencia, conservación,
  limpieza; las observaciones humanas siguen pendientes. Firma ausente y
  advertencias se describen sin enseñar a eludir SmartScreen.
- La URL se confirma al arrancar la instalación humana. Nunca conviertas la
  URL del smoke en la URL definitiva, ni reveles rutas con tokens.
- Idioma y etiquetas de las pantallas/botones realmente vistos del asistente
  Inno de este Setup, para guiar sin adivinar controles del compilador.
- Ruta de `MANUAL_TEST2.md`, primer paso elegible y próximo subpaso. Si falta
  cualquier identidad o el nuevo Setup, el primer paso es resolver ese bloqueo,
  NO ejecutar el `fe954cab4655` histórico.
- Descarga solo si ya hay una ubicación privada autorizada y has verificado
  archivo/acceso; en otro caso, «sin URL de descarga; disponible en esta ruta
  local». Los enlaces de fuente no son enlaces al binario. No lo publiques.

Si se interrumpe, guarda candidato, hashes, último control confirmado, bloqueo
y siguiente acción en ese mismo handoff. Al reanudar, compara identidad y
estado real; reutiliza evidencia válida del mismo artefacto, no reconstruyas
ni repitas un smoke por costumbre. Un cambio de producto crea otro candidato.

Termina con un resumen corto de resultado, ruta/hash y bloqueos pendientes.
Detente: David iniciará `MANUAL_TEST2.md` cuando quiera instalar y probar.

FIN
