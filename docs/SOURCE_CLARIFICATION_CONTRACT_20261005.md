# Contrato de aclaración de fuentes, 2026-10-05

## Decisión

**Candidato de reparación, no aceptación de producción ni cierre semántico.**
Parte de `b0fa6f9599a3032289746b2425b3ba0471620feb`, rama
`fix/production-readiness-windows-20261005`. El informe y las respuestas reales
v8 se conservan sin modificar: 34/36 aceptadas; siguen sin cerrarse mediante
nueva inferencia los casos `followup-conflict` y `followup-level`.

Esta reparación usa el mismo generador y una sola llamada al proveedor. No
añade otro modelo, juez, detector por palabras prohibidas ni una aprobación
docente automática. Su contrato de salida cambia a
`teacher-reviewed-v9-explicit-source-concerns`. Las repeticiones de trabajos
guardados conservan sus IDs y versión anterior; no se reetiquetan como v9 ni se
sobrescriben las correcciones del docente.

## Causa y cambio acotado

El resultado v8 del contador describía correctamente cinco frente a ocho, pero
omitía la pregunta directa al docente. La instrucción en prosa no bastó. Ahora,
para una lección con fuente, el proveedor debe devolver `source_review`:

- `status: no_issue_reported` y `issues: []`, o
- `status: needs_clarification` y de una a seis incidencias, cada una con `kind`
  (`missing`, `conflicting`, `suspect`), `description` y `teacher_question`.

Una declaración ausente/incoherente, o una incidencia sin pregunta acotada con
algún carácter imprimible no blanco, produce error de validación. No se guarda
como elemento listo; se puede
reintentar dentro del trabajo existente. Las preguntas válidas se incorporan
al principio del cuerpo mediante las secciones existentes, por lo que pasan por el mismo
editor, visor, serialización del alumno y fuente seleccionable del tutor. No quedan sólo
en preguntas de discusión opcionales o en metadatos ocultos. Añadir una pregunta
no convierte una respuesta sin contenido en una lección válida.

La selección del tutor sigue limitada a 6.000 caracteres. Las preguntas se
priorizan ahora al principio, también en lecciones largas; una selección explícita
de otras secciones o un conjunto excepcionalmente largo sigue limitado por ese
presupuesto. No se afirma que toda pregunta entre en cada prompt. El contrato se
aplica tanto a `/lesson` y Full Package como a las
lecciones anidadas de `/topic-content`. El contenido sin lección no adquiere
un requisito de revisión de lección.

La revisión final reprodujo y corrigió también la duplicación del cuerpo cuando
el proveedor enviaba `content` y `sections` equivalentes, y la pérdida del cuerpo
en el visor directo cuando antes sólo había `content`. Se reutiliza primero la
representación canónica; texto y secciones permanecen sincronizados. Se eliminan
duplicados de preguntas como párrafos planos; en formato enriquecido no se
presupone visibilidad por encontrar una subcadena. Hay pruebas de repetición
idempotente.

Una revisión independiente encontró preguntas ocultas por comentarios HTML,
etiquetas o definiciones Markdown. Las preguntas se insertan como texto literal
escapado en una sección prioritaria, antes incluso de los objetivos. No se
confía en una marca de sección que pueda falsificar el proveedor: su título y
contenido se reconstruyen. La representación del alumno sólo conserva una marca
booleana verdadera; no expone la revisión cruda del modelo. DOMPurify sigue
siendo el límite de seguridad existente, sin segundo motor de renderizado.
Las pruebas cubren texto literal, comentarios/etiquetas/fences sin cerrar,
comparaciones con `<`, metadatos de sección falsificados y aplanado del editor.
El caché de assets cambia a v21 para entregar el renderer corregido.

La fuente de `followup-level` ya contenía la definición defectuosa de mitad.
No se altera esa fuente congelada ni se elimina su puntuación negativa. El
prompt distingue ahora fidelidad textual y exactitud: pide señalar definiciones
o cálculos sospechosos, separar citas atribuidas de afirmaciones educativas
respaldadas y solicitar una fuente corregida. No debe corregirla silenciosamente,
inventar datos externos ni tratar hechos ficticios desconocidos como errores.

## Lo que este contrato no demuestra

`no_issue_reported` significa únicamente que el modelo no declaró incidencias.
No demuestra que leyera bien, que detectara todas las contradicciones o que una
definición sea correcta. Validar una cadena `teacher_question` tampoco juzga su
pertinencia educativa. Un modelo puede clasificar mal, producir una pregunta
inadecuada o repetir un error sin señalarlo. La calidad de esos comportamientos
necesita evaluación real; no se sustituye por pruebas de cadenas del prompt.

