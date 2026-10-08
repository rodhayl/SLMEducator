# DEFECTS · Campaña auto-2026-10-08-001

Registro único de defectos observados en ESTA ejecución. No renumera ni sobrescribe los informes
históricos D/G ni los defectos del plan. IDs con prefijo `SLM-AUTO-`.

Severidad: S1 pérdida/exposición grave o arranque esencial bloqueado · S2 flujo esencial roto ·
S3 función degradada · S4 presentación menor.

---

## SLM-AUTO-001 · El campo de búsqueda de «Personas» pierde caracteres escritos deprisa

- **Estado**: OPEN
- **Severidad**: S3 (función degradada: el filtrado existe y es correcto, pero escribir rápido produce un término distinto al tecleado)
- **Prioridad**: Media
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001`
- **Candidato**: rama `fix/react-functional-continuation-20261007`, HEAD `0f3ff15`, frontend React construido en esta ejecución, runtime web `http://127.0.0.1:8000`, base sintética desechable
- **Entorno**: Windows 10.0.26200.9550 · Chrome vía DevTools · viewport 1440 × 900 · Español · tema Sistema
- **Rol**: Administrador (sesión `admin`)
- **Caso relacionado**: AUTO-PEO-03 · regresión G4
- **Precondiciones**: al menos una cuenta en la lista; lista «Personas» con filtro de rol = «Docente»
- **Datos sintéticos**: cuentas `docente_auto08` (Docente Demo) y `alba_auto08` (Alba Demo)

### Hecho observado (literal)

1. Admin → Personas. Filtro «Filtrar por rol» = `Docente`.
2. Escribir `Demo` en «Buscar en esta lista».
   - Con entrada rápida el campo queda con `Deo` y la lista responde `0 cuentas`.
     La URL del enlace «Crear cuenta» llegó a mostrar `?role=teacher&q=eo` en una repetición anterior.
   - Con una pulsación por carácter (4 ida y vuelta) el campo conserva `Demo` y la lista responde `1 cuentas`.
3. El mismo campo, con `Demo` completo, filtra correctamente: aparece la fila
   `Docente Demo · docente_auto08 · Docente · Activa · docente.auto08@example.com`.

Esperado: el campo de búsqueda conserva exactamente el texto tecleado y filtra por él.
Observado: con velocidad de escritura por encima de un carácter por ciclo de render, se pierden
caracteres y el término aplicado no coincide con el tecleado.

**Frecuencia**: 2 de 2 repeticiones con entrada rápida (una con `fill`, otra con pulsaciones rápidas);
0 de 1 con entrada lenta. Acotado a 3 intentos, sin bucles.

**Efecto**: solo afecta al filtrado de la lista. No afecta cuentas, matrícula ni datos.

### Evidencia

- `evidence/04_peo_busqueda_demo.png` (captura original inspeccionada)
- Instantáneas originales de esta sesión: campo `value="Deo"` con `0 cuentas`; campo `value="Demo"` con `1 cuentas`.

### Qué NO pudo verificarse

- Comportamiento con escritura humana real a velocidad normal (no hay control de teclado del sistema).
- Si el mismo defecto afecta a otros campos de búsqueda de la aplicación: no inventado, no reproducido.
- Causa exacta: no instrumentada. El síntoma es compatible con que un estado de búsqueda
  diferido/escrito por el componente sobrescriba el valor del campo mientras el usuario escribe.

### Hecho observado vs. causa

- Observado: el valor del campo y el parámetro `q` no coinciden con el texto tecleado cuando la
  escritura es rápida.
- No comprobado: el componente, hook o estado concreto responsable.

### Alternativa temporal segura

Escribir el término a ritmo lento o pegar el texto completo funciona correctamente y permite
continuar la campaña; se usó para el resto de la prueba.

### Histórico

No consta en `implementation_documents/manual_windows_20261006/DEFICIENCIAS.md` (H-D1..H-D3) ni en
los defectos G1–G5. Es un hallazgo actual, no una reopening.

---

## SLM-AUTO-002 · La biblioteca no distingue «sin materiales» de «sin resultados por filtro»

