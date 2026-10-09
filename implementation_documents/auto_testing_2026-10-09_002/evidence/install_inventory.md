# Inventario de instalación existente (solo lectura) · auto-2026-10-09-002

Comprobado el 2026-10-09 **sin modificar nada** (sin abrir, sin desinstalar, sin ejecutar):

| Elemento | Valor observado |
|---|---|
| Directorio de programa | `%LOCALAPPDATA%\Programs\SLMEducator` — contiene `SLMEducator.exe`, `_internal\`, `slm_educator.db` (+ `-shm`/`-wal`), `env.properties`, `api.log`, `starter_debug.log`, `logs\`, `unins000.exe/.dat` |
| Registro HKCU | clave `{40301115-8D29-4D37-A067-F025278BCDC0}_is1`, DisplayName `SLMEducator 2.0.0 (build fe954cab4655)` |
| Desinstalador | `"...\Programs\SLMEducator\unins000.exe"` |
| Fechas observadas | programa 06/10/2026; base y logs con actividad hasta 07/10/2026 |

Implicaciones (AUTO_TEST §2 y `docs/WINDOWS_INSTALLER.md`):

- Esta es la instalación del propietario con sus datos y configuración; **no se toca**: ni
  actualización in-place, ni desinstalación por parte del agente, ni empaquetado de su base.
- La guardia per-user de Inno rechazaría instalar el candidato encima; el ciclo
  instalar/actualizar/desinstalar del candidato queda **BLOCKED** hasta que el propietario
  desinstale su instalación (los datos se conservan por diseño) o se aporte un perfil
  desechable autorizado.
- El Setup histórico `fe954cab4655` **no se abrió ni se reutilizó**; no contiene esta GUI.
