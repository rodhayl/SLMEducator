# SESSION_LOG · auto-2026-10-08-001

Secuencia realmente ejecutada. Sin secretos: las credenciales son sintéticas, desechables y
documentadas en RUN.md §4.

## Preparación técnica (autorizada por David)

1. Identificación del candidato: rama `fix/react-functional-continuation-20261007`, HEAD `0f3ff15`,
   árbol `4faf96`, producto `642966a`. Diferencia con la base de producto: solo cuatro ficheros
   documentales. No se reconstruye el instalador.
2. Inventario del entorno: Python 3.14.7 en `venv`, Node v24.21.0, Inno Setup 6 presente,
   puertos 8000 y 11434 libres, 1234 ocupado (LM Studio).
3. `npm ci --ignore-scripts` en `src/frontend` (319 paquetes) y `npm run build` (26 assets locales y
   29 licencias verificados). No existía `src/frontend/dist` en el checkout.
4. Directorio de runtime aislado en
   `C:\Users\dhays\AppData\Local\Temp\opencode\slm-auto-2026-10-08-001` con copia de
   `env.properties`, `logs/`, `data/`, `exports/` y base de datos nueva vía `SLM_DB_PATH`.
5. Arranque del runtime real: `src/starter_headless.py`, escuchando en `127.0.0.1:8000`, PID propio.

### Preparación de IA (autorizada por David)

6. `env.properties` apuntaba a `ollama`/`gpt-oss` y no hay nada escuchando en 11434. LM Studio sí
   escucha en 1234. Se descubrió el modelo realmente cargado (`slm-production-evaluation`, vlm,
   Q4_K_XL, `state=loaded`) y se configuró `default_provider = lm_studio` con ese modelo, con un
   comentario en el fichero que identifica destino y modelo. También se configuró en la cuenta
   docente desde la propia pantalla (AUTO-AI-01).

### Correcciones de preparación propia (identificadas como tales)

- **Credencial admin, intento 1**: la generación aleatoria en PowerShell 5.1 falló
  (`RandomNumberGenerator.Fill` no existe) y el `admin` quedó sembrado con una contraseña de 24
  caracteres idénticos. Se detuvieron solo procesos PROPIOS (árbol `starter_headless` y su hijo,
  verificados por línea de comandos y hora de creación), se eliminó la base sintética creada un
  minuto antes y se resembró.
- **Credencial admin, intento 2**: se resembró con una credencial sintética documentada y desechable
  para que ninguna contraseña real viaje por el chat, los informes o Git.
- **Proceso huérfano**: al detener el launcher, el proceso servidor (nieto) sobrevivió al padre.
  Identificado por PID y detenido. Relevante para AUTO-BOOT-04.
- **Curso duplicado (ID 1)**: un clic mío mal dirigido tras un re-render guardó el curso antes de que
  apareciera el diálogo de cambios sin guardar, creando un homónimo del curso 2. **No se atribuye al
  producto.** Se conservó y se usó como evidencia de SLM-AUTO-006 (homónimos indistinguibles).
- **Perdida de un valor propio**: «Máximo de intentos» quedó en 1 tras un envío programático de varios
  campos a la vez; reescrito a mano persistió 2. Registrado como observación sin atribuir defecto.
- **Falso positivo descartado**: el contador «1 preguntas sin responder» no se actualizaba tras un
  `fill` programático, pero sí con pulsaciones reales. Se descartó como artefacto de la herramienta, no
  como defecto del producto.
- **Fallo de herramienta propio**: el actualizador incremental de `COVERAGE.csv` fallaba al buscar
  `AUTO-VIS-02.idiomas_temas` porque yo escribía `idiemas` en el script. Diagnosticado comparando
  bytes; se sustituyó por una reescritura atómica de todas las filas.

## Pasada I · ejecución GUI (evidencia GUI_CDP)

