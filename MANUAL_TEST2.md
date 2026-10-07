# MANUAL_TEST2 — guiar la prueba humana de la GUI React, una acción cada vez

Fase 2. Usa el instalador NUEVO y el handoff de `MANUAL_TEST1.md`.
Conserva A–F y sus pasos originales; los subpasos concretan la GUI vigente.
Si David pide ejecutar este archivo, empieza o reanuda sin exigir que lo copie
ni pedir una segunda orden. También puede copiar desde INICIO hasta FIN. Este documento es una
guía; ninguna casilla significa que una prueba humana ya haya pasado.

INICIO

Soy David. Quiero probar personalmente SLMEducator. Tú preparas los datos
ficticios, compruebas la versión y analizas lo que veo; yo manejo el instalador,
el navegador y la aplicación. Háblame en español sencillo, con UNA acción
concreta por mensaje y espera mi respuesta. No hagas mis clics, no rellenes mis
formularios por API/SQL y no me envíes este plan entero.

## Ruta rápida para el agente

Recorrido básico: A → B → D → E → F. C y las llamadas de IA de D solo se
hacen si David elige un proveedor ya disponible; el resto puede seguir sin IA.
No es obligatorio ejecutar todos los casos adicionales para terminar la sesión:
registra exactamente lo observado y deja sus variantes pendientes. Si se
interrumpe, reanuda por el ID de subpaso, no desde A. Consulta internamente
solo el siguiente bloque pertinente; no recites toda la guía en cada turno.

## Antes del primer mensaje: versión, alcance y responsabilidades

1. Lee `AGENTS.md`, `README.md`, `docs/FUNCTIONAL_REQUIREMENTS.md`,
   `docs/ASSISTANCE_POLICY.md`, `docs/AI_REQUESTS_AND_OPERATIONS.md`,
   `docs/BROWSER_TEST.md`, `MANUAL_TEST1.md` y el handoff MÁS RECIENTE que
   identifica el instalador de esta sesión. Comprueba ruta real, nombre,
   versión/build, SHA-256, SHA/árbol de producto, dist y smokes de ESE artefacto.
2. Referencia actual: `642966a93e7e9c9f9c5e93cce0bc842f538846fb`, árbol
   `e0a3966bddc8bbd4cfc2ab4041668c3162ce86f7`, rama
   `fix/react-functional-continuation-20261007`. Admite un descendiente solo
   documental comprobado y registra su identidad. Otro producto necesita una
   decisión expresa y su propio handoff. No selecciones `main` por defecto.
3. El handoff `implementation_documents/manual_windows_20261006/` y el Setup
   `fe954cab4655` son HISTÓRICOS: no contienen esta GUI React. Si solo tienes
   ese archivo, o falta un nuevo instalador verificado, explica el bloqueo y
   pide preparar `MANUAL_TEST1.md`. NO pidas instalar/probar otra vez la GUI
   antigua, no reconstruyas desde esta sesión, no uses `start.bat` como sustituto.
4. Si ya empezamos, lee el registro de la sesión: misma instalación, mismo
   artefacto y mismo estado guardado permiten continuar desde el subpaso
   pendiente. No reinstales ni rehagas A/B. Si cambió el candidato, conserva el
   informe anterior y abre una sesión de evidencia distinta.
5. Etiquetas verificadas contra `src/frontend/src/i18n/common.ts`,
   `features/*/locales.ts` y componentes/rutas del SHA anterior. La web usa español por defecto, pero puede restaurar el idioma guardado
   por ese navegador/origen; si aparece EN, selecciona «Idioma» → «Español»
   en un paso separado; el launcher y el instalador pueden tener otro idioma. Usa EN
   solo si lo confirma la pantalla y el catálogo vigente. No traduzcas por
   intuición ni busques controles del viejo dashboard `.html`.
6. Tú puedes revisar fuentes y evidencia técnica autorizada, sin cambiar el
   producto, instalación o datos durante esta evaluación. Si no ves mi pantalla,
   di que te basas en mi descripción. Pide solo el título/texto pertinente o
   una captura sin secretos. No afirmes haber visto una acción que no viste.
7. Solo personas adultas ficticias y datos sintéticos. Yo introduzco localmente
   contraseñas únicas y las guardo en privado. No pidas contraseñas, claves API,
   tokens ni datos reales en chat; no los leas en capturas ni los registres.
   Cambiar/resetear credenciales o habilitar acceso respeta la política de las
   herramientas: cuando exige entrega al usuario, yo introduzco, confirmo y envío.
8. Conserva mi instalación anterior y todos sus datos. Nada de desinstalar,
   limpiar registros, cambiar firewall/VPN, matar procesos ajenos, descargar
   modelos ni usar Actions. No reabras la investigación de seguridad ni
   navegador/localhost denegados mediante otro método. Registra BLOCKED y sigue
   solo tramos independientes legítimos.

## Regla de conversación: una acción, resultado y espera

Formato de CADA mensaje:

«Paso B.1.c. En “Crear una cuenta”, escribe “Docente” en “Nombre”. Debería
quedar ese texto en el campo. ¿Lo ves?»

- Un mensaje = un clic, un campo, una elección, una pulsación o una observación.
  Una ruta con flechas se divide en mensajes: primero abrir el menú; esperar;
  después abrir la página. Nunca «entra, rellena y guarda» en un mensaje.
- Incluye rol actual, pantalla/control visible, dato exacto para ese campo,
  resultado esperado y una sola pregunta de comprobación. Detente hasta mi
  respuesta. No envíes el siguiente paso porque pasó tiempo o hubo un test verde.
- «Listo» confirma únicamente la acción pendiente. «No aparece», error o una
  pantalla distinta activa la rama de incidencia; no presupongas el resultado.
- Un clic en Guardar y la confirmación de un diálogo son DOS pasos. Elegir
  varias opciones o rellenar tres campos son pasos separados. No uses `/goal`
  ni veinte preguntas iniciales. Pregunta solo lo que falta ahora.
- No muestres claves docentes cuando esté respondiendo como alumna. El texto
  para un único campo puede ser un bloque breve que pueda copiar.
- El primer mensaje será el primer paso ejecutable de A.1, el subpaso pendiente
  al reanudar o la única pregunta sobre la identidad/handoff que falta.

### Navegación y cambio de cuenta reutilizables

En escritorio, los enlaces están a la izquierda. Si no se ven por el ancho,
primero pide pulsar el botón «Abrir navegación» (icono de menú de la cabecera),
espera y después el enlace. El nombre puede leerse con la ayuda de accesibilidad;
no describas el icono solo por color o posición.

| Cuenta actual | Enlaces relevantes que debe ver |
|---|---|
| Administrador | Inicio; Personas; Cursos y materiales; Evaluaciones; Correcciones; Solicitudes de ayuda; Mensajes; Cuenta y ajustes; Copias de seguridad; Estado de la aplicación |
| Docente | Inicio; Mis estudiantes; Cursos y materiales; Evaluaciones; Correcciones; Solicitudes de ayuda; Mensajes; Cuenta y ajustes |
| Estudiante | Inicio; Mis cursos; Evaluaciones; Mi progreso; Tutor y preguntas; Solicitudes de ayuda; Mensajes; Cuenta y ajustes |

Rutina CAMBIAR CUENTA, dosificada en cinco o más mensajes:
1. Comprueba y guarda el trabajo pendiente en su pantalla; no elijas descartar
   sin mi decisión. La conversación del tutor no se convierte en historial
   permanente al cambiar de cuenta.
2. Pulsa «Cerrar sesión». Esperado: «¿Cerrar la sesión de esta cuenta?».
3. Pulsa «Salir y conservar mis borradores aquí» si he elegido conservarlos.
   Esperado: formulario de acceso. No elijas «Salir y borrar mis borradores
   aquí» por defecto; explica su efecto antes de una elección expresa.
4. En «Usuario», escribe el usuario sintético que YA creamos. Esperado: ese
   usuario, no el de otra instalación. Luego, en un mensaje separado, pídeme
   introducir su «Contraseña» localmente sin comunicarla.
5. Pulsa «Entrar». Esperado: «Inicio» y el nombre/rol correcto en la cabecera.
   Si no coincide, no continúes con acciones de ese rol.

### Rama de incidencia, para todos los pasos

- Falta la etiqueta o página: para ese paso; pide título y controles visibles,
  confirma cuenta/rol, idioma, origen y build con el handoff. Consulta la fuente
  de ese candidato. No inventes un botón, ID, URL, puerto ni contraseña; no
  saltes a una ruta adivinada o a la API para fabricar el recorrido.
- Error 422/validación: conserva los valores, registra el texto y campo.
  Corrige UN campo por turno usando el mensaje real. Un error legible esperado
  puede ser PASS del caso negativo; no es PASS del alta/guardado.
- `[object Object]`, volcado JSON, error vacío o mensaje de servidor ilegible:
  FAIL de claridad; captura saneada o transcripción exacta. No lo maquilles
  como validación correcta ni pidas repetir veinte veces.
- Servidor no accesible/503/500: conserva la página y textos; comprueba la
  ventana del launcher de esta instalación. No reinicies servicios ajenos ni
  cambies el puerto a mano. Un frontend faltante/inválido necesita volver a
  fase 1; no uses GUI legacy como alternativa.
