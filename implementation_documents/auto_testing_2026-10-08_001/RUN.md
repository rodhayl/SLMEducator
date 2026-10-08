# RUN · Campaña autónoma AUTO_TEST

Run ID: `auto-2026-10-08-001`
Fecha real de ejecución: 2026-10-08 (hora local, Europe/Madrid)
Estado: EN CURSO

## 1. Candidato probado

| Elemento | Valor |
|---|---|
| Tipo de candidato | Checkout de trabajo ejecutado como runtime web local (NO Setup instalado, NO portable) |
| Rama | `fix/react-functional-continuation-20261007` |
| HEAD | `0f3ff15292f84a7d6877f9f2d6e47a3f646355f4` |
| Árbol HEAD | `4faf9638a5c558991a60a91b489cda6943a52e4f` |
| Base de producto | `642966a93e7e9c9f9c5e93cce0bc842f538846fb`, árbol `e0a3966bddc8bbd4cfc2ab4041668c3162ce86f7` |
| Diferencia respecto a la base de producto | Solo documental: `AUTO_TEST.md`, `MANUAL_TEST1.md`, `MANUAL_TEST2.md`, `implementation_documents/manual_windows_20261006/MANUAL_TEST_HANDOFF.md`. Sin cambios de producto → no exige reconstruir. |
| Frontend | `src/frontend` construido en esta ejecución con `npm ci --ignore-scripts` + `npm run build` (319 paquetes, 26 assets locales verificados, 29 licencias) |
| Entrega del frontend | `src/frontend/dist` verificada por `validate_frontend_dist` en cada petición |
| Launcher | `src/starter_headless.py` (ciclo de vida real: `find_free_port`, `wait_for_server`, `stop_owned_process`), modo sin ventana |
| Origen/puerto | `http://127.0.0.1:8000` (puerto 8000 libre, elegido por el launcher; PID propio verificado) |
| Base de datos | Sintética y desechable: `C:\Users\dhays\AppData\Local\Temp\opencode\slm-auto-2026-10-08-001\slm_educator.db` (creada de cero por esta campaña) |
| Configuración | Copia de `env.properties` del repo en el directorio aislado; sin claves ni secretos |
| Logs/config | `api.log`, `starter_debug.log`, `data/`, `exports/`, `logs/` en el directorio aislado |

No se abrió el Setup histórico `SLMEducator-Setup-2.0.0-fe954cab4655.exe` ni los portables
`dist/SLMEducator_acceptance*`. No se construyó ni instaló ningún Setup: el candidato probado es el
checkout, y sus resultados no se extienden al instalador.

## 2. Entorno

| Elemento | Valor |
|---|---|
| Sistema | Windows 10.0.26200.9550 (build 26200) |
| Python del runtime | `venv` del repo, Python 3.14.7 |
| Node usado solo para construir | v24.21.0 / npm 11.19.0 |
| Navegador | Chrome administrado por el cliente DevTools (MCP chrome-devtools) |
| Viewport | 1440 × 900 CSS px (redimensionado explícito antes de las capturas) |
| Idioma de la sesión | Español (valor inicial real observado) |
| Tema | Sistema (valor inicial real observado) |
| Lector de pantalla | No disponible |
| Audio/acústica | No disponible |

## 3. Desviación declarada respecto a AUTO_TEST.md §1

David ordenó explícitamente usar DevTools/CDP porque «la app funciona únicamente en web».
Consecuencias, aplicadas a toda la campaña:

- La evidencia es `GUI_CDP`: interacción real sobre la aplicación servida en `127.0.0.1:8000`,
  observada mediante instantáneas del árbol de accesibilidad y capturas originales inspeccionadas.
- **No** hay control nativo de pantalla, ratón ni teclado del sistema.
- **No** se puede acreditar por esta vía: X nativa del launcher, foco a nivel de sistema, escalado
  nativo del menú del navegador, lector de pantalla, sonido, instalación/Setup, ciclo de vida del
  instalador. Esos casos quedan BLOCKED por variante, no PASS.
- Las PASADAS I y II se ejecutan sobre el runtime web del checkout. Los casos AUTO-BOOT-01..05 y
  AUTO-LIFE-01 que exigen ventana nativa del launcher, Setup o instalador quedan BLOCKED.

## 4. Cuentas sintéticas

Todas creadas desde la GUI salvo `admin`, creado con el bootstrap mantenido
`scripts/seed_admin.py` sobre la base NUEVA y desechable de esta campaña (create-only; no se adoptó
ni reseteó ninguna cuenta existente). Credenciales sintéticas desechables, sin valor real:

| ID | Usuario | Rol | Contraseña sintética | Creación |
|---|---|---|---|---|
| 1 | `admin` | Administrador | `AutoTest2026Disposable` | bootstrap sobre base nueva |
| 2 | `docente_auto08` | Docente (T1 «Docente Demo») | `Fracciones#2026Aa` | GUI, Admin → Personas → Crear cuenta |
| 3 | `alba_auto08` | Estudiante (S1 «Alba Demo») | `Fracciones#2026Aa` | GUI, Admin → Personas → Crear cuenta |

T2 (traspaso) y S2 (Bruno) están pendientes de crear en el corte básico.

## 5. Proveedor de IA

| Elemento | Observado |
|---|---|
| `env.properties` (config por defecto) | `default_provider = ollama`, `default_model = gpt-oss` |
| Puerto 11434 (Ollama) | NO escucha en esta máquina |
| Puerto 1234 (LM Studio) | Escucha en esta máquina |
| Nota | El destino configurado por defecto no está disponible; existe un runtime local distinto. La configuración de proveedor es por cuenta y se guardará indicando qué cuenta la realiza. |

## 6. Límites de acceso y autorizaciones

- Autorizado por David: preparación técnica de build; uso de DevTools/CDP para toda la campaña;
  credencial admin mediante bootstrap controlado.
- No autorizado / no realizado: installer, Setup, ciclo de vida, desinstalación, registro HKCU,
  publicación en Git, Actions, merges, OTA, cambios de red/firewall/VPN, descargas de modelos,
  proveedores de pago, auditorías ofensivas o campañas semánticas masivas.
- Archivos de laritten campaña: locales. No se publica nada sin autorización expresa.

## 7. Estructura de la campaña

- `COVERAGE.csv`: una fila por caso y variante, todas inicializadas en `NOT_RUN`.
- `DEFECTS.md`: registro único de defectos de esta ejecución (`SLM-AUTO-NNN`).
- `SESSION_LOG.md`: secuencia realmente ejecutada.
- `RESUME.json`: punto exacto de reanudación.
- `evidence/`: capturas originales inspeccionadas y comprobaciones técnicas saneadas.
