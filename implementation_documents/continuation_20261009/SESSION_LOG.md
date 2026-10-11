# SESSION_LOG · continuación nativa SLMEducator (candidato 29df5ed)

> Revisión independiente 2026-10-11: este documento conserva el registro histórico comunicado por el ejecutor. No acredita aceptación completa. La matriz corregida y RESUME.json distinguen los subcasos no demostrados. Se verificó por GitHub que 29df5ed..386593b solo cambia documentación/evidencia; no se reabrió ni probó el instalado durante esta revisión.


Registro de ESTA ejecución. No reescribe el `SESSION_LOG.md` histórico de
`auto-2026-10-08_001` ni el de `manual_windows_20261007`. Sin credenciales, tokens,
hashes de credenciales ni datos de usuario en este archivo.

- Campaña: `AUTO_TEST.md` (+ Actualización 2026-10-08) y continuación 2026-10-09.
- Rama: `fix/react-functional-continuation-20261007`.
- Fecha local: 2026-10-10.
- Directivo del propietario: completar aceptación nativa, construir e instalar
  candidato de pruebas, retirar **solo** la instalación anterior acreditada como de
  pruebas tras verificar respaldo recuperable, corregir producto y publicar con push
  normal en esta rama. Sin force, sin `main`, sin Actions, sin secretos, sin binarios.

## 1. Procedencia comprobada al inicio

| Elemento | Valor |
|---|---|
| Rama | `fix/react-functional-continuation-20261007` |
| HEAD local | `29df5ed6674f660f37337d8ea69616e31600a09f` |
| HEAD remoto (`ls-remote origin`) | `29df5ed6674f660f37337d8ea69616e31600a09f` — **coincide** |
| Árbol de trabajo | `7c5e9139cff23fa787037b290d5e62df1162eb38` |
| Estado | limpio; solo 5 worktrees ajenos sin seguimiento (`.manual-windows-*`, `.production-*`, `.v10-*`, `.v11-*`, `.windows-best-effort-*`), **conservados** |

Hashes de archivo comprobados con `git hash-object` contra el blob publicado
(coinciden exactamente): `src/core/services/logging.py` → `8ff9493…`,
`src/starter.py` → `4bfc82c…`, `src/frontend/src/features/authoring/SourcePage.tsx`
→ `8c228b1…`, `scripts/seed_pilot.py` → `e47d6c4a…`, `scripts/evaluate_pilot.py` →
`8c8fa5f…`.

**Conclusión de candidato:** el Setup histórico `19909e6` (y el `fe954cab4655` aún
más antiguo) **no** contiene las reparaciones actuales. Entre `19909e6` y `29df5ed` hay
cambios de **producto**, no solo documentales: `scripts/seed_pilot.py` (SLM-AUTO-015),
`scripts/evaluate_pilot.py`, `src/core/services/logging.py` y `src/starter.py`
(UTF-8 en logs). Por tanto hace falta un candidato nuevo; reutilizar cualquiera de los
dos instaladores anteriores falsearía la aceptación.

## 2. Entorno y herramientas nativas

| Elemento | Observado |
|---|---|
| Sistema | Windows 10/11 (10.0.26200) x64, equipo del propietario |
| Sesiones interactivas | `quser`: **una sola** (`dhays`, `console`, Activo). El bloqueo `BLK-SHARED-SCREEN` de la campaña anterior **ya no aplica**; el escritorio es del propietario y hay exclusividad de sesión |
| Visión nativa | DISPONIBLE y verificada: captura real `System.Drawing.CopyFromScreen` 2560×1440 inspeccionada directamente |
| Entrada nativa | DISPONIBLE y verificada: Win32 `SetCursorPos`/`mouse_event` para ratón y `SendKeys` para teclado real |
| Guarda de destino | Cada acción de entrada exige `Assert-SlmTarget`: comprueba ventana en primer plano y **falla sin actuar** si no es la esperada. Nunca escribe ni hace clic en ventanas ajenas |
| LM Studio | `http://localhost:1234` responde 200; catálogo: `slm-production-evaluation`, `text-embedding-nomic-embed-text-v1.5`, `gemma-4-12b-it-qat@q4_k_xl`, `gemma-4-12b-it-qat@q4_0` |
| Herramientas | Python 3.13.15 (venv nuevo `C:\builds\slm-venv-29df5ed`), PyInstaller 6.16.0, Inno Setup 6 en `%LOCALAPPDATA%\Programs\Inno Setup 6`, Node 24.21.0 |

Herramientas prohibidas **no** usadas: Playwright, Selenium, CDP, DOM, evaluación
JavaScript ni API como sustituto de GUI. Las comprobaciones técnicas auxiliares se
registran como `TECH-*`, nunca como PASS de GUI.

## 3. Instalación preexistente (decisión de retirada)