- Guardado/envío «sin confirmar»: no pulse otra vez Guardar/Enviar a ciegas.
  Lee el registro existente con «Comprobar contenido guardado», «Revisar lista
  de cuentas», «Actualizar estado del servidor» o «Enviados», según la pantalla.
  Es una comprobación de lectura. Un reintento posterior requiere mi elección;
  conserva el ID si es «Reintentar la misma solicitud».
- Pérdida de texto, acceso ajeno o acciones bajo otra cuenta: detén el tramo
  dependiente, registra FAIL, conserva la evidencia mínima sin difundir datos.
  No cambies permisos ni borres información para ocultar el fallo.
- Máximo un reintento dirigido cuando haya motivo y yo lo elija; si persiste,
  registra el bloqueo y ofrece continuar por un tramo independiente. No arregles
  el producto mientras pruebo: una corrección exige otro build/handoff.

## Datos sintéticos: tú los suministras, yo los escribo

Elige una sola etiqueta de sesión corta, por ejemplo `m0710a`, y úsala en todos
los nombres de usuario/correos. Comprueba colisiones al crear; si una cuenta ya
existe, no la adoptes ni resetees. Cambia el sufijo solo para la cuenta nueva y
registra la correspondencia. En instrucciones a David sustituye las variables
por el texto final, nunca le pidas resolver marcadores.

| Referencia | Nombre / Apellidos | Usuario / correo de ejemplo |
|---|---|---|
| T1 | Docente / Demo | `docente_m0710a` / `docente.m0710a@example.com` |
| S1 | Alba / Demo | `alba_m0710a` / `alba.m0710a@example.com` |
| S2 | Bruno / Demo | `bruno_m0710a` / `bruno.m0710a@example.com` |
| T2, solo prueba de reasignación | Docente / Contraste | `docente2_m0710a` / `docente2.m0710a@example.com` |

Sin edad, fecha de nacimiento o contraseña publicada. «Correo electrónico» es
obligatorio en el formulario actual: usa estas direcciones reservadas de ejemplo que admite el servidor,
no una dirección personal ni una bandeja que debamos abrir. `.invalid` y `.test`
NO sirven para altas válidas con el validador actual; solo se usa `.invalid`
expresamente como dato del caso negativo B.1.f.

- CURSO: `Fracciones cotidianas | m0710a`.
- DESCRIPCIÓN: `Curso ficticio para personas adultas: leer y comparar fracciones
  de la misma unidad. Objetivo: interpretar numerador y denominador y comparar
  fracciones con igual denominador. No contiene datos reales.`
- UNIDAD: `Unidad de práctica`.
- L1, título: `Partes iguales`. Texto: `Una fracción representa partes iguales
  de una unidad. En 3/8, el 8 indica en cuántas partes iguales se ha dividido la
  unidad y el 3 cuántas se han elegido. Si las partes no son iguales, contarlas
  no basta para representar correctamente la fracción.`
- L2, título: `Comparar fracciones`. Texto: `Para comparar fracciones de la misma
  unidad con igual denominador, comparamos sus numeradores. Así, 5/8 es mayor
  que 3/8. Esta regla no se aplica directamente a denominadores distintos ni a
  unidades de diferente tamaño.`
- L3, caso E3 del plan: `Comprobar la unidad`. Texto: `La mitad de una pizza
  pequeña no tiene la misma cantidad que la mitad de una pizza grande. Antes
  de comparar, comprueba que el todo de referencia sea el mismo.`
- NOTA: `Quiero recordar que las partes deben ser iguales y la unidad la misma.`
- AYUDA, asunto: `Misma unidad`; descripción: `¿Por qué no puedo comparar media
  pizza pequeña con media pizza grande como si fueran la misma cantidad?`.
- RESPUESTA DOCENTE: `Ambas son una mitad, pero sus unidades tienen tamaños
  diferentes. Para comparar cantidades hay que usar la misma unidad.`

Material de práctica PR1: título `Denominador | m0710a`; tipo «Opción múltiple»;
pregunta `En 3/8, ¿qué indica el 8?`; claves A/B/C y textos, respectivamente:
`Las partes elegidas` / `El total de partes iguales de la unidad` /
`El número de unidades enteras`. Clave docente B. Explicación:
`El denominador cuenta todas las partes iguales en que se divide la unidad.`
PR2: título `Comparación | m0710a`; pregunta `De la misma unidad, ¿cuál es mayor:
2/9 o 6/9?`; textos A/B/C: `2/9` / `6/9` / `Son iguales`; clave B;
explicación `Con la misma unidad y denominador, seis partes son más que dos.`

EVALUACIÓN: `Comprobación de fracciones | m0710a`; instrucciones:
`Prueba ficticia. Responde usando la misma unidad y explica las partes iguales.`
Dos preguntas, 5 puntos cada una, máximo 2 intentos, sin límite de tiempo
(campo vacío), puntuación mínima 60, «Calificación manual».
- P1 «Opción múltiple»: `De la misma unidad, ¿cuál es mayor: 7/10 o 4/10?`.
  Valores A/B/C; textos `7/10` / `4/10` / `Son iguales`; clave docente A.
- P2 «Respuesta corta»: `Explica qué representan el 2 y el 5 en 2/5 y qué
  condición deben cumplir las partes.` Referencia docente:
  `El 5 es el total de partes iguales de la unidad; el 2 indica las elegidas.`
- Rúbrica: `Fracción y unidad`; descripción `Numerador, denominador y partes
  iguales`; criterios `Numerador` (2 puntos), `Denominador` (2),
  `Partes iguales` (1), con sus descripciones literales correspondientes.
- Ayuda: «Ayuda de IA desactivada». Esta política se guarda por separado.
- No adelantes a Alba la referencia docente. Para probar revisión manual,
  Alba debe escribir una respuesta NO vacía en P2; dejarla vacía puede dar cero
  automático. Una pregunta objetiva puede autocorregirse incluso en modo manual.

## Recorrido A–F: dosificar, no enviarlo entero

### A. Instalación, primer acceso y persistencia

#### A.1. Identificar y abrir el Setup nuevo

a. Agente, sin clic humano: verifica el handoff actual y hash local. Si solo
   existe el candidato histórico, usa la rama de bloqueo inicial.
b. Usuario: abre el archivo Setup en la ruta absoluta verificada del handoff.
   Esperado: asistente SLMEducator de la versión/build correcta. Pregunta qué
   ventana ve. No pidas ejecutar una ruta de ejemplo.
c. Si aparece un aviso de firma/SmartScreen, registra su texto. No indiques
   cómo eludirlo; pausa si no se puede continuar de forma segura. Si aparece
   una elección de idioma, guía solo la opción visible correspondiente.

#### A.2. Instalar y abrir la aplicación correcta

a. Da UN paso por pantalla del asistente utilizando la etiqueta real observada
   y documentada en el handoff del nuevo build. Los botones estándar de Inno
   dependen del idioma/versión del compilador; no están definidos por React.
   Si falta ese dato, pide el título y el botón visible antes de indicar un clic.
b. En la pantalla de destino, pide comprobar el directorio nuevo del handoff.
   Esperado: destino escribible, no un portable ni instalación existente. Si
   se detecta instalación registrada, conserva todo y bloquea la instalación;
   no mandes desinstalar aunque el mensaje de Setup lo sugiera.
c. Solo tras confirmar destino e identidad, pide el clic de instalación con
   su etiqueta visible. Esperado: finalización sin reemplazar datos antiguos.
d. Pide abrir el acceso directo SLMEducator instalado, una vez. Esperado:
   ventana nativa de inicio, transición a listo y navegador de esa instancia.
e. Pide leer «Dirección local» del launcher. Registra el origen
   completo real, incluido puerto. Si el launcher está en EN, la etiqueta es
   «Local address». No copies el puerto del README/smoke. Si el navegador
   no abre, usa el control «Abrir SLMEducator» que muestra el launcher; si
   tampoco está disponible, registra el estado antes de otra acción.

#### A.3. Entrar y cambiar mi contraseña localmente

a. Pantalla «Te damos la bienvenida»: escribe `admin` en «Usuario».
b. Pídeme introducir la contraseña inicial desde el mecanismo privado del
   handoff en «Contraseña», sin enviártela ni mostrarla en una captura.
c. Pulsa «Entrar». Esperado: «Inicio», rol «Administrador».
d. Abre «Cuenta y ajustes». Esperado: tarjetas de ajustes de esta cuenta.
e. Abre «Contraseña». Esperado: aviso de revocación de sesiones anteriores.
f. Introduce localmente «Contraseña actual». Esperado: campo oculto; no lo leas.
g. Introduce localmente «Nueva contraseña», única y con los requisitos visibles
   (12+ caracteres, mayúscula, minúscula, número, símbolo; máximo 72 bytes UTF-8).
h. Introduce localmente «Repetir nueva contraseña».
i. Pulsa «Cambiar contraseña». Esperado: «¿Cambiar tu contraseña?».
j. Pídeme confirmar mediante «Cambiar contraseña» en ese diálogo. Esperado:
   verificación de sesión/«Vuelve a entrar». No escribas ni envíes tú el secreto.
k. Guía de nuevo acceso campo a campo con la nueva contraseña. Esperado:
   misma cuenta admin. No cambies variables bootstrap para recuperar el acceso.

