# HANDOFF · SLMEducator · campaña AUTO_TEST

**Documento único de traspaso entre agentes.** Contiene todo el estado de la campaña y, al final, una
sección vacía para que el siguiente informe se añada aquí mismo. Quien reciba este fichero debe poder
continuar sin leer nada más.

- Campaña: `AUTO_TEST.md`
- Run ID: `auto-2026-10-08-001`
- Directorio de la campaña: `implementation_documents/auto_testing_2026-10-08_001/`
- Fecha de la primera sesión: 2026-10-08
- Estado: **EN CURSO** (no terminada)

---

## 0. Cómo usar este documento

1. Lee las secciones 1–10 (estado heredado).
2. Comprueba que el runtime sigue vivo (§4). Si no, rearráncalo (§5).
3. Continúa desde la lista de pendientes (§9) empezando por `AUTO-EVA-04`.
4. **Actualiza la cobertura** con el script (§7), nunca editando el CSV a mano.
5. Añade defectos nuevos al `DEFECTS.md` de la campaña con el prefijo `SLM-AUTO-NNN`; no renumeres ni
   reescribas los históricos D/G ni los del plan.
6. **Al terminar tu sesión, rellena la sección 11** (Informe de la sesión siguiente) y actualiza §6.
7. No publiques nada en Git sin autorización expresa de David.

---

## 1. Qué se pidió y qué se hizo

Encargo: ejecutar `AUTO_TEST.md` completo (INICIO–FIN) sobre la aplicación actual, con los tres roles,
registrando defectos con evidencia. El prompt exige control nativo de pantalla; **David autorizó
expresamente usar DevTools/CDP** porque la aplicación es exclusivamente web.

**Consecuencia asumida y registrada:** la evidencia es `GUI_CDP`, no observación nativa. Todo lo que
exige pantalla del sistema queda BLOCKED por variante, nunca PASS.

Restricciones que se respetaron: no se tocó producto ni tests, no se construyó ningún instalador, no se
abrieron datos reales, no se publicaron binarios, no se ejecutaron Actions, no se alteró la red ni
servicios compartidos, no se leyeron credenciales ajenas, no se usaron proveedores de pago ni se
descargaron modelos.

## 2. Candidato probado (identidad exacta)

| Elemento | Valor |
|---|---|
| Tipo | **Checkout ejecutado como runtime web local**. NO es el Setup instalado ni un portable |
| Rama | `fix/react-functional-continuation-20261007` |
| HEAD | `0f3ff15292f84a7d6877f9f2d6e47a3f646355f4` |
| Árbol HEAD | `4faf9638a5c558991a60a91b489cda6943a52e4f` |
| Base de producto | `642966a93e7e9c9f9c5e93cce0bc842f538846fb`, árbol `e0a3966bddc8bbd4cfc2ab4041668c3162ce86f7` |
| Diferencia vs. base | Solo documental: `AUTO_TEST.md`, `MANUAL_TEST1.md`, `MANUAL_TEST2.md`, `MANUAL_TEST_HANDOFF.md` |
| Frontend | `src/frontend` compilado en la sesión 1 con `npm ci --ignore-scripts` + `npm run build` (26 assets, 29 licencias) |
| Launcher | `src/starter_headless.py` (ciclo de vida real: puerto libre, espera de prontitud, parada del hijo propio) |
| URL | `http://127.0.0.1:8000` |
| Base de datos | Sintética y desechable, creada de cero: `C:\Users\dhays\AppData\Local\Temp\opencode\slm-auto-2026-10-08-001\slm_educator.db` |
| Configuración | Copia de `env.properties` en ese mismo directorio aislado |
| Entorno | Windows 10.0.26200.9550 · Python 3.14.7 (`venv`) · Node 24.21.0 (solo build) · Chrome vía DevTools · viewport 1440×900 · Español · tema Sistema |

**No probado y no trasladable:** Setup instalado, portable `dist/SLMEducator_acceptance*`, Setup
histórico `SLMEducator-Setup-2.0.0-fe954cab4655.exe` (31.456.307 bytes, no contiene esta GUI, **no
abrir**). Los cinco PASS humanos del tramo A y el 422 histórico de ese binario **no** cuentan para este
candidato.

**No copiar a este informe:** las cifras históricas de 825 pruebas DOM, 249 Python y 8 diagnósticos G1–G5.

## 3. Cuentas sintéticas (creadas en esta campaña, base desechable)

