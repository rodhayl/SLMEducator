# MANUAL_TEST_HANDOFF — instalador SLMEducator listo para la prueba manual

Este handoff permite continuar con `MANUAL_TEST2.md` sin rehacer la preparación.
No contiene contraseñas, tokens, claves ni copia de la base. El informe técnico
completo está en `REPORT.md`, junto a este archivo.

## 1. Artefacto exacto que debe usarse

| Elemento | Valor |
|---|---|
| Instalador real (el que se ejecuta) | `C:\Users\dhays\Github\SLMEducator\.manual-windows-worktree\dist\SLMEducator-installer-fe954cab4655\SLMEducator-Setup-2.0.0-fe954cab4655.exe` |
| Nombre | `SLMEducator-Setup-2.0.0-fe954cab4655.exe` |
| Versión / build | 2.0.0 · `fe954cab4655` |
| Tamaño | 31.456.307 bytes |
| SHA-256 | `c02c79e21e6d04d327ed11223203c85ef95fd5b796fbc6a2c771ed5f952a1531` |
| Payload prístino (carpeta portable `onedir`) | `C:\Users\dhays\Github\SLMEducator\.manual-windows-worktree\dist\SLMEducator-installer-payload-fe954cab4655\` |
| EXE del payload (referencia) | `SLMEducator.exe` · SHA-256 `e60912db796fa59b8aa9c8f8ea405b112e46eb27915fde8360acb3f385f3c230` |

Diferencias entre los tres niveles:

- **Instalador**: el `.exe` de Setup (31,4 MB). Es el archivo que se abre una vez.
- **EXE instalado**: `<destino>\SLMEducator.exe` (15,96 MB), copia que el
  instalador deja en el destino; su hash debe coincidir con el del payload.
- **Carpeta portable**: el payload `onedir` prístino (`SLMEducator.exe` +
  `_internal` + base + config). Es la fuente de compilación, no un instalador.

**Sin URL de descarga; disponible en esta ruta local.** No existe una ubicación
privada autorizada, así que no hay enlace al binario y el instalador no se
publica. Fuentes verificables por separado (no son el binario): commit base
`https://github.com/rodhayl/SLMEducator/commit/5e839d2b0bc0bb89309f49eac648a6eee747cd79`
y su informe
`https://github.com/rodhayl/SLMEducator/blob/5e839d2b0bc0bb89309f49eac648a6eee747cd79/implementation_documents/windows_best_effort_20261006/REPORT.md`.

El instalador está sin firmar: SmartScreen puede advertir. No se debe indicar al
usuario que eluda protecciones; si no se puede continuar con seguridad, se para.

## 2. Origen y reproducción sin contraseñas

- Rama: `feature/windows-installer-inno-20261006` (worktree
  `C:\Users\dhays\Github\SLMEducator\.manual-windows-worktree`).
- Base documentada: `5e839d2b0bc0bb89309f49eac648a6eee747cd79`
  (árbol `673b386dc19f140c143859edfd8545640ae5bb6d`).
- Commit de construcción: `fe954cab4655969c357ec38208299a8af1563b1b`
  (árbol `c70acd13e4a39e7dbc8faf0740a8842c9c79ba64`), árbol limpio al construir.
- Receta previa incluida en el mismo rango: `25e29101e24f…` (ver `REPORT.md`).
- Cambios pendientes: ninguno. El artefacto entregado se construyó en
  `fe954cab4655` con el árbol limpio; los commits posteriores de la rama solo
  añaden el informe, este handoff y el test opt-in del instalador.

Comando de build reproducible (sin contraseñas; el operador aporta la suya por
`SLM_INITIAL_ADMIN_PASSWORD` en el entorno del proceso):

```powershell
build_installer.bat --payload-dir "C:\ruta-nueva\payload" --output-dir "C:\ruta-nueva\instalador" --version 2.0.0
```

Requiere Windows nativo, Python 3.13 con PyInstaller 6.16.0 e Inno Setup 6
(`ISCC.exe`). Las rutas deben ser nuevas y absolutas. Ver `docs/WINDOWS_INSTALLER.md`.

## 3. Destino propuesto para la prueba de David

Antes de abrirlo, volver a comprobar el hash local del punto 1, ejecutar sin
privilegios elevados y confirmar que no hay registro de instalación ni accesos
SLMEducator preexistentes en las carpetas reales de Inicio/escritorio. La
comprobación de carpeta vacía que sigue es histórica: hay que repetirla. No usar
un destino portable existente; esta receta no lo protege si no está registrado.
Un destino distinto tampoco evita el bloqueo de un registro HKCU existente.

- Destino nuevo: `%LOCALAPPDATA%\Programs\SLMEducator` (por defecto del
  instalador). Se comprobó que esa carpeta **no existe** todavía, así que será
  una instalación nueva. Instalación por usuario, sin administrador.