#### A.4. X nativa, observación humana pendiente del nuevo candidato

a. Comprueba que no hay texto sin guardar. Pide localizar la ventana NATIVA
   del launcher SLMEducator, no una pestaña del navegador.
b. Pide pulsar su X. Esperado: diálogo del launcher «Cerrar» con
   «¿Detener la aplicación local y cerrar esta ventana? Guarda primero tu
   trabajo en el navegador.». EN, solo si corresponde: «Close» /
   «Stop the local application and close this window? Save your work in the
   browser first.». Registra el texto realmente visto.
c. En otro mensaje, pide confirmar con el botón afirmativo visible del diálogo
   del sistema, tras identificarlo. Esperado: la ventana se cierra.
d. Agente: si tienes acceso permitido, comprueba solo el árbol de procesos y
   puerto de ESA instancia. Si no lo tienes, registra la comprobación técnica
   NOT RUN, sin pedir comandos al usuario. Una página estática aún visible no
   prueba que el servidor siga activo. Un `terminate` no prueba la X.

#### A.5. Reabrir, persistencia y Detener

a. Pide abrir de nuevo el mismo acceso directo. Esperado: una instancia lista;
   lee otra vez su URL real, que puede cambiar si un puerto quedó ocupado.
b. Guía el acceso como admin con la contraseña cambiada. Esperado: entra sin
   resembra de cuenta. Si falla, no hagas muchos intentos ni resetees a ciegas.
c. En el launcher listo, pide pulsar «Detener» («Stop» solo si está en EN).
   Esperado: diálogo «Detener» con «¿Detener la aplicación local? Guarda
   primero tu trabajo en el navegador. Las pestañas abiertas perderán la
   conexión.». En otro turno, confirma el botón afirmativo visible del sistema.
   Esperado: «Aplicación detenida». Comprueba, si está permitido, proceso/puerto.
   No confundas esto con la X.
d. Pide pulsar «Iniciar» («Start» en EN) cuando esté disponible. Esperado:
   estado listo; abre «Abrir SLMEducator» si hace falta, en otro turno.
e. Confirma acceso y misma cuenta. Si X o Detener dejó servidor propio activo,
   duplicó instancia o perdió estado, registra FAIL y pausa lo dependiente.
   Cualquier limpieza autorizada posterior tiene evidencia separada.

### B. Cuentas y materiales hechos por mí

#### B.1. Tres roles, alta legible y matrícula explícita

Como admin, crea T1. Cada fila es UN mensaje, esperando respuesta:

| Subpaso | Acción GUI | Resultado esperado |
|---|---|---|
| a | Abrir «Personas» | Lista de cuentas |
| b | Pulsar «Crear cuenta» | «Crear una cuenta» |
| c | Escribir `Docente` en «Nombre» | Texto visible |
| d | Escribir `Demo` en «Apellidos» | Texto visible |
| e | Escribir el usuario final de T1 en «Usuario» | Usuario sintético |
| f | Escribir `docente.m0710a@example.invalid` en «Correo electrónico» | Dominio reservado rechazado, solo para este caso negativo |
| g | Introducir una contraseña local única en «Contraseña» | Campo oculto, cumple requisitos de alta visibles |
| h | Elegir «Docente» en «Rol» | Rol docente seleccionado |
| i | Pulsar «Crear cuenta» | Error de correo comprensible; ningún alta confirmada |
| j | Sustituir solo «Correo electrónico» por el correo final de T1 | Otros campos/rol conservados |
| k | Pulsar «Crear cuenta» | «Cuenta creada»; admin sigue conectado |
| l | Pulsar «Abrir cuenta» | Ficha de T1 correcta; registrar ID no secreto |

La dirección `.invalid` tiene formato de correo pero el servidor actual la
rechaza con 422. Espera un mensaje comprensible junto al correo, sin crear
cuenta ni mostrar `[object Object]`. Si el navegador impide el envío antes,
regístralo como validación local: NO prueba por sí solo el 422 del servidor. Si aparece error de servidor,
contrástalo con la rama de incidencia. No desactives validación ni envíes una
petición técnica para convertir el caso manual en prueba de API.

m. Vuelve por «Volver a la lista». Crea S1 como admin siguiendo las mismas filas,
   ahora Nombre `Alba`, Apellidos `Demo`, usuario/correo finales de S1 y rol
   «Estudiante», correo válido desde el principio. No des a David esta lista
   completa: sigue campo por campo. Espera «Cuenta creada».
n. Pulsa «Elegir docente responsable». Esperado: ficha de Alba.
o. En «Elige un docente activo», selecciona T1 por el nombre y usuario mostrados. Contrasta con el ID
   que registraste en su ficha; el selector no muestra ese número.
p. Pulsa «Guardar matrícula». Esperado: «Confirmar matrícula» con Alba y T1.
q. En el diálogo, pulsa «Guardar matrícula». Esperado: «Matrícula guardada.
   Las asignaciones anteriores se conservan.» Comprueba «Docente responsable
   actual». No basta con que ambos usuarios existan.
r. CAMBIAR CUENTA a T1. Abre «Mis estudiantes». Esperado: Alba a su cargo.
s. Pulsa «Crear estudiante». Repite alta campo por campo para S2 (`Bruno`,
   `Demo`, usuario/correo finales, contraseña local). Como docente, el rol es
   estudiante y queda a su cargo; no busques un selector de rol de personal.
t. Espera «Cuenta creada» y abre su ficha. Debe indicar «A tu cargo». No se
   cambió a la sesión de Bruno ni se creó una cuenta de personal.

Caso G4, antes de salir de Personas/Mis estudiantes, una acción cada turno:
- En «Buscar en esta lista» escribe `Demo`; si es admin, elige «Estudiante» en
  «Filtrar por rol» y «Solo activas» en «Estado de la cuenta», por separado.
- Abre la ficha de Alba mediante su nombre. Usa el botón Atrás DEL NAVEGADOR.
  Deben conservarse búsqueda/filtros; registra selección y scroll si había
  desplazamiento. Con solo dos filas no declares probado scroll de una lista larga.
- Abre otra vez la ficha y pulsa «Volver a la lista». Mismos filtros y retorno
  a Alba. Al crear una cuenta desde una lista filtrada, comprueba también
  «Abrir cuenta» → «Volver a la lista» sin perder su origen.

#### B.2. Curso y lecciones manuales, sin IA

a. T1: abre «Cursos y materiales». Esperado: «Cursos» y enlace
   «Biblioteca de materiales». Pulsa ese enlace en el turno siguiente:
   biblioteca accesible aunque todavía no exista un curso.
b. Comprueba que muestra «Crear material» y «Generar con IA» para T1.
   No generes aún. Pulsa «Cursos» para volver, en otro mensaje.
c. Pulsa «Crear curso». Esperado: editor con «Título del curso».
d. Escribe CURSO en «Título del curso».
e. Escribe DESCRIPCIÓN en «Descripción». No hay campo independiente de
   nivel/objetivo en este editor: ese dato va en la descripción.
f. En la primera unidad, sustituye «Nombre de la unidad» por UNIDAD.
g. Pulsa «Crear lección» de esa unidad. Esperado: formulario de lección.
h. Escribe el título L1 en «Título de la lección».
i. Escribe el texto completo L1 en «Texto de la lección».
j. Elige `1` en «Dificultad (1–10)», si no es ya ese valor.
k. Pulsa «Guardar lección y añadir a la unidad». Esperado: lección guardada
   en biblioteca y añadida al borrador, posición del curso aún sin confirmar.
l. Repite g–k para L2 y L3, campo por campo. Tres lecciones permiten verificar
   anterior/pausa/continuación del plan sin inventar un árbol largo.
m. Pulsa «Guardar borrador» DEL CURSO. Esperado: «Borrador guardado. Debes
   revisarlo antes de publicar.». Guarda en el registro el ID real del curso,
   extraído de su URL visible `/cursos/<id>/editar`, nunca inventado.
n. Pulsa «Ver curso». Esperado: estructura guardada con las tres lecciones.
   No confundir lección guardada con posición guardada o curso publicado.
o. En «Todos los cursos», escribe `Fracciones` en «Buscar un curso»; abre CURSO,
   vuelve con Atrás del navegador; repite abriendo y pulsando «Todos los cursos».
   Cada navegación es un turno. Busca texto conservado y retorno al mismo
   elemento; scroll solo se evalúa si realmente existía desplazamiento.

#### B.3. Práctica y evaluación separadas

Práctica PR1; cada campo/clic siguiente se envía por separado:
a. Abre «Cursos y materiales», luego «Biblioteca de materiales» y luego
   «Crear material», esperando en cada página.
b. Escribe el título PR1 en «Título del material».
c. Elige «Ejercicio de práctica» en «Tipo de material».
d. Elige «Opción múltiple» en «Tipo de ejercicio».
e. Escribe la pregunta PR1 en «Pregunta».
f. Las filas de opciones empiezan vacías. Pulsa «Añadir opción» para la fila
   1, escribe A en «Clave de opción 1» y su texto en «Texto de opción 1»,
   un mensaje por acción. Repite «Añadir opción» y los dos campos para B y C.
g. En «Respuesta correcta» selecciona «El total de partes iguales de la unidad»
   para PR1 (clave B); para PR2, «6/9» (clave B). Se ve el TEXTO, no la letra.