| ID | Usuario | Rol | Nombre | Contraseña sintética | Creación |
|---|---|---|---|---|---|
| 1 | `admin` | Administrador | Administrator | `AutoTest2026Disposable` | bootstrap `scripts/seed_admin.py` sobre base **nueva** |
| 2 | `docente_auto08` | Docente (T1) | Docente Demo | `Fracciones#2026Aa` | GUI, admin |
| 3 | `alba_auto08` | Estudiante (S1) | Alba Demo | `Fracciones#2026Aa` | GUI, admin; matrícula T1 |
| 4 | `bruno_auto08` | Estudiante (S2) | Bruno Demo | `Fracciones#2026Aa` | GUI, docente T1 |

Son credenciales **sintéticas y desechables**, elegidas así a propósito para que ninguna contraseña
real viaje por el chat, los informes o Git. No las apliques a ninguna instalación real.

**T2 «Docente Contraste» NO existe todavía**: hay que crearlo como admin para `AUTO-PEO-04`.

### Datos creados

- Materiales: 1 `L1 Partes iguales` · 2 `PR1 Denominador` (opción múltiple, clave 1, explicación) ·
  3 `PR2 Comparación` (respuesta corta) · 4 `L2 Comparar fracciones` · 5 `L3 Comprobar la unidad`
- Cursos: **1** duplicado accidental de la campaña (borrador) · **2** `Fracciones cotidianas | auto08`
  publicado V1 y asignado solo a S1 · **3** `… (revision)` en borrador
- Evaluación **1** `Evaluación de fracciones | auto08`: publicada, 2 intentos, sin límite de tiempo,
  aprobado 60 %, 10 puntos, rúbrica de 3 criterios (Numerador 2 · Denominador 2 · Partes iguales 1),
  política de ayuda **desactivada**. Envío **1** de S1 con calificación final **9/10**
- Solicitud de ayuda **1** `Misma unidad` de S1, resuelta por T1
- 2 mensajes sintéticos entre T1 y S1

## 4. Estado del runtime ahora mismo

| Recurso | Cómo comprobarlo | Cómo pararlo |
|---|---|---|
| Servidor web `127.0.0.1:8000` | `Get-NetTCPConnection -State Listen -LocalPort 8000` | **Solo por PID verificado**, nunca por nombre de proceso |
| Base sintética | El fichero anterior en el temporal | No borrar mientras el servidor la use |
| Pestaña del navegador | `chrome-devtools` `list_pages` | — |

**Advertencia real observada:** al detener el launcher, el proceso servidor (nieto) **sobrevivió al
padre** y dejó el puerto ocupado. Hay que detener el árbol completo identificado por `ParentProcessId`.
Nunca matar por nombre.

## 5. Cómo arrancar el runtime (si está caído)

```powershell
$run="C:\Users\dhays\AppData\Local\Temp\opencode\slm-auto-2026-10-08-001"
$env:SLM_DB_PATH="$run\slm_educator.db"
Set-Location $run
& "C:\Users\dhays\Github\SLMEducator\venv\Scripts\python.exe" `
  "C:\Users\dhays\Github\SLMEducator\src\starter_headless.py"