Las salidas siguen siendo borradores; `source_support=unverified` permanece.
Publicar sin revisión continúa devolviendo 409. La declaración del modelo no
equivale a detección verificada ni a revisión humana. No se exige otra revisión
paralela ni se declara insegura automáticamente toda lección.

## Regresiones y casos nuevos

El nuevo contrato se probó primero contra el servicio v8 sin modificar:
12 FAIL y 2 PASS, con fallos por admisión de declaraciones incompletas, pérdida
de preguntas en el cuerpo y ausencia de la distinción de exactitud. Un primer
ensayo del propio arnés carecía del campo HTTP `model`; se corrigió el arnés y
se repitió el rojo auténtico. Ese ensayo inválido no se usa como prueba del fallo
del producto. Tampoco se usan los fallos por fixtures antiguas sin el nuevo
campo para fingir una regresión semántica.

Las fixtures sintéticas de transporte que ya comprobaban recibos, objetivos,
fragmentos y conservación de campos incluyen ahora la nueva declaración
obligatoria. Se mantienen sus aserciones anteriores. No se altera ninguna
respuesta real, rúbrica histórica o umbral para conseguir un pase.

Hay controles con conflicto de siete/once, definición sospechosa de cuarto,
información ausente, fuente válida y ausencia de fuente. La integración usa el
adaptador/parser real con sólo el transporte HTTP simulado: incidencia sin
pregunta → cero contenidos guardados; reintento completo → un borrador;
repetición → mismo ID y ninguna llamada extra; publicación sin revisar → 409.
Estas son pruebas contractuales sintéticas, no inferencia ni aceptación docente.

La batería adicional congelada antes de cualquier inferencia v9 está en
`tests/fixtures/local_semantic_source_review_20261005.json`: ocho casos nuevos
con conflicto de 70/90 en el mismo evento, dos eventos compatibles, definición
de cuarto mala y buena, hechos ficticios desconocidos, capacidad ausente,
instrucción maliciosa de «corrección» y una fuente explícitamente corregida
sobre mitad. La última es un caso nuevo; nunca sustituye a `followup-level`.
Los ocho permanecen **sin ejecutar contra el modelo**. Los once reservados de
v8 ya son conocidos y no se vuelven a presentar como inéditos.

La fixture histórica conserva su blob Git
`9de1673f2287ccdeb3f5e8ceb3f0883e26186d90`. Su SHA-256 en Git/LF es
`a5c1622411c64d87942c601a93baeb59c52771e877e2c167e214e209ad24def1`;
con finales CRLF de Windows reproduce exactamente el SHA
`cf3c6d9c6e0e02004368aaabd0c86332a56429b13b059e17d8d14fdc93ddf107`
del informe anterior. No se confunde esa diferencia de codificación con un
cambio de casos u oráculos.

## Consolidado final

Código/assets congelados: árbol `src` Git
`18fa8d463a512b4ba5ab06c5d97fce32077bc515`. El commit local de prueba es
`71ad66623f4adc1f68a5ed384c867a11878042b1`; es una instantánea de trabajo,
no el SHA remoto de entrega. El recibo de evidencia identifica los hashes de
cada fichero y el commit remoto se comprueba tras publicar.

- Python: 1.007 PASS, 36 SKIP, cinco deseleccionados; exit 0, 565,48 s,
  cobertura 81,62 % y umbral 80 % conservado. Comando: `SLM_OFFLINE_TESTS=1
  USE_REAL_AI=0 python -m pytest tests -q -ra --strict-markers
  --ignore=tests/manual --ignore=tests/e2e --ignore=tests/real_ai -m "not real_ai"
  --cov=src --cov-report=term --cov-fail-under=80 --basetemp=RUTA_NUEVA`.
- DOM completo: 192 PASS con `npm --prefix tests/ui test`. Incluye once casos
  de aclaración literal comprobados también desde Python; no son once
  inferencias reales.
- Browser final: 11 PASS, 49,83 s, Chromium 141/Playwright 1.56, con fixtures
  sintéticas y proveedor simulado. Incluye instalación/actualización real del
  service worker v14→v21, offline/reconexión, permisos, editor y corrección.
  Se excluyó explícitamente `test_native_zoom.py`: no hay display para su
  Chromium visible; no se sustituye por zoom CSS ni se cuenta como pase.
- Lint crítico: `flake8 src scripts tests --select E9,F63,F7,F82`, PASS.
- Mypy de los cuatro servicios afectados (`ai_service`, `learning_context`,
  `generation_workflow`, `content_schema`), `--follow-imports=silent`, PASS.
- `pip check`, PASS. No se afirma actualizar ni auditar todas las dependencias.
- Auditoría contractual independiente: 23 Python y 26 DOM, PASS sobre los
  mismos cambios de servicio/renderer; incluyó persistencia, reintento,
  conservación de correcciones docentes y casos de marcado hostil no incluidos
  inicialmente por la implementación. No es revisión educativa humana.

