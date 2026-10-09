# Evidencia técnica · construcción del candidato (auto-2026-10-09-002)

Fecha: 2026-10-09. Todo se construyó con procedimiento mantenido y destinos nuevos.

## Identidad

| Elemento | Valor |
|---|---|
| Fuente | rama `fix/react-functional-continuation-20261007`, HEAD `19909e6038c180ce15f5e987928934d34dfc797e`, árbol `e13ba1248a22294582670eade6e27754af8b94a0` |
| Python de empaquetado | 3.13.15 en `C:\builds\slm-pkg-venv-19909e6` (Tcl/Tk en directorio real; el guard zipfs de `build_package.py` no se activa) |
| Compilador instalador | Inno Setup 6 `ISCC.exe` en `%LOCALAPPDATA%\Programs\Inno Setup 6` |
| Payload (prod, sin cuentas) | `C:\builds\slm-payload-19909e6` — `slm_educator.db` con 27 tablas y **0 usuarios** (consulta solo-lectura URI `mode=ro`) |
| EXE payload SHA-256 | `38b7fe64f87bca860c714d82db53dfb19e8d11f04b77b3ae0ff1ce9a7e5b8697` |
| Setup | `C:\builds\slm-setup-19909e6\SLMEducator-Setup-2.0.0-19909e6038c1.exe`, 28.924.575 bytes |
| Setup SHA-256 | `66839a0752e3b43b597d328b3a4afc4d7d5098ae9501842963a24aaaac6115b6` |

## Confirmaciones de seguridad

- Directorios `--payload-dir` y `--output-dir` verificados inexistentes antes de construir; el builder los rechaza si existen.
- Ni el build ni el empaquetado leyeron, empaquetaron ni modificaron la base del usuario (`%LOCALAPPDATA%\Programs\SLMEducator\slm_educator.db`) ni su `env.properties`; la instalación existente solo se inventarió de forma solo-lectiva.
- No se incluyó ninguna cuenta ni contraseña de build (`SLM_INITIAL_ADMIN_PASSWORD` no se usó).

## Log crudo (local, no publicado)

| Log | SHA-256 |
|---|---|
| `C:\builds\slm-installer-build.log` | `55687ececd9c80bdb0fe24afcf0737fbc3afd5758a66f27b638884f9c9307410` |
