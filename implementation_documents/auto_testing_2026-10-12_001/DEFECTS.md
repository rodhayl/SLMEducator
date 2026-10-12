# DEFECTS · Campaña auto-2026-10-12-001 (noche autónoma)

Registro único de defectos de ESTA ejecución. No renumera ni sobrescribe
`auto-2026-10-09-002/DEFECTS.md` ni sus IDs `SLM-AUTO-001..015`.

Severidad: S1 pérdida/exposición grave o arranque esencial bloqueado · S2 flujo
esencial roto · S3 función degradada · S4 presentación menor.

Clases: **producto** (aplicación) · **arnés** (código de prueba/campaña) ·
**entorno** (máquina, proveedor, red). No se atribuye causa sin evidencia.

---

## SLM-AUTO-016 · El objetivo diario usa una base de fechas distinta al día local del usuario

- **Estado**: REPARADO EN TESTS 2026-10-12 (decisión del propietario: Madrid).
  El default UTC documentado del producto NO se toca (contrato explícito con
  ~15 fijaciones en tests/frontend/docs; cambiarlo sería refactorización,
  no corrección mínima).
- **Clase**: arnés/tests (el producto cumplía su contrato; los tests no
  fijaban la precondición de zona que el contrato exige)
- **Severidad original**: S3
- **Fecha/run**: 2026-10-12 · `auto-2026-10-12-001` (continuación 002)
- **Reparación**: `tests/integration/test_daily_goal_regression.py` y
  `tests/integration/test_trustworthy_scoring_sessions.py` fijan ahora
  `settings.timezone = Europe/Madrid` y calculan el día esperado desde el
  instante UTC con `ZoneInfo` (nada de `date.today()` del host). Nueva
  regresión `test_daily_goal_follows_madrid_across_utc_midnight` (instante
  congelado 23:30Z → meta del 12-10) en verde. Suites temporal+objetivo+
  scoring: 89 PASS.
- **Uso real**: verificado por GUI que fijar Europe/Madrid en
  `/ajustes/zona-horaria` cambia los sellos a `(Europe/Madrid)`.
- Informe original conservado arriba sin reescritura.
- **Clase**: producto (candidato 29df5ed / checkout dfbc15a)
- **Severidad**: S3 — el progreso del objetivo diario se cuenta en el día
  equivocado cerca de medianoche para husos no alineados con la base del
  servidor; no hay pérdida de datos, pero la meta y su contador quedan
  incorrectos hasta el día siguiente.
- **Fecha/run**: 2026-10-12 · `auto-2026-10-12-001`
- **Candidato**: rama `fix/react-functional-continuation-20261007`, HEAD
  `dfbc15a18ec7362bf832bf0cd6e564d89710f5c0` (producto `29df5ed`), fixture
  sintético `%TEMP%\opencode\slm-auto-2026-10-12-001-r2`
- **Entorno**: Windows 10/11 (10.0.26200), Python 3.14.7, local UTC+2
- **Rol**: n/a (suite de integración)
- **Casos relacionados**: `tests/integration/test_daily_goal_regression.py::test_daily_goal_full_flow`,
  `tests/integration/test_trustworthy_scoring_sessions.py::test_session_start_end_restore_and_rewards_are_idempotent`

### Hecho observado (literal)

Suite completa ejecutada de noche, cruzando la medianoche local:

```
E       AssertionError: assert '2026-10-11' == '2026-10-12'
tests\integration\test_daily_goal_regression.py:69: AssertionError
```

y

```
>       assert goal.current_value == 1
E       AssertionError: assert 0 == 1
tests\integration\test_trustworthy_scoring_sessions.py:268: AssertionError
```

En ambos casos el test corrió con fecha local `2026-10-12` mientras el
registro guardado por la aplicación llevaba fecha `2026-10-11`. Los DOS tests
**PASAN ejecutados aislados** (mismo día local y de servidor):
`2 passed, 1 warning in 4.30s`.

