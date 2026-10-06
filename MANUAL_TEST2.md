# SLMEducator: acompañarme en la prueba manual del instalador

## Prompt para el agente que me guía

Soy David. Quiero probar personalmente SLMEducator, usando el instalador preparado con `MANUAL_TEST1.md`. Guíame en español, **una acción concreta por mensaje, esperando mi respuesta después de cada acción**. Tú preparas los datos ficticios y analizas lo que yo observo; yo manejo el instalador y la aplicación. No necesitas ser Codex ni usar comandos especiales de objetivos.

No me pegues este plan completo, listas de veinte tareas ni comandos de ingeniería. No marques un paso realizado por silencio o porque exista un test automatizado. No hagas mis clics ni generes por API/SQL los datos que debo crear en la UI. Antes de cada acción puedes preparar lo necesario tú mismo en el repositorio, sin cambiar el producto o la instalación durante la sesión.

### Preparación silenciosa y límites

1. Lee `AGENTS.md`, `README.md`, `docs/FUNCTIONAL_REQUIREMENTS.md`, `docs/ASSISTANCE_POLICY.md`, `docs/AI_REQUESTS_AND_OPERATIONS.md` y el `MANUAL_TEST_HANDOFF.md` de la construcción más reciente. Verifica archivo/versión/hash del instalador y que los resultados corresponden a ese artefacto. Usa el handoff, no el ZIP histórico posterior al smoke.
2. La base de referencia es `5e839d2b0bc0bb89309f49eac648a6eee747cd79` y su [informe Windows](https://github.com/rodhayl/SLMEducator/blob/5e839d2b0bc0bb89309f49eac648a6eee747cd79/implementation_documents/windows_best_effort_20261006/REPORT.md). Este es un recorrido de un instalador nuevo, no una reapertura de todas las campañas históricas. Si falta un instalador verificado o acceso al handoff, dime el bloqueo y pide ejecutar primero `MANUAL_TEST1.md`. No lo sustituyas por el antiguo portable o `start.bat`.
3. Identifica desde el código y la UI de esta versión los nombres reales de pantallas, campos y botones. Las etapas siguientes son objetivos del recorrido, no permiso para inventar controles. Si no puedes ver mi pantalla, dilo y pide el texto que aparece o una captura sin credenciales; no afirmes haber observado mi acción.
4. Solo usaremos datos sintéticos de personas adultas. No solicites información de alumnos reales, claves API ni contraseñas por chat. Yo introduzco localmente las contraseñas únicas y las guardo de forma privada. No captures pantallas de credenciales ni escribas sus valores en informes.
5. Usa una instalación, base y cuentas nuevas para esta sesión. No abras ni alteres otras bases/configuraciones, no cambies seguridad de Windows, no instales modelos y no pares Gemma, Trading ni servicios ajenos. No recurras a cloud de pago. No ejecutes Actions, campañas semánticas ni baterías globales.
6. Si surge un fallo, conserva mi trabajo y registra paso, entrada sintética, texto visible y resultado. Haz una sola comprobación dirigida o un reintento explícito cuando tenga sentido. No reintentes automáticamente la inferencia ni me hagas repetir recorridos sin cambio. Un fallo persistente se registra y se pasa a una rama independiente del recorrido, si existe. Si afecta seguridad, datos o acceso, detén la parte dependiente y pide decisión.
7. No corrijas el producto mientras lo evalúo. Un bloqueo que requiera código vuelve a una preparación separada; el binario corregido necesita nueva identidad/hash y smoke. No presentes el funcionamiento de la versión corregida como evidencia de la que probé.

### Forma de cada intervención

Da el número del paso actual, una instrucción breve con el dato exacto que necesito copiar, qué debería observar y una sola pregunta al final. Ejemplo: «Paso 1. Abre el instalador [ruta verificada]. Debería aparecer el asistente de SLMEducator. ¿Qué ventana ves?». Espera siempre mi respuesta antes de avanzar.

Un formulario completo no es un solo paso si contiene varias decisiones: guíame campo por campo. Puedes dar un bloque breve para pegar en **un único campo**. No reveles de golpe las respuestas correctas de los ejercicios; son tu referencia de comprobación. Mantén un registro corto de completado/pendiente y continúa desde donde estemos si interrumpo.

La primera respuesta debe ser únicamente el primer paso ejecutable de instalación, o la pregunta mínima sobre el handoff que realmente falta.

### Datos ficticios preparados para esta sesión

Todos los nombres representan adultos ficticios de evaluación, sin edades ni fechas de nacimiento. Si un nombre ya existe, añade un sufijo corto de sesión y consérvalo durante todo el recorrido.

- Docente: «Docente Demo», usuario `docente_demo`, email solo si el formulario lo exige: `docente.demo@example.invalid`.
- Alumna principal: «Alba Demo», usuario `alba_demo`, email opcional `alba.demo@example.invalid`.
- Alumno de contraste: «Bruno Demo», usuario `bruno_demo`, email opcional `bruno.demo@example.invalid`.
- Ninguna contraseña viene en este archivo. La introduciré localmente cuando toque.
- Curso: «Fracciones cotidianas | prueba manual». Nivel/audiencia: «Personas adultas, iniciación». Descripción: «Curso ficticio para leer, comparar y practicar fracciones de una misma unidad. No contiene datos reales».
- Objetivo del curso: «Interpretar numerador y denominador y comparar fracciones con igual denominador de la misma unidad».
- Primera lección: «Partes iguales». Texto: «Una fracción representa partes iguales de una unidad. En 3/8, el 8 indica en cuántas partes iguales se ha dividido la unidad y el 3 cuántas se han elegido. Si las partes no son iguales, contarlas no basta para representar correctamente la fracción».
- Segunda lección: «Comparar fracciones». Texto: «Para comparar fracciones de la misma unidad con igual denominador, comparamos sus numeradores. Así, 5/8 es mayor que 3/8: cinco octavos son más que tres octavos. Esta regla no se aplica directamente a denominadores distintos ni a unidades de diferente tamaño».
- Vocabulario, si existe el campo: «Numerador: partes elegidas. Denominador: número total de partes iguales. Unidad: el todo que tomamos como referencia».
- Nota privada de Alba: «Quiero recordar que las partes deben ser iguales y la unidad debe ser la misma».
- Petición de ayuda al docente: asunto «Misma unidad»; mensaje «¿Por qué no puedo comparar media pizza pequeña con media pizza grande como si fueran la misma cantidad?».

Práctica de bajo riesgo, preparada sin IA si hace falta:

- Opción múltiple: «En 3/8, ¿qué indica el 8?». Opciones: «Las partes elegidas», «El total de partes iguales de la unidad», «El número de unidades enteras». Clave docente: segunda opción. Explicación: «El denominador cuenta todas las partes iguales en que se divide la unidad».
- Opción múltiple: «De la misma unidad, ¿cuál es mayor: 2/9 o 6/9?». Opciones: «2/9», «6/9», «Son iguales». Clave docente: segunda opción. Explicación: «Las partes son del mismo tamaño; seis novenos son más que dos novenos».

Evaluación separada: «Comprobación de fracciones | demo».

- Pregunta objetiva: «De la misma unidad, ¿cuál es mayor: 7/10 o 4/10?». Opciones «7/10», «4/10», «Son iguales». Clave docente: primera opción.
- Pregunta abierta: «Explica qué representan el 2 y el 5 en 2/5 y qué condición deben cumplir las partes».
- Referencia docente: «El 5 es el total de partes iguales de la unidad; el 2 indica cuántas se eligen».
- Rúbrica sencilla: identifica numerador, identifica denominador y menciona partes iguales. Usa la escala que admita la UI, sin inventar campos o fórmulas.
- Política de asistencia del intento: «Desactivada / disabled», para comprobar una restricción visible sin exigir que un modelo respete semánticamente una pista.

### Recorrido que debes dosificar, nunca enviar completo

#### A. Instalación, primer acceso y persistencia

1. Hazme abrir el instalador real indicado en el handoff. Confirma identidad/versión y destino nuevo antes de instalar. Una advertencia de firma o SmartScreen se registra; no me digas que ignore protecciones. Si no podemos continuar con seguridad, paramos.
2. Guíame por el asistente de instalación en su ubicación de evaluación nueva. No aceptaré borrar ni reemplazar una instalación anterior. Después abriré el acceso directo instalado. Anota el URL/puerto real del servidor local y el proceso/ruta que tú puedas observar de esta instancia.
3. Iniciaré sesión como `admin`, consultando la contraseña inicial por el mecanismo privado del handoff. Guíame para cambiarla por otra única directamente en la UI. Después cerraré sesión y entraré con la nueva, sin compartirla contigo.
4. Comprobación pendiente de **X nativa**: hazme guardar lo pendiente y pulsar la X de la ventana nativa del launcher, no la X de una pestaña del navegador. Mientras espero, comprueba de forma dirigida si han terminado los procesos propiedad de ese launcher y si dejó de escuchar su servidor. No confundas un árbol de procesos cerrado por ti con el cierre humano correcto. Una pestaña estática todavía visible no demuestra que el servidor siga vivo.
5. Abriré una vez el acceso directo de nuevo y entraré con la contraseña ya cambiada. Comprueba que no aparece otra instancia/puerto inesperado ni se resembró la cuenta. Si la X dejó el servidor vivo o perdió estado, registra FAIL y para el tramo dependiente; no lo ocultes matando procesos y marcando PASS. Cualquier limpieza posterior se hace aparte y solo sobre esta instancia.

#### B. Cuentas y materiales hechos por mí

1. Desde la administración, guíame para crear «Docente Demo». Luego cerraré la sesión admin y entraré como ese docente. Con su UI crearé Alba y Bruno; comprueba la asignación docente explícita que corresponda. No uses registro anónimo para crear roles de personal.
2. Como docente, crearé el curso y sus dos lecciones utilizando los textos anteriores. Guíame por los campos reales y por guardar un borrador. Si una pantalla solo genera con IA, busca primero el editor manual mantenido. No rellenes por SQL o endpoints un recorrido manual que la interfaz no permite.
3. Añadiré la práctica y crearé la evaluación separada. Mantén claves y rúbrica en los controles del docente, nunca dentro de un texto que se vaya a publicar al alumno. Enlaza la evaluación al curso solo mediante la función mantenida, si ese recorrido lo necesita.
4. Guarda la política de asistencia «Desactivada» de la evaluación. Guíame para revisar el contenido y las claves, corregir un error visible si lo hay, revisar/publicar la evaluación y después revisar/publicar el curso según los estados reales de la UI.
5. Asignaré el curso **solo a Alba**. Bruno permanece sin ese curso para la comprobación de acceso. Observa que no se salta la revisión/publicación y que el material ya asignado no se modifica silenciosamente; si se necesita revisarlo, la vía es un borrador separado.

#### C. Elegir IA opcional desde la UI

1. Pregunta una sola vez: «¿Quieres probar también un modelo local que ya tengas funcionando, o prefieres continuar hoy sin IA?». Espera mi elección. Un recorrido sin IA sigue siendo válido; anota las inferencias como NOT RUN.
2. Si elijo IA local, pregunta qué proveedor y modelo existente quiero usar. Usa Ollama o LM Studio y el endpoint/modelo que yo elija y que la UI admita. No impongas Gemma, un segundo modelo ni un tamaño concreto. No descargues nada, no cambies configuraciones de Trading y no reinicies su servidor para esta prueba.
3. Guíame por Configuración de IA de la cuenta que vaya a realizar la inferencia. Verifica si la configuración es por usuario; configurar al docente no prueba que Alba use el mismo modelo. Si las opciones de alumno no están expuestas, identifica la vía soportada desde el código, sin copiar credenciales ni asumir herencia.
4. Guarda la selección y, si existe, ejecuta una sola prueba de conexión. Registra proveedor, identificador exacto del modelo y resultado. Una conexión correcta no certifica calidad; una conexión fallida no autoriza cambiar de modelo en bucle.
5. Si falla o no hay modelo local preparado, conserva el error y continúa con las lecciones manuales y funciones que no dependen de IA. No presentes respuestas del arnés, mocks o textos tuyos como inferencias reales. Cloud o credenciales nuevas quedan fuera de esta sesión.

#### D. Alumna autónoma, práctica, ayuda y modelo real si lo elegí

1. Cierra la sesión del docente. Entra como Alba sin dejar una sesión docente abierta. Hazme localizar su curso asignado, abrir la primera lección, escribir la nota privada y pausar. Comprueba al continuar que nota y avance se conservan; pausar no equivale a completar.
2. Completaré la primera lección y avanzaré a la siguiente. Haré una respuesta correcta y otra incorrecta en la práctica, cuando el modo lo permita. Verifica que se distingue feedback de práctica de una calificación formal y que un error no se convierte en éxito artificial.
3. Envía desde la UI la petición de ayuda ficticia al docente. Comprueba la confirmación y que la ausencia de respuesta del docente no impide seguir leyendo o practicando. No requiere presencia simultánea del profesor.
4. Solo si elegí modelo local y su configuración funciona en Alba: con la lección seleccionada, pregunta al tutor «En 3/8, ¿qué significa el 8? Explícalo con un ejemplo corto». Observa el contexto/selección de secciones, la respuesta real, aviso de sugerencia no verificada y recibo si está disponible. Pregúntame si la explicación me resulta comprensible. Registra errores factuales o límites sin exigir perfección.
5. Prueba una sola pregunta de tutor sin curso seleccionado: «¿Qué diferencia hay entre numerador y denominador?». No debe requerir que un docente esté conectado. Si la pantalla ofrece Q&A por separado, usa una pregunta breve distinta allí: «¿Por qué 6/9 es mayor que 2/9 si representan partes de la misma unidad?». No repitas llamadas para mejorar una puntuación.
6. Si una inferencia falla o tarda hasta el límite visible, registra el mensaje, que mi pregunta se conserve y que el fallo no figure como respuesta educativa útil. No envíes otra llamada por tu cuenta. Pregunta si quiero un único reintento explícito o continuar sin IA. Los recibos pueden indicar que el proveedor aún trabaja tras cancelar; no prometas cancelación física ni coste cero.
7. No hace falta provocar un fallo deteniendo servidores o alterando endpoints compartidos. Los errores simulados del informe anterior son evidencia aparte. No conviertas este recorrido corto en una campaña de robustez o de selección de modelos.

#### E. Evaluación, límites de asistencia y revisión docente

1. Como Alba, iniciaré el intento de evaluación. Comprueba que la asistencia desactivada se presenta y se aplica durante el intento; intentar abrir tutor/Q&A debe dar la restricción, sin obtener una solución. La autorización no depende de elegir u omitir el curso.
2. Contestaré la pregunta objetiva y la abierta con los datos ficticios. Guíame para enviar una vez y leer el estado; no vuelvas a enviar para fabricar mejor nota. Abrir los resultados no debe reservar otro intento.
3. Si existe evaluación subjetiva por el modelo elegido, su resultado debe quedar **provisional** hasta revisión docente. Un error o modelo ausente no debe producir una nota final de cero. Registra «sin calificación IA / pendiente de revisión» cuando corresponda; no invoques un proveedor para forzar el paso.
4. Cerraré la sesión de Alba y volveré como Docente Demo para abrir su entrega, comparar con la rúbrica y revisar/confirmar por la vía de la UI. La confirmación humana usa lo que realmente responda la alumna ficticia; no iguala automáticamente la nota sugerida.
5. Vuelve después a Alba y comprueba feedback e historial. La finalización del intento libera su restricción de asistencia; que una nota siga pendiente es un estado distinto. Si revisar manualmente sin proveedor no está disponible, documéntalo como límite en vez de inventar un control.

#### F. Privacidad, lectura sin profesor y cierre

1. Entra como Bruno y comprueba en la UI que no ve el curso privado asignado a Alba, sus notas, entregas ni feedback. No hace falta una campaña de penetración ni ataques a endpoints. Una filtración detiene el recorrido y se registra claramente.
2. Vuelve a Alba. Si la UI permite exportar material para el alumno, guíame por previsualización y exportación de una copia legible HTML o Markdown. Comprueba que el archivo no incluye claves, rúbricas ocultas o la fuente privada del docente. No exportes el paquete docente como si fuera material del alumno.
3. Distingue tres hechos: el docente desconectado no impide leer lo asignado; un proveedor indisponible no debe borrar la lección; el navegador sin servidor no tiene una aplicación interactiva completa. Podemos abrir el archivo exportado independientemente del servidor. No desconectes mi red ni alteres firewall/VPN para fingir una prueba offline; no marques inferencia sin Internet como probada sin haberla observado.
4. Cambia una vez ES/EN en una pantalla representativa, y vuelve al idioma que elija. Registra etiquetas, avisos y mensajes que realmente aparezcan. No extiendas esto a otra auditoría completa de accesibilidad, hardware, zoom, service worker o recuperación ya cubierta históricamente.
5. Cierra la sesión de forma normal y conserva esta instalación y sus datos ficticios para mí. No desinstales ni borres automáticamente. La comprobación de X nativa ya tuvo su paso único; no la repitas para conseguir un resultado distinto sin una corrección identificada.

### Resultado de la sesión y parada

Prepara al terminar un informe local breve bajo `implementation_documents/manual_windows_<fecha>/`, separado de secretos y datos de ejecución. Si me paro antes, guarda el estado alcanzado y termina como sesión parcial.

Incluye:

- Instalador, versión, hash, commit y entorno efectivamente usados.
- Pasos observados por mí frente a comprobaciones técnicas hechas por ti; PASS, FAIL, BLOCKED, NOT RUN o SKIPPED BY USER con motivo. Lo pendiente no se convierte en PASS.
- Resultado de instalación/login/rotación/persistencia y de la X nativa; cuentas y material ficticio, sin contraseñas.
- Resultado funcional de revisión/publicación/asignación, lectura autónoma, práctica, permisos, evaluación y notas provisionales.
- Si elegí IA: proveedor/modelo real, preguntas realizadas, respuesta útil o fallo, calidad observada y límites. Si no, declara inferencia NOT RUN. No mezcles resultados sintéticos previos con esta observación ni cambies sus puntuaciones.
- Incidencias accionables con pasos mínimos de reproducción y qué impiden. Sin registros completos con tokens ni capturas de datos privados.
- Una conclusión concreta: qué pude usar y qué quedó bloqueado. Esta prueba individual no certifica eficacia educativa, adecuación para menores, cumplimiento normativo ni todos los proveedores/modelos/hardware.

Muéstrame un resumen corto y la ubicación del informe. **Detente después del informe o cuando yo diga que pare. No inicies otra auditoría, no arregles ni reconstruyas automáticamente, no publiques y no programes más pruebas.**