h. Escribe la explicación PR1 en «Explicación».
i. Pulsa «Vista previa» para comprobar pregunta/opciones; luego
   «Guardar borrador» en otro turno. Esperado: «Material <id> guardado en el
   servidor.». El docente conoce la clave; no la copies al texto del alumno.
j. Repite a–i para PR2 con sus datos. No generes práctica por API.
k. Abre CURSO y «Editar estructura». En UNIDAD, elige PR1 en «Elegir material
   existente», luego pulsa «Añadir material seleccionado». Repite para PR2,
   con confirmación tras cada elección/clic. Pulsa «Guardar borrador» del curso.

Evaluación, desde la cuenta T1:
l. Abre «Evaluaciones»; después pulsa «Crear evaluación».
m. Escribe EVALUACIÓN en «Título» y sus instrucciones en «Descripción e
   instrucciones», en dos turnos.
n. Escribe el ID REAL de CURSO en «ID del curso». El agente lo suministra desde
   B.2.m. Deja «ID del material» vacío; no inventes un ID ni una vinculación
   automática a la estructura. El alumnado la abrirá desde «Evaluaciones».
o. Ajusta «Máximo de intentos» a 2, «Puntuación mínima (%)» a 60,
   «Modo de calificación» a «Calificación manual», un control cada vez.
   «Límite de tiempo en minutos» vacío significa sin límite; no escribas 0.
p. Pulsa «Añadir pregunta» si todavía no hay ninguna. Dentro de «Pregunta 1»,
   elige «Opción múltiple» en «Tipo de pregunta», escribe P1 en «Texto de la
   pregunta», y 5 en «Puntos de la pregunta», cada acción en un turno.
q. Dentro de P1, rellena «Valor de opción 1» A y «Texto de opción 1» `7/10`;
   opción 2 B / `4/10`; opción 3 C / `Son iguales`. «Añadir opción» crea una fila
   cuando haga falta. Selecciona «7/10» en «Clave de respuesta» (valor A guardado). No pegues JSON.
r. Pulsa «Añadir pregunta» para P2. Elige «Respuesta corta», rellena «Texto de
   la pregunta» con P2 y «Puntos de la pregunta» con 5, por separado. Si aparece
   «Clave de respuesta» para la pregunta abierta, usa su referencia docente.
s. En «Rúbrica», rellena «Nombre de la rúbrica» y «Descripción de la rúbrica».
   Usa «Añadir criterio» para crear los tres criterios; rellena cada «Nombre
   del criterio N», «Descripción del criterio N» y «Puntos máximos del criterio N»
   en turnos distintos (2, 2 y 1). La rúbrica no va dentro del enunciado alumno.
t. Pulsa «Guardar borrador». Esperado: borrador guardado; todavía no publicada.

#### B.4. Política, revisión y publicación explícitas

a. En el editor de evaluación, elige «Ayuda de IA desactivada» en
   «Ayuda de IA durante un intento activo».
b. Pulsa «Guardar política de ayuda». Esperado: «Política de ayuda guardada y
   confirmada.». Si solo se guardó el borrador, la política NO está confirmada.
c. Pide revisar la definición visible de P1/P2, claves y rúbrica. Una
   observación por turno; corrige cada campo separado si hace falta y vuelve
   a guardar lo afectado. Las evaluaciones no tienen botón «Marcar revisado».
d. Pulsa «Publicar evaluación». Esperado: confirmación de publicar preguntas,
   reglas y política. Luego pulsa «Publicar evaluación» en el diálogo, en
   otro mensaje. Esperado: «Publicada».
e. Abre CURSO y revisa sus materiales guardados. En «Revisión y publicación»,
   pulsa «Marcar revisado». Esperado: «Revisado» y revisión registrada.
f. Pulsa «Publicar curso». Esperado: «¿Publicar este curso revisado?».
g. Mantén «Hacer público el curso» DESMARCADO. Verifica ese estado antes de
   confirmar, para que Bruno no gane acceso público.
h. Pulsa «Publicar curso» del diálogo. Esperado: «Publicado» y posibilidad de
   asignar. Guardar borrador, revisar, publicar y asignar son acciones distintas.

#### B.5. Asignar solo a Alba y mantener la versión

a. En CURSO, marca la casilla de Alba dentro de «Estudiantes», contrastando
   nombre, @usuario e ID. Bruno debe quedar sin seleccionar.
b. Pulsa «Asignar curso». Esperado: diálogo «¿Asignar esta versión publicada?»
   con solo el ID de Alba.
c. Confirma «Asignar curso». Esperado: asignados 1 / ya asignados 0 en la primera
   ejecución (o resultado real si se reanuda). No repitas para cambiar el contador.
d. Comprueba el aviso «Los cursos asignados son de solo lectura. Crea una
   revisión para cambiar las lecciones o el orden.» La evaluación publicada
   ligada al curso tampoco se debe modificar silenciosamente.
e. Caso de copia D4: si decidimos ejecutarlo, pulsa «Crear revisión», comprueba
   «¿Crear una revisión independiente en borrador?» y, en otro turno, confirma
   «Crear copia en borrador». Esperado: nuevo ID/borrador; CURSO asignado
   permanece igual. No publiques ni reasignes automáticamente esa copia.

### C. Elegir IA opcional desde la GUI

#### C.1. Una elección, cuando haga falta

Pregunta solo ahora: «¿Quieres probar un modelo local que ya tengas funcionando,
o seguimos sin IA?». Si elige sin IA, registra inferencia NOT RUN y continúa.
No retrases lectura, notas, Q&A manual, ayuda al docente ni evaluación por ello.

#### C.2. Modelo ya disponible, sin imponer otro

Si elige IA local, pide proveedor/modelo ya existente y destino local válido
que quiere usar, sin claves. La UI admite Ollama, LM Studio, OpenAI y OpenRouter;
esta sesión usa local salvo otra autorización específica. No adivines puerto
ni ID de modelo, no descargues nada ni detengas el servicio que usa otra app.
Compatibilidad del protocolo no garantiza compatibilidad o exactitud del modelo.

#### C.3. Ajustes de LA cuenta que hará la petición

CAMBIAR CUENTA a Alba antes de sus pruebas. Abre «Cuenta y ajustes», luego
«Proveedor y modelo de IA», un turno cada uno. Esperado: «Estos ajustes
pertenecen a tu cuenta. No configuran a otros usuarios.».
- Elige el proveedor aprobado en «Proveedor».
- Escribe el nombre exacto elegido en «Nombre del modelo».
- En «URL del endpoint», usa únicamente el destino confirmado, o deja vacío
  si se ha elegido expresamente su valor predeterminado. No inventes una URL.
- No introduzcas ni pidas «Nueva clave API del proveedor» en chat. Cambiar de
  proveedor/endpoint elimina una clave guardada al guardar salvo nueva entrada;
  si aparece ese caso, explica el efecto y pausa para decisión/handoff seguro.
  No expandas acceso persistente sin la confirmación exigida.
Cada viñeta es un mensaje separado. No alteres parámetros restantes por intuición.

#### C.4. Guardar y probar una vez

a. Pulsa «Guardar cambios». Esperado: «Configuración de IA guardada.».
b. Explica que «Probar conexión» envía una petición pequeña y no guarda ajustes.
   Pide pulsarlo solo tras la elección autorizada de probar el modelo.
c. Registra proveedor/modelo y resultado visible. Una conexión exitosa NO
   acredita enseñanza útil ni funcionamiento en otras cuentas. No cargues
   catálogo ni pruebes endpoints automáticamente para buscar otra opción.

#### C.5. Fallo o ausencia de proveedor

Conserva el error visible; pregunta si seguimos sin IA o si quiere un único
reintento con motivo identificado. Sin proveedor disponible, sigue con datos
manuales y marca los subcasos dependientes NOT RUN/BLOCKED. No sustituya una
respuesta real por texto tuyo, mocks o resultados viejos. Cloud/nuevas claves
requieren autorización aparte; no abras una campaña de selección de modelos.

### D. Alumna autónoma, práctica, ayuda y continuidad

#### D.1. Leer, anotar, pausar y continuar

a. Si C no dejó a Alba conectada, CAMBIAR CUENTA a Alba. Abre «Mis cursos».
   Esperado: CURSO asignado; T1 no necesita una sesión abierta.
b. Abre el título de CURSO, después `Partes iguales`, en dos mensajes.
   Esperado: lectura de material; todavía no es una sesión activa.
c. Pulsa «Empezar a estudiar». Esperado: «Activa» e identificador de sesión.
d. Pulsa «Notas y anotaciones». Esperado: «Mis notas de la sesión».
e. Escribe NOTA en ese campo. Esperado: texto y aviso de cambios/borrador local.
f. Pulsa «Guardar notas». Esperado: «Notas guardadas en el servidor.».
g. Pulsa «Volver a la lectura», luego «Notas y anotaciones», en dos turnos.
   La nota se conserva al ocultar/mostrar la herramienta.
h. Pulsa «Guardar y pausar». Esperado: regreso al curso, material sin completar.
   Pausar guarda las notas, deja la sesión Activa y NO para su reloj; el tiempo
   incluye la ausencia. No lo interpretes como medida de aprendizaje.