### Causa y evidencia

- Hecho: la fecha que la aplicación usa para "hoy" no coincide con el día local
  del usuario cuando el reloj local está en la tarde/noche de un huso
  desplazado respecto a la base que usa el servidor.
- Evidencia correlacionada: hora local del fallo 01:27 (= 23:27 UTC del día
  anterior); `goal_date` persistido `2026-10-11`; `date.today()` del test
  `2026-10-12`.
- NO verificado esta noche: qué base usa exactamente el servidor (UTC vs hora
  local del proceso) ni si la zona horaria de la cuenta (`/ajustes/zona-horaria`)
  interviene. Se requiere investigación acotada antes de cualquier corrección.
- Hipótesis (no comprobada): el servicio de gamificación usa la fecha del
  servidor en lugar de la zona horaria configurada por el usuario.

### Frecuencia y efecto

- Frecuencia: 100% en la ventana nocturna para usuarios con desfase de huso;
  0% ejecutando de día con la misma base.
- Efecto: la meta diaria no rota a medianoche local; el contador de progreso
  queda en 0 hasta que cambia el día de la base del servidor.

### Alternativa temporal segura

- Ninguna del lado de prueba. No modificar el reloj del sistema.

---

## SLM-AUTO-017 · tests/trust/test_pytest_database_isolation.py falla al limpiar temporales en Windows

- **Estado**: OPEN
- **Clase**: arnés (código de prueba)
- **Severidad**: S4 — no afecta al producto; rompe la puerta "todo verde" en la
  suite completa de Windows.
- **Fecha/run**: 2026-10-12 · `auto-2026-10-12-001`
- **Candidato**: checkout `dfbc15a`
- **Entorno**: Windows 10/11, Python 3.14.7

### Hecho observado (literal)

```
PermissionError: [WinError 32] El proceso no tiene acceso al archivo porque está
siendo utilizado por otro proceso:
'C:\Users\dhays\AppData\Local\Temp\slm-pytest-collection-*\logs\errors.log'
```

Las dos parametrizaciones (`collect_only` True/False) fallan **después** de que
las pruebas del subproceso pasen (`2 passed`); el fallo está en el `rmtree` del
directorio temporal de colección al salir del pytest anidado.

### Causa y evidencia

- Hecho: el manejador de logging del subproceso sigue abierto cuando
  `tempfile` intenta borrar el directorio en Windows.
- Evidencia: traza completa en `evidence/pytest_full.log`; el fallo ocurre en
  `_ensure_unconfigure` → `cleanup` → `onexc`.
- NO verificado: si el mismo fallo ocurre en el gate de lotes afectados (la
  campaña 002 no ejecutó la suite completa).

### Alternativa temporal segura

- Ejecutar la suite por lotes (como la campaña 002) hasta que el cierre del
  handler de logging se arregle en el test.

---

## SLM-AUTO-018 · Con el modelo local actual (sustituto, razonador) el tutor contextual y 11 pruebas AI e2e no pueden completarse

- **Estado**: PARCIALMENTE RESUELTO 2026-10-12 (decisión del propietario: subir
  el tope del tutor). `TUTOR_MAX_OUTPUT_TOKENS` 1200 → 4000
  (`src/core/services/ai_service.py:93`) + 3 fijaciones de test actualizadas
  (lifecycle, transport, boundaries). Regresión 180 PASS. Verificación extremo
  a extremo: tutor contextual con fuente responde 200 con
  `max_output_tokens=4000`, `tokens_used=1775` y respuesta útil en 81.5 s.
- **Resto pendiente (modelo sustituto, no producto)**: suite r2 deja 3 fallos
  de esta clase — `grade_answer` usa presupuesto propio fijo de 1000
  (NO modificado: decisión de consistencia de calificación, pendiente del
  propietario), y dos e2e reciben JSON con caracteres de control del modelo.
  Sin éxito falso en ningún caso (rechazos honestos).