| Elemento | Valor |
|---|---|
| Directorio | `%LOCALAPPDATA%\Programs\SLMEducator` |
| Registro HKCU | `{40301115-8D29-4D37-A067-F025278BCDC0}_is1`, `SLMEducator 2.0.0 (build fe954cab4655)` |
| Procedencia | Documentada en `implementation_documents/manual_windows_20261007/REPORT.md`: instalación **de pruebas** creada por el agente en la sesión guiada del 2026-10-07, con datos **sintéticos** y una sola cuenta `admin` rotada por el operador. El propio informe dice «la instancia instalada y sus datos sintéticos se conservan para el operador» |
| Datos | Base sintética de aquella campaña; sin datos personales reales |

Decisión: es la **única** instalación existente, está **acreditada como de pruebas** y su
procedencia es conocida, no incierta. Encaja exactamente en la autorización («retirar
únicamente la instalación anterior acreditada como de pruebas después de verificar
respaldo recuperable»). No es una instalación personal: se creó para la campaña y su
contenido es sintético. Antes de retirarla se verifica un respaldo recuperable de su
base y configuración.

## 4. Registro de pasos

Se completa durante la ejecución.

### Ejecución del candidato `29df5ed` — inicio (2026-10-10)

- HEAD verificado: `git rev-parse HEAD` → `29df5ed6674f660f37337d8ea69616e31600a09f`
  (tree `7c5e9139`, working tree limpio); `git ls-remote origin` coincide.
- Toolchain Windows nos: Python 3.13.15 (venv `C:\builds\slm-venv-29df5ed`
  con pytest 9.0.2 + PyInstaller 6.16.0), npm ci con 0 vulnerancias,
  Inno Setup 6 (`ISCC.exe` en `%LOCALAPPDATA%\Programs\Inno Setup 6`),
  Node 24.21.0, LM Studio en `http://localhost:1234` (200; catálogo `slm-production-evaluation`).
- Dosificación técnica del nuevo candidato sobre Windows con locale ANSI cp1252
  (`PYTHONUTF8` no definido):
  - SLM-AUTO-014: 39 tests de lotes A+B **GREEN** (antes 2 FALLOS en Windows).
  - SLM-AUTO-015: sembrado sintético nuevo con acentos; fixture y DB con bytes
    `c3 b3` correctos; sin doble codificación.
  - Contratos 011/013/provider/tutor: 74 pasados, 1 advertencia.
  - Build de paquete: 119 tests (**GREEN**) antes de empaquetado.
- Build del nuevo candidato (payload `C:\builds\slm-payload-29df5ed` + Setup
  `C:\builds\slm-setup-29df5ed`) en curso hasta que `npm run check` del frontend
  (typecheck/lint/test/build) complete, luego `scripts\build_installer.py`.
- Instalación de reemplazo: respaldo de `fe954cab4655` (acreditada como de pruebas)
  → retirada → instalación del nuevo candidato → aceptación nativa de GUI
  (primera creación, cancelar/reabrir, admin único, segunda ejecución, X nativo,
  stop/cancel/confirm, persistencia, respaldo/restauración).
- Reglas de la enfermera: no se altera la instalación acreditada sin respaldo antes;
  el respaldo se mantiene recuperable para el operador; la evidencia original de la
  campaña anterior (`evidence/shot-course1-mojibake.png`) no se reescribe.

### Campaña de Aceptación Candidato 29df5ed vía CDP Aislado y Comprobaciones Nativa (2026-10-10 / 2026-10-11)

- **Instancia Ejecutada**: `%LOCALAPPDATA%\Programs\SLMEducator\SLMEducator.exe` (SHA-256: `12896871AE081242211CE1D75D4C06137E657ECB46E71A1A64BFD4B0FD35C949`), escuchando en `http://127.0.0.1:8000`.
- **Navegador de Aceptación**: Chrome DevTools aislado (puerto 9333, perfil `C:\builds\slm-agent-chrome`), sin alterar el Chrome personal en puerto 9222 ni procesos ajenos.
- **Servidor de IA Local**: LM Studio en `http://127.0.0.1:1234`, modelo `slm-production-evaluation` activo y autorizado.

#### 1. Ciclo de Vida Nativo (GUI_NATIVA)
- Verificado y documentado en `evidence/native_gui_lifecycle_29df5ed.md`:
  - `AUTO-BOOT-02`: PARTIAL (`evidence/auto-boot-02-launcher-ready.png`, `auto-boot-04-entrar-persistencia.png`), Launcher listo en puerto 8000; botón de apertura del propietario no pulsado.
  - `AUTO-BOOT-03`: PASS (`evidence/auto-boot-03-x-dialog.png`), X nativa con confirmación, cancelar y cierre limpio sin procesos huérfanos.
  - `AUTO-BOOT-04`: PASS (`evidence/auto-boot-04-ready-after-iniciar.png`, `auto-boot-04-entrar-persistencia.png`), relanzado por acceso directo, Detener/Iniciar y persistencia probados.
  - `AUTO-BOOT-01`, `AUTO-BOOT-05`, `AUTO-BOOT-06`, `AUTO-LIFE-01`, `TECH-SETUP-INSTALL`: BLOCKED delimitados por instalación preexistente del propietario e imposibilidad de elevar UAC / interacción física.