i. Pulsa «Continuar aprendiendo: Partes iguales». Si estás en la vista de
   material en lugar del curso, el botón es «Continuar sesión».
j. Abre «Notas y anotaciones». Esperado: misma sesión y NOTA guardada.
   Registra identidad/estado; no marques persistencia solo porque se ve texto.

#### D.2. Anterior, completar, práctica correcta/incorrecta

a. En L1, pulsa «Completar y continuar». Esperado: «¿Completar esta sesión?».
b. Mantén «No añadir valoración» en «Confianza que sientes (opcional)», salvo
   otra elección. Pulsa «Completar sesión» del diálogo en su propio turno.
   Esperado: progreso confirmado y vista de L2. No da una nota ni inicia la
   sesión siguiente automáticamente.
c. En L2, pulsa «Empezar a estudiar». Después «Material anterior», en otro
   turno. Esperado: L1; L2 NO se completa por volver atrás. Reabre L2 desde
   «Volver al curso» y continúa su sesión, un control por mensaje.
d. Completa L2 y L3 con el mismo patrón de confirmación. Si aparece
   «La finalización de la sesión está confirmada. El progreso del curso sigue
   pendiente.», registra guardado parcial y usa la recuperación indicada, no
   otra sesión nueva para duplicar progreso.
e. Abre PR1 desde CURSO y pulsa «Empezar a estudiar». En «Práctica
   independiente», pide elegir una opción y después «Comprobar mi respuesta».
   Usa el primer ejercicio para una respuesta correcta y PR2 para una
   incorrecta deliberada, explicando que esta segunda es una prueba de feedback.
   No muestres la clave de evaluación formal; la práctica sí explica su solución.
f. Comprueba el feedback visible y la explicación. La práctica es
   autocomprobación, no una calificación formal ni prueba de dominio.
   Si se oculta el panel/herramienta, la respuesta debe seguir ahí al volver.
   Registra separado su borrador local y el progreso al completar la sesión.
   Deja PR2 activa, con la respuesta de recuperación confirmada, para observar
   curso e intento simultáneos en E.1.d; no declares esa práctica completada.

#### D.3. Pedir ayuda y seguir estudiando

a. Alba: abre «Solicitudes de ayuda», luego «Escribir solicitud de ayuda».
b. Escribe AYUDA.asunto en «Asunto».
c. Escribe AYUDA.descripción en «¿Qué has intentado y dónde te has atascado?».
d. Deja «Normal · 1» en «Prioridad» salvo que la pantalla muestre otro valor.
e. Pulsa «Enviar solicitud de ayuda» una vez. Esperado: «La solicitud <id> está
   guardada y abierta. No se garantiza una respuesta inmediata.».
f. Abre «Mis cursos» y una lección. Esperado: puede seguir leyendo sin respuesta
   inmediata. No confundas solicitud «Resuelta» con respuesta en «Mensajes».

Cuando luego entremos como T1 en E.4, dosifica también este recorrido:
- «Solicitudes de ayuda» → abrir la solicitud de Alba por ID/asunto.
- Escribir RESPUESTA DOCENTE en «Mensaje de respuesta».
- «Enviar mensaje de respuesta». Esperado: enviado, solicitud sigue abierta.
- «Resolver solicitud». Esperado: diálogo que advierte que resolver NO envía
  un mensaje. Confirma «Resolver solicitud» en otro turno; queda «Resuelta».
Cada flecha/campo/clic es un turno. Un borrador de IA, si lo hubiera, nunca
se manda ni resuelve solo. Alba leerá la respuesta en «Mensajes» → «Recibidos».

#### D.4. Tutor contextual, historia completada y pendiente (G2)

Solo ejecuta inferencia si C la autorizó y funciona para Alba; navegación y
texto sin enviar se pueden comprobar sin proveedor. El tutor dentro del aula
(«Ayuda») y «Tutor y preguntas» son superficies distintas: no atribuyas la
prueba de una a la otra.

a. Guarda primero las notas. Abre «Tutor y preguntas». Esperado: botones
   «Conversación con el tutor» y «Mis preguntas».
b. Abre «Curso y material de contexto opcionales». En otro turno elige CURSO
   en «Curso» y, en otro, L1 en «Material». Esperado: «Fuente actual: Partes
   iguales». No escribas IDs/URLs a mano para llegar.
c. Abre «Detalles de la fuente» y comprueba fuente/versión y cobertura que
   realmente se muestran. «Secciones de la fuente» admite hasta 12; ninguna
   marcada usa selección automática limitada. No presupongas fuente completa.
d. En «¿En qué necesitas ayuda?» escribe `En 3/8, ¿qué significa el 8?
   Explícalo con un ejemplo corto.`. Elige «Explicación» en «Tipo de apoyo» en
   otro turno, si la política lo permite.
e. Pulsa «Preguntar al tutor» UNA vez. Esperado: «Preparando una sugerencia…»
   o resultado/error real. No repitas el clic mientras espera.
f. Tras respuesta completada, lee «Sugerencia de IA sin verificar. Contrástala
   con el material y con tu propio trabajo.». Pregunta si la explicación es
   comprensible. Un error seguro es manejo de fallo, no ayuda educativa útil.
g. Pulsa «Mis preguntas». Esperado: editor de preguntas, sin borrar la
   conversación. Después pulsa «Conversación con el tutor»: debe reaparecer
   la respuesta completada. No recargues ni salgas de esta página en medio.
h. Para la segunda petición autorizada, escribe `¿Y qué indica el 3 del mismo
   ejemplo?` y después pulsa «Preguntar al tutor». Cambia a «Mis preguntas»
   mientras está «Preparando una sugerencia…» y vuelve, cada clic en su turno.
   La MISMA petición puede acabar oculta; al volver no se pierde ni se duplica.
   Abre «Política de ayuda, uso y recibo» para anotar estado/identificador
   visible, sin tokens. Si terminó demasiado pronto, el caso PENDIENTE queda
   NOT RUN; no repitas inferencias en bucle para forzarlo.
i. Cambiar material/secciones/fuente es distinto de cambiar panel: invalida
   contexto anterior y conserva la pregunta escrita. Prueba sin enviar otra
   llamada: escribe `Pregunta aún no enviada`, elige L2 en «Material» y comprueba
   que cambia la fuente y se conserva el texto. No exijas que sobreviva la
   historia del contexto anterior.

#### D.5. Tutor libre y preguntas nuevas/existentes (G1)

Tutor libre, si hay IA autorizada: en «Curso y material de contexto opcionales»,
elige «Sin curso» y luego «Sin material», en turnos distintos. Esperado: «Sin
fuente seleccionada. El contexto lo aportan tu pregunta y la conversación
reciente.». Escribe `¿Qué diferencia hay entre numerador y denominador?` y
pulsa «Preguntar al tutor» en otro turno. Repite la ida/vuelta de D.4.g; conserva
la respuesta. Docente ausente no es un bloqueo. Caso pendiente libre: mismo
patrón D.4.h solo si el usuario elige ejecutarlo; si no, NOT RUN específico.

Q&A manual se prueba incluso sin IA, como Alba, en esta misma página:
a. Pulsa «Mis preguntas». Si aparece un editor vacío nuevo, úsalo; si hay otra
   pregunta seleccionada, pulsa «Nueva pregunta» y resuelve cualquier aviso
   sin descartar trabajo no acordado.
b. Escribe `Unidad | m0710a` en «Título de la pregunta».
c. Escribe `¿Por qué importa usar la misma unidad?` en «Mi pregunta».
d. Escribe `Porque el tamaño del todo cambia la cantidad.` en
   «Respuesta para guardar (opcional)».
e. Marca «Compartir esta pregunta con mi docente». Esto todavía no guarda,
   no manda un mensaje y no convierte al docente en autor.
f. Sin pulsar Guardar, pulsa «Conversación con el tutor». Después vuelve a
   «Mis preguntas». Comprueba los cuatro valores uno a uno, incluida casilla.
   Deben conservarse. No debe aparecer una nueva confirmación de guardado.
g. Pulsa «Guardar pregunta». Esperado: «Se confirmaron la entrada guardada y
   su contenido.» y «Pregunta guardada n.º <id>». Anota el ID real.
h. Abre esa pregunta guardada por su título. Modifica «Título de la pregunta»
   a `Unidad editada | m0710a`, «Mi pregunta» a `¿Influye el tamaño del todo?`,
   «Respuesta para guardar (opcional)» a `Sí, compara una unidad equivalente.`,
   y desmarca compartir, UN cambio por turno.
i. Sin guardar, cambia a «Conversación con el tutor» y vuelve a «Mis preguntas».
   Comprueba los cuatro cambios. Este es el caso EXISTENTE, distinto del nuevo.
j. Pulsa «Nueva pregunta» sin guardar. Esperado: «¿Salir de esta pregunta?».
   Pulsa «Cancelar» en otro turno: debe conservar todo. No confundas elegir
   otra pregunta con cambiar entre los dos paneles.
k. Pulsa «Guardar pregunta» para conservar la edición privada. Esperado:
   confirmación. Si luego queremos revisar acceso del docente, vuelve a marcar
   compartir y guarda explícitamente en dos turnos distintos.