- **Estado**: OPEN · **Severidad**: S4 (presentación) · **Prioridad**: Baja
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001` · candidato `0f3ff15`, runtime web `127.0.0.1:8000`
- **Entorno**: Windows 10.0.26200.9550 · Chrome vía DevTools · 1440×900 · Español · Sistema
- **Rol**: Docente (`docente_auto08`) · **Caso**: AUTO-MAT-01 (variante de lista vacía)

### Hecho observado

1. Docente → Cursos y materiales → Biblioteca de materiales, con la biblioteca vacía y los filtros por
   defecto («Todos los tipos», «Todos los autores visibles»).
2. La pantalla muestra el encabezado «Ningún material coincide con estos filtros.» y el botón
   «Quitar filtros».
3. Al pulsar «Quitar filtros» la pantalla muestra exactamente el mismo encabezado y el mismo botón.

Esperado: una biblioteca sin ningún material debe ofrecer un estado vacío propio («aún no hay
materiales, crea uno o genera con IA») y el estado «sin resultados» debe aparecer solo con un filtro
que descarte lo existente.
Observado: ambos estados son indistinguibles y la acción ofrecida no cambia nada.

**Efecto**: solo presentación y orientación; no afecta datos.

### Qué NO pudo verificarse
Si el mismo texto aparece en otros listados vacíos: no inventado, no reproducido.

### Alternativa temporal segura
Crear el primer material; el listado deja de estar vacío.

---

## SLM-AUTO-003 · Claves de opción duplicadas: el rechazo no indica ningún campo

- **Estado**: OPEN · **Severidad**: S3 (función degradada) · **Prioridad**: Media
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001`
- **Rol**: Docente · **Caso**: AUTO-MAT-02 · **Precondición**: editor de «Ejercicio de práctica», tipo
  «Opción múltiple», 3 opciones

### Hecho observado

1. Crear material «PR1 Denominador», tipo Ejercicio de práctica → Opción múltiple.
2. Escribir 3 opciones y dejar la clave de la opción 2 igual a la de la opción 1 (ambas `1`).
3. Pulsar «Guardar borrador».

Esperado: el rechazo señala el campo incorrecto, como ya ocurre con otros validadores de esta misma
pantalla (p. ej. «Completa este campo.» por campo, o «Correo electrónico: Introduce un correo
válido…» en el alta de cuentas).
Observado: el guardado no se completa (estado «Cambios sin guardar») y el único mensaje es el resumen
genérico «Revisa los campos del formulario y reinténtalo.». No hay ningún campo con
`invalid="true"` ni mensaje asociado a las claves, al texto de la opción ni a la respuesta correcta.
Con la clave corregida el mismo formulario se guarda sin problemas (material 2).

**Frecuencia**: 1 de 1 con clave duplicada; el guardado con claves únicas funcionó a la primera.

### Hecho observado vs. causa
- Observado: el mensaje no identifica el campo y el formulario no marca dónde está el error.
- No comprobado: qué validación concreta rechaza el envío y por qué su detalle no se traduce a un
  error por campo. No se instrumentó la respuesta del servidor para ese intento.

### Alternativa temporal segura
Corregir la clave duplicada y volver a guardar; no se perdió trabajo previo.

---

## SLM-AUTO-004 · «Tutor y preguntas» no carga: el servidor no sirve la ruta /tutor que el menú y el contrato declaran

- **Estado**: OPEN · **Severidad**: S2 (flujo esencial roto) · **Prioridad**: Alta
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001` · candidato `0f3ff15`
- **Rol**: Docente (`docente_auto08`) · **Casos**: AUTO-TUT-01..03, AUTO-QA-01..03, AUTO-AI-03/04,
  historicales G1 y G2

### Hecho observado

1. Como docente, el menú «APOYO» muestra el enlace «Tutor y preguntas» →
   `http://127.0.0.1:8000/tutor`.
2. Al pulsarlo, la página carga y muestra literalmente el texto `{"detail":"Not Found"}` junto con un
   formulario sin contexto (sin lista de preguntas, sin selector de material, sin historial).