Los 36 skips Python son 23 de proveedor/contexto, 12 de browser opt-in y uno
de paquete Windows. Los cinco deseleccionados y los ámbitos manual, e2e de
servidor existente y real-AI siguen excluidos de este gate, igual que en la
base. Se conserva la advertencia de deprecación del TestClient.

El primer candidato pasó 987 Python/181 DOM; después recibió correcciones por
la revisión adversarial, de modo que esos números no certifican el final.
Dos consolidaciones de desarrollo quedaron interrumpidas al hallar cambios
necesarios y no cuentan como pases. El DOM detectó la incoherencia entre el
caché v21 y tres query tags v20 del dashboard: se corrigió el HTML manteniendo
la aserción, y se ejecutó de nuevo el conjunto final.

El primer browser dio 10 PASS/1 FAIL porque Playwright 1.56 no propagaba offline
al service worker sin `PW_EXPERIMENTAL_SERVICE_WORKER_NETWORK_EVENTS=1`;
se comprobó esa condición en su runtime instalado y se habilitó el flag sin
alterar la aserción 503. Otra tanda tuvo un cierre del target Chromium al sacar
una captura: 10 PASS/1 FAIL, conservada como tal. La repetición final, serial
tras el gate Python, dio los 11 pases anteriores. No se unen pases parciales
de ejecuciones diferentes. [Referencia de service workers de Playwright](https://playwright.dev/python/docs/service-workers).

Recibo público de alcance, hashes y resultados:
[`source_clarification_20261005.json`](evidence/source_clarification_20261005.json).

## Verificación pendiente y reproducción

El entorno disponible es Linux con Python 3.12.14. No hay acceso al LM Studio/Gemma del equipo
Windows. No se sustituyó por otro modelo para certificar estos casos; no se
usaron proveedores de pago, nuevas credenciales ni GitHub Actions.

Se comprobó también la alternativa CPU con los mismos pesos, sin dar por
imposible la inferencia sólo por faltar Windows. El [archivo oficial de la
revisión exacta](https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF/blob/980b060c40a8539ac159e0501a3e0f66a6365af3/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf)
publica el SHA-256 `90fd44e29e0d7cffeb0fd00dc73cfdab9ed0b0e95306ecf7821ea634c940c370`.
Los pesos ocupan 6.716.356.800 bytes. El runtime oficial llama.cpp b11146 ya
disponible incluye la arquitectura `gemma4`, aunque no se ha probado la carga
de ese GGUF concreto. El equipo de pruebas tiene 10.451.464.192 bytes de RAM
total, aproximadamente 2,16 GB disponibles durante los gates, sin swap ni GPU
NVIDIA visible y 10,63 GB libres de disco. Los pesos solos exceden esa memoria
disponible antes de añadir KV/cache y buffers a contexto 8.192. No se fuerza
una carga con presión de memoria ni se detienen otros servicios. La compatibilidad
y el consumo exacto no se declaran medidos sin cargar el modelo. Una eventual
ejecución CPU con iguales pesos sería evidencia semántica adicional, no una
certificación del runtime LM Studio/CUDA o del EXE Windows original.
Después del gate Python se volvió a medir: 2.924.318.720 bytes disponibles,
todavía menos que los pesos solos. No se descargó ni cargó el modelo de 6,72 GB
en este equipo compartido.

Para decidir sobre v9, en un entorno sintético nuevo y con el modelo, revisión,
hash, parámetros y presupuesto exactos del [informe Windows](PRODUCTION_READINESS_WINDOWS_20261005.md):

1. Repetir sin modificaciones todos los casos de
   `tests/fixtures/local_semantic_objective_20261005.json`, ambos splits.
2. Ejecutar en otro directorio de resultados nuevo los ocho casos `reserved`
   de `tests/fixtures/local_semantic_source_review_20261005.json` mediante el
   mismo driver `tests/browser/evaluate_local_provider.py`.
3. Conservar solicitudes, salidas crudas, errores, tiempos y puntuaciones.
   Rechazar una salida es un fallo del caso, no una aceptación semántica segura.
   Puntuar las cinco dimensiones 0/1/2; sólo cinco doses permiten aceptación.
4. No retocar prompt, configuración ni fuentes durante esa tanda. Cualquier
   cambio posterior exige otra tanda íntegra, conservando la anterior.
5. Reconstruir y comprobar el artefacto Windows final después de los cambios;
   el EXE v8 no incluye esta reparación. La X nativa y aceptación educativa
   humana siguen separadas y pendientes. No se solicita piloto al usuario ahora.

No se hace merge ni despliegue. La publicación de esta rama conserva el trabajo
anterior y usa `[skip ci]` para no consumir la cuota de Actions.