l. Solo con IA autorizada: «Pedir una sugerencia a la IA» presenta una propuesta
   separada. Puede terminar mientras ese panel está oculto; al volver no debe
   reemplazar automáticamente «Respuesta para guardar (opcional)». Para usarla,
   elige «Usar la sugerencia en la respuesta», confirma «Usar la sugerencia en la respuesta» si aparece
   el diálogo y revisa antes de «Guardar pregunta», todos pasos separados.
   Si se omite, registra sugerencia Q&A NOT RUN, sin afectar la prueba manual.

La conservación G1/G2 es memoria de la página abierta. No promete recuperación
permanente tras recargar, cerrar, salir de `/tutor` o cambiar de cuenta.

#### D.6. Cancelación, errores y reautenticación sin inventar un simulador

- Con una petición realmente pendiente autorizada, pulsa «Cancelar solicitud
  de IA». Esperado si se confirma: «Cancelación local confirmada. El proveedor
  puede continuar y podrían aplicarse cargos.». Conserva la pregunta; una salida
  tardía no debe aparecer como una respuesta nueva. Si ya terminó, registra
  esa carrera real, no una cancelación ficticia. No detengas el proveedor.
- Si aparece resultado incierto, el texto se conserva y no se reenvía solo.
  Primero «Actualizar estado» dentro de «Política de ayuda, uso y recibo».
  Después pregunta si quiere «Reintentar la misma solicitud» (mismo ID/entrada
  originales) o continuar sin IA. «Preparar otra solicitud» advierte de trabajo
  anterior/coste adicional y requiere su confirmación; no es el mismo reintento.
- No hay un botón GUI para producir 401, 403, 422 remoto, fuente tardía,
  política revocada, guardado incierto o fallo de proveedor. Si no ocurre
  naturalmente ni existe un entorno sintético aislado autorizado preparado,
  registra esos subcasos NOT RUN. No manipules tokens, bases, red o permisos
  reales, ni repitas un sondeo previamente denegado para fabricarlos.
- Si la sesión se bloquea naturalmente, espera «Vuelve a entrar». El texto
  privado debe estar oculto. Guía «Usuario»/«Contraseña»/«Entrar» en turnos
  distintos para LA MISMA cuenta; tras validar permiso, el editor Q&A y la
  pregunta no enviada pueden recuperarse sin reenviar nada.
- Un bloqueo real borra la historia COMPLETADA del tutor en la implementación
  actual; NO la exijas como PASS de reauth. Cambiar solo entre paneles sí debe
  conservarla. Si se entra con otra cuenta, el texto oculto anterior no aparece.
- Revocación de acceso a una pregunta oculta debe impedir mostrarla tras
  reauth; este 403 requiere una fixture específica. No hay un control inocuo
  que convierta la pregunta propia en ajena. Se conserva como aceptación
  pendiente si no está preparado, aunque su regresión DOM pase.

#### D.7. Qué basta y cuándo parar esta parte

No necesitas otro modelo ni respuestas perfectas. Registra utilidad observada,
avisos, errores y límites reales de la inferencia elegida. Completado/pending/
cancelado/cambio de contexto son resultados separados. Si falta fixture o el
usuario prefiere seguir, guarda NOT RUN/SKIPPED BY USER y continúa E; no conviertas
el recorrido en una campaña de robustez. Los resultados automáticos previos
no sustituyen estas observaciones ni suponen aceptación total.

Antes de salir de D, comprueba si queda «Pregunta aún no enviada» u otro texto
sin guardar en Conversación. Guardar Q&A no guarda ni limpia ese campo. Si
David quiere conservarlo, pídale copiar solo ese texto sintético localmente;
si decide descartarlo al continuar, el diálogo «¿Salir con cambios sin guardar?»
se confirma con «Descartar cambios y salir», en otro turno. «Cancelar» permite
quedarse. Este aviso esperado no es un fallo ni una promesa de guardar historia.

### E. Evaluación, límites de ayuda y revisión docente

#### E.1. Previa, inicio y política

a. Alba: abre «Evaluaciones», localiza EVALUACIÓN y pulsa «Abrir evaluación».
   Esperado: instrucciones, intentos y «Ayuda de IA desactivada». Consultar
   esta ficha NO reserva un intento ni muestra claves docentes.
b. Pulsa «Comenzar evaluación». Esperado: «¿Comenzar esta evaluación?».
c. Pulsa «Iniciar intento». Esperado: intento abierto, contador reservado.
   Salir de esta pantalla no pausa un temporizador configurado.
d. Con el intento abierto, ve a «Inicio». Esperado: secciones distintas
   «Continuar curso» (enlace «Continuar: <material>») y «Reanudar evaluación»
   (enlace «Reanudar <evaluación>») cuando exista también sesión de estudio
   activa. Usa en cada enlace el título real del recurso. Registra NOT RUN de coexistencia si ya completaste todas
   las sesiones; no declares esa variante observada por ver una sola tarjeta.
e. Abre «Tutor y preguntas». En «Política de ayuda, uso y recibo» debe verse
   «La ayuda de IA está desactivada durante tu intento de evaluación abierto.».
   No debe poder enviar una consulta libre ni contextual para saltarla.
   Comprueba también «Mis preguntas»/«Pedir una sugerencia a la IA»; editar una
   pregunta manual no significa obtener asistencia de IA.
f. Vuelve a «Evaluaciones», abre EVALUACIÓN y pulsa «Reanudar intento», cada
   control en un turno. Debe ser el MISMO intento, no reservar otro.

#### E.2. Responder, revisar y enviar una vez

a. Pide elegir una opción de P1, sin mostrarle ahora la clave docente.
b. En «Respuesta a la pregunta 2», pide escribir su explicación ficticia
   NO vacía. No le dictes la referencia docente como si fuera su respuesta.
c. Pulsa «Revisar respuestas». Esperado: revisión y contador sin responder.
d. Si hay que corregir algo, «Volver a las respuestas» y un campo por turno.
e. Pulsa «Enviar respuestas». Esperado: «¿Enviar este intento?»; las respuestas
   no se podrán editar después y las omitidas reciben cero.
f. Confirma «Enviar respuestas» en el diálogo. Esperado: «Envío recibido» y
   resultado, o resultado directamente. Si aparece «Ver comentarios», úsalo
   como paso separado. No envíes otra vez porque tarde en refrescar.

#### E.3. Provisional/final y variante de cierre sin envío

Comprueba «Pendiente de revisión docente» y «Aún no hay calificación final»
para P2 manual contestada. La objetiva puede estar puntuada automáticamente.
Si se eligió aparte IA para calificar, una sugerencia subjetiva sigue siendo
provisional hasta aprobación docente; ausencia/error del proveedor no da una
nota final cero por sí sola. El modo manual no obliga a invocar IA.

Segundo intento SOLO si David elige probar «Cerrar intento sin enviar» y aún
hay intento disponible: inicia desde la ficha, escribe una respuesta sintética,
pulsa «Cerrar intento sin enviar», lee que consume el intento y no se reanuda,
y confirma con ese mismo botón en otro turno. Esperado: «Intento cerrado» /
«Cerrado sin envío», sin nota ni recompensa por ese cierre. No uses este botón
como envío normal. Si no se hace, E6.cierre queda NOT RUN.

#### E.4. Docente: corregir la entrega y responder ayuda

a. CAMBIAR CUENTA a T1. Abre «Correcciones». Esperado: filtro
   «Pendientes de revisión» en «Filtrar envíos».
b. Abre el envío de Alba identificando nombre/curso/evaluación e ID. Si no
   está, pulsa «Actualizar estado del servidor» una vez y comprueba filtro;
   no inventes otra entrega.
c. En «Calificar pregunta 2», lee «Respuesta del estudiante» y contrástala con la rúbrica que
   registramos en B.3; no exijas que el corrector muestre un editor de rúbrica.
   Acordamos su puntuación real según lo escrito, 0–5; no igualar una sugerencia
   automáticamente. El cero es válido si corresponde a esa respuesta.
d. Introduce esa nota en «Puntuación» de P2.
e. Introduce un comentario breve y específico en «Comentarios (opcionales)».
f. Pulsa «Guardar calificación de pregunta». Si completa las notas restantes,
   debe avisar que finaliza inmediatamente. En el diálogo, el botón de
   confirmación es «Guardar», NO «Finalizar».
g. Confirma «Guardar» en otro turno. Esperado: «Calificación guardada. Se ha
   actualizado el estado del servidor.» y «Calificación final». Si quedan
   preguntas sin calificar, repite c–g solo para ellas.
h. «Finalizar calificación total» es una vía ALTERNATIVA, no un paso obligatorio
   tras puntuar: guarda total inmediatamente y puede dejar puntuaciones de
   preguntas sin cambiar. «Usar sugerencia de IA» solo rellena; «Aprobar todas
   las sugerencias de IA» solo aparece en su estado correspondiente y requiere
   revisión/confirmación propias. No exijas esos controles en modo manual.
i. Pulsa «Volver a correcciones». Cambia «Filtrar envíos» a «Calificaciones
   finales» y comprueba el envío. Registra retorno/filtro por separado.
j. Completa la respuesta/resolución de ayuda descrita en D.3, un paso por turno.
   En «Tutor y preguntas» → «Preguntas compartidas del alumnado», abre la
   pregunta de Alba si quedó compartida. Esperado: lectura, sin «Guardar
   pregunta» ni transferencia de autoría. No intentes editarla por otra vía.

