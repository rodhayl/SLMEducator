# Instalador Windows para la prueba manual — informe de preparación

Fecha: 2026-10-06. Encargo: `MANUAL_TEST1.md` (preparar un instalador Windows
nuevo y real, sin iniciar la prueba humana `MANUAL_TEST2.md`).

## Base, rama y commits

| Rol | Commit | Árbol |
|---|---|---|
| Base de entrega documentada | `5e839d2b0bc0bb89309f49eac648a6eee747cd79` | `673b386dc19f140c143859edfd8545640ae5bb6d` |
| Receta del instalador | `25e29101e24ffa67d696f812a156fec43f3e8d7b` | `3b990653343cb9ecbf5f814fea25170ba30fc63c` |
| Corrección + construcción final | `fe954cab4655969c357ec38208299a8af1563b1b` | `c70acd13e4a39e7dbc8faf0740a8842c9c79ba64` |

Rama propia: `feature/windows-installer-inno-20261006`, en el worktree
`.manual-windows-worktree`. El checkout principal (`docs/manual-tests-windows-20261006`)
solo añade `MANUAL_TEST1.md`/`MANUAL_TEST2.md` sobre la base; no hay cambios de
producto posteriores, por lo que no se pidió decisión de cambio de base. `main`
no se tocó; no se publicó nada.

En la base no existía ninguna receta Inno/MSI mantenida (tampoco `.iss` alguno):
se verificó antes de añadir la receta. El ZIP histórico de 37.140.055 bytes no se
reutilizó, distribuyó ni ejecutó.

## Cambios añadidos (mínimos)

- `installer/SLMEducator.iss`: receta Inno Setup 6 per-user.
- `scripts/build_installer.py` + `build_installer.bat`: invocación documentada;
  reutiliza `scripts/build_package.py --prod` y `scripts/seed_admin.py`.
- `tests/test_build_installer.py`: 15 contratos de receta/orquestación.
- `tests/windows/test_installer_lifecycle.py`: test opt-in del ciclo real
  instalación → accesos → rechazo de reinstalación → desinstalación →
  reinstalación sobre datos conservados.
- `docs/WINDOWS_INSTALLER.md` y una sección en `README.md`.
- Sin cambios de producto.

Corrección demostrada durante el smoke (commit `fe954ca`): el bloqueo de
actualización in-place usaba `MsgBox`, que `/VERYSILENT` no puede cerrar, y una
instalación silenciosa sobre una instalación existente quedaba esperando en vez
de detenerse. `SuppressibleMsgBox` respeta `/SUPPRESSMSGBOXES` y aborta en 1 s.
La primera compilación (`25e2910`, SHA-256 `d75e068d…`) se descartó, se eliminó y
no se entrega.

## Entorno efectivamente usado

Windows 11 (10.0.26200), x64 · Python 3.13.15 (gestionado por `uv`; Tcl/Tk en
directorios, preflight superado) · PyInstaller 6.16.0 · Inno Setup 6.7.3
(`ISCC.exe`) · pytest 9.0.2 · `uv pip check`: 74 paquetes compatibles ·
flake8 y mypy (`--follow-imports=silent`) sin hallazgos en los archivos nuevos.

No se usó `terminate` ni cierres por API para sustituir la X nativa; no se
detuvo ningún proceso preexistente (Gemma, Trading u otros) y no se consultó
GitHub Actions. Las suites DOM/Node y de navegador no se ejecutaron: no están
afectadas por este cambio de empaquetado.

## Artefacto entregado