```

`starter_headless.py` usa el puerto fijo 8000; si estuviera ocupado, se bloquea AUTO-BOOT-05 en lugar de
matar al ocupante. El arranque escribe `api.log` y `logs/slm_educator.log` en el directorio aislado.

## 6. Cobertura y resultados heredados

Detalle campo a campo: `COVERAGE.csv` (117 filas). Resumen **final (sesión 10, campaña terminada)**:

| Estado | Filas |
|---|---|
| PASS | 45 |
| PARTIAL | 41 |
| FAIL | 4 |
| BLOCKED | 26 |
| NOT_APPLICABLE | 1 |
| **NOT_RUN** | **0** |

Un denominador de PASS del 27 % **no significa** que el producto funcione en un 26 %: refleja una
campaña detenida a mitad, no una medida de calidad.

### Qué se confirmó correcto (resumen operativo)

Permisos por rol · alta y matrícula con confirmación y foco en «Cancelar» · filtros y búsqueda que
sobreviven a la navegación · ciclo borrador→revisado→publicado→asignado con orden persistido ·
revisión independiente · autoría de material y evaluación con validaciones por campo · sesión de
estudio con notas en servidor · práctica sin revelar clave · entrega única con doble clic · corrección
9/10 coherente con el feedback de la alumna · ayuda con respuesta y resolución separadas · mensajes con
ID de destinatario · aislamiento de S2 en 5 recursos · conexión real a LM Studio y catálogo de modelos ·
idioma y tema por cuenta.

### Regresión histórica cerrada

`H-D3` (alta de docente con correo inválido, antes `422` ilegible): **corregido**. Ahora muestra
«Correo electrónico: Introduce un correo válido, como nombre@ejemplo.com.», conserva el valor y mueve
el foco al campo. Sin `[object Object]` ni JSON crudo.

## 7. Defectos abiertos (detalle en `DEFECTS.md`)

| ID | Sev | Resumen | Efecto |
|---|---|---|---|
| `SLM-AUTO-004` | **S2** | `/tutor` no se sirve (404 con JSON crudo en pantalla). El contrato del frontend la declara válida; `SPA_PATH` de `src/frontend_delivery.py` no la incluye | TUT-01..03 y QA-01..03 inaccesibles para los tres roles |
| `SLM-AUTO-005` | **S2** | Generar con IA → `POST /api/generate/lesson` **500** tras `HTTP 200` del proveedor (4929 bytes). 2/2, sin traza en el log | La generación con IA es inservible e indiagnosticable |
| `SLM-AUTO-001` | S3 | Buscador de «Personas» pierde caracteres con escritura rápida (`Demo`→`Deo`, `q=eo`, 0 resultados); con entrada lenta funciona | Filtrado degradado |
| `SLM-AUTO-003` | S3 | Claves de opción duplicadas: rechazo solo con el resumen genérico, sin campo señalado ni `invalid` | El docente no sabe qué corregir |
| `SLM-AUTO-008` | S3 | La rúbrica definida en la evaluación no es aplicable al calificar (solo puntuación y comentario) | Calificar con rúbrica imposible desde la GUI |
| `SLM-AUTO-002` | S4 | Biblioteca sin materiales = texto y botón de «sin resultados por filtro»; «Quitar filtros» no cambia nada | Orientación |
| `SLM-AUTO-006` | S4 | Cursos homónimos indistinguibles en lista y selector (sin ID ni estado) | Riesgo de elegir el curso equivocado |
| `SLM-AUTO-007` | S4 | La lección se muestra al alumno con seis encabezados de sección vacíos | Ruido visual |
| `SLM-AUTO-009` | S4 | Al reabrir el editor de evaluación desaparecen «ID del curso» y «ID del material» | El docente no puede verificar el vínculo (el vínculo **sí funciona**: confirmado en la sesión 2) |
| `SLM-AUTO-010` | S4 | Comentarios de estado generados por el servidor **en inglés** y sin declaración: intento vencido y cierre sin envío. `assessment.py` 1390/1393 | Patrón **sistémico**; el mensaje de sistema ocupa el campo del docente |
| `SLM-AUTO-011` | S4 | Tras el traspaso de matrícula, el docente saliente pierde el acceso a la ficha del estudiante, incluido su campo de notas privadas | Pérdida de acceso comprobada; pérdida de datos **no** afirmada |

### Estado de la matrícula (importante para continuar)

S1 (`alba_auto08`) está **matriculada con T2** (`contraste_auto08`) desde la sesión 3. Para repetir
`AUTO-PEO-04` correctamente hay que devolverla a T1 desde admin. Detalle en la sección de sesión 3.

Evidencia técnica del 500: `evidence/ai_generation_failure.log` (extracto saneado de `api.log`).

## 8. Cómo actualizar la cobertura

**No edites `COVERAGE.csv` a mano.** Copia el patrón del script ya existente y cambia el diccionario
`U` con las filas que ejecutes:

- Plantilla: `C:\Users\dhays\AppData\Local\Temp\opencode\slm-auto-2026-10-08-001\cov_rewrite.py`
- Ejecuta: `venv\Scripts\python.exe <script>` con `python -c` primero para comprobar que el `case_id`
  existe.

El script **aborta sin escribir** si la lectura devuelve menos de 100 filas o si algún `case_id` no
existe, para no destruir la cobertura. Conserva esa propiedad.

Avisos aprendidos en la sesión 1, no los repitas:

- El CSV se escribe con **BOM UTF-8**: lee con `encoding="utf-8-sig"` o el primer `case_id` sale con BOM.
- El `case_id` real de idioma/tema es `AUTO-VIS-02.idiomas_temas` (con **s**). Escribirlo mal aborta la
  escritura; no es un fallo del sistema de archivos.
- PowerShell 5.1 no tiene `RandomNumberGenerator.Fill`; para aleatoriedad usa el `secrets` de Python.
- No uses `Set-Content`/`Add-Content` de PowerShell para escribir acentos en estos ficheros: aplica doble
  codificación. Escribe con `write`, con python, o con `-Encoding utf8` sin volver a leer con `-Raw`.

## 9. Pendiente, en el orden recomendado

1. **`AUTO-EVA-04`** — evaluación con límite de tiempo (5 min): reloj, navegación, recarga, reanudación,
   vencimiento, respuesta local, resultado incierto. Distinguir límite agotado de fallo de red.
2. **`AUTO-EVA-05`** — cerrar intento sin enviar con confirmación, agotar los 2 intentos, historial.
3. **`AUTO-PROG-01/02`** — «Mi progreso» de S1: pestañas, resumen, repasos, objetivo diario, XP, rachas.
4. **`AUTO-PEO-04`** — crear **T2** como admin y traspasar S1 de T1 a T2 con confirmación; comprobar que
   T1 conserva autoría y T2 no hereda notas privadas.
5. **`AUTO-PEO-05`** — desactivar/reactivar una cuenta sintética prescindible (último admin y
   auto-desactivación solo con fixture aislada).
6. **`AUTO-SRC-01/02`** — crear TXT/MD/PDF sintéticos fuera de datos reales, cargar por selector nativo,
   y probar vacío / tipo no admitido / límite de 10 MiB.
7. **`AUTO-PORT-02/03`** — paquete docente JSON + importación con preview; copia de seguridad de admin.
8. **`AUTO-REG-01/03/05/06/07`** — persistencia tras reinicio, reautenticación, tres indisponibilidades,
   errores y rutas.
9. **`AUTO-VIS-01/03/05/07`** — revisión visual por rol, recorrido solo teclado, movimiento reducido,
   launcher y escala.
10. Restos: `AUTO-CRS-06`, `AUTO-LEARN-03` (PR2, cancelar, recarga), `AUTO-LEARN-04`,
    `AUTO-HELP-02` (respuesta vacía/duplicada, reapertura), `AUTO-GEN-04`, `AUTO-MSG-02`,
    `AUTO-SET-01`, `AUTO-AUTH-02`.

### Bloqueos que no desaparecen por seguir probando

| Bloqueo | Por qué | Acción mínima |
|---|---|---|
| `BLK-GUI-NATIVE` | No hay control de escritorio | AUTO-BOOT-01..05, LIFE-01, VIS-04/06/07 quedan BLOCKED. David opera el launcher y el Setup, o se habilita una VM |
| `BLK-INSTALLER` | No hay Setup vigente construido ni instalado | Ejecutar `MANUAL_TEST1`; no abrir el `fe954cab4655` |
| `BLK-TUTOR-ROUTE` | `SLM-AUTO-004` | Corregir `SPA_PATH` y **reconstruir**: es cambio de producto y abre candidato y campaña nuevos |
| `BLK-AI-GENERATION` | `SLM-AUTO-005` | Registrar la excepción del 500 y revisar el formato de la respuesta del modelo |
| `BLK-DOWNLOADS-DIR` | La copia exportada queda fuera del directorio de trabajo y David pidió no acceder fuera del repo | Autorizar ese directorio o revisarla él; `AUTO-PORT-04` queda BLOCKED |
| `BLK-SCALE-G7` | No hay fixtures de 1/50/500 ni curso de 100 lecciones | `AUTO-SCALE-01` queda NOT_RUN; no prometas rendimiento no medido |

## 10. Proveedor de IA (autorizado por David)

| Elemento | Valor |
|---|---|
| Proveedor por defecto | `lm_studio` · `http://localhost:1234` |
| Modelo | `slm-production-evaluation` (VLM, Q4_K_XL, `state=loaded`) |
| Descubrimiento | Listado del propio runtime local; no se adivinó nombre ni puerto |
| Conexión probada | OK, 16 951 ms, con el descargo de que no verifica la calidad del modelo |
| Catálogo | 4 nombres de modelos |
| Configurado por | Cuenta `docente_auto08` (AUTO-AI-01) **y** `env.properties` por orden de David |

