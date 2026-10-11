# Acreditación técnica · candidato 29df5ed (2026-10-10)

> Revisión independiente 2026-10-11: este documento conserva el registro histórico comunicado por el ejecutor. No acredita aceptación completa. La matriz corregida y RESUME.json distinguen los subcasos no demostrados. Se verificó por GitHub que 29df5ed..386593b solo cambia documentación/evidencia; no se reabrió ni probó el instalado durante esta revisión.


Fecha local: 2026-10-10. Sin reconstrucción ni reinstalación por rutina.
HEAD 5bf4e48 sólo añade 26 líneas a DEFECTS.md sobre 29df5ed (documental).

## Fuente

| Elemento | Valor verificado |
|---|---|
| Rama | `fix/react-functional-continuation-20261007` |
| HEAD local == remoto | `5bf4e48744ab34618e502f1ae3cdb1f1cbf27ac7` |
| Código a acreditar | `29df5ed6674f660f37337d8ea69616e31600a09f`, árbol `7c5e9139cff23fa787037b290d5e62df1162eb38` |
| Diff 29df5ed..HEAD | sólo `implementation_documents/auto_testing_2026-10-09_002/DEFECTS.md` → no obliga a reconstruir |
| Estado trabajo | sólo `??` ajenos (worktrees, SESSION_LOG, run_vitest/vitest_*.txt), preservados |

## Frontend construido (verificador mantenido)

Verificación 2026-10-10 con `src.frontend_delivery.validate_frontend_dist`
(venv `C:\builds\slm-venv-29df5ed`, Python 3.13.15):

| Eslabón | Resultado |
|---|---|
| checkout `src/frontend/dist` (con `source_root`) | VALID 26 assets |
| payload `C:\builds\slm-payload-29df5ed\_internal\src\frontend\dist` | VALID 26 assets |
| instalado `%LOCALAPPDATA%\Programs\SLMEducator\_internal\src\frontend\dist` | VALID 26 assets |
| `frontend_source_digest(src/frontend)` | `41fe5b04ccf32dfa529b4481e1b43639f7f6ab79d4fec1dcdab922b9d996bb73` == `build-manifest.json source_sha256` |

Nota: una fila TECH ausente en COVERAGE para 29df5ed es lag documental,
no prueba de build incorrecto. El venv de compilación citado en el log
(`slm-pkg-venv-19909e6`) reutiliza toolchain verificada
(Python 3.13.15, PyInstaller 6.16.0, Tcl/Tk 8.6); el nombre antiguo
no invalida su toolchain. No se recompila para rellenar la matriz.

## Payload prístino (solo lectura, sin modificar)

Sonda 2026-10-10 vía fichero script + SQLite URI `mode=ro` + `PRAGMA query_only=ON`:

| Elemento | Valor |
|---|---|
| Dir | `C:\builds\slm-payload-29df5ed` |
| Tablas | 27 |
| Usuarios | **0** → elegible para primera configuración local |
| Columnas users | id,username,email,password_hash,role,first_name,last_name,grade_level,active,created_at,last_login,teacher_id,failed_login_count,locked_until,xp,level,current_streak,longest_streak,last_activity_date,settings |
| EXE | `SLMEducator.exe` 16044355 bytes, SHA-256 `12896871AE081242211CE1D75D4C06137E657ECB46E71A1A64BFD4B0FD35C949` |
| index.html payload | SHA-256 `E0E7A0C7C769076ABEBEA7E93678E411D387D913D6D785BC1359C1C647E89DFB` == manifest |

Sin datos personales ni credenciales impresos. Base prístina no modificada.

## Setup

| Elemento | Valor |
|---|---|
| Ruta | `C:\builds\slm-setup-29df5ed\SLMEducator-Setup-2.0.0-29df5ed.exe` |
| Tamaño | 31754370 bytes (2026-10-09 19:10:30) |
| SHA-256 | `26217942AF4EEF00CD2F10D196F259ACE4A7F1B41FF3775CA71222D05143AB17` |
| Compilador | Inno Setup 6.7.3, `Successful compile (28,235 sec)`, `[OK] Installer created` |
| Log install | `/VERYSILENT`, privilegios None, HKCU, no-elevado, 2026-10-09 19:13:25 |

## EXE instalado (sin reinstalar)

| Elemento | Valor |
|---|---|
| Ruta | `%LOCALAPPDATA%\Programs\SLMEducator\SLMEducator.exe` |
| SHA-256 | `12896871AE081242211CE1D75D4C06137E657ECB46E71A1A64BFD4B0FD35C949` == payload |
| index.html instalado | `E0E7A0C7C769076ABEBEA7E93678E411D387D913D6D785BC1359C1C647E89DFB` == payload |
| Registro HKCU | `SLMEducator 2.0.0 (build 29df5ed)`, InstallLocation `...\SLMEducator\` |
| Estado | sin proceso activo; `starter_debug.log` muestra arranques 09/10 + detención 10/10 07:36; `api.log` con `GET /api/status 200` hasta 10/10 07:36 |
| Cuentas instalado | NO sondeado en esta pasada (requiere copia; el instalado tiene -shm/-wal activos y no se toca sin autorización). Primera creación queda como fase separada pendiente de perfil desechable. Si aparece diálogo de credenciales, handoff privado al propietario. |

## Resultados técnicos conservados (no son PASS GUI)

| Prueba | Resultado | Evidencia |
|---|---|---|
| Lotes A+B UTF-8 | 39 passed | `C:\builds\slm-utf8-full.log` |
| test_pilot_utf8 + test_logging_utf8 | 8 passed | `C:\builds\slm-utf8-tests.log` |
| Contratos 011/013/provider/tutor | 74 passed, 1 warning | `C:\builds\slm-contract-tests.log` |
| Paquete | 119 passed | `C:\builds\slm-pkg-tests.log` |
| npm ci | 319 packages, 0 vulnerabilities | `C:\builds\slm-npmci.log` |

Ninguna prueba UTF-8 se convierte en PASS de GUI no observada.

## Matriz (calculada de archivos reales 2026-10-10)

`COVERAGE.csv`: 126 filas (cabecera + 126 datos → 127 líneas):
PASS 7 / PARTIAL 1 / FAIL 2 (de candidato viejo 19909e6) / BLOCKED 2 / NOT_RUN 114.
Todas las filas declaran candidato `19909e6`; la revalidación 29df5ed vive en
`DEFECTS.md §Revalidación 2026-10-10` + este archivo. Promoción a COVERAGE/RESUME
pendiente de autorización de escritura (esta pasada ya permite doc local sin commit).

## Bloqueo concreto siguiente

1. Perfil/VM Windows desechable autorizado para lifecycle aislado
   (`SLM_INSTALLER_SETUP` + `tests/windows/test_installer_lifecycle.py`),
   primera creación y ciclo desinstalar/reinstalar — la falta de perfil bloquea
   sólo esa fase, no los recorridos del instalado actual.
2. Confirmación de disponibilidad de pantalla del propietario para GUI nativa
   del instalado existente (arranque fuera de checkout, X/cancelar,
   Detener/Iniciar, relanzamiento, persistencia, recorridos sintéticos),
   respetando procesos AAC ajenos (uvicorn/browser/verify_pr conservados).