| Elemento | Ruta / valor |
|---|---|
| Instalador real | `C:\Users\dhays\Github\SLMEducator\.manual-windows-worktree\dist\SLMEducator-installer-fe954cab4655\SLMEducator-Setup-2.0.0-fe954cab4655.exe` |
| Tamaño / SHA-256 | 31.456.307 bytes · `c02c79e21e6d04d327ed11223203c85ef95fd5b796fbc6a2c771ed5f952a1531` |
| Versión / build | 2.0.0 · `fe954cab4655` (commit de construcción) |
| Payload prístino (carpeta portable `onedir`) | `…\dist\SLMEducator-installer-payload-fe954cab4655\` (2.465 archivos, sin sidecars `*.db-*`) |
| EXE del payload | `SLMEducator.exe` · 15.960.120 bytes · `e60912db796fa59b8aa9c8f8ea405b112e46eb27915fde8360acb3f385f3c230` |
| Base sembrada del payload (prístina) | `slm_educator.db` · 434.176 bytes · `99cca1846629fbd7a3d476a5f27ea43a96d92481a3713c82e9513aad6fdedb88` |
| Configuración generada | `env.properties` · 1.465 bytes · `c17516564be99482ddaf07272927bdccd4f064ca8651fae2f43d00825f36194f` |

Tras todo el smoke, el instalador y el payload prístino conservan exactamente los
mismos hashes; la base del payload sigue sin rotar (`99cca184…`). La carpeta
portable es la fuente de compilación, no un instalador; el EXE instalado es la
copia que entrega el instalador y comparte hash con el EXE del payload.

## Comprobaciones ejecutadas

| Control | Resultado | Evidencia y alcance |
|---|---|---|
| Tests de packaging/bootstrap | PASS | `python -m pytest tests/test_build_package.py tests/test_seed_admin.py -q` con base temporal nueva: 59 pasan, 0 fallos. Freezer simulado en estos tests, identificado como tal; no se sustituyó por Linux. |
| Tests de la receta nueva | PASS | `tests/test_build_installer.py`: 15 pasan, 0 fallos (contratos estáticos de la receta y de la orquestación; no incluyen el compilado real). |
| Build Windows nativo | PASS | `build_installer.bat` con Python 3.13 + PyInstaller 6.16.0 + ISCC 6.7.3; payload `--prod` y salida nueva; sin bases/config de usuario. |
| Instalación per-user sin elevación | PASS | Instalación silenciosa con salida 0 en carpeta desechable propia; registro de desinstalación bajo `HKEY_CURRENT_USER`; carpeta bajo el perfil del usuario; receta `PrivilegesRequired=lowest`. |
| Accesos y entrada de desinstalación | PASS | Acceso directo en menú Inicio y escritorio; `DisplayName=SLMEducator 2.0.0 (build fe954cab4655)`, `Publisher=SLMEducator`, `UninstallString` correcta. |
| EXE instalado == payload prístino | PASS | SHA-256 instalado `e60912db…` idéntico al del payload. |
| Arranque sin Python/venv/CWD del repo | PASS | `tests/windows/test_packaged_bootstrap.py` con `PATH` solo `System32`, sin `PYTHONPATH`/`VIRTUAL_ENV`, `cwd` fuera del repo; usa la base del destino. |
| Login admin inicial + rotación + reinicio + persistencia | PASS | Mismo test: login 200 con la credencial inicial, cambio de contraseña, reinicio, contraseña anterior 401 y token previo revocado. |
| Rechazo de actualización in-place | PASS | Segunda ejecución del mismo instalador: salida 1 en 1 s; db/config/EXE idénticos antes y después; mensaje registrado en el log. |
| Desinstalación conserva datos/configuración | PASS | `unins000.exe /VERYSILENT`: se eliminan EXE, `_internal` y archivos del desinstalador; `slm_educator.db`, `env.properties`, `logs/`, `api.log`, `starter_debug.log` y sidecars permanecen con hash idéntico. Sin `[UninstallDelete]` ni comodines. |
| Reinstalación tras desinstalación conserva datos | PASS | Instalación de nuevo: programas restaurados; `slm_educator.db` y `env.properties` conservan el hash anterior (`onlyifdoesntexist`). |
| Test opt-in del ciclo del instalador | PASS | `SLM_INSTALLER_SETUP` + `SLM_INSTALLER_PAYLOAD_SHA256`: mismo recorrido automatizado contra el instalador entregado; al terminar deja limpios registro HKCU, accesos y carpeta desechable. Se salta si ya existe una instalación registrada, para no tocar la de David. |
| Credencial inicial privada verificada | PASS | El valor del archivo privado valida contra el hash del `admin` del payload prístino; no se imprimió. |
| X nativa del launcher | NOT RUN | Paso humano reservado a `MANUAL_TEST2.md`. El smoke cerró con terminación por PID para poder reiniciar; eso no es evidencia de la X nativa. |
| Firma digital | Ausente | El instalador no está firmado; Windows SmartScreen puede advertir. No se indica eludir protecciones y no se afirma confianza. |
| Inferencia real / modelos | NOT RUN | Fuera de alcance; no se descargaron modelos ni se consultaron proveedores. |
| Actions / publicación | NOT RUN | No consultadas ni ejecutadas; sin push, Release ni PR. |

## Aislamiento, datos y limpieza

Solo se usaron bases nuevas y desechables creadas por el builder/seeder. No se
abrió, copió, reinició ni empaquetó ninguna base o configuración privada. La
contraseña inicial aleatoria (24 caracteres) se pasó solo por entorno al build y
se guarda en un archivo fuera del repo con ACL restringida a la cuenta; no
aparece en el chat, en los informes, en Git, en manifiestos ni en logs
publicables.

La copia de smoke se instaló en una carpeta desechable propia, se desinstaló y se
eliminó junto con los directorios temporales de prueba. Los artefactos
entregables (instalador + payload prístino) y la credencial privada se
conservan. Los datos ficticios del smoke no vuelven al payload.

## Límites explícitos

- No se ofrece ni se probó una ruta de actualización in-place: reinstalar sobre
  una instalación existente se rechaza con un mensaje claro; desinstalar primero
  conserva datos y configuración.
- Inno Setup 6.7.3 (edición gratuita) informa «Non-commercial use only»; es una
  consideración de licencia de la herramienta, no una certificación de este
  artefacto.
- El instalador incluye la base sembrada con su administrador exclusivo para
  esta evaluación privada; no debe redistribuirse ni reutilizarse como paquete
  universal con el mismo hash de contraseña.
- Este trabajo no certifica eficacia educativa, adecuación para menores,
  cumplimiento normativo, calidad de modelo, ni funcionamiento en otros
  proveedores/hardware/plataformas. La validación pedagógica y el piloto humano
  siguen pendientes.