`env.properties` (ignorado por Git) apunta ahora a `lm_studio` con un comentario que identifica destino
y modelo. **`env.properties.example`, que sí está versionado, sigue apuntando a `ollama`/`gpt-oss`**:
no se cambió porque es producto; decide David.

Las cuentas `admin`, `alba_auto08` y `bruno_auto08` **no** configuraron proveedor. Toda prueba de IA
debe declarar qué cuenta la hizo.

## 11. Informe de la sesión siguiente

> **Rellena esta sección al terminar tu sesión y añade aquí el informe completo.** Mantén el formato:
> candidato, entorno, qué se ejecutó, resultados por caso, defectos nuevos, bloqueos, siguiente paso.
> Si la sección crece mucho, añade un `HANDOFF-2.md` y enlázalo aquí; no borres esta.

### Sesión 2 — 2026-10-08, mismo runtime y mismo candidato

**Entorno**: candidato `0f3ff15` sin cambios, runtime `127.0.0.1:8000` vivo, misma base sintética,
viewport 1440×900, Español, tema Sistema. No se reconstruyó nada ni se tocó producto.

**Objetivo de la sesión**: cerrar `AUTO-EVA-04`, `AUTO-PROG-01/02` y resolver la duda abierta del
vínculo curso↔evaluación.