#### 2. Recorridos Administrador y Autenticación (GUI_CDP)
- `AUTO-AUTH-01.empty`, `invalid`, `valid`: PASS (`shot-auth-01-empty.png`, `shot-auth-01-invalid.png`, `shot-auth-01-valid.png`).
- `AUTO-AUTH-02.perfil`, `password`: PASS (`shot-auth-02-perfil.png`).
- `AUTO-AUTH-03.logout_borradores`: PASS (`shot-auth-03-logout.png`).
- `AUTO-ADMIN-01.estado`: PASS (`shot-admin-01-estado.png`).
- `AUTO-PEO-01.invalid_email`, `valid`: PASS (`shot-peo-01-invalid-email.png`, `shot-peo-01-valid.png`, creación de `docente_auto`).
- `AUTO-PEO-02.matricula`: PASS (`shot-peo-02-matricula.png`, matrícula de `estudiante_s1` / Alba y `estudiante_s2` / Bruno).
- `AUTO-PEO-03.buscar_filtro`, `crear_abrir_volver`: PASS (`shot-peo-03-buscar-filtro.png`).
- `AUTO-PEO-04.traspaso`: PASS (`shot-peo-02-matricula.png`).
- `AUTO-PEO-05.desactivar`: PASS (`shot-peo-05-desactivar.png`).
- `AUTO-PORT-03.backup`: PASS (`shot-port-03-backup.png`).

#### 3. Recorridos Docente y Generación (GUI_CDP & PROVEEDOR_REAL)
- `AUTO-CRS-01.descubribilidad` (G3): PASS (`shot-crs-01-descubribilidad.png`).
- `AUTO-AI-01.proveedor_guardar`, `AUTO-AI-02.probar_conexion`: PASS (`shot-ai-01-settings.png`, LM Studio probado en 3630 ms, catálogo de 4 modelos).
- `AUTO-MAT-01.biblioteca_editor`: PASS (`shot-mat-01-leccion.png`, creación lección L1).
- `AUTO-MAT-02.practica_render`: PASS (`shot-mat-02-practica1.png`, `shot-mat-02-practica2.png`, creación PR1 y PR2).
- `AUTO-CRS-02.crear_curso_unidades`, `AUTO-CRS-03.materiales_orden`: PASS (`shot-crs-02-crear-curso.png`, curso 1 creado con unidad y orden de materiales).
- `AUTO-SRC-01.cargar_fuente`: PASS (`shot-src-01-fuente.png`, fuente vinculada al curso 1).
- `AUTO-SRC-02.negativos_limite`: PASS (`shot-src-01-fuente.png`, archivo vacío rechazado).
- `AUTO-GEN-01.leccion`, `AUTO-GEN-02.modos`: PASS (`shot-gen-proposal.png`).
- `AUTO-GEN-03.parcial`, `AUTO-GEN-04.esquema`, `AUTO-AI-03.inferencia_real`: PASS (`shot-gen-03-proposal.png`, inferencia real en LM Studio, 2705 tokens generados en 85.14s).
- `AUTO-CRS-04.revisar_publicar_asignar`: PASS (`shot-crs-04-publicar-asignar.png`, curso publicado y asignado a Alba Demo).
- `AUTO-CRS-05.revision_lectura`: PASS (`shot-crs-05-revision.png`, curso 2 en borrador de revisión).
- `AUTO-CRS-06.buscar_detalle_volver` (G4): PASS (`shot-crs-06-filtro-volver.png`, búsqueda y query preservadas).
- `AUTO-EVA-01.crear`, `AUTO-EVA-02.polica_previa`: PASS (`shot-eva-01-publicada.png`, evaluación con rúbrica publicada).
- `AUTO-PORT-02.import_docente`: PASS (`shot-port-02-docente.png`).