- Informe original conservado abajo sin reescritura.
- **Clase**: entorno/proveedor (con comportamiento de producto honesto)
- **Severidad**: S3 — funcionalidad degradada real hoy: el tutor contextual con
  fuente devuelve "No se confirmó una sugerencia utilizable" de forma
  sistemática; 11 pruebas AI e2e fallan por límite de salida.
- **Fecha/run**: 2026-10-12 · `auto-2026-10-12-001`
- **Candidato**: checkout `dfbc15a` + LM Studio local
- **Entorno**: LM Studio `127.0.0.1:1234`, modelo cargado
  `gemma-4-12b-it-qat@q4_k_xl` (sustituye a `slm-production-evaluation`,
  ausente del catálogo actual)

### Hecho observado (literal)

Tutor contextual desde la GUI: «No se confirmó una sugerencia utilizable.
Puedes iniciar otra solicitud o consultar a tu docente.»

Captura de inferencia correlacionada (misma petición):

```
max_tokens_req=1200 finish=length completion=1200 content_len=0 prompt_len=4215
```

(y el tutor libre, con prompt de 1393 chars, sí completó:
`max_tokens_req=1200 finish=stop completion=1115 content_len=1134`).

Suite completa: 11 fallos en `tests/ai/test_ai_*_e2e.py`, todos con
`AIOutputLimitError: Provider reached the output limit...` (4 de ellos además
contra Ollama inexistente en este entorno).

### Causa y evidencia

- Hecho 1 (verificado): el límite efectivo del tutor es **1200 tokens**
  (`TUTOR_MAX_OUTPUT_TOKENS`), aunque la cuenta tenga 4000 configurados; la
  petición real al proveedor salió con `max_tokens=1200`.
- Hecho 2 (verificado): LM Studio sustituye el modelo pedido por el cargado;
  el modelo cargado es razonador y consume presupuesto antes de emitir
  contenido (con 1200 tokens: `content_len=0`).
- Hecho 3 (verificado): el producto **rechaza honestamente** el truncado
  (`require_complete_response`) y no inventa contenido ni marca éxito falso.
- NO atribuido: no es un defecto de lógica del producto; es la combinación
  modelo-sustituto + presupuesto. Subir el límite es decisión del propietario
  (hoy verificado en 1200); instalar/descargar otro modelo no está autorizado.

### Frecuencia y efecto

- Tutor contextual con fuente: 1/1 fallos hoy. Tutor libre: 1/1 correcto.
- 11/18 pruebas AI e2e fallan; el resto de la suite no se ve afectada.

### Alternativa temporal segura

- Usar el tutor en modo libre, o configurar un modelo local no razonador
  autorizado por el propietario.

---

## SLM-AUTO-019 · El hook de captura del fixture rompe el catálogo de modelos (GET sin body)

- **Estado**: REPARADO EN EL ARNÉS 2026-10-12. Helpers
  `decode_captured_request` / `append_captured_record` en
  `tests/browser/local_provider_server.py` (body vacío → `request: None`) +
  `tests/browser/test_capture_hook_regression.py` con 3 casos (7 PASS con
  harness contracts). Verificación viva con fixture nuevo: catálogo responde
  «3 nombres de modelos recibidos».
- Informe original conservado abajo sin reescritura.
- **Clase**: arnés (`tests/browser/local_provider_server.py`)
- **Severidad**: S3 para la instrumentación de campaña (bloquea la evidencia
  del catálogo); el producto no está afectado.
- **Fecha/run**: 2026-10-12 · `auto-2026-10-12-001`
- **Candidato**: fixture `tests/browser/local_provider_server.py` (sin
  modificaciones)

### Hecho observado (literal)

Al pulsar «Cargar catálogo del proveedor configurado» la UI muestra:

> «No se pudo completar la solicitud. Reinténtalo cuando el servidor esté
> disponible.»

y `GET /api/settings/ai/models?provider=lm_studio` devuelve **500**. Traza del
servidor:

```
src.api.dependencies - ERROR - Failed to fetch LM Studio models: Expecting value: line 1 column 1 (char 0)
```

justo después de `GET http://127.0.0.1:1234/v1/models "HTTP/1.1 200 OK"` (la
petición del producto tuvo éxito con JSON válido de 402 bytes).

### Causa comprobada

El hook de captura del fixture hace:

```python
record = {"request": json.loads(response.request.content), ...}
```

para toda respuesta hacia `127.0.0.1:1234`. En un `GET /v1/models` el body del
request está vacío (`b''`) → `json.loads(b'')` lanza `JSONDecodeError` **dentro
del hook** → la petición revienta con 500 aunque el transporte fue correcto.

### Efecto en la evidencia histórica

El PASS histórico de AUTO-AI-02 («catálogo carga 4 modelos») pudo obtenerse con
un endpoint alias (p. ej. `localhost`) que el hook deja pasar. La evidencia del
catálogo de esta campaña queda **no acreditada por el arnés**; el comportamiento
del producto (petición y parseo correctos) sí está verificado por traza.

### Arreglo mínimo propuesto (no aplicado esta noche)

Guardia antes de parsear: si `response.request.content` está vacío, no capturar.
Con prueba fallida primero (hook ejecutado contra un GET sin body).

---

## SLM-AUTO-020 · NEEDS_REPRO: respuesta 403 en POST /api/classroom/messages con el mensaje creado

- **Estado**: NEEDS_REPRO (sin cambios 2026-10-12). 12 envíos controlados más
  en r4: 0 reproducciones del 403-con-creación (total acumulado 40+).
  Incidencia de paso: al reutilizar la credencial obsoleta de learner_b tras
  su rotación, el login devuelve 401 y los reintentos BLOQUEAN la cuenta
  («Account is locked due to too many failed attempts») — el anti-fuerza
  bruta funciona; la cuenta sintética queda bloqueada y documentada, sin
  desbloquearla a mano.
- **Clase**: producto (sin confirmar)
- **Severidad**: S3 si se confirma (autorización inconsistente); hoy S4-dado
  que no reaparece.
- **Fecha/run**: 2026-10-12 · `auto-2026-10-12-001`

### Hecho observado (literal)

Dos envíos sintéticos (`learner_a` → `teacher_a`) devolvieron HTTP 403
`{"detail":"Access denied"}` al cliente **y** quedaron persistidos en la base
(ids 1 y 3 con el `sent_at` de esos momentos). La política aplicable
(`can_message`) permite ese par (matrícula verificada) y de hecho el mismo par
funciona de forma normal.

### Intentos de reproducción

- 28 envíos controlados posteriores (incluido el mismo orden login→petición):
  **0 fallos**.
- El par prohibido real (`learner_b` → `teacher_a`) devuelve 403 **sin** crear
  mensaje: la política funciona.

### Causa

Desconocida. NO se atribuye al producto sin reproducción; podría ser artefacto
del cliente de sonda. Queda registrado para el propietario con los datos
exactos (IDs, marcas de tiempo, política aplicable).

---

## Notas de esta ejecución (no son defectos)

- **Sustitución de modelo por LM Studio**: responde con el modelo cargado a
  cualquier nombre, incluso inexistente. Observación de entorno documentada en
  RUN.md; afecta a la interpretación de cualquier prueba de IA de esta noche.
-**Títulos generados por el modelo**: el modelo razonador prefijó un título con
  `[General Knowledge Requiring Review]`; el borrador es editable y el docente
  puede corregirlo. No es defecto del producto.
-**Pérdida de propuestas temporales al reautenticar**: contrato documentado en
  la UI («Las propuestas son temporales hasta que las guardes explícitamente»).