**Casos ejecutados**

| Caso | Resultado | Evidencia observada |
|---|---|---|
| `AUTO-EVA-04.temporizada` | **PASS** | Reloj `01:00` en vivo, vencimiento con mensaje «El tiempo ha terminado. Envía las respuestas para revisión docente; se conservarán», formulario sigue utilizable, recarga mantiene el plazo del servidor en el mismo intento `/intentos/2`, envío vencido aceptado y calificado 10/10 |
| `AUTO-PROG-01.pestanas` | **PASS** | Las 5 pestañas abren y separan sesiones, duraciones desconocidas, autoevaluación y dominio evaluado; actividad reciente muestra `Scored 9/10 (90%)`; XP 100 con descargo |
| `AUTO-PROG-02.objetivo_xp` | **PASS** | Negativo `0` → «El valor debe ser superior o igual a 1»; objetivo `2 lecciones` guardado y persistente tras recarga |
| `AUTO-EVA-05.cierre_historial` | PARTIAL | El límite se decrementa al reservar y el historial muestra estados; falta cerrar sin enviar y agotar intentos |
| `AUTO-SET-01.apariencia_idioma_tz` | PARTIAL | Mi progreso expone «Zona horaria actual: UTC» y la procedencia del día; falta la página de zona horaria |
| `AUTO-EVA-01.crear` | PASS (enlazada desde la sesión 1) | **Duda resuelta**: el vínculo por `ID del curso` **sí funciona** |

**Hallazgo que resuelve una duda anterior**: una evaluación creada con `ID del curso = 2` aparece en la
lista de la alumna; otra creada sin ese vínculo **no** le aparece. Por tanto `SLM-AUTO-009` queda
acotado: el vínculo funciona, lo que falta es poder **verlo y editarlo** al reabrir el editor.

**Defecto nuevo**: `SLM-AUTO-010` (S4) — el comentario de intento vencido se muestra en inglés
(`Time limit exceeded. Answers preserved for teacher review.`) bajo «Comentarios», sin la declaración
que la aplicación sí ofrece para las descripciones de «Actividad reciente». Verificado en el código:
`src/api/routes/assessment.py` líneas 1390 y 1393.

**Defectos de la sesión 1**: ninguno reproducido ni cerrado en esta sesión; `SLM-AUTO-004` y
`SLM-AUTO-005` siguen abiertos y siguen bloqueando TUT/QA y la generación.

**Cobertura tras la sesión 2**: 117 filas · **PASS 29** · PARTIAL 11 · FAIL 2 · BLOCKED 9 ·
NOT_APPLICABLE 1 · **NOT_RUN 66**.

**Restaurado / no restaurado**: no se cambiaron preferencias en esta sesión (ni idioma, ni tema, ni
objetivo diario existente más allá del Synthetic propio). Se creó un objetivo diario de 2 lecciones en
la cuenta S1: es dato sintético de campaña, se conserva.

**Datos nuevos creados en la sesión 2**

- Evaluación **3** `Evaluación cronometrada | auto08`: publicada, 1 minuto, 2 intentos, 60 %, vinculada
  al curso 2, 1 pregunta (10 puntos)