3. El mismo enlace aparece en el menú del administrador.

Esperado: la pantalla «Tutor y preguntas» (tutor libre/contextual + «Mis preguntas») es la
superficie principal de IA y de preguntas propias; debe servirse.
Observado: la ruta devuelve 404 y la aplicación renderiza el JSON de error como contenido de pantalla.

### Contrato comparado (técnico, complementario)

- `src/frontend/src/app/route-contracts.ts` declara `{ path: '/tutor', label: 'help', roles: all }` y su
  regex de cliente incluye `|progreso|tutor|ayuda|solicitudes`.
- `src/frontend_delivery.py` (`SPA_PATH`) incluye `progreso|ayuda|solicitudes|mensajes` pero **no**
  `tutor`.
- `LEGACY_VIEWS` en el mismo módulo mapea `tutor → /ayuda`, es decir el servidor conoce el
  identificador legacy pero no sirve la ruta actual.

Conclusión técnica: desajuste entre el contrato de rutas del frontend y la frontera de entrega del
servidor. No es un error de navegación ni de la cuenta.

**Efecto**: toda la superficie de IA conversacional y de preguntas propias queda inutilizable desde la
GUI: TUT-01, TUT-02, TUT-03, QA-01, QA-02, QA-03 y la parte libre de AI-03/AI-04 quedan BLOCKED por
este defecto, no por falta de permiso ni de proveedor.

### Qué NO pudo verificarse
El contenido de la pantalla una vez arreglada la ruta; y si el mismo 404 JSON se muestra en alguna
otra ruta no declarada.

### Alternativa temporal segura
Ninguna desde la GUI: `/ayuda` es la cola de solicitudes de ayuda (solo estudiantes) y al abrirla
como docente la aplicación exige re-verificar sesión. No se ha encontrado ninguna ruta alternativa al
tutor.

---

## SLM-AUTO-005 · Generar con IA responde 500 aunque el proveedor local conteste 200, y no deja causa registrada

- **Estado**: OPEN · **Severidad**: S2 (flujo esencial roto) · **Prioridad**: Alta
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001` · candidato `0f3ff15`
- **Rol**: Docente · **Casos**: AUTO-GEN-01, AUTO-GEN-02, AUTO-AI-03

### Hecho observado

1. Docente → Generar con IA → modo «Lección individual», Materia «Matemáticas», Curso o nivel
   «Personas adultas, inicio», Tema «Comparar fracciones de la misma unidad», dos objetivos de
   aprendizaje, curso en borrador «… (revision)».
2. Pulsar «Generar con IA».
3. Tras ~60 s la pantalla muestra el aviso «El resultado es desconocido. Tu texto se conserva.
   Comprueba el registro antes de reintentar para evitar duplicados.» y el botón «Reintentar la
   solicitud capturada». «Trabajos de generación guardados» indica «Este curso no tiene trabajos
   guardados.»
4. Confirmado el reintento con el control visible (diálogo «Reintentar la solicitud capturada»): mismo
   resultado. 2 de 2.

### Evidencia técnica complementaria (`evidence/ai_generation_failure.log`, de `api.log`)

- `17:28:10,235 - httpx - HTTP Request: POST http://localhost:1234/v1/chat/completions "HTTP/1.1 200 OK"`
  con `Content-Length: 4929` y cuerpo leído completo.
- Inmediatamente después: `POST /api/generate/lesson HTTP/1.1" 500`.
- Segundo intento: `POST /api/generate/lesson HTTP/1.1" 500` de nuevo.
- `Generating lesson for topic: Comparar fracciones de la misma unidad (Grade Personas adultas, inicio)`.
- **No hay traza ni mensaje de error** en `api.log` ni en `logs/slm_educator.log` para ese 500.

Esperado: o una propuesta utilizable y editable, o un error honesto que diga qué falló.
Observado: el proveedor responde correctamente y la aplicación falla al procesar la respuesta, sin
explicar la causa ni en pantalla ni en el log.