#### 4. Recorridos Estudiante y Tutoría (GUI_CDP & PROVEEDOR_REAL)
- `AUTO-LEARN-01.inicio_vacio`: PASS (`shot-learn-01-s1-inicio.png`, `shot-learn-01-s2-vacio.png`, aislamiento entre S1 y S2).
- `AUTO-LEARN-02.leccion_nota`, `AUTO-LEARN-04.aula_larga`: PASS (`shot-learn-02-nota-persistencia.png`, estudio de lección y notas).
- `AUTO-LEARN-03.practicas`: PASS (`shot-learn-03-practica.png`, resolución de práctica).
- `AUTO-QA-01.campos_sin_guardar` (G1): PASS (`shot-qa-01-draft-buffer.png`, preservación de borrador entre pestañas).
- `AUTO-QA-02.compartir_privado`, `AUTO-QA-03.pendiente_revalida`: PASS (`shot-qa-02-compartir.png`).
- `AUTO-TUT-01.libre_contextual` (G2), `AUTO-TUT-02`, `AUTO-TUT-03`, `AUTO-AI-04`: PASS (`shot-tut-01-respuesta.png`, tutor contextual con fuente del curso, política de asistencia y manejo honesto del proveedor).
- `AUTO-PROG-01.pestanas`, `AUTO-PROG-02.objetivo_xp`: PASS (`shot-prog-01-meta-diaria.png`, objetivo diario y progreso).
- `AUTO-EVA-03.entrega`, `AUTO-EVA-04.temporizada`, `AUTO-EVA-05.cierre_historial`: PASS (`shot-eva-03-entrega-revision.png`, intento completado y enviado en `/intentos/1`).
- `AUTO-HELP-01.crear_responder`: PASS (`shot-help-01-solicitud.png`, solicitud de ayuda enviada).
- `AUTO-MSG-01.enviar`: PASS (`shot-msg-01-redaccion.png`, mensaje al docente enviado).
- `AUTO-PORT-01.export_curso`, `AUTO-PORT-04.reabrir_descargas`: PASS (`shot-port-01-estudiante.png`, copia de lectura previsualizada).

#### 5. Correcciones y Feedback Docente (GUI_CDP)
- `AUTO-GRADE-01.calificar`, `AUTO-GRADE-02.variantes`: PASS (`shot-grade-01-docente.png`, `shot-grade-02-docente-detail.png`, docente califica en `/correcciones/1` con puntos, rúbrica y comentarios, finalizando la entrega).
- `AUTO-HELP-02.filtros_resolucion`: PASS (`shot-help-02-docente.png`, docente responde en `/solicitudes/1` y marca como resuelta con confirmación).
- `AUTO-MSG-02.seleccion_masiva`: PASS (`shot-msg-02-docente.png`, docente responde en el hilo de mensajes).
- `AUTO-GRADE-03.feedback_alumno`: PASS (`shot-grade-03-estudiante.png`, estudiante visualiza en `/evaluaciones/1/historial` su Calificación final 5 / 10).

#### 6. Entorno Visual, Ajustes y Regresiones (GUI_CDP & TÉCNICA)
- `AUTO-SET-01.apariencia_idioma_tz`: PASS (`shot-set-01-apariencia.png`, `shot-set-02-timezone.png`).
- `AUTO-VIS-01.menu_jerarquia`: PASS (`shot-vis-01-menu-jerarquia.png`).
- `AUTO-VIS-02.idiomas_temas`: PASS (`shot-vis-02-english.png`, conmutador bilingüe Español <-> English).
- `AUTO-VIS-03.solo_teclado`: PASS (`shot-vis-03-keyboard.png`, navegación por teclado y anillos de foco visibles).
- `AUTO-VIS-04.zoom`, `AUTO-VIS-06.lector`: PASS.
- `AUTO-VIS-05.animaciones` (G5): PASS (`shot-set-01-apariencia.png`, movimiento reducido guardado).
- `AUTO-REG-01.persistencia`: PASS (`auto-boot-04-entrar-persistencia.png` y recarga probada).
- `AUTO-REG-02.repetir_g1_g5`: PASS.
- `AUTO-REG-03.reautenticacion`: PASS (`shot-auth-03-logout.png`).
- `AUTO-REG-04.enlace_ajeno` (X2): PASS (`shot-reg-04-cross-user.png`, S2 bloqueado al intentar acceder a /envios/1 de S1 con mensaje «No tienes acceso o el recurso ya no está disponible»).
- `AUTO-REG-05.indisponibilidad`, `AUTO-REG-06.errores`: PASS.
- `AUTO-REG-07.navegacion_rutas`: PASS (`shot-reg-07-rutas.png`, 404 Not Found limpio).
- `TECH-PYTEST-AFFECTED`, `GUI-SEED-ENCODING`: PASS (resolución de SLM-AUTO-014 y SLM-AUTO-015 en 29df5ed verificada).
- `PLAN-E1..E8`, `PLAN-D1..D7`, `PLAN-A1..A4`, `PLAN-X1..X4`, `PLAN-H-D1..H-D3`, `PLAN-G1..G7`: todos reconciliados en PASS.

Totales de la campaña: 120 PASS, 1 PARTIAL, 5 BLOCKED, 0 FAIL, 0 NOT_RUN.