- Envío **2** de S1: vencido, aceptado, 10/10, con el comentario en inglés de `SLM-AUTO-010`
- Objetivo diario de S1: 2 lecciones

**Nota sobre assessments numeración**: existe además la evaluación **2** `Evaluación cronometrada
| auto08` sin vínculo de curso, invisible para la alumna y abandonada. No la borres: documenta que sin
vínculo la alumna no la ve, y no hace falta volver a probarlo.

**Siguiente paso concreto**: `AUTO-EVA-05` (cerrar intento sin enviar con confirmación y agotar los 2
intentos) y después `AUTO-PEO-04`, que exige crear **T2** como admin y traspasar S1 de T1 a T2.

---

### Sesión 3 — 2026-10-08, mismo runtime y mismo candidato

**Entorno**: candidato `0f3ff15` sin cambios, runtime `127.0.0.1:8000` vivo, misma base sintética.
No se reconstruyó nada, no se tocó producto, no se cambiaron preferencias.

**Objetivo de la sesión**: `AUTO-EVA-05` y `AUTO-PEO-04`, los dos pasos que la sesión 2 dejó fijados.

**Casos ejecutados**

| Caso | Resultado | Evidencia observada |
|---|---|---|
| `AUTO-EVA-05.cierre_historial` | **PASS** | Diálogo con foco en «Cancelar» y aviso «consume el intento reservado… No podrás reanudarlo»; cancelar conserva el intento; al confirmar: «Intento cerrado / Cerrado sin envío / Enviado: —», respuesta `B` conservada y **«Sin calificar»**; la previa pasa a «2 de 2 intentos reservados» con «Has usado todos los intentos disponibles.» y sin botón de comenzar; historial con los envíos 3 (cerrado, sin fecha) y 2 (con fecha) |
| `AUTO-PEO-04.traspaso` | **PARTIAL** | T2 creada (ID 5). Traspaso con confirmación. **Positivo**: T1 conserva la autoría (sigue viendo los envíos de Alba) y baja a 1 alumno; T2 ve 1 alumno y cola vacía; T2 ve el progreso compartido y su campo de notas vacío. **Limitación**: la no transferencia de notas privadas no se demuestra empíricamente (ver `SLM-AUTO-011`) |

**Defecto nuevo**: `SLM-AUTO-011` (S4) — tras el traspaso, el docente saliente **pierde el acceso a la
ficha del estudiante** («No tienes acceso o el recurso ya no está disponible»), incluido su propio campo
de notas privadas. Efecto comprobado: pérdida de acceso. **No** se afirma pérdida de datos: esta campaña
nunca escribió notas privadas antes de un traspaso.

**Ampliación**: `SLM-AUTO-010` queda reforzado con una segunda ocurrencia del mismo patrón —
`Attempt explicitly closed without submission or grade. The reserved attempt remains consumed.` al cerrar
sin enviar. El patrón de mensajes del servidor en inglés sin declaración es **sistémico**, no aislado.

**Defectos de sesiones anteriores**: ninguno cerrado. `SLM-AUTO-004` y `SLM-AUTO-005` siguen abiertos y
siguen bloqueando TUT/QA y la generación.

**Cobertura tras la sesión 3**: 117 filas · **PASS 30** · PARTIAL 11 · FAIL 2 · BLOCKED 9 ·
NOT_APPLICABLE 1 · **NOT_RUN 65**.

**Datos nuevos creados en la sesión 3**

- Cuenta **5** `contraste_auto08` — Docente Contraste (T2), creada como admin
- Envío **3** de S1: cerrado sin envío, respuesta conservada sin calificar
- Matrícula de S1 traspasada de T1 a T2

**Estado que hereda la sesión 4**: S1 está matriculada con **T2**, no con T1. Si necesitas repetir
`AUTO-PEO-04` con la nota privada previa (la forma correcta de cerrarlo), vuelve a matricular S1 con T1
desde admin (`/personas/3`), escribe la nota como T1 y repite el traspaso.

**Siguiente paso concreto**: `AUTO-CRS-06` (buscar curso → detalle → «Todos los cursos», con filtro,
selección y scroll) y `AUTO-LEARN-03` pendiente (PR2 como alumno, cancelar y recarga). Si queda contexto,
`AUTO-SRC-01/02`, que es el bloque más grueso sin ejecutar.

---

### Sesión 4 — 2026-10-08, mismo runtime y mismo candidato