- Datos y configuración: en la propia carpeta instalada —
  `slm_educator.db`, `env.properties`, `logs\`, `api.log`,
  `starter_debug.log` y posibles sidecars `*.db-*`.
- URL de la aplicación: se confirma al arrancar. El launcher elige el primer
  puerto libre desde 8000 y abre el navegador; **no fijar un puerto** en la guía.
- Desinstalación: conserva datos y configuración; no hay actualización in-place
  (reinstalar sobre una instalación existente se rechaza con un mensaje claro).

## 4. Cuenta inicial y credencial privada

- Usuario inicial: `admin` (correo `admin@example.invalid`, rol administrador).
- Contraseña inicial: **no figura aquí**. Está en el archivo privado
  `C:\Users\dhays\SLMEducator-Eval-Secrets\initial-admin-fe954cab4655.txt`
  (carpeta fuera del repo, con ACL restringida a la cuenta de David). Ese valor
  se verificó contra el hash del administrador del payload prístino; no se
  imprimió en terminal, informes, logs ni Git.
- Rotación en el primer acceso: en la UI, abrir la pantalla de cambio de
  contraseña de la cuenta (`POST /api/auth/change-password` es el contrato
  mantenido) y cambiarla por una única. La rotación revoca las sesiones
  anteriores; el guía debe identificar el control real en la UI, no inventarlo.
- Importante: el smoke rotó la contraseña **de su copia desechable**, no la del
  payload prístino. La credencial inicial del archivo privado sigue siendo la del
  instalador entregado.

## 5. Resultado de la preparación (artefacto final)

La tabla conserva los resultados nativos comunicados durante la preparación
original. El smoke endurecido (`e1e46d8`, incorporado como `1562190`) recibió
el 2026-10-07 su ejecución nativa desechable en Windows: 38 tests
sintéticos/estáticos pasan y el ciclo real instalar → rechazo in-place →
desinstalar → reinstalar pasó en 19,04 s reutilizando este mismo instalador
(tamaño y SHA-256 del punto 1 re-verificados antes y después del smoke; sin
recompilación). Detalles y rutas verificadas en
`../installer_smoke_safety_20261006/REPORT.md`. El cierre con la X del
launcher sigue siendo un paso humano pendiente.

| Control | Estado | Prueba realmente ejecutada |
|---|---|---|
| Tests packaging/bootstrap | PASS | 59 pasan (`tests/test_build_package.py`, `tests/test_seed_admin.py`, base temporal nueva; freezer simulado etiquetado) |
| Tests de la receta nueva | PASS | 15 pasan (`tests/test_build_installer.py`) |
| Build nativo Windows | PASS | `build_installer.bat`, Python 3.13.15 + PyInstaller 6.16.0 + ISCC 6.7.3 |
| Instalación silenciosa y accesos | PASS | salida 0; accesos en menú Inicio y escritorio; entrada de desinstalación en HKCU |
| Arranque sin Python/venv/CWD del repo | PASS | `tests/windows/test_packaged_bootstrap.py` con `PATH` solo `System32` |
| Login admin, rotación, reinicio, persistencia | PASS | mismo test: contraseña anterior 401 tras reinicio, token revocado |
| Rechazo de actualización in-place | PASS | segunda ejecución: salida 1 en 1 s, datos sin cambios |
| Desinstalación conserva datos/config | PASS | programas eliminados; base, config y logs conservados con hash idéntico |
| Reinstalación conserva datos | PASS | `onlyifdoesntexist`: hash de base y config idéntico |
| X nativa del launcher | NOT RUN | **paso humano** de `MANUAL_TEST2.md`; el reinicio del smoke usó terminación por PID, no la X |
| Firma / SmartScreen | Ausente | sin firma digital; advertencia posible, sin instrucciones de elusión |
| Inferencia real / modelos | NOT RUN | fuera de alcance |
| Actions / publicación | NOT RUN | no consultadas; sin push ni Release |

## 6. Incidencias que condicionan la sesión manual

1. **X nativa pendiente (paso humano).** Es el control que `MANUAL_TEST2.md`
   pide observar. Por código mantenido, la X del launcher abre un diálogo
   «Exit / Stop the server and exit?»; la comprobación humana es pulsar la X,
   confirmar y verificar que el árbol de procesos de esa instancia termina y que
   el puerto deja de escuchar. La terminación por PID del smoke no cuenta como
   ese paso.
2. **Sin actualización in-place.** Si el instalador se ejecuta sobre una
   instalación existente, se detiene con un mensaje claro en ~1 s. Desinstalar
   primero conserva datos y configuración.
3. **Puerto no fijo.** Confirmar la URL real al arrancar; no asumir 8000.
4. **Sin firma digital.** Registrar la advertencia de SmartScreen si aparece, sin
   eludir controles.
5. **Credencial privada local.** Solo en la ruta del punto 4; no pedirla por
   chat, no capturarla y no incluirla en el informe de sesión.

`MANUAL_TEST2.md` está en `C:\Users\dhays\Github\SLMEducator\MANUAL_TEST2.md`
(también hay copia de este trabajo en el checkout principal para localizarlo).

## 7. Primer paso de la sesión (para el agente que guíe)

Paso 1: pide a David abrir el instalador en la ruta absoluta del punto 1 y
confirma con él que ve el asistente de SLMEducator con versión 2.0.0 y destino
nuevo. No instales tú, no inicies la prueba y no continúes más allá de ese paso
hasta que David responda.
