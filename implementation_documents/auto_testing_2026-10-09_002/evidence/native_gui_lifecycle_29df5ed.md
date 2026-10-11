# Evidencia GUI nativa · ciclo de vida del launcher (candidato 29df5ed)

Fecha local: 2026-10-10 (cierre 14:00:56). Solo pruebas y documentación; sin
cambios de producto, sin GitHub Actions, sin push, sin tocar el navegador del
propietario (Chrome 9222). Esto **no** es una declaración de aceptación humana.

## Artefactos identificados

| Elemento | Valor |
|---|---|
| Setup | `C:\builds\slm-setup-29df5ed\SLMEducator-Setup-2.0.0-29df5ed.exe`, SHA-256 `26217942AF4EEF00CD2F10D196F259ACE4A7F1B41FF3775CA71222D05143AB17` |
| EXE instalado | `%LOCALAPPDATA%\Programs\SLMEducator\SLMEducator.exe`, SHA-256 `12896871AE081242211CE1D75D4C06137E657ECB46E71A1A64BFD4B0FD35C949` == payload |
| Registro HKCU | `SLMEducator 2.0.0 (build 29df5ed)`, InstallLocation `%LOCALAPPDATA%\Programs\SLMEducator\` |
| Acceso directo | `%APPDATA%\Microsoft\Windows\Start Menu\Programs\SLMEducator\SLMEducator.lnk` → destino `...\SLMEducator\SLMEducator.exe` |
| Base instalada | `slm_educator.db` 434176 bytes; 27 tablas; 1 cuenta `admin` ADMIN creada `2026-10-09 17:26:58 UTC` (preexistente, no resembbrada); SHA-256 post-ciclo `464A63A9A4FE9CE3FE492365ADA097E67F24B600FD1A184CC62607C109473263` |
| Aislamiento agente | Chrome propio headless CDP `127.0.0.1:9333`, perfil `C:\builds\slm-agent-chrome`; captura `C:\builds\cap9333.js` |

## Método de interacción nativa

- Clics reales: `SetForegroundWindow` + `SetCursorPos` + `mouse_event` sobre el
  HWND comprobado con `WindowFromPoint`/`GetAncestor` (los `PostMessage`
  sintéticos no funcionan en Tk; se abandonaron).
- Diálogos Tk: botones expuestos por UIA como `Pane` sin `InvokePattern`; se
  usó `SendMessage(BM_CLICK=0xF5)` directo al HWND del botón (ret 0) y verificación posterior por UIA + estado del servidor.
- Ventana tapada por otras ventanas: `SetWindowPos` TOPMOST/NOTOPMOST temporal;
  captura del estado con `PrintWindow(PW_RENDERFULLCONTENT)` para no incluir el
  escritorio privado del propietario.

## Resultados observados

| Paso | Observación | Resultado |
|---|---|---|
| X → «No» (hecho por el propietario) | PID 58896 vivo, `/api/status` 200 `online`, puerto 8000 LISTEN | PASS (cancelación) |
| X → «Sí» (instancia 58896/28548) | launcher terminado, sin procesos SLMEducator, puerto 8000 libre, API caída | PASS (cierre) |
| Relanzado EXE instalado | PIDs 28548+49728, `/api/status` 200 `{"status":"online","version":"2.0.0"}` | PASS |
| Relanzado por acceso directo Menú Inicio | `.lnk` destino verificado; PIDs 69464+70308; ventana «SLMEducator · Aplicación local» | PASS |
| «Detener» → «No» (launcher 70308) | diálogo «¿Detener la aplicación local?…» observado; No cierra diálogo; `/api/status` sigue 200; sin huérfanos | PASS (cancelar) |
| «Detener» → «Sí» | puerto 8000 libre, API caída, launcher 70308 vivo (solo servidor detenido) | PASS (detenido) |
| «Iniciar» | nuevo PID servidor 27916, puerto 8000 LISTEN, API 200, estado «Lista para abrir» | PASS (listo) |
| X → «No» (launcher 70308) | diálogo «Cerrar» observado; No lo descarta; ventana y servidor siguen | PASS (cancelar) |
| Persistencia | 27 tablas, misma cuenta `admin` 2026-10-09, sin resembrado; `/entrar` renderiza «Te damos la bienvenida · SLMEducator» en el navegador del agente | PASS |

## Capturas (inspeccionadas, solo ventana, sin escritorio privado)

| Archivo | Contenido |
|---|---|
| `evidence/auto-boot-03-x-dialog.png` | Diálogo nativo «Cerrar» con «¿Detener la aplicación local y cerrar esta ventana?…» y botones Sí/No |
| `evidence/auto-boot-02-launcher-ready.png` | Launcher «Lista para abrir», «Dirección local http://127.0.0.1:8000», botones Iniciar/Detener/Cerrar |
| `evidence/auto-boot-04-ready-after-iniciar.png` | Mismo estado «Lista para abrir» tras el ciclo Detener(cancelar) → Detener(confirmar) → Iniciar |
| `evidence/auto-boot-04-entrar-persistencia.png` | `/entrar` funcional tras relanzado (título «Te damos la bienvenida · SLMEducator») |

## Límites declarados

1. **AUTO-BOOT-02 = PARTIAL**: el botón «Abrir SLMEducator» no se pulsó porque
   usaría el navegador predeterminado del propietario; la apertura se demostró
   navegando el navegador propio del agente (CDP 9333) a la dirección publicada
   por el launcher.
2. **AUTO-BOOT-01 / AUTO-BOOT-05 / AUTO-BOOT-06** sin cambiar: Setup GUI,
   fixture de puerto ocupado y alta del primer administrador con handoff de
   credenciales siguen pendientes/bloqueados.
3. Los clics «Sí»/«No» de diálogo se enviaron con `BM_CLICK` (mensaje nativo al
   control), no con ratón física en todos los casos; el oráculo (estado del
   diálogo, procesos y puerto) se verificó por UIA/Win32/HTTP en cada paso.
4. Ninguna credencial aparece en este documento; la cuenta no fue modificada.