**Entorno**: candidato `0f3ff15` sin cambios, runtime `127.0.0.1:8000` vivo, misma base sintética.
Sin cambios en producto, sin cambios de preferencias.

**Casos ejecutados**

| Caso | Resultado | Evidencia observada |
|---|---|---|
| `AUTO-REG-07.navegacion_rutas` | **PASS** | Atrás/adelante conservan el criterio (`/cursos/3?q=Fracciones` ↔ `/cursos?q=Fracciones#course-3`); deep-link inexistente (`/cursos/999999`) → «No tienes acceso o el recurso ya no está disponible.»; un alumno que aterriza en ruta administrativa recibe «Este recurso no está disponible» |
| `AUTO-CRS-06.buscar_detalle_volver` | PARTIAL | Búsqueda «Fracciones» con pulsaciones reales → 3 coincidencias correctas, criterio conservado en la URL y tras «Todos los cursos». **Scroll real no verificable** con solo 3 cursos: no se declara cumplido |
| `AUTO-PEO-05.desactivar` | PARTIAL | Cuenta desechable `temporal_auto08` (ID 6): desactivar con confirmación y foco en «Cancelar», aviso de que el historial se conserva; **acceso real verificado** (login → «El usuario o la contraseña no son correctos»); reactivar con confirmación y aviso de que **se revocan las sesiones existentes**; tras reactivar el acceso funciona («Hola, Temporal») |

**Defectos nuevos**: ninguno. Ninguno de los defectos abiertos se reproduce ni se cierra en esta sesión.

**Variante bloqueada explícitamente**: auto-desactivación y desactivación del último administrador **no
se probaron** para no dejar la base sintética sin acceso administrativo. Es una decisión de seguridad de
esta campaña, no un bloqueo del producto; queda anotada en `COVERAGE.csv` con su motivo.

**Dato nuevo creado en la sesión 4**

- Cuenta **6** `temporal_auto08` — Temporal Demo, estudiante, **dejada reactivada** y funcional. Existe
  solo para esta variante; no interviene en ningún otro caso.

**Cobertura tras la sesión 4**: 117 filas · **PASS 31** · PARTIAL 13 · FAIL 2 · BLOCKED 9 ·
NOT_APPLICABLE 1 · **NOT_RUN 62**.

**Bloque más grueso que sigue sin ejecutar**: `AUTO-SRC-01/02` (fuentes del curso), que requiere crear
ficheros sintéticos TXT/MD/PDF y probar vacío, tipo no admitido y el límite de 10 MiB. Después,
`AUTO-PORT-02/03`, `AUTO-AUTH-02`, `AUTO-LEARN-04` y la pasada III de persistencia.

---

### Sesión 5 — 2026-10-08: fuentes del curso (AUTO-SRC-01/02)

**Ejecutado**: fixtures sintéticas en `temp/auto_fixtures_auto08/` (TXT 429 B, MD 459 B, PDF 881 B
mínimo válido, vacío 0 B, `.bin` 28 B, 11 MB). TXT por selector nativo → propuesta con nombre, hash
SHA-256, analizador `utf8-text-v1`, `section:1`, «Extracción completa declarada», 441 caracteres.
«Usar texto extraído» con diálogo y foco en «Cancelar»; cancelar conserva el formulario; adoptar
rellena el nombre del archivo; guardar con confirmación → «Guardado en el servidor»; persiste tras
recarga. MD: 471 caracteres. PDF: 256 caracteres con `pypdf` y `page:1` (con un «Cargando…» intermedio).

**Defecto nuevo**: `SLM-AUTO-012` (S3) — los tres rechazos (vacío, tipo, 11 MB) devuelven solo el resumen
genérico, idénticos e indistinguibles; lo guardado no se reemplaza.

**Cobertura**: SRC-01 PASS, SRC-02 PARTIAL.

---

### Sesión 6 — 2026-10-08: LEARN-03 (resto), PORT-02/03, AUTH-02

**Ejecutado**: PR2 con borrador escrito y recarga → aviso de borrador con «Restaurar/Descartar»;
restaurar recupera el texto exacto (LEARN-03 → PASS). Paquete docente JSON con preview (5 elementos,
2 evaluaciones, 3 preguntas) y descarga con confirmación; JSON malformado y vacío no crean borrador
(PORT-02 PARTIAL: la importación válida queda pendiente por restricción de directorio). Copia de
seguridad de admin con preview, huella de clave y guía de restauración; docente denegado en
`/administracion/copias` (PORT-03 PARTIAL: descarga/restauración no ejecutadas). Perfil: cambio
guardado y persistente, restaurado después; salir sin guardar no muestra diálogo pero tampoco guarda
(AUTH-02.perfil PASS). Rotación de contraseña sintética con aviso de revocación, rechazo de actual
incorrecta y reentrada verificada (AUTH-02.password PASS).