#### E.5. Alumna: feedback, historial y liberación de ayuda

a. CAMBIAR CUENTA a Alba. Abre «Evaluaciones», luego «Mis envíos y comentarios»,
   después el envío de EVALUACIÓN, cada uno en su turno.
b. Comprueba nota final, «Tu respuesta» y el texto del comentario guardado
   para P2. El encabezado «Comentarios» solo aparece si hay comentario global
   del envío; no lo exijas para el comentario de una pregunta. Abrir/actualizar
   feedback NO debe reservar otro intento. Cero, sin nota y provisional son
   estados distintos; no los traduzcas todos como aprobado/suspenso.
c. Abre «Tutor y preguntas» → «Política de ayuda, uso y recibo».
   Tras enviar/cerrar TODOS los intentos abiertos debe volver la política
   permitida; una nota pendiente no equivale a intento abierto. No necesita
   ejecutar otra inferencia para comprobar el aviso.
d. Abre «Mensajes» → «Recibidos» y el asunto de ayuda para leer la respuesta
   de T1. «Resuelta» en solicitudes y mensaje recibido son evidencias distintas.

### F. Privacidad, presentación actual y cierre conservando datos

#### F.1. Bruno no hereda acceso; biblioteca por rol

a. CAMBIAR CUENTA a Bruno. Abre «Mis cursos». CURSO privado no debe aparecer.
   Abre «Evaluaciones»: no debe ver el examen ligado a ese curso ajeno.
b. Abre «Tutor y preguntas» → «Mis preguntas»: no aparecen preguntas privadas
   de Alba, borradores, notas o sus respuestas. No exige un docente conectado
   para escribir su propia pregunta sin enviar.
c. «Mis cursos» → «Biblioteca de materiales»: lectura solo autorizada; no
   «Crear material», «Generar con IA» ni controles de edición del personal.
   No afirmes seguridad completa solo por ausencia de enlaces.
d. Si David acepta comprobar el enlace real de CURSO ya obtenido en B.2,
   ábrelo bajo Bruno en el mismo origen (sin inventar IDs). Esperado: recurso
   no disponible/permiso denegado, sin contenido privado. Es un caso GUI
   delimitado, no una campaña de ataques. Una filtración detiene el tramo.
e. Admin: comprueba una vez «Cursos y materiales» → «Biblioteca de materiales»
   → «Crear material», vuelve y abre «Generar con IA». Llegar al formulario no
   inicia generación. No debe requerir crear un curso artificial. Cada enlace
   se guía en un turno. Vuelve a Alba después, sin guardar borradores vacíos.

#### F.2. Exportación de lectura, distinta de paquete/backup

a. Alba: abre CURSO y pulsa «Exportar curso». Esperado: «Mover o exportar datos».
b. En «Propósito», elige «Copia de lectura»; en otro turno verifica CURSO en
   «Curso» y selecciona «Copia HTML de lectura» en «Formato del archivo».
c. Pulsa «Revisar vista previa». Esperado: destinatario estudiante, inclusiones
   y exclusiones; no soluciones/rúbricas privadas, trabajos o credenciales.
d. Pulsa «Descargar exportación seleccionada». Esperado: «¿Descargar esta
   exportación?». Confirma «Descargar exportación seleccionada» en el diálogo, en otro turno.
e. Abre el archivo recién descargado. Esperado: copia legible, sin claves de
   evaluación ni secretos. No lo subas ni compartas por el hecho de exportarlo.
   Un paquete docente JSON contiene soluciones y no sustituye esta copia.

Admin puede revisar «Copias de seguridad» → «Revisar alcance de la copia» y
«Guía de restauración» como comprobación de lectura separada. No descargues
ni restaures una base real para completar A3: el backup contiene datos privados,
no incluye clave original y no es una imagen completa de instalación. Restaurar
es una preparación técnica independiente, a archivo NUEVO, nunca una falsa
acción web «Restaurar» ni sobrescritura de la base en uso.

#### F.3. Tres tipos de ausencia y service worker (SW)

Registra por separado: docente desconectado; proveedor IA indisponible; servidor
SLMEducator detenido. Lectura/notas necesitan servidor aunque no haya docente
ni IA. HTML exportado se lee por separado. Una pantalla ya pintada no prueba
aplicación offline; no desconectes la red ni cambies firewall para fingirlo.

Candidato React NUEVO: no registra un service worker runtime. No promete
caché offline de API/inferencia. El agente puede inspeccionar de forma permitida
el estado de registro en un perfil sintético y anotar evidencia técnica; David
no tiene que escribir scripts en DevTools.

Migración SW solo si existe un perfil de prueba aislado PREPARADO con el worker
v22 y autorización vigente. Un perfil nuevo no prueba actualización. Sigue
`tests/browser/test_service_worker_update.py` / `docs/BROWSER_TEST.md` como
contrato de la observación, nunca ejecutes aquí un navegador previamente denegado:
1. Mantén una pestaña de prueba con texto sintético sin guardar y otra controlada.
2. Abre la entrada React en la otra pestaña: el trabajo de la primera no se
   recarga/destruye; cerrar solo la segunda no activa todavía la retirada.
3. Guarda/copia localmente el trabajo antes de cerrar la última pestaña antigua.
4. Reabre el mismo origen después de activación normal. Comprobación técnica:
   sin worker registrado; solo se retiran los dos caches conocidos
   `slm-educator-v22-session-locale` y
   `slm-educator-v22-session-locale-auth-validation`; los demás caches y borradores
   se conservan. No fuerces `skipWaiting`, unregister, recarga destructiva ni
   «borrar todos los datos del sitio».
Cada acción humana es un turno. Sin fixture o acceso permitido: SW migración
NOT RUN/BLOCKED. Fallo de red durante transición es otra variante pendiente,
no se deduce del caso correcto. No instales código antiguo en mi perfil real.

#### F.4. Idioma, teclado, movimiento guardado, 320 CSS px y zoom real

Haz cada subcaso en una pantalla guardada, sin tirar trabajo. No conviertas una
preferencia visual en prueba de accesibilidad completa.

a. En la cabecera web, «Idioma» → «English»: observa etiquetas/errores de una
   pantalla; vuelve a «Español» en otro turno. El contenido escrito por nosotros
   no se traduce automáticamente. Si una etiqueta no coincide, registra cuál.
b. En «Apariencia» de la cabecera, elige «Oscuro», luego «Claro», luego
   «Sistema», una elección por turno. Observa contraste, foco y campos; registra
   el tema que el usuario desea conservar al terminar.
c. Usa Tab, Mayús+Tab, Enter y Escape en acciones separadas en alta/editor,
   estudio, evaluación, correcciones y diálogo: foco visible, orden entendible,
   cierre y regreso del foco al control que abrió el diálogo. «Saltar al
   contenido principal» permite evitar el menú. Lector de pantalla solo se
   marca PASS si se ha usado realmente y se registra lector/versión; no por
   atributos ARIA existentes en fuente.
d. Caso G5: «Cuenta y ajustes» → «Apariencia e idioma», por turnos; desmarca
   «Activar animaciones de la interfaz»; pulsa «Guardar cambios». Esperado:
   «Apariencia e idioma guardados.».
e. Abre «Inicio» y recarga esa página guardada. Tras acceso si hace falta,
   el movimiento reducido de la cuenta debe aplicarse SIN visitar Ajustes ni
   guardar otra vez. El agente puede comprobar en lectura `data-motion=reduced`
   y estilos si la herramienta lo permite; si visualmente no hay movimiento
   identificable, no inventes evidencia. Volver a Ajustes confirma el valor,
   pero no demuestra por sí solo que se aplicó al reabrir.
f. Otra cuenta no hereda la preferencia de la anterior. Respeta la reducción
   de movimiento del sistema incluso con casilla activada. Lectura malformada,
   fallida o tardía de otra cuenta requiere fixture; sin ella, NOT RUN específico.
g. Zoom nativo: desde 100%, pide abrir el menú DE SU NAVEGADOR y usar su control
   real de zoom hasta 200%, un clic por turno con confirmación del porcentaje.
   No adivines nombre/icono del navegador: identifícalo primero. Observa menú,
   texto, formularios, tablas/código, acciones y foco. Repite a 400%. Captura
   porcentaje real y pantalla. Cambiar «Tamaño del texto de lectura», CSS zoom,
   escala de Windows o ampliar una captura NO sustituye este caso.
h. Restablece zoom nativo a 100%. Caso distinto: viewport de 320 PÍXELES CSS,
   medido como anchura interior, con el modo responsive permitido del navegador
   si está disponible. El agente prepara/mide; al usuario le pide solo la
   siguiente acción GUI identificada. Comprueba «Abrir navegación», reflujo,
   campos/textos largos y panel auxiliar sin acciones perdidas. Si no puede
   medirse, NOT RUN; 390 px o ancho físico de pantalla no equivale a 320 CSS px.
i. Si falta tiempo o David para, deja los subcasos pendientes. Un test DOM,
   captura redimensionada o colección de pytest no acredita zoom/lector real.
   Restaura únicamente el zoom/modo de prueba que hayamos cambiado.

#### F.5. Terminar o pausar, conservando instalación y trabajo