**Efecto**: la generación con IA no produce material. El aviso de «resultado desconocido» evita afirmar
una falsehood (no inventa contenido) y el registro visible confirma que no quedó ningún trabajo
guardado, así que no se observa corrupción ni duplicado; pero la funcionalidad es inservible y no es
diagnosticable.

### Hecho observado vs. causa
- Observado: 500 tras respuesta 200 del proveedor; sin traza en el log.
- No comprobado: si el contenido devuelto no cumple el formato que el parser exige, si falta un campo
  de la respuesta, o si falla la persistencia del borrador. No se reprodujo fuera de la GUI ni se
  inspeccionó el cuerpo de la respuesta del modelo (contendría material generado, no datos reales).

### Alternativa temporal segura
El trabajo humano del docente no depende de la IA: autoría manual, curso, evaluación, correcciones,
ayuda y mensajes siguen operativos (demostrado en otros casos de esta campaña).

### Nota de entorno
El destino por defecto de `env.properties` era `ollama`/`gpt-oss`, que no está disponible en esta
máquina (nada escucha en 11434). Con autorización de David se configuró LM Studio
(`http://localhost:1234`) con el modelo realmente cargado `slm-production-evaluation`. La conexión y el
catálogo de modelos funcionan (16,9 s y 4 nombres), por lo que el defecto no es de conectividad sino
del procesamiento de la respuesta en la ruta de generación de lección.

---

## SLM-AUTO-006 · Cursos con el mismo título son indistinguibles en la lista y en el selector de curso

- **Estado**: OPEN · **Severidad**: S4 (presentación con riesgo operativo) · **Prioridad**: Media
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001` · **Rol**: Docente · **Caso**: AUTO-CRS-06,
  AUTO-GEN-02

### Hecho observado

1. La lista «Cursos» muestra dos entradas con el texto exacto «Fracciones cotidianas | auto08», la
   misma descripción y la misma etiqueta «Privado», sin ID, sin estado de borrador/publicado ni
   contador que las distinga.
2. El selector «Curso en borrador» de «Generar con IA» ofrece dos opciones con texto idéntico.

Origen de la duplicación: la creó esta campaña por un clic mío mal dirigido tras un re-render (guardó
el curso antes de que apareciera el diálogo de cambios sin guardar). Se documenta como preparación
propia, **no** se atribuye al producto. Un docente puede llegar al mismo estado con dos cursos de
contenido parecido.

Esperado: opciones y filas que permitan distinguir cursos distintos (por ejemplo ID, versión o estado).
Observado: la única pista es leer la URL de cada enlace, algo no disponible en la selección de un
`<select>`.

**Efecto**: riesgo de elegir el curso equivocado al generar material o al asignar. No se observó
pérdida de datos.

### Qué NO pudo verificarse
Si el producto ofrece alguna otra vía para distinguir homónimos: no se encontró en las pantallas
revisadas.

---

## SLM-AUTO-007 · La lección se muestra al alumno con seis encabezados de sección vacíos

- **Estado**: OPEN · **Severidad**: S4 (presentación) · **Prioridad**: Baja
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001` · **Rol**: Alumna (`alba_auto08`) y docente
- **Casos**: AUTO-MAT-01 (variante de render), AUTO-LEARN-02

### Hecho observado

1. Como docente, «Crear material» de tipo «Lección» ofrece una sola sección («Título de la sección 1»
   y «Contenido de la sección 1») más un desplegable de objetivos.
2. Guardado el material, la lectura del alumno muestra la sección escrita y además seis encabezados
   de nivel 2 sin ningún texto: «Resumen», «Ejemplo resuelto», «Intento independiente», «Comentarios»,
   «Repaso posterior» y «Antes de empezar».

Esperado: mostrar solo las secciones con contenido, o indicar que están vacías.
Observado: la lección creada con una sola sección se presenta al alumno con seis encabezados de sección
sin cuerpo, lo que sugiere una plantilla incompleta o un renderizado de campos vacíos.

**Efecto**: ruido visual en el aula; el contenido real sí está presente y legible.

### Qué NO pudo verificarse
Si esos encabezados corresponden a estructura prevista por el contrato de contenidos; no se investigó
el contrato del renderer ni el material generado por IA (SLM-AUTO-005 lo impide).