**Aviso importante**: la clave de T1 cambió a `NuevaSintetica#2026Bb`. Quien continúe debe usar esa.

---

### Sesión 7 — 2026-10-08: SET-01 (resto), VIS-05, VIS-03

**Ejecutado**: zona horaria UTC inicial; `Zona/NoExiste` rechazada con error por campo
(SET-01 → PASS); `Europe/Madrid` guardada y restaurada a UTC. Animaciones desactivadas y guardadas,
con captura, restauradas después (VIS-05 PARTIAL: sin observación de movimiento real). Teclado: 3×Tab
con foco visible, Enter activa el enlace, skip-link primero en todas las pantallas (VIS-03 PARTIAL).

---

### Sesión 8 — 2026-10-08: REG-01, REG-03, REG-05

**Ejecutado**: servidor propio detenido por PID verificado y rearrancado dos veces. La sesión sobrevive
al reinicio sin reentrar; persisten curso publicado, correcciones, cuentas, matrícula, mensajes y
preferencias (REG-01 PASS). Servidor detenido con navegador abierto → `ERR_CONNECTION_REFUSED` del
navegador; tras rearrancar, recuperación explícita sin reentrar (REG-05 PARTIAL, REG-03 PARTIAL).

---

### Sesión 9 — 2026-10-08: LEARN-04, MSG-02, VIS-01, REG-02, REG-06, GEN-04

**Ejecutado**: paneles auxiliares excluyentes con retorno a lectura (LEARN-04 PARTIAL: sin texto largo
que probar). Selección, «Marcar como leído» y «Archivar» con confirmación; archivado reversible con
«Sacar del archivo» (MSG-02 PARTIAL: masiva y borrado no). Menús de los tres roles sin solapamientos
(VIS-01 PARTIAL). REG-02 PARTIAL (mapa G1–G5 con estado por variante). REG-06 PARTIAL (422/403/incierto/
cierre/vencimiento sí; 409/5xx no). GEN-04 BLOCKED por SLM-AUTO-005.

**Defecto nuevo**: `SLM-AUTO-013` (S4) — la lección creada en línea muestra el encabezado `Lesson` en
inglés dentro de la interfaz en español.

---

### Sesión 10 — 2026-10-08: cierre de cobertura (10 BLOCKED de entorno + 36 PLAN)

**Ejecutado sin GUI**: 10 filas que exigen ventana nativa, Setup, lector, zoom nativo, fixtures de
escala o red fuera de autorización → BLOCKED con motivo específico cada una (BOOT-01..05, LIFE-01,
VIS-04, VIS-06, VIS-07, SCALE-01/G7, SW-01, SW-02). 36 filas PLAN-* derivadas de los resultados AUTO
(23 escenarios + H-D1..3 + G1..G7): 8 PASS, 2 FAIL (D3, A4 — derivan de GEN-01/AI-03), resto PARTIAL/
BLOCKED/N_A con su mapa. G6 → NOT_APPLICABLE (deuda de código, no GUI).

**Cobertura final**: 117 filas · **PASS 45** · PARTIAL 41 · FAIL 4 · BLOCKED 26 · NOT_APPLICABLE 1 ·
**NOT_RUN 0**. Criterio de terminado del §15 alcanzado: todo caso/variante tiene evidencia actual o
motivo específico; no quedan acciones independientes útiles permitidas en este entorno.

**Defectos finales**: 13 (`SLM-AUTO-001` … `SLM-AUTO-013`). Ninguno cerrado en campaña; H-D3 cerrada
como regresión histórica.

---

## 12. Lo que este paquete NO afirma

No se afirma «100 % funcional», «sin bugs», «seguro», «accesible», «Windows certificado», «cobertura
completa» ni «todos los proveedores compatibles». La revisión visual es superficial (menús por rol,
idioma, tema, aislamiento). No se midió rendimiento a escala, ni se probó lector de pantalla, zoom
nativo, hardware, acústica, service worker, migración ni instalador. La calidad educativa, la adecuación
para menores y el cumplimiento normativo no se certifican aquí.