### Administrador
| Caso | Resultado |
|---|---|
| AUTO-AUTH-01 (vacío / inválido / válido) | PASS ×3 |
| AUTO-ADMIN-01 estado y versión | PASS |
| AUTO-PEO-01 (correo inválido y alta) | PASS — **H-D3 corregido** |
| AUTO-PEO-02 (matrícula) | PASS |
| AUTO-PEO-03 (buscar / filtrar / volver) | PARTIAL — SLM-AUTO-001 |
| AUTO-AUTH-03 logout con borradores | PARTIAL (diálogo correcto, trabajo pendiente no probado) |

### Docente
| Caso | Resultado |
|---|---|
| AUTO-CRS-01 descubribilidad (G3) | PASS |
| AUTO-MAT-01 / MAT-02 | PARTIAL — SLM-AUTO-002, SLM-AUTO-003 |
| AUTO-CRS-02 / CRS-03 | PASS |
| AUTO-CRS-04 / CRS-05 | PASS |
| AUTO-EVA-01 / EVA-02 | PASS — SLM-AUTO-009 (observación) |
| AUTO-GRADE-01 | PASS — SLM-AUTO-008 |
| AUTO-HELP-01 | PASS |
| AUTO-AI-01 / AI-02 | PASS |
| AUTO-GEN-01 | FAIL — SLM-AUTO-005 |
| AUTO-GEN-02 | PARTIAL (5 modos inventariados) |
| AUTO-TUT-01..03, AUTO-QA-01..03 | BLOCKED — SLM-AUTO-004 |

### Alumna (Alba, S1)
| Caso | Resultado |
|---|---|
| AUTO-LEARN-01 / LEARN-02 | PASS — SLM-AUTO-007 |
| AUTO-LEARN-03 | PARTIAL |
| AUTO-EVA-02 (previa) / EVA-03 (entrega) | PASS ×2 |
| AUTO-EVA-04 | NOT_APPLICABLE (sin límite de tiempo por diseño) |
| AUTO-GRADE-03 feedback | PASS |
| AUTO-MSG-01 | PASS |
| AUTO-VIS-02 idioma y tema | PARTIAL |
| AUTO-PORT-01 export | PASS |
| AUTO-PORT-04 | BLOCKED (fuera del directorio permitido) |

### Alumno (Bruno, S2) y aislamiento
| Caso | Resultado |
|---|---|
| AUTO-LEARN-01 (vacío de S2) | PASS |
| AUTO-REG-04 enlaces ajenos | PASS — sin filtración en 5 recursos |

## Capturas inspeccionadas

`01_auth_admin_inicio.png` · `02_admin_estado_actualizar.png` · `03_peo_confirmar_matricula.png` ·
`04_peo_busqueda_demo.png` · `05_crs_vacio.png` · `06_crs_estructura_guardada.png` ·
`07_crs_asignar_confirmacion.png` · `08_ai_proveedor_lmstudio.png` · `09_eva_borrador.png` ·
`10_learn_leccion_vacia_secciones.png` · `11_eva_envio_resultado.png` ·
`12_grade_confirmar_finalizacion.png` · `13_vis_english_dark.png`

Evidencia técnica: `ai_generation_failure.log` (extracto saneado de `api.log`).

## Restitución

Preferencias de la cuenta S1 restauradas a Español / Sistema. No se desinstaló, desactivó ni borró
ninguna cuenta, curso, material ni mensaje. El fichero exportado queda en el directorio de descargas
del navegador; no se abrió ni se eliminó (fuera del directorio de trabajo).

## Recursos propios abiertos al cierre

- Servidor web local `127.0.0.1:8000` (proceso propio, parado solo por PID verificado).
- Base sintética desechable en el directorio temporal aislado.
- Pestaña del navegador con sesión de `alba_auto08`.

## Siguiente acción

AUTO-EVA-04 (evaluación con reloj), AUTO-PROG-01/02, AUTO-PEO-04 (crear T2 y traspasar S1),
AUTO-SRC-01/02 y AUTO-PORT-02/03. Ver RESUME.json.