---

## SLM-AUTO-008 · La rúbrica definida en la evaluación no es aplicable al calificar

- **Estado**: OPEN · **Severidad**: S3 (función degradada) · **Prioridad**: Media
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001` · **Rol**: Docente
- **Casos**: AUTO-GRADE-01, AUTO-GRADE-02

### Hecho observado

1. En «Nueva evaluación» se define una rúbrica «Lectura de 2/5» con tres criterios y puntos:
   Numerador 2, Denominador 2, Partes iguales 1. Se guardó y persistió al reabrir el editor.
2. Con la evaluación publicada y una entrega pendiente, la pantalla «Correcciones» para esa pregunta
   abierta ofrece únicamente un campo numérico «Puntuación» (0–5) y «Comentarios (opcionales)», más
   «Guardar calificación de pregunta» y «Finalizar calificación total».
3. La pantalla no contiene ninguna referencia a la rúbrica ni a sus criterios (verificado también por
   inspección del texto de la página).

Esperado: poder aplicar los criterios de la rúbrica al calificar la respuesta abierta.
Observado: el docente define una rúbrica que después no tiene dónde usarse; la calificación es un único
número más un comentario libre.

**Efecto**: la calificación con rúbrica no es posible desde la GUI. La coincidencia de puntos con la
suma de criterios (5) resulta aquí accidental, no forzada por el sistema.

### Hecho observado vs. causa
- Observado: ausencia de control de rúbrica en la pantalla de corrección.
- No comprobado: si la rúbrica se aplica en otro flujo (por ejemplo sugerencias de IA) o si existe una
  superficie no descubierta en esta campaña.

---

## SLM-AUTO-009 · Al reabrir el editor de evaluación desaparecen los campos de vínculo con curso y material

- **Estado**: OPEN · **Severidad**: S4 (presentación con riesgo de trazabilidad) · **Prioridad**: Media
- **Fecha/run**: 2026-10-08 · `auto-2026-10-08-001` · **Rol**: Docente
- **Casos**: AUTO-EVA-01

### Hecho observado

1. En «Nueva evaluación» existen los campos «ID del curso» y «ID del material», con la ayuda «ID
   opcional de un recurso existente. El servidor comprueba tu permiso de autoría.». Se introduce el ID 2
   del curso y se guarda el borrador.
2. Al reabrir `/evaluaciones/1/editar`, esos dos campos ya no están en el formulario.
3. La vista de solo lectura de la evaluación tampoco indica a qué curso o material está vinculada.

Esperado: que el vínculo sea visible y editable al reabrir, para que el docente pueda verificar a qué
curso pertenece la evaluación.
Observado: tras crear, el docente no tiene ninguna pantalla donde comprobar el vínculo.

**Efecto**: el docente no puede confirmar desde la GUI si la evaluación quedó vinculada al curso que
creyó vincular. La lectura posterior por parte de la alumna sugiere que el vínculo funcionó, pero eso
no se ha comprobado de forma directa y no se da por bueno.

### Qué NO pudo verificarse
El valor realmente almacenado del vínculo: exigiría inspección de la base sintética o de la API, fuera
del recorrido de pantalla de esta campaña.


---

## SLM-AUTO-010 · El comentario de intento vencido se muestra en inglés y sin la declaración que sí cubre las actividades

- **Estado**: OPEN · **Severidad**: S4 (presentación) · **Prioridad**: Media
- **Fecha/run**: 2026-10-08, sesión 2 · `auto-2026-10-08-001` · candidato `0f3ff15`
- **Rol**: Alumna (`alba_auto08`) leyendo su propio envío · **Caso**: AUTO-EVA-04, AUTO-VIS-02

### Hecho observado

1. Con una evaluación de 1 minuto, S1 inicia el intento, espera al vencimiento y envía.
2. La pantalla de resultado, en una interfaz íntegramente en español, muestra bajo el encabezado
   «Comentarios» el texto literal: `Time limit exceeded. Answers preserved for teacher review.`
3. La respuesta se conserva y se califica (10/10), y el estado del envío es correcto.

Esperado: mensaje en el idioma de la interfaz, o una declaración de que ese texto lo genera el
servidor en inglés.
Observado: el texto aparece en inglés y sin contexto.

### Matiz importante (evita un diagnóstico equivocado)

En «Mi progreso → Actividad reciente» la aplicación **sí declara** que las descripciones de actividad
las aporta el servidor en inglés y se muestran sin cambios. Ese aviso cubre la actividad, pero **no**
cubre el campo de comentarios del envío, que es donde aparece este texto. La diferencia es real y
comprobable en pantalla.

### Contrato comparado (técnico, complementario)

`src/api/routes/assessment.py`, líneas 1390 y 1393, escribe literalmente en `submission.feedback`:

- `"Original attempt timezone unknown. Answers preserved for teacher review."`
- `"Time limit exceeded. Answers preserved for teacher review."`

No hay ninguna clave de traducción asociada en el diccionario del cliente.

**Efecto**: presentación y consistencia de idioma. Además, el mensaje de sistema ocupa el mismo campo
`feedback` que usaría el docente para su retroalimentación, lo que puede inducir a confusión sobre quién
escribió qué; no se ha observado que se sobrescriba ni que se pierda la valoración del docente, porque
no se ha probado esa combinación.

### Segunda ocurrencia del mismo patrón (añadida en la sesión 3)

Al cerrar un intento **sin enviar**, el resultado muestra bajo «Comentarios» otra cadena fija del
servidor, también en inglés y también sin declaración:

`Attempt explicitly closed without submission or grade. The reserved attempt remains consumed.`

Confirma que el patrón de `SLM-AUTO-010` es **sistémico** en los mensajes de estado del servidor
presentados al alumno, no un caso aislado. El resto del comportamiento es correcto: estado «Cerrado
sin envío», fecha `—`, respuesta conservada y «Sin calificar» sin sustituir por cero, e intento
consumido.

### Qué NO pudo verificarse
- La variante «Original attempt timezone unknown» (línea 1390): no alcanzada, porque no se preparó un
  intento con zona horaria desconocida.
- Si el docente ve el mismo texto en «Correcciones» y si su propio comentario convive con él.
- Si existe traducción de este campo en el cliente para otros idiomas.

### Nota de alcance
No se propone arreglo: este informe no modifica producto.

---

## SLM-AUTO-011 · Tras el traspaso de matrícula el docente anterior pierde acceso a la ficha del estudiante

- **Estado**: OPEN · **Severidad**: S4 (con riesgo para el trabajo del docente) · **Prioridad**: Media
- **Fecha/run**: 2026-10-08, sesión 3 · `auto-2026-10-08-001` · candidato `0f3ff15`
- **Rol**: Docente saliente (T1 `docente_auto08`) · **Caso**: AUTO-PEO-04

### Hecho observado

1. Con T1 como docente responsable de S1, la ficha `/estudiantes/3` incluye el bloque «Tus notas
   privadas», con su nota «Solo tu cuenta puede leer estas notas».
2. Se traspasa S1 a T2 con confirmación. T1 conserva la autoría: sigue viendo los envíos de Alba en
   «Correcciones» (la propia pantalla lo anuncia: «incluso del alumnado cuya matrícula haya cambiado»)
   y su «Mis estudiantes» queda en 1 cuenta.
3. T1 intenta abrir `/estudiantes/3`: **`No tienes acceso o el recurso ya no está disponible.`**
4. T2 sí abre la ficha y ve el progreso compartido (1 lección, 2 entregas, 90 %) y **su propio campo de
   notas privadas vacío**.

Esperado: el traspaso cambia la gestión del estudiante. No consta qué debe pasar con las notas privadas
que el docente saliente hubiera escrito antes.
Observado: el docente saliente pierde el acceso a la ficha y, con ella, a su propio campo de notas.

**Efecto comprobado**: pérdida de acceso a la ficha. **Efecto NO comprobado**: si existían notas
privadas escritas por T1 antes del traspaso, se vuelven ilegibles para ella. Esta campaña nunca escribió
esas notas, así que **no se afirma pérdida de datos**; es un riesgo deducido del modelo de permisos, no
un hecho observado.

### Por qué esto importa para el caso AUTO-PEO-04

La cláusula «T2 no hereda notas privadas de T1» **no puede demostrarse empíricamente** con esta
secuencia: al bloquear el acceso a T1, no existe nota previa con la que comparar. El caso queda PARTIAL
por esa razón, y no PASS por analogía.

### Qué haría falta para cerrarlo
Repetir la secuencia escribiendo una nota privada de T1 **antes** del traspaso, y comprobar después si
T1 puede leerla y si T2 la ve.

### Alternativa temporal segura
Ninguna desde la GUI para recuperar acceso. Requiere decisión de producto: ¿debe conservar el docente
anterior la lectura de sus notas propias, o la responsabilidad debe transferirlas?

---

## SLM-AUTO-012 · Los rechazos de archivo en «Fuentes del curso» usan el resumen genérico y son indistinguibles

- **Estado**: OPEN · **Severidad**: S3 (función degradada) · **Prioridad**: Media
- **Fecha/run**: 2026-10-08, sesión 5 · `auto-2026-10-08-001` · candidato `0f3ff15`
- **Rol**: Docente · **Casos**: AUTO-SRC-02

### Hecho observado

1. En «Fuentes del curso» (curso 3, en borrador) con una fuente guardada de 441 caracteres.
2. Se suben por el selector nativo, uno tras otro: `vacio.txt` (0 bytes), `tipo-no-admitido.bin`
   (28 bytes) y `demasiado-grande.txt` (11 MB).
3. Los tres rechazos muestran **únicamente** el resumen genérico «Revisa los campos del formulario y
   reinténtalo.» (`uid=449_0 alert`), sin campo señalado ni mensaje asociado al archivo.

Esperado: error legible que distinga archivo vacío, tipo no admitido y límite superado, como ya ocurre
con otros validadores de la misma aplicación (p. ej. «Introduce un correo válido…» en el alta).
Observado: el mismo mensaje para las tres causas; el docente no sabe qué está mal. El problema no está
en ningún «campo del formulario»: está en el archivo.

**Lo que sí funciona y se declara**: lo guardado **no** se reemplaza (el formulario conserva la fuente
TXT de 441 caracteres) y el límite publicado es coherente (el botón indica «hasta 10 MB»).

### Relación con otros defectos
Mismo patrón de mensaje genérico que SLM-AUTO-003 (claves duplicadas en el editor de práctica), pero
en otra superficie y con otra causa; se registra aparte para no mezclar flujos.

### Qué NO pudo verificarse
El comportamiento con un curso publicado/asignado (exigencia de revisión por inmutabilidad): no
ejecutado en esta sesión.

---

## SLM-AUTO-013 · La lección creada en línea muestra el encabezado «Lesson» en inglés dentro de la interfaz en español

- **Estado**: OPEN · **Severidad**: S4 (presentación) · **Prioridad**: Baja
- **Fecha/run**: 2026-10-08, sesión 9 · `auto-2026-10-08-001` · candidato `0f3ff15`
- **Rol**: Alumna (`alba_auto08`) · **Casos**: AUTO-LEARN-04, AUTO-VIS-02

### Hecho observado

1. La lección «L2 Comparar fracciones», creada en línea desde el editor del curso (solo título y texto),
   se muestra a la alumna con un encabezado de nivel 2 con el texto literal `Lesson`, en una interfaz
   íntegramente en español.
2. Las lecciones creadas desde «Crear material» muestran sus secciones con los títulos escritos por el
   docente (p. ej. «Qué es una fracción»).

Esperado: etiqueta localizada («Lección») o el título de la sección.
Observado: cadena fija en inglés que parece una etiqueta de reserva sin traducir.

**Efecto**: solo presentación. No afecta al contenido ni a la navegación.

### Qué NO pudo verificarse
Si la misma etiqueta aparece en materiales generados por IA (SLM-AUTO-005 impide generarlos) o en
otros tipos de material.