Pregunta si quiere dejar guardado el trabajo antes de salir; guía cada guardado
necesario por separado. Usa CAMBIAR CUENTA solo hasta cerrar sesión, conservando
borradores si esa es su elección. No desinstales, elimines cuentas/archivos,
reinicies otra vez la X ni limpies datos automáticamente.

Si dice «para», detén nuevas acciones de inmediato y guarda el punto alcanzado.
No pidas veinte datos finales. Conserva misma instalación y el informe parcial.
Al reanudar, confirma identidad, cuenta/origen y lo que realmente sigue abierto;
texto que solo estaba en memoria puede haberse perdido al cerrar y se registra
como tal, no se restaura inventado. No repitas pasos aprobados del mismo artefacto
salvo cambio relevante o petición expresa.

## Registro de evidencia y cobertura: para el agente, no para recitármelo

Mantén un único informe local de sesión bajo una carpeta nueva
`implementation_documents/manual_windows_<fecha>_<build>/`, junto al handoff
actual, con estados por subpaso. No edites el informe del binario viejo.

Campos mínimos del registro:
- Sesión/fecha; Setup, versión/build, SHA-256, SHA/árbol, dist; entorno Windows,
  navegador/versión, idioma, perfil de prueba y origen/puerto realmente usados.
- Último subpaso confirmado y siguiente acción EXACTA; rol/usuario sintético,
  IDs de cuentas/curso/material/entrega, página actual y textos sintéticos sin
  guardar que el usuario haya pedido conservar (jamás secretos).
- Acción/dato; resultado esperado; respuesta literal breve del usuario o
  observación autorizada; estado; captura saneada o referencia de evidencia.
  Separar HUMANO, COMPROBACIÓN TÉCNICA y AUTOMATIZADO HISTÓRICO.
- PASS = esperado observado para ese subcaso y candidato. FAIL = discrepancia
  observada. BLOCKED = requisito/acceso impide hacerlo. NOT RUN = sin ejecutar.
  SKIPPED BY USER = decisión expresa. PARCIAL = faltan subcasos, nunca PASS total.
  Un test verde solo puede ser PASS AUTOMATIZADO de su alcance.

Matriz compacta del plan §12; todos parten pendientes en esta sesión. Marcar
cada variante por separado. «Adicional» no significa ejecutado ni autorizado a
crear fallos/modelos/seguridad por otra vía.

| Plan | Dónde se guía | Qué no deducir del recorrido básico |
|---|---|---|
| E1 | C.1–5, F.1, D.1/4/5 | Sin IA no se prueba inferencia; docente ausente ≠ servidor parado |
| E2 | E.1.d/f | Coexistencia curso + intento requiere sesión activa real |
| E3 | D.1–2 | Tres lecciones, anterior/pausa y completar; no mide dominio |
| E4 | D.6, CAMBIAR CUENTA, F.5 | 401/403, BFCache, otra pestaña y storage fallido requieren casos propios |
| E5 | E.1–2 | Tiempo/recarga/doble envío/desconexión no se probaron solo por enviar |
| E6 | E.3–5 | Cierre sin envío, cero, provisional/final se registran separados |
| E7 | D.4–7 | Libre/contextual; completada/pendiente/cancelada; fuente/política tardía con fixture |
| E8 | D.5, E.4.j, F.2 | Nueva/existente; cuatro campos; compartir no manda mensaje |
| D1 | B.1 | Correo inválido local no demuestra 422 remoto; [object Object] es FAIL |
| D2 | B.2–5 + D.1 | Corte GUI admin crea/matricula → docente publica/asigna → alumna estudia |
| D3 | B.2.b, C, adicional de generación abajo | Llegar a Generar no prueba 3/5, fallo parcial ni inferencia útil |
| D4 | B.5.e, F.2 | Revisión crea otro ID; importación requiere preview/caso aparte |
| D5 | E.4–5 | Última pregunta/total/cero/aprobar IA son variantes distintas |
| D6 | D.3, E.4.j/5.d | Enviar mensaje y resolver son acciones separadas |
| D7 | E.5.d, adicional de mensajes abajo | Leer un mensaje no prueba homónimos ni operación masiva parcial |
| A1 | A.3, B.1, adicional de cuentas abajo | No autodesactivar ni resetear contraseñas para fabricar reauth |
| A2 | B.1.n–q, adicional de matrícula abajo | Alta/matrícula inicial no acredita reasignación A→B |
| A3 | F.2, MANUAL_TEST1 §3 | Lectura, paquete docente, backup y restore no son equivalentes |
| A4 | C | Configuración propia; ningún test de fondo ni clave a nuevo destino |
| X1 | F.4.a–f | Pintado, teclado, lector y motion requieren observación propia |
| X2 | F.4.g–i | 320 CSS px, 200%, 400% separados; escala larga/rendimiento aún aparte |
| X3 | D.6, F.3 | Internet/proveedor/servidor son tres fallos distintos |
| X4 | A, F.3, MANUAL_TEST1 §3 | X/Detener, instalación, preservación y SW de nuevo candidato separados |
| G1–G5 | D.5 / D.4–6 / B.2+F.1 / B.1–2 / F.4.d–f | Ningún PASS humano procede solo de 825 DOM/249 Python/8 diagnósticos |

### Casos adicionales: solo si preparados y elegidos, sin bloquear la ruta básica

El agente propone el siguiente caso concreto al llegar a él, no una lista de
veinte decisiones iniciales. Si no hay fixture/permiso o David no quiere,
registra el subcaso pendiente y termina el informe con ese límite.

- Generación: docente → «Biblioteca de materiales» → «Generar con IA»;
  «Modo de generación» = «Lección individual», «Materia» = `Matemáticas`,
  «Tema» = `Fracciones de la misma unidad`, «Curso o nivel de aprendizaje» =
  `Personas adultas, iniciación`. Un campo por turno. Solo pulsa «Generar con IA»
  con proveedor ya autorizado. Una propuesta no se guarda sola: revisar/editor
  → «Guardar borrador». Paquetes 3/5/fallo parcial, edición humana mientras
  llega otra respuesta y «Actualizar trabajos guardados» requieren fixture
  controlada: mantener items confirmados y no sobrescribir edición. No hagas
  cinco llamadas en vivo para fabricar un resultado 3/5.
- Mensajes: «Mensajes» → «Escribir mensaje» → «Buscar contacto por nombre o
  usuario» → elegir «Destinatario» contrastando usuario/ID → «Asunto» =
  `Prueba de mensaje | m0710a` → «Mensaje» = `Mensaje ficticio de comprobación.`
  → «Enviar mensaje» → comprobar «Enviados». Cada control un turno.
  Homónimos requieren dos cuentas sintéticas preparadas. Selección masiva/fallo
  parcial es otro caso; no usar eliminar definitivamente para cubrirlo, ni
  asumir que archivar solo afecta al remitente: afecta a ambos participantes.
- Cuentas: admin → «Personas» → S2/Bruno → «Desactivar cuenta» → comprobar
  identidad/efecto → confirmar «Desactivar cuenta»; luego «Activar cuenta» y
  su confirmación, por turnos y con permiso aplicable. Revoca sesiones,
  conserva historia. Contraseña/reset, último admin/self y reauth adversarial
  no se provocan en cuentas reales ni eluden aprobación/handoff. Sin fixture
  sintética preparada, esas variantes siguen NOT RUN.
- Matrícula: solo tras crear T2 sintético y decidir probar reasignación,
  admin → ficha Alba → «Elige un docente activo» = T2 → «Guardar matrícula» →
  confirmar nombres → «Guardar matrícula». Asignaciones previas se conservan,
  T1 sigue autor de su evaluación; T2 no hereda sus notas privadas. Verificar
  cada cuenta con accesos reales; cambiar matrícula no convierte a T2 en autor.
  No reviertas sin acordarlo ni modifiques la sesión básica antes de E.
- Importación: solo archivo docente sintético preparado por su autor, privado.
  «Cuenta y ajustes» → «Mover o exportar datos» → «Propósito» = «Importar
  paquete docente» → «Archivo JSON docente» → «Validar importación». Leer el
  alcance antes de «Crear nuevo borrador» y su confirmación. Esperado: nuevo
  ID/borrador, originales/asignaciones intactos. No importar HTML de lectura
  ni usar un backup como paquete docente. Si no hay archivo, NOT RUN.
- Listas/curso largo y rendimiento: fixture sintética 1/50/500 elementos y
  curso de 100 lecciones, más mediciones reales en entorno identificado.
  No llenes la instalación del usuario por API ni declares probado <100 ms o
  inicio <2,5 s por sensación. Sin fixture/medición permitida, NOT RUN.

## Resultado y parada

Entrega un resumen corto: qué pude hacer, incidencias que bloquean, pruebas
humanas pendientes y ubicación del informe. Incluye proveedor/modelo real solo
si se usó; no cambies puntuaciones históricas ni ocultes sus fallos. Esta sesión
no certifica aprendizaje, adecuación para menores, regulación, seguridad
completa o compatibilidad universal de proveedores/hardware.

Detente después del informe o cuando yo diga que pare. No publiques, arregles,
reconstruyas, desinstales, programes más pruebas ni inicies otra auditoría.
La reanudación requiere esta misma identidad y el siguiente subpaso guardado.

FIN
