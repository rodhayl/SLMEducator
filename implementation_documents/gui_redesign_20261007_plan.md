# SLMEducator: plan de rediseño integral de GUI y flujos

**Versión de planificación:** 2026-10-07 · propuesta final tras tres rondas de revisión de diseño/código.  
**Alcance autorizado en esta entrega:** revisar y planificar. No se implementó, instaló, publicó ni sustituyó la GUI.  
**Base del producto:** [`99ebef03901871ca9c9a1c548058971ae1f7e089`](https://github.com/rodhayl/SLMEducator/tree/99ebef03901871ca9c9a1c548058971ae1f7e089), incluido el arreglo D3 de errores de registro.  
**Destino sugerido en el repositorio:** `implementation_documents/gui_redesign_20261007_plan.md`.

## 1. Recomendación

Rehacer toda la interfaz educativa con **React, TypeScript y Vite**, conservar FastAPI y el dominio educativo, y construir un sistema visual propio a partir de los tokens y patrones de AAC. La interfaz nueva tendrá rutas reales, navegación por tareas y roles, componentes compartidos, formularios coherentes y estados de guardado/error comprensibles.

El resultado final retirará los 13 HTML, 21 scripts propios, CSS y service worker legacy como implementaciones, además de Bootstrap/Sortable vendorizados. **No será una capa React alrededor del dashboard antiguo ni un cambio de colores.** Los contratos útiles de seguridad, sesiones, renderizado, borradores, progreso y errores se portarán con sus pruebas antes de retirar los archivos.

También se rediseñará la presentación del launcher Tkinter y la experiencia de acceso/arranque. Se conserva su gestión de proceso y la distribución PyInstaller/Inno Setup. No hace falta Electron, otro backend ni Node en la instalación del usuario.

### Lo que el rediseño debe resolver

- D1: menú plano y confuso → grupos con tareas reconocibles y acceso específico por rol.
- D2: alta estrecha y fuera de contexto → página integrada en Personas/Mis estudiantes, ancho fluido y resultado útil.
- D3: error ilegible → preservar el arreglo seguro y extender un único patrón de errores a toda la GUI.
- Duplicación de shell, formularios, modales, renderers, fetch y estado → una implementación por responsabilidad.
- Pantallas independientes sin continuidad suficiente → conservar contexto, filtros, navegación atrás y borradores autorizados.
- Información pedagógica y técnica mezclada → lectura prioritaria; fuentes, IA, datos operativos y métricas en el nivel adecuado.

### Restricciones del producto que se mantienen

Tres roles reales: estudiante, docente y administrador. El alumno puede estudiar material preparado y pedir ayuda best effort sin que haya un docente conectado. El tutor puede funcionar sin curso seleccionado. Crear material estructurado, publicar/asignar y convertir calificaciones subjetivas en finales mantienen sus barreras actuales. No se añaden aprobación docente para cada pregunta, perfección de contenido, un modelo obligatorio o una segunda IA.

La IA permanece configurable dentro de Ollama, LM Studio, OpenAI y OpenRouter; compatibilidad de protocolo no equivale a compatibilidad universal ni exactitud garantizada. El diseño no inicia otra campaña de selección/puntuación de modelos.

## 2. Evidencia y cobertura de la revisión

El [inventario de fuentes verificadas](gui_redesign_20261007_source_inventory.json) acompaña este plan: commit, 36 rutas, líneas, bytes y hashes de blob. La matriz de migración está incluida en el Anexo A; no requiere otros documentos relativos.

| Elemento | Cobertura comprobada | Límite |
|---|---|---|
| GUI propia | Inventario y recorrido funcional por archivo: **36/36**, 16.062 líneas, 770.178 bytes; hashes Git coincidentes con la base publicada | No equivale a aceptación visual ni auditoría de seguridad de cada línea |
| Dashboard HTML, dashboard JS, inbox JS, CSS | Lectura completa específica: **4/4**, 9.085 líneas, 402.112 bytes | Los defectos derivados son observaciones estáticas, no reproducciones de navegador |
| Resto de GUI | Lectura de páginas, módulos, entradas, estados, llamadas y contratos de sus **32 archivos**, con detalle de auth/D3, sesiones, intentos, builders, ayuda, portabilidad, renderizado y preferencias | No se contabilizan dependencias minificadas como código propio auditado |
| Backend | Inventario de **18 módulos de rutas**; contraste de roles, propiedad, matrícula, evaluación, mensajes, notas, IA, fuentes y portabilidad | Se conserva el dominio; no se declara revisión completa de todas las líneas backend |
| Entrega | `main.py`, launcher, utilidades de arranque, builder, Inno y workflows revisados | No se construyó ni ejecutó un nuevo instalador |
| Referencia AAC | Código de tokens, shell/componentes y dependencias, referencia `777c32c9b747cc6efb37a6c5758d955ae6ab9668` | Referencia de código; no se declara reproducción visual actual de AAC |
| Validación humana | **0 sesiones de usuario y 0 recorridos de navegador ejecutados en esta revisión** | Las tres rondas son iteraciones de diseño/code walkthrough, no pruebas con usuarios |

El dashboard actual tiene **13 vistas y 9 modales explícitos**, más diálogos generados. Ronda 1 contó 10; el recuento detallado lo corrigió. La navegación legacy ya tiene aliases/hash/Back; se reemplaza conservando esa intención, no se afirma que carezca por completo de historial.

La evidencia histórica del instalador conserva A.1–A.5 y B bloqueada; C–F no ejecutadas. D3 tiene su propia evidencia API/DOM (257 pruebas DOM y pruebas Python focalizadas según su informe), que **no certifica** este rediseño, todos los flujos manuales o un binario nuevo. No hace falta repetir ahora la antigua GUI antes de aprobar este plan.

Fuentes: [contratos funcionales](https://github.com/rodhayl/SLMEducator/blob/99ebef03901871ca9c9a1c548058971ae1f7e089/docs/FUNCTIONAL_REQUIREMENTS.md), [políticas de recursos](https://github.com/rodhayl/SLMEducator/blob/99ebef03901871ca9c9a1c548058971ae1f7e089/src/api/policies.py), [informe D3](https://github.com/rodhayl/SLMEducator/blob/99ebef03901871ca9c9a1c548058971ae1f7e089/implementation_documents/registration_feedback_20261007.md).

## 3. Roles, propiedad y vocabulario

| Rol | Capacidades que se conservan | Límites importantes |
|---|---|---|
| Estudiante | Cursos asignados y contenido visible autorizado; sesiones, notas/anotaciones, práctica, intentos/historial, Q&A personal y tutor libre/contextual; ayuda y mensajes; progreso/objetivos; ajustes e IA propios; lectura exportada permitida | No autoalta de personal, autoría estructurada/publicación o datos ajenos. Compartir Q&A no otorga edición al docente. Restricción IA depende del intento abierto, no de presencia docente |
| Docente | Crear estudiantes propios; gestionar su matrícula visible y progreso; notas privadas propias; cursos/materiales manuales o IA; evaluaciones de su autoría; revisión/publicación/asignación; corrección; ayuda/mensajería autorizada; portabilidad docente | Visibilidad no concede edición/republicación. No administra otras cuentas/docentes, reasigna alumnado ajeno o descarga backup de instalación |
| Administrador | Personas de los tres roles, estado/recuperación, matrícula explícita; acceso de instalación a recursos educativos y herramientas docentes; backup privado | No autodesactivar ni dejar sin último admin activo. No ve notas privadas escritas en la cuenta de otro docente. Su IA sigue siendo por cuenta, no configuración global de todos |

**Tres identidades distintas:** dueño del contenido/evaluación; docente responsable del alumno; usuario que escribe una nota privada. No deben colapsarse en un único `teacher_id` conceptual. Al reasignar A→B, los cursos/asignaciones históricos se conservan; A puede seguir corrigiendo sus evaluaciones y B no se convierte en autor de ellas. La cola de correcciones no se filtra solamente por la lista de «mis estudiantes» actual.

**Curso / plan:** usar «Curso» para el recorrido educativo y «Estructura» para fases/unidades, manteniendo `study_plan_id` y el modelo actual. Material independiente sigue existiendo. «Guardar borrador», «Marcar revisado», «Publicar», «Asignar» y «Crear revisión» son acciones diferentes. La UI no inventa un cambio de rol de cuenta porque exista selector de rol al crearla.

## 4. Arquitectura de información definitiva

### Estudiante

- **Estudiar:** Inicio · Mis cursos · Evaluaciones · Mi progreso
- **Apoyo:** Tutor y preguntas · Mensajes
- Tutor y preguntas incluye conversación IA, Mis preguntas y Mis solicitudes, con estado **Abierta / Resuelta**. Las respuestas se consultan en Mensajes; no inventar «respuesta no leída» en la API de solicitudes.
- Perfil y ajustes al pie, y salida de sesión separada.

Inicio diferencia «Continuar curso» de «Reanudar evaluación». Ambas muestran identidad del recurso. Si coinciden, el usuario elige; visitar la tarjeta no reserva un intento. El inicio no necesita seis métricas, clasificación y configuración IA para poder empezar a estudiar.

### Docente

- **Docencia:** Inicio · Cursos y materiales · Evaluaciones · Mis estudiantes
- **Atención:** Correcciones · Solicitudes de ayuda · Mensajes
- Cuenta y ajustes propios al pie.

Cursos y materiales tiene subrutas claras para cursos/materiales; la creación se sitúa en su contexto. Correcciones conserva filtro/selección/scroll; solicitudes conserva prioridad y estado. Q&A compartido aparece como contenido del alumno, con permiso de lectura explícito.

### Administrador

- **Administración:** Inicio · Personas · Copias de seguridad · Estado de la aplicación
- **Docencia:** Cursos y materiales · Evaluaciones · Correcciones · Solicitudes de ayuda
- Mensajes y cuenta compartidos.

El grupo Docencia puede plegarse por elección, se abre si contiene la ruta actual y no implica suplantación. Personas reúne filtros de Estudiantes/Docentes/Administradores y activos/inactivos. «Estado» muestra versión/servidor y guía; no promete operaciones globales inexistentes. No se impone un número arbitrario de enlaces a costa de esconder tareas.

### Rutas y retorno

Rutas propuestas: `/inicio`, `/cursos`, `/cursos/:id`, `/materiales/:id`, `/estudio/:sessionId`, `/evaluaciones`, `/evaluaciones/:id`, `/intentos/:submissionId`, `/envios/:submissionId`, `/correcciones`, `/personas`, `/estudiantes/:id`, `/ayuda`, `/solicitudes/:id`, `/mensajes`, `/ajustes/*`, `/administracion/copias`.

Son nombres de diseño, sujetos al spike de compatibilidad. El mapa legacy conserva IDs validados y parámetros relevantes: `view`, `tab`, hash, `content_id`, `plan_id`, `submission_id`, `assessment_id`, `mode`, `from_session`, `ask_help`, filtros y contexto. Un alias nunca autoriza recursos ni acepta destinos externos. Acceso directo y refresh deben funcionar con el servidor empaquetado.

## 5. Diseño de las pantallas principales

| Pantalla | Jerarquía y acción principal | Decisiones concretas |
|---|---|---|
| Login | Marca pequeña, título, usuario/contraseña, Entrar | Idioma accesible antes de login; error persistente y seguro; retorno validado. No enlace de autorregistro público |
| Inicio alumno | Continuar/reanudar, recursos recientes, novedades pertinentes | Recurso y estado antes de métricas; sin afirmaciones de aprendizaje derivadas de XP |
| Cursos | Búsqueda/filtros, listado, estado y acción | Curso y material suelto diferenciados; lista/estructura comparten permisos; error ≠ lista vacía |
| Detalle de curso | Título, progreso real, estructura, Continuar | Publicación/asignación/revisión visibles para staff; exportación en contexto; no árbol enorme abierto por defecto |
| Aula de estudio | Lección central y navegación de estudio | Ancho de lectura 65–75 caracteres; una herramienta auxiliar activa entre índice, notas/anotaciones y ayuda; «Pausar» separado de «Completar y seguir» |
| Tutor | Contexto opcional + conversación + pregunta | Tutor libre sin curso; fuentes/política/recibos en detalle progresivo; cancelar/reintentar explicados; pregunta conservada |
| Previa de evaluación | Título, instrucciones, límites, estado, Comenzar/Reanudar | GET de lectura nunca llama `/start`; staff usa preview read-only; alumno confirma empezar |
| Intento | Preguntas, estado de respuestas, tiempo y revisar/enviar | Guardado local explícitamente rotulado; cerrar intento es terminal y consume límite; historia/resultados no empiezan otro |
| Historial/feedback | Envío seleccionado, estado, respuestas, comentarios | Cero real; provisional/final/cerrado distintos. No enseñar soluciones privadas por el mero cambio de ruta |
| Editor de curso/material | Título y estado, estructura/contenido, Guardar | Página, no modal gigante; manual e IA comparten bloques. Guardado explícito, fuente opcional, preview y workflow separados |
| Generación | Ítems elegidos, estado por ítem, revisión | Paquete/plan/material individual conservados; ninguna barra temporal inventada; lo guardado queda accesible ante parcial |
| Editor de evaluación | Preguntas, opciones, puntos/rúbrica, ajustes | Opciones como filas, no CSV; un único patrón de formulario; mover arriba/abajo accesible; vista previa sin intento |
| Corrección | Cola + respuesta/submisión | En estrecho, lista → detalle con regreso. Guardar pregunta puede finalizar al completar la última según API; comunicar ese efecto antes, no inventar publicación separada de notas |
| Alumno/Persona | Identidad, alcance, estado, pestañas pertinentes | Página con progreso/matrícula/notas propias; acciones de cuenta separadas y confirmadas; no badges de otra cuenta por error |
| Alta | «Crear estudiante/docente/administrador», grupos de identidad/acceso | Fluido, max 48–56 rem; role/owner impuestos para docente; selección admin explícita; éxito con Volver/Crear otro y sesión creadora intacta |
| Solicitud | Asunto, prioridad, curso/material, estado | Alumno: seguimiento. Staff: borrador de respuesta manual/IA, enviar mensaje y resolver son pasos independientes |
| Mensajes | Recibidos/Enviados/Archivados, búsqueda y detalle | Reply por ID, no por homónimo; selection definida por carpeta/resultados visibles. Archivo/eliminación comparten efecto actual; sin papelera/undo ficticios |
| Ajustes | Cuenta · Seguridad · Apariencia/idioma · Zona horaria · Tu IA | Probar IA distinto de guardar; muestra qué configuración usa el catálogo de modelos. Tamaño de lectura y reducción de movimiento como mejoras explícitas, no controles históricos inventados |
| Portabilidad | Elegir propósito → revisar → confirmar → resultado | Lectura de alumno, JSON docente y backup privado separados; restauración abre guía CLI/destino nuevo, no botón falso de restore web |
| Launcher | Estado y «Abrir SLMEducator» | Redimensionable/DPI/teclado, ES/EN, diagnóstico secundario; listo solo tras `/api/status` válido del proceso/origen elegido, no TCP; URL accesible por teclado, inicio lento/error/parado y Stop/X comprensibles |

## 6. Sistema visual AAC, adaptado al estudio

### Tokens iniciales

| Token | Claro | Oscuro |
|---|---|---|
| Fondo | `#f3f5ef` | `#112725` |
| Superficie | `#fffef9` | `#1c3532` |
| Superficie secundaria | `#e7ede5` | `#29433f` |
| Texto | `#193432` | `#f0f5ed` |
| Texto secundario | `#50625d` | `#becdc4` |
| Borde | `#7a9088` | `#91a59a` |
| Acción principal | `#17635f` | `#99d4c7` |
| Texto sobre principal | `#ffffff` | `#112725` |
| Error | `#983c34` | `#ffb7a9` |
| Éxito | `#27643e` | `#a8dbae` |
| Aviso | `#76500a` | `#ead28f` |

Son puntos de partida tomados del CSS real AAC, **no contraste global ya certificado**. Cada pareja y estado hover/focus/disabled se mide en el candidato.

- Fuente de sistema, sin descarga: Segoe UI/sistema; raíz 100%, base 16 px, lectura 18 px orientativa y ajustable; línea 1,5–1,65. Títulos 24/32 px, pesos limitados.
- Espaciado: 4/8/12/16/24/32/48 px expresado en rem. Radios 6/8/12/16 px; tarjetas 12 px; sombras solo cuando aportan profundidad real.
- Superficie, borde y jerarquía sustituyen saturación de badges, encabezados azules y emojis repetidos.
- Controles habituales mínimo 44×44 CSS px como objetivo del producto; foco 3 px con separación 3 px. **44 px no se presenta como mandato general WCAG AA.**
- Layout de documento con min-height natural; no `overflow-x:hidden` para esconder fallos, ni `h-dvh`/overflow cerrado general heredado de AAC.
- Sidebar en escritorio; drawer accesible en estrecho, sin ocultar la acción primaria. Formularios se apilan; labels largos se parten. No tres scrolls obligatorios para leer una lección.
- Temas claro/oscuro/sistema; compatible con forced-colors y reduced-motion. No añadir otro ajuste persistente de alto contraste sin especificar su contrato.

### Catálogo único

**Primitivas:** Button/IconButton, Input/Textarea, Select/Combobox, Checkbox/Radio, Field/FieldError, FormSection/ErrorSummary, Dialog/AlertDialog, Tabs, Tooltip, Toast, Badge, Card.

**Composición:** AppShell/RoleNavigation, PageHeader/Breadcrumbs, SearchFilters, List/Table/Pagination, Empty/Loading/Error/PermissionState, SaveStatus, DraftRecovery, Stepper, ContentRenderer, CourseOutline, QuestionBlock, PersonIdentity, SourceCoverage, AIRequestStatus.

Cada componente tiene variantes limitadas, nombres accesibles, error/loading/disabled, ES largo y temas. Las páginas consumen componentes; no redefinen botones/modales. CSS acotado sigue permitido para lectura, tablas, impresión y geometría; Tailwind no obliga a prohibir cualquier CSS propio. Colores de contenido/autor no se confunden con tokens de acción o confianza.

### Accesibilidad e i18n

- Objetivo WCAG 2.2 AA: contraste de texto normal 4,5:1, texto grande 3:1 y controles relevantes 3:1; foco visible/no oculto, teclado completo, landmarks/encabezados y skip link. [Contraste](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [contraste no textual](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html), [foco no oculto](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html).
- 320 CSS px, texto ampliado, zoom real 200% y 400%, sin scroll horizontal de página salvo contenidos esencialmente bidimensionales contenidos y accesibles. [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).
- Cambio de ruta actualiza título/H1/foco; Back conserva filtro/posición; Escape/cierre retorna a disparador válido. Diálogos no ocultarán errores/acciones fuera del viewport.
- ES/EN para texto, aria-labels, estados, errores, títulos y launcher. Una fuente de catálogos mantenida; migración explícita de interpolación `{nombre}` legacy a `{{nombre}}` i18next, con test.
- Fechas con `Intl` y zona IANA/UTC confirmada. Datos legacy sin offset siguen «zona desconocida»; no se adivinan ni se falsifican plazos.
- Toast complementario; envío, nota, publicación y error tienen estado persistente. El temporizador no se anuncia cada segundo al lector de pantalla.

## 7. Estados, formularios, privacidad y recuperación

### Estado remoto / UI / borradores

1. **AuthProvider** mantiene identidad confirmada; el backend autoriza. No renderizar datos de sesión previa al verificar cuenta. El protocolo bearer actual se conserva; una migración de autenticación sería otro cambio explícito.
2. **TanStack Query** es la única caché remota: keys por sesión/cuenta/recurso/filtro; AbortSignal y descarte de resultados tardíos; limpieza en logout/cambio de cuenta. Sin caché privada persistida ni datos API en SW.
3. **UI local/reducers** mantienen paneles y máquinas pequeñas de sesión/solicitud. No nueva store global de todo el producto.
4. **React Hook Form** mantiene formulario sucio, validación, errores y arrays. No convierte memoria en persistencia. Guardado explícito inicial de autoría/corrección/notas de staff.
5. **DraftAdapter** conserva solo los borradores ya soportados: cuenta/recurso/intento, TTL siete días, validación antes de recuperación. Notas de sesión tienen cola de guardado al servidor; respuestas de intento son borrador local, no entrega; editor de generación tiene alcance distinto de previews temporales.

### Reautenticación sin perder ni filtrar trabajo

Ante 401 con editor sucio, no desmontar y redirigir ciegamente. Congelar acciones, ocultar/inertizar trabajo privado y mostrar reingreso dentro del shell; conservar exclusivamente en memoria un buffer asociado a la cuenta original. Solo reautenticar **esa misma cuenta y revalidar acceso al recurso** permite reabrirlo. No reenviar la mutación automáticamente.

Si entra otra cuenta, descartar el buffer privado y queries antes de mostrar su pantalla. Si la página se recarga/cierra, recuperar únicamente los borradores ya soportados; explicar que el trabajo no persistido puede perderse. React Hook Form por sí solo no resuelve ese caso. En logout voluntario, aviso previo de cambios sin guardar y limpieza de memoria; no se afirma seguridad frente a otra persona con acceso al mismo perfil de navegador/DevTools.

Borradores en navegador no están cifrados por ser account-scoped. Para equipos compartidos, recomendar perfiles del sistema/navegador separados. Si hay borradores al salir, ofrecer claramente **Salir y conservar mis borradores aquí**, **Salir y borrar mis borradores aquí** y **Cancelar**; explicar la pérdida de recuperación, sin borrado silencioso. La expiración de sesión no borra la única copia. La acción alcanza solo los borradores de esa cuenta/origen; no almacenamiento de otras apps ni otros usuarios por un wildcard. Revalidar también al restaurar una página por `pageshow`/BFCache, sin mostrar la vista privada antigua durante la comprobación. Comprobar otra pestaña y respuestas tardías, no solo la navegación normal.

### Herramientas de estudio sin pérdida de texto

La pregunta no enviada, notas y selección de herramienta viven en el estado de la sesión, no dentro del componente que se desmonta. Cambiar Índice → Notas → Ayuda conserva texto y selección bajo la misma cuenta/contexto. Ocultar una herramienta no inicia una nueva solicitud ni anuncia cancelación: la máquina sigue su estado; Cancelar es explícito. Cambiar de lección/cuenta invalida la entrega anterior y solicita cancelación donde corresponda, sin prometer detener al proveedor. No aplicar la respuesta antigua al contexto nuevo. El foco vuelve al control correcto al cerrar o volver a lectura.

### Matriz de respuesta

| Estado | Comportamiento |
|---|---|
| Cargando | Skeleton/estado con contexto; no datos de otra cuenta ni acciones prematuras |
| Vacío | Causa y siguiente paso autorizado; nunca usarlo para disimular error |
| 401 | Reingreso con buffer misma cuenta donde proceda; retorno seguro, sin replay |
| 403/404 | Acceso/recurso no disponible; no filtrar existencia/propietario innecesariamente |
| 409 | Estado/revisión/conflicto explicado; conservar entrada y revalidar antes de acción |
| 422 | Errores de campos allowlisted + resumen; foco al primer error; no imprimir `input/msg/ctx` arbitrarios |
| 429 | Límite real/solicitud activa; no bucle de retry ni petición con nueva identidad automática |
| Red/5xx/no JSON | Mensaje seguro, texto conservado, reintento explícito; efecto incierto distinguido de fallo confirmado |
| Guardado local | «En este dispositivo; no enviado» y fecha/alcance; si storage falla, decirlo |
| Guardado servidor | Solo tras respuesta válida ligada al recurso/cuenta/operación |
| Doble clic | Single-flight por operación; backend replay-safe cuando ya exista; no prometer idempotencia universal |
| Salir sucio | Guardar / descartar / permanecer; `useBlocker` para SPA, browser unload como best effort; no confiar solo en `beforeunload` para persistir |
| Respuesta IA tardía | Solo se aplica si coincide contexto y versión local del editor; si hubo edición, resultado queda como propuesta que el usuario aplica, no sobreescritura |

El error D3 se porta completo. Las políticas de contraseña varían por operación; no se cambia inadvertidamente registro, cambio propio y reset admin a una única regla de longitud. Los secretos nunca se guardan en borradores, caché de Query persistida, logs, capturas o fixtures publicados.

No se promete control de concurrencia multiusuario/CAS donde la API no lo expone. El diseño evita sobrescritura por su propio refetch/respuesta tardía, conserva cambios y pide reconciliar cuando detecta discrepancia. Una revisión condicional server-side es extensión separada si el despliegue la requiere.

## 8. IA, fuentes y conectividad limitada

- Un motor de ayuda común para tutor libre, Q&A y ayuda contextual; una conversación nueva no conserva silenciosamente el contexto anterior.
- Con contexto: cuenta + curso/contenido + sesión/snapshot + versión de fuente + hasta 12 secciones; actualizaciones invalidan resultados obsoletos.
- Sugerencia no verificada siempre distinguible de contenido revisado y evaluación final. Referencia de fuente demuestra texto usado, no verdad factual.
- Contrato actual: una solicitud activa por cuenta, 100 inicios por día UTC y plazo local de entrega de 90 segundos; conservar esos límites y sus recibos, sin presentarlos como presupuesto monetario. Tokens conocidos y coste desconocido. Retry misma identidad, nueva solicitud y cancelación son estados diferentes; la cancelación de entrega no prueba que el proveedor paró/cobró cero.
- Generación por ítem conserva guardados y ediciones. Contadores «3/5 guardados» se basan en confirmaciones, no en tiempo estimado. Se puede volver al material guardado ante parcial; publicación conserva el contrato vigente, sin exigir un modelo perfecto.
- Probar conexión es acción explícita y diferente de guardar. Catálogo de modelos explica si usa configuración guardada; no se prueba ni hace POST proveedor al abrir/refocar una pantalla.
- Fuentes PDF/TXT/MD conservan límites, hash, cobertura y omisiones; no inventar OCR, almacenamiento de binario o acceso a medios externos.
- Q&A actual guarda la pregunta, no necesariamente la respuesta IA mostrada: rotular «Guardar pregunta» y respuesta temporal. Persistir conversación/respuesta completa requeriría decisión de producto/privacidad adicional.

| Situación | Qué debe funcionar / explicar |
|---|---|
| Internet ausente; app local y datos preparados activos | Lectura, práctica, notas, intentos y funciones locales según API; IA local preparada puede funcionar |
| Proveedor local parado/no configurado | Material y práctica siguen utilizables; ayuda IA muestra fallo/configuración, conserva pregunta |
| Proveedor cloud sin red | No prometer inferencia; reintentar más tarde. Material local sigue accesible mientras el servidor vive |
| Servidor local parado/inaccesible | Una página ya abierta puede explicar el fallo y retener texto en memoria, pero una apertura nueva puede mostrar el error de conexión del navegador. Iniciar/reconectar desde launcher; no se promete shell/PWA ni datos offline. Exportados de lectura son independientes |
| App cambia de puerto/origen | API relativa al origen. Los borradores/storage del origen antiguo no viajan automáticamente; no prometer recuperarlos en otro puerto |
| Docente no conectado | Estudio y ayuda IA disponible continúan. Solicitud humana queda abierta, sin promesa de respuesta inmediata |

## 9. Arquitectura y dependencias elegidas

**Ubicación propuesta:** `src/frontend/`, módulos bajo `src/frontend/src/`; output `src/frontend/dist/` ignorado y verificado, servido en fuente/paquete con manifest. Tests bajo `tests/frontend/` y navegador Python mantenido.

- `app/`: router, shell, providers, guardas, error boundaries.
- `components/ui/`: primitivas y variantes; `components/content/`: renderer seguro.
- `features/`: auth, home, people, courses, content, learning, assessments, grading, help, messages, progress, settings, portability.
- `lib/`: cliente fetch tipado, errores, tiempo, sanitización, IDs y adaptadores pequeños.
- `styles/`: tokens/base/contenido; `i18n/`: integración de catálogos.

| Dependencia | Razón y límite |
|---|---|
| React/React DOM + TypeScript | Componentes y estados explícitos; tipos no sustituyen validación runtime/API |
| Vite | Build estático y dev; no servidor Node en instalación |
| React Router, Data mode | Rutas anidadas/lazy/bloqueo de salida. No loaders/actions con segunda caché o mutaciones duplicadas |
| TanStack Query | Lecturas repetidas, invalidación y cancelación de listas/detalles; única caché remota efímera |
| Base UI | Primitivas interactivas sin estilo y semántica/foco; wrappers propios del proyecto |
| Tailwind + CSS variables | Tokens/variantes compartidos; CSS específico permitido |
| React Hook Form | Un patrón de formularios y arrays; no sumar Zod/Yup para duplicar Pydantic |
| i18next + react-i18next | ES/EN completo y namespaces; no copiar textos/negocio AAC |
| Lucide React | Un conjunto de iconos SVG tree-shaken; siempre texto o nombre accesible |
| Marked + DOMPurify | Conservar Markdown/HTML seguro y política de enlaces; un solo punto de HTML inyectado |
| cva/clsx/tailwind-merge | Solo utilidades consumidas por wrappers, sin infraestructura genérica |
| Vitest + Testing Library | Pruebas de componentes/contratos de interacción; Playwright Python existente para E2E |

No se incluye Zustand/Redux, Axios, Sonner, otro kit de UI, SSR, framework full-stack, Electron/Qt, WYSIWYG, gráficos, drag-and-drop general ni service worker de caché runtime. Base UI Toast basta. Reordenar tiene controles accesibles; drag es mejora opcional. El renderer actual no acredita soporte matemático; no se introduce KaTeX por suposición. No paquete UI compartido AAC/SLM ni monorepo solo para compartir aspecto.

### Alternativas valoradas

1. **Refactor de Bootstrap/HTML:** menor inicio, pero conserva duplicación y fragmentación que motivan el trabajo; apropiado para emergencia, insuficiente como destino.
2. **React/Vite estático:** recomendado; reemplazo real de UI con backend/instalador existentes, sin segundo runtime.
3. **Framework full-stack/SSR:** no aporta aquí una necesidad demostrada; añade convenciones/infraestructura a justificar. No se afirma que todo framework obligue a SSR, pero no se necesita para este objetivo.

### Verificación oficial y pins

Documentación oficial consultada el 7 de octubre: [React](https://react.dev/learn/build-a-react-app-from-scratch), [Vite/backend](https://vite.dev/guide/backend-integration), [Router modos](https://reactrouter.com/start/modes) y [bloqueo](https://reactrouter.com/api/hooks/useBlocker), [Base UI](https://base-ui.com/react/overview/quick-start), [formularios](https://base-ui.com/react/handbook/forms), [Query defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults) y [cancelación](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation), [Tailwind compatibilidad](https://tailwindcss.com/docs/compatibility), [i18next React](https://react.i18next.com/latest/usetranslation-hook), [Lucide](https://lucide.dev/guide/react), [RHF oficial](https://github.com/react-hook-form/react-hook-form), [Marked](https://marked.js.org/), [DOMPurify](https://github.com/cure53/DOMPurify), [Vitest](https://vitest.dev/guide/).

No copiar ciegamente pins AAC. Fijar versiones compatibles y lockfile durante el spike. Las docs Vite consultadas exigen Node 20.19+/22.12+ para build; se escogerá una versión LTS soportada compatible en ese momento. Tailwind v4 exige comprobar Chrome 111/Safari 16.4/Firefox 128 como pisos declarados. La app no añade un navegador embebido. No se instala nada por este plan.

Query empieza con retry de mutaciones 0 y lecturas explícitamente configuradas; sin defaults de refetch que pisen editores ni POST de fondo a proveedores. Marked no sanea HTML: sanitización y whitelist siguen obligatorias. Retener texto escapado cuando falla el renderer; no ampliar a scripts/iframes/estilos arbitrarios.

## 10. Corregir inconsistencias sin inventar un backend nuevo

Hallazgos de fuente, **no reproducidos en navegador en esta revisión**:

| Problema observado | Tratamiento en implementación |
|---|---|
| IDs/handlers inexistentes en árbol, búsqueda, catálogo de modelos; leaderboard definido dos veces | Reemplazar por rutas/componentes tipados; pruebas de éxito/fallo/teclado; no transportar esas conexiones rotas |
| Reply por nombre y selección masiva incluye ocultos/fallos no comprobados | Destinatario por ID autorizado, selección por resultado/carpeta y resultado confirmado por elemento |
| Ayuda muestra controles staff al alumno | Presentación por capacidad; el backend sigue denegando resolución no autorizada |
| Texto «auto-saved» en notas staff sin autosave real | Estados sin guardar/guardando/guardado; botón explícito |
| Badge de detalle alumno consulta endpoint de badges propios | Retirar tarjeta engañosa; conservar badges propios. Badge ajeno necesita endpoint autorizado nuevo antes de ofrecerse |
| Resumen de calificaciones transforma cero en null | Corrección backend puntual, con test de cero/ausente; el cliente no inventa cero cuando recibe null |
| Notas al resolver enviadas JSON pero endpoint espera parámetro query | Especificar DTO JSON compatible y prueba de persistencia; no poner texto privado en URL para maquillar el problema |
| Contactos limitados a 50 antes de filtrar permiso | Corrección acotada: autorización antes de límite y búsqueda/paginación explícita. Mantener ámbito, no directorio global |
| Listas de contenido/cursos/envíos sin paginación de servidor | Carga solo por ruta y detalles diferidos; medir datos representativos. Si exceden presupuesto, añadir contrato de paginación en cambio backend separado antes de prometer esa escala |

**Alcance recomendado obligatorio para no perpetuar fallos:** arreglos frontend de identidad/selección/controles, retirada de badge de actor incorrecto, y los cambios backend mínimos de cero, JSON de resolución y filtrado autorizado de contactos con sus pruebas. No se condicionan a añadir nuevas funciones. Estas correcciones de contrato se separan de estilos y tienen diff/tests propios. No cambian permisos, almacenamiento principal ni reglas educativas. Extensiones como papelera privada, edición colaborativa, persistir toda conversación, cambio de rol, badges de terceros o un nuevo modo offline quedan fuera de la primera sustitución salvo aprobación específica de alcance.

## 11. Entrega y retirada de legacy

La sección de matriz al final enumera cada archivo y su sustituto. La migración es incremental **durante desarrollo**, con una sola GUI en el candidato final. No se distribuye un modo clásico perpetuo ni se mezclan Bootstrap y Base UI globales.

### Primer corte vertical de los tres roles

1. Admin entra, crea docente y estudiante **matriculado explícitamente con ese docente**.
2. Docente entra, ve su estudiante, crea curso/lección manual, guarda, revisa/publica y asigna.
3. Alumno entra, abre el curso, lee, escribe nota, pausa y continúa; docente consulta el progreso autorizado.
4. Repetir un permiso negativo, error de registro D3, error de guardado y vuelta por ruta profunda; ES/EN, teclado y estrecho desde este corte.

Esta entrega valida arquitectura/UX con una tarea entera antes de multiplicar pantallas. No exige IA real ni un modelo perfecto.

### Fases, entregables y dimensión orientativa

**Las cifras siguientes son solo una referencia aproximada de esfuerzo humano equivalente; no son una ETA de ejecución por agentes, un calendario prometido ni trabajo ya realizado.** Se conservan para dimensionar la amplitud del reemplazo. La ejecución se organiza por entregables verticales acotados; la estimación real de tiempo transcurrido se recalibra después del primer corte implementado y probado. No se dividen jornadas humanas por número de agentes.

| Fase | Resultado y puerta de salida | Referencia humana equivalente, no ETA |
|---|---|---:|
| 0. Diseño ejecutable | Tokens, mapa de rutas, estados, prototipo navegable de tres roles y 6 pantallas clave; revisión visual antes de producir todo | 4–6 días |
| 1. Base + corte vertical | Shell, auth/D3, forms, API/query y flujo admin→docente→alumno completo | 7–10 días |
| 2. Aprendizaje/evaluación | Sesión/práctica/notas, previa/intento/historial/feedback, tutor/Q&A y reauth | 8–12 días |
| 3. Docencia completa | Autoría manual/IA, fuentes/jobs/revisión/asignación, evaluaciones y corrección | 9–13 días |
| 4. Personas/atención/datos | Mensajes, solicitudes, progreso, ajustes, portabilidad/backup y correcciones API acotadas | 7–10 días |
| 5. Retirada/entrega/aceptación | Eliminar legacy, retirar SW/deep links, build/installer/launcher y regresión visual/native | 6–9 días |
| **Dimensión total orientativa** | **Reemplazo integral, con revisión UX/QA por entregable** | **41–60 jornadas humanas equivalentes; no ETA de agentes** |

No se propone un calendario basado en dotación de personas o agentes. Cada entrega termina con su evidencia local y el siguiente alcance explícito. Si se exige nueva paginación general, edición concurrente o cambios de producto excluidos, reestimar como alcance separado. Priorizar un corte usable y probado, evitando infraestructura que no contribuya a completar esa tarea.

### Build/instalación

- Compilar frontend en entorno build explícito, verificar manifest/hash y copiar **solo** dist; `build_package.py` hoy copia todo `src`, por lo que debe usar entradas permitidas y excluir node_modules/herramientas/tests frontend y datos privados. Su comprobación recursiva de symlinks también se limita a esas entradas empaquetables, conservando el rechazo de enlaces en el payload; no puede fallar por los enlaces de node_modules que nunca se incluyen.
- Resolver source/frozen/override del frontend nuevo sin servir fuentes vecinas antiguas por accidente. APIs y assets antes del fallback; `/api/no-existe` no recibe HTML con 200.
- Cero CDN/fuentes/analítica necesaria, Node solo dev/build, assets/licencias locales. No descargas/modelos/servicios durante install/launch.
- Mantener bootstrap create-only, outputs nuevos, DB/config conservadas, restore copy-first y clave separada. Sin cambio silencioso de AppId, elevación, host o permisos.
- Installer actual rechaza actualización in-place. UX/documentación explica desinstalar/reinstalar preservando datos conforme al contrato; no implementar auto-update desde esta reescritura.
- **Retirar el SW de caché runtime**, mediante un endpoint mínimo de compatibilidad en `/sw.js`; no crear otro sistema PWA. La decisión y transición segura se detallan a continuación.
- Fijar artefacto por commit/hash y probar paquete sin Python/Node del checkout. X/Stop/reabrir, puerto ocupado, inicio lento, proceso terminado, fallo al abrir navegador, primer arranque/login/cambio/restart, Windows 200% DPI, desinstalar/reinstalar y recuperación son evidencia Windows separada. Abrir solo se habilita tras `/api/status` válido; comprobar un socket abierto no basta, y la URL también se puede activar/copiar con teclado.

### Decisión final: retirar el service worker runtime

El árbol publicado no contiene web app manifest ni flujo de instalación PWA; `static/vendor/manifest.json` es un inventario de dependencias. El SW registra desde index/dashboard y cachea HTML/JS/CSS, pero excluye `/api/` y no ofrece lecciones/inferencia con backend apagado. El uso sin Internet ya lo permite el servidor local con assets incluidos. Mantener otra caché aporta poco frente a su complejidad y riesgo de UI antigua.

**Destino:** assets con hash servidos localmente y caché HTTP ordinaria; HTML revalidado/no-cache, assets inmutables por hash. Sin service worker funcional permanente, Workbox ni offline replay. Manifest de build sirve para integridad/empaquetado, no es un manifiesto PWA.

**Retirada en una transición controlada:**

1. Mantener `/sw.js` en el mismo scope/origen, sirviendo un worker mínimo de retirada y no simplemente 404. No registrar SW en una instalación nueva; para registros SLM existentes, comprobar scriptURL/scope y solicitar su actualización cuando la app está disponible.
2. El worker de retirada no precachea ni intercepta datos; espera el ciclo normal. No `skipWaiting`, `clients.claim` ni navegación/recarga forzada de pestañas con intentos o texto sucio. La UI puede explicar que cerrar las pestañas antiguas permitirá terminar la transición, después de guardar/salir con seguridad.
3. Solo cuando no queden clientes de la versión antigua y se active la retirada: eliminar caches estáticos **propios reconocidos** de SLM, desregistrar ese registro y comprobar el estado en la siguiente apertura. No borrar localStorage, IndexedDB, respuestas, notas, API data o registros/caches ajenos. Una respuesta true de unregister por sí sola no sustituye comprobar el resultado.
4. Probar desde caches `slm-educator-v22-session-locale` y `slm-educator-v22-session-locale-auth-validation`, una pestaña vieja sucia y otra nueva; red caída durante update; cierre seguro y reapertura. El registro anterior sigue funcionando si la actualización no se completa. No declarar transición terminada hasta observar registro/controller esperado y assets correctos.
5. Conservar el endpoint pequeño de retirada durante la ventana de compatibilidad de instalaciones antiguas; no es una segunda GUI. El build final contiene solo la GUI nueva. Cualquier pestaña antigua en memoria sigue usando sus APIs compatibles hasta cerrarse; no se fuerza destrucción de ese estado.

La [guía de ciclo de vida](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers) y la documentación de [unregister](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/unregister) fundamentan la estrategia; el flujo exacto debe demostrarse en navegador. Esta simplificación modifica intencionadamente el mecanismo de caché de shell, manteniendo el contrato de aprendizaje con servidor local activo.

## 12. Rendimiento y pruebas de aceptación

### Presupuestos propuestos, aún no medidos

- Carga inicial shell/login objetivo ≤350 KiB JS gzip y ≤80 KiB CSS gzip; builders/renderer grandes cargados por ruta. No descargar todo catálogo, curso completo o listado de personas al login.
- Interacciones locales corrientes objetivo <100 ms; inicio útil objetivo <2,5 s con servidor local y datos del fixture acordado, en un equipo de gama baja representativo. Se mide arranque frío/caliente, no se deduce de un build verde.
- Fixtures: vacío, 1/50/500 elementos y curso largo de 100 lecciones; personas/contactos por encima de límites actuales y homónimos. Identificar límites API de verdad; paginar DOM no arregla una descarga no acotada.
- No añadir virtualización por defecto: primero filtros/paginación/lectura perezosa; hacerlo solo si datos y medición lo exigen y conserva accesibilidad.

### Gates automatizados locales

La evidencia primaria se obtiene ejecutando las pruebas en el entorno local o remoto autorizado, con el menor gasto práctico y sin perder su alcance. **No consultar, activar ni ejecutar GitHub Actions con la autorización actual.** Revisar la configuración CI como documentación no autoriza su uso: cualquier futura activación, consulta o ejecución requiere autorización separada y no es requisito para cerrar este plan. No se programa ni presupone Actions automáticamente en la implementación.

- Typecheck/lint/build frontend; tests de componentes/estados; paridad ES/EN y placeholders; tests del renderer con markup hostil/clarificaciones/fuentes.
- Migración de las **16 suites DOM**, manteniendo todas las aserciones de contrato o su sustituto equivalente. No borrar pruebas porque nombren archivos legacy sin registrar la nueva cobertura.
- Suites API/trust/backend existentes, incluido alcance/autorización, snapshots, attempts, idempotencia, zero/provisional grades, portabilidad y bootstrap; conservar target Python 80%. Cobertura frontend por flujos/ramas críticas, no sustitución por una cifra global cómoda.
- Seis suites de navegador existentes adaptadas + casos nuevos, con Playwright Python y datos sintéticos. Tests de interfaz deben usar roles/nombres/locators estables, no estilos como contrato de negocio.
- Entrega: build manifest, ausencia de vendor/global legacy en grafo, rutas profundas y 404; SW/privacy; packaging/installer tests sintéticos. La configuración del workflow de navegador tiene filtros de ramas antiguos; documentar esa incompatibilidad para una eventual revisión autorizada de CI. La prueba del candidato se ejecuta localmente y se vincula al SHA, sin consultar ni ejecutar Actions.

### Recorridos de aceptación por rol

| ID | Rol / escenario | Resultado observable requerido |
|---|---|---|
| E1 | Alumno sin curso, docente ausente, IA no configurada | Inicio honesto, tutor/configuración accesibles; no bloqueo inventado de material existente |
| E2 | Continuar curso con intento abierto | Destinos separados; ninguna consulta reserva intento |
| E3 | Tres lecciones: notas, Previous/Pause/Complete/Next | Snapshot estable; pause/previous no completan; retry no duplica progreso/recompensa |
| E4 | Borrador local → 401 → misma cuenta / otra cuenta | Recuperación autorizada solo misma cuenta; otra cuenta no ve datos, Back no los resucita |
| E5 | Evaluación: tiempo/recarga/desconexión/doble enviar | Plazo servidor, una entrega confirmada o incertidumbre visible; local draft no se etiqueta enviado |
| E6 | Cerrar intento y leer feedback | Cierre consume intento sin nota/recompensa; historial no reserva otro; cero/provisional/final diferenciados |
| E7 | Tutor: secciones, fuente nueva, cancelar, retry | Identidad/contexto/política; ausencia de respuesta tardía en contexto nuevo; costes/cancelación honestos |
| E8 | Q&A personal, compartir/descompartir y exportar lectura | Propiedad/privacidad correctas; guardar pregunta no finge persistir respuesta; lectura sin claves |
| D1 | Crear alumno con email inválido y corregir | D3 legible, valores/rol conservados, una alta y sesión docente/admin creadora intacta |
| D2 | Curso manual sin IA → revisar/publicar/asignar | Acciones/estados separados, alumno correcto, API rechaza borrador/ajeno |
| D3 | Generación 3/5 + editar + respuesta tardía/retry | Ítems confirmados y fallidos; edición humana no se sobrescribe; cancelación no promete parar proveedor |
| D4 | Curso asignado → editar/importar/revisión | Inmutable; copia nueva, preview antes de importar; no sobrescritura oculta |
| D5 | Corrección por pregunta/total y sugerencia IA | Cero válido; consecuencias de última pregunta/finalización claras; claves no llegan al alumno |
| D6 | Solicitud: borrador IA/manual → enviar → resolver | Borrador nunca envía solo; mensaje y resolución separados; alumno solo ve acciones autorizadas |
| D7 | Mensajes con homónimos, filtros y fallo masivo parcial | IDs correctos; solo selección indicada; no éxito total ficticio; efecto compartido/permanente confirmado |
| A1 | Crear/activar/desactivar/reset con last-admin/self | Identidad, efectos/revocación y rechazos correctos; datos educativos conservados |
| A2 | Reasignar docente A→B | Matrícula cambia; autoría de evaluación y asignaciones previas permanecen; notas staff no se comparten |
| A3 | Backup vs paquete docente vs lectura alumno | Previa/audiencia/clave/exclusiones; sin restore web falso ni datos fuera de alcance |
| A4 | Ajustes IA propios, proveedor/endpoint cambiado | No clave antigua enviada al nuevo destino; otros usuarios no modificados; no pruebas de fondo |
| X1 | ES/EN, claro/oscuro/sistema, teclado y lector de pantalla | Labels/estados/foco/contraste correctos en todas las tareas críticas |
| X2 | 320 px, zoom 200/400%, texto largo/tabla/código | No acciones ocultas, página legible, panel auxiliar manejable, foco visible |
| X3 | Internet caída / proveedor caído / servidor parado | Tres mensajes distintos y capacidades reales; export de lectura aparte |
| X4 | Instalación/reinicio/retirada SW y puerto distinto | Dist nuevo consistente, transición sin recarga destructiva, sin SW runtime/Node, datos intactos y límites de drafts por origen claros |

Cada resultado registra commit, entorno, rol, fixture, captura/trace y PASS/FAIL/NOT RUN. Los casos de modelo real pueden comprobar usabilidad best effort, latencia y errores; no hay umbral de perfección como gate de entrega. Un error seguro no cuenta como una respuesta educativa útil.

### Definición de terminado

1. Todos los destinos/capacidades de la matriz tienen ruta y prueba equivalente; ningún enlace legacy desemboca en una pantalla retirada.
2. Un solo shell/sistema visual/grafo de assets; cero Bootstrap/globals/handlers legacy ejecutables. Se permiten el mapa HTTP de compatibilidad y endpoint mínimo de retirada SW documentados.
3. Los tres roles completan sus tareas críticas y negativas en navegador real; el usuario puede reconocer continuidad visual con AAC en pantallas aprobadas.
4. Errores/guardado/provisionalidad/privacidad/reautenticación/no red son comprobables y veraces; no fuga por Back, caché o cambio de cuenta.
5. Accesibilidad/i18n/zoom pasan con evidencia; nada se marca aceptado por JSDOM solamente.
6. Build/paquete/launcher/instalador nativos probados con datos sintéticos y artefacto identificado; skip no es pass.
7. Docs/tests/catalogue actualizados, informes antiguos conservados; gaps/bloqueos restantes se declaran antes de llamar el resultado listo.

## 13. Las tres iteraciones y cómo cambió la propuesta

Son iteraciones reales de la propuesta documentada, con crítica y cambios, **no tres ejecuciones del producto ni tres pruebas con usuarios**.

| Ronda | Método y roles recorridos | Resultado y cambio de diseño |
|---|---|---|
| **1. Inventario y propuesta** | Contrastar código/base; recorrer seis escenarios de estudiante, seis de docente y cinco de admin; mapear todas las superficies | Propuso reemplazo completo y stack estático, con navegación demasiado agregada y máximo cinco destinos. Identificó shell/registro/player fragmentados y conservó contratos |
| **2. Crítica y nueva propuesta** | Revisar todos los roles frente a interrupciones, IA ausente, autoría, cuenta compartida, permisos y entrega | Sustituyó etiquetas vagas por tareas, eliminó máximo cinco, hizo evaluación visible y previa sin reservar, una herramienta de estudio, guardado explícito y una pila decidida. Añadió launcher y primer corte vertical |
| **3. Desafío independiente y cierre** | Revisión completa de R2 + matriz de migración; 30 escenarios adversariales (10 por rol), con source checks y aceptación falsable | Corrigió 401 con formulario sucio, control real de borradores al salir/BFCache, matrícula frente a autoría, solicitudes open/resolved, preview staff, efectos exactos de calificar, límites offline/origen, texto entre paneles y readiness nativo. Verificó mecánicamente matriz 36/36 sin faltantes/extras; el cierre técnico simplificó la entrega retirando SW runtime después de verificar que no hay contrato PWA/datos offline |

Las prioridades P0/P1 siguientes señalan huecos de la propuesta de diseño, no incidentes de seguridad de producción demostrados.

### Trazabilidad de los ocho hallazgos de Ronda 3

| ID / prioridad | Decisión final incorporada | Dónde se verifica |
|---|---|---|
| R3-01 / P0 | Reauth misma cuenta conservando buffer privado en memoria, no redirect que desmonta RHF, revalidar permiso y sin replay | §7; E4 y D5, casos de mismo/otro usuario y 403 tras revocación |
| R3-02 / P0 | Salir conservando/borrando borradores propios, expiración no destructiva, revalidación BFCache y limitación de localStorage sin cifrado | §7; E4/X4 + casos A→B→Atrás/otra pestaña/storage bloqueado |
| R3-03 / P1 | Solicitudes solo Abierta/Resuelta; respuesta es mensaje separado, sin notificación de respuesta inventada | §§4–5; D6 y caso resolver sin enviar/enviar sin resolver |
| R3-04 / P0 | Matricular explícitamente en primer corte; matrícula, autoría y notas privadas separadas después de A→B | §§3 y 11; A2 y D2/5 |
| R3-05 / P1 | Preview staff no muta intentos ni suplantación; última pregunta puede finalizar, reconsultar estado | §5; D5 con espía de red, cero y aceptar todas incompletas/409 |
| R3-06 / P1 | Sin Internet ≠ proveedor caído ≠ servidor apagado; borrador ligado a origen/puerto | §8; X3/X4, localhost frente a 127.0.0.1 |
| R3-07 / P1 | Estado de texto separado del panel visible; ocultar no pierde pregunta ni crea/cancela falsamente solicitudes | §7; E3/E7 con teclado, petición pendiente y cambio de lección |
| R3-08 / P1 | Launcher accesible y redimensionable; listo solo tras API real, URL por teclado e inicio lento/fallo | §§5 y 11; X4/aceptación Windows 200% |

### Tercera pasada resumida por rol

- **Estudiante:** revisar curso + intento simultáneos; ausencia docente/IA; paneles a 320 px; IA pendiente y contexto nuevo; previa/inicio/salir/retomar; tiempo sin red; 401/cambio de cuenta; feedback/XP; resolver sin mensaje; logout/BFCache. El plan final conserva tareas y estado, y no atribuye capacidades al SW que no tiene.
- **Docente:** error y éxito incierto de alta; alumno sin responsable; creación manual; generación parcial/edición tardía; contenido ajeno/Q&A; 401 con texto; cero/última nota; reasignación; mensajes/resolución; orden/publicación/retorno con teclado. El plan final separa propiedad, persistencia y efecto de cada acción.
- **Administrador:** primer arranque/reapertura; crear/matricular; reset/inactivar/last-admin; reasignación con historial; preview sin suplantación/notas ajenas; IA propia; tipos de export/backup; guía restore; puerto/SW; personas/backup con zoom. El plan final cubre operación y acceso sin introducir otro runtime o autoridad.

No quedan bloqueos de diseño de esas ocho observaciones sin respuesta en este plan. La confirmación de que funcionen pertenece a implementación y aceptación, todavía no realizadas.

## 14. Siguiente paso recomendado

Aprobar esta dirección y realizar **Fase 0 + primer corte vertical**, con seis diseños revisables: Inicio alumno, Aula de estudio, Evaluación, Editor de curso, Correcciones y Personas/Alta, además del launcher compacto. Validar el aspecto y la continuidad de tareas antes de extender componentes al resto de rutas.

La implementación posterior debe arrancar desde la revisión publicada acordada, incorporar D3, trabajar en rama aislada y mantener los datos/instalación del usuario intactos. Este documento por sí solo no ejecuta esos cambios ni autoriza publicación/instalación.

## Anexo A. Matriz exacta de retirada y conservación

# Matriz de retirada, migración y conservación

Base exacta: `99ebef03901871ca9c9a1c548058971ae1f7e089`. Matriz completa de los 36 archivos propios de GUI; 16.062 líneas / 770.178 bytes. Los destinos son propuestos dentro de `src/frontend/src/`, excepto el endpoint público temporal de retirada del SW. «Retirar» significa al cerrar paridad en la rama de implementación; no se ha eliminado nada.

| Archivo actual (`src/web/…`) | Líneas | Acción final | Sustituto propuesto | Contrato que migra | Prueba base |
|---|---:|---|---|---|---|
| `404.html` | 40 | Reemplazar y retirar | `routes/errors` | 404 real, retorno seguro, ES/EN | `auth, route/404` |
| `assessment_builder.html` | 201 | Reemplazar y retirar | `features/assessments/AssessmentEditor` | preguntas/rúbrica/política, draft/publish separado | `assessment_journey` |
| `assessment_history.html` | 48 | Reemplazar y retirar | `features/assessments/SubmissionHistory` | lectura propia sin reservar intento | `assessment_journey` |
| `assessment_taker.html` | 113 | Reemplazar y retirar | `features/assessments/AttemptWorkspace` | previa, respuestas, temporizador y cierre | `assessment_journey` |
| `course_designer.html` | 220 | Reemplazar y retirar | `features/courses/CourseEditor + GenerationPanel` | manual/IA, fuentes, resultado parcial | `course_source_journey` |
| `dashboard.html` | 2039 | Reemplazar y retirar | `app/AppShell + routes + features/*` | 13 vistas y 9 modales descompuestos | `role_journeys, dashboard_startup` |
| `grading.html` | 134 | Reemplazar y retirar | `features/grading/GradingWorkspace` | cola/filtro, pregunta/total, provisional/final | `assessment_journey` |
| `index.html` | 62 | Reemplazar y retirar | `routes/EntryRoute` | estado servidor y acceso sin pantalla redundante | `dashboard_startup, route/entry` |
| `login.html` | 43 | Reemplazar y retirar | `features/auth/LoginPage` | login/retorno, D3, reauth misma cuenta | `auth_errors` |
| `portability.html` | 86 | Reemplazar y retirar | `features/portability/*` | previsualización por propósito y alcance | `portability_journey` |
| `register.html` | 70 | Reemplazar y retirar | `features/people/CreateAccountPage` | alta autorizada dentro del shell y sesión creadora | `auth_errors, role_journeys` |
| `session_player.html` | 235 | Reemplazar y retirar | `features/learning/LearningWorkspace` | snapshot, lectura, una herramienta auxiliar | `session_progress_locale, learning_help` |
| `static/css/main.css` | 2058 | Reemplazar y retirar | `styles/tokens.css + styles/base.css + component variants` | tokens AAC medidos, layout natural, sin overrides Bootstrap | `test_style_standardization → design-system tests` |
| `static/js/admin-accounts.js` | 88 | Reemplazar y retirar | `features/people/accountActions` | identidad, confirmación, revocación, no último admin | `admin_accounts` |
| `static/js/assessment.js` | 128 | Reemplazar y retirar | `features/assessments/list + preview + stats` | lista, lectura previa, estadísticas finales, borrar | `assessment_journey` |
| `static/js/assessment_builder.js` | 346 | Reemplazar y retirar | `features/assessments/editor + forms` | validar/persistir política y preguntas, publicar explícito | `assessment_journey` |
| `static/js/assessment_history.js` | 171 | Reemplazar y retirar | `features/assessments/history` | cuenta/ID y respuesta tardía, historial read-only | `assessment_journey` |
| `static/js/assessment_taker.js` | 308 | Reemplazar y retirar | `features/assessments/attemptMachine + draftAdapter` | start explícito, draft por intento, expiry/replay/close | `assessment_journey` |
| `static/js/auth.js` | 428 | Migrar contrato y retirar implementación | `features/auth/authClient + AuthProvider + errorAdapter` | normalización rol, D3 safe errors, creator session | `auth_errors, role_journeys` |
| `static/js/course_designer.js` | 785 | Reemplazar y retirar | `features/courses/generation + source workflow` | identidad jobs/fuente, parcial, reintento, cancelar verdad | `course_source_journey` |
| `static/js/dashboard.js` | 4339 | Reemplazar y retirar | `features/home,courses,content,tutor,people,progress,settings,help` | sin globals; cada capacidad se asigna a dominio explícito | `role_journeys + todos los dominios vinculados` |
| `static/js/grading.js` | 283 | Reemplazar y retirar | `features/grading/queries + forms` | cero, aceptación IA, guardado confirmado y cola | `assessment_journey` |
| `static/js/i18n.js` | 264 | Reemplazar y retirar | `i18n/index + namespaces` | ES/EN sin mutar DOM; nombres accesibles/traducción de estado | `session_progress_locale, new i18n parity` |
| `static/js/learning-client.js` | 107 | Migrar contrato y retirar implementación | `lib/api + features/drafts` | errores/request ownership, TTL/scope y recuperación | `frontend_safety, role_journeys` |
| `static/js/learning-help.js` | 517 | Reemplazar y retirar | `features/help/ContextHelp + requestMachine` | fuente/snapshot/política/12 secciones/recibos/idempotencia | `learning_help, tutor_receipts_journey` |
| `static/js/modules/inbox.js` | 649 | Reemplazar y retirar | `features/messages/*` | bandejas, destinatarios autorizados, masivas, semántica compartida | `role_journeys + new messages contract tests` |
| `static/js/portability.js` | 178 | Reemplazar y retirar | `features/portability/client + flows` | preview invalidation, formats, scope, no import overwrite | `portability_journey` |
| `static/js/practice.js` | 99 | Reemplazar y retirar | `features/learning/PracticeBlock` | opciones canónicas, pistas, self-check no nota, draft | `practice_option_contract` |
| `static/js/safe-render.js` | 92 | Migrar contrato y retirar implementación | `components/content/ContentRenderer + lib/sanitize` | único HTML seguro, enlaces, estructura, fuente | `frontend_safety, source_clarification` |
| `static/js/session.js` | 887 | Reemplazar y retirar | `features/learning/sessionMachine + notes/annotations` | end/progress en dos fases, pause/prev no completan | `session_progress_locale, role_journeys` |
| `static/js/study_plan_builder.js` | 303 | Reemplazar y retirar | `features/courses/manualEditor` | orden, reutilización autorizada, inmutabilidad/copia | `role_journeys, content_edit_journey` |
| `static/js/theme.js` | 71 | Reemplazar y retirar | `app/AppearanceProvider` | light/dark/system, preferencia sin actuar como auth | `ai_settings_journey + new theme tests` |
| `static/js/time-display.js` | 94 | Migrar contrato y retirar implementación | `lib/time + features/settings/Timezone` | IANA, UTC default, legacy desconocido; no adivinar | `session_progress_locale` |
| `static/js/toast.js` | 276 | Reemplazar y retirar | `components/ui/Toast,Dialog,AlertDialog` | foco/cierre/escape/texto seguro, estados persistentes aparte | `frontend_safety + component tests` |
| `study_plan_builder.html` | 131 | Reemplazar y retirar | `features/courses/CourseEditor` | estructura manual/reordenar/guardar/workflow | `role_journeys, course_source_journey` |
| `sw.js` | 169 | Migrar contrato y retirar implementación | `public/sw-retirement.js + build asset manifest` | misma URL /sw.js solo para retirar SW/cache legacy de forma segura; sin runtime SW nuevo | `service_worker → retirement, browser/test_service_worker_update` |

## Dependencias vendorizadas: 10 archivos

- Retirar `src/web/static/vendor/bootstrap@5.3.0/` completo (CSS, bundle JS, LICENSE) una vez no haya consumidores.
- Retirar `src/web/static/vendor/sortablejs@1.15.0/` completo (bundle, LICENSE). Mantener reordenación mediante controles accesibles. Drag/pointer es mejora posterior si se justifica; no otro kit por costumbre.
- Sustituir `src/web/static/vendor/dompurify@3.4.16/` y `marked@15.0.12/` por imports de dependencias fijadas en lockfile. Conservar avisos/licencias legales en la distribución y mismas barreras de sanitización, no borrar la protección.
- Retirar `src/web/static/vendor/manifest.json`; reemplazar por manifest/hash de build más inventario de licencias/SBOM de assets. Cero CDN/runtime downloads.
- Licencias de terceros se conservan donde corresponda al bundle nuevo; no confundir retirada de un directorio con permiso de suprimir atribuciones.

## Borde API y entrega: conservar dominio, adaptar integración

| Ruta exacta o grupo | Acción propuesta | Verificación de paridad |
|---|---|---|
| `src/api/main.py` | Cambiar `_looks_like_web_dir`, `_resolve_web_dir`, mounts y HTML serving por dist/manifest y allowlist de rutas SPA; registrar APIs antes del fallback | Source/frozen/override válido; assets faltantes fallan claro; API 404 sigue JSON/error, nunca HTML; deep links/alias old IDs allowlisted, sin open redirect/path traversal |
| `src/api/security.py`, `src/api/policies.py`, `src/core/roles.py` | Conservar controles; cliente no les sustituye | Permisos negativos de cada rol y recurso; no emitir contenidos privados durante loading |
| `src/api/routes/*.py` (18 módulos) y `src/core/models`, `src/core/services` | Conservar contratos y semántica; adaptar consumo tipado, sin rewrite de dominio | Suites API/trust. Cualquier gap nuevo exige cambio explícito separado; no inventar endpoint ni capacidad cliente |
| `src/starter.py` | Rediseñar presentación Tkinter, separar vista de lifecycle existente; ES/EN, DPI, redimensionado, diagnóstico secundario | Arranque/listo/error, abrir navegador con origen real, doble clic, Stop y X confirmados nativamente |
| `src/starter_headless.py`, `src/startup_utils.py` | Conservar arranque/puerto/cwd y usar en tests | Sin bootstrap alternativo, host expuesto o procesos ajenos afectados |
| `scripts/build_package.py` | Incluir solo assets dist verificados; `_copy_inputs` actual copia `src` recursivamente, debe excluir node_modules, herramientas/tests frontend y secretos. Comprobar manifest antes del freeze; validar symlinks solo en entradas empaquetables, no en node_modules excluido | Test explícito con archivo centinela en node_modules y datos runtime excluidos; bundle autosuficiente; no servir fuente vecina por accidente |
| `scripts/build_installer.py`, `installer/SLMEducator.iss`, `build_package.bat`, `build_installer.bat` | Conservar contrato; validar payload frontend/hash actualizado. Cambios de texto/identidad visual limitados | Nuevos outputs, per-user/sin elevación; no in-place update; DB/config conservadas; no descargas/modelos/servicios |
| `scripts/seed_admin.py`, `scripts/recover_database.py`, migraciones y backups | Conservar sin cambios funcionales por la GUI | Cuenta existente intacta; recuperación/copy-first y clave separada; datos sintéticos en tests |
| `start.bat`, `install_dependencies.bat`, `run_tests.bat` | Adaptar instrucciones/check de build frontend y nuevos gates; no instalar/compilar silenciosamente al arrancar | Node solo entorno dev/build. Dist ausente da instrucción clara, no descarga en primer uso |
| `.github/workflows/offline-tests.yml` | Documentar compatibilidad futura de typecheck/lint/component tests/build y lockfile; no activar ni ejecutar CI con esta autorización | Ejecutar los gates localmente; preservar 80% Python y bloqueo de red. Consultar/activar/ejecutar Actions requiere autorización separada |
| `.github/workflows/browser-acceptance.yml` | Documentar cambios futuros de build/rutas/filtros; ninguna activación, consulta o ejecución automática | Sus filtros antiguos no acreditan aceptación. Usar evidencia local por SHA; cualquier uso de Actions requiere autorización separada y no bloquea este plan |
| `translations/en.json`, `translations/es.json` | Conservar claves/semántica; adaptar namespaces/catalogues con una fuente mantenida y puente de interpolación `{x}`→i18next `{{x}}` explícito | Paridad de claves/placeholder; no traducir contenido de usuarios automáticamente; startup/offline strings empaquetados |
| `README.md`, `docs/CONTRIBUTING.md`, `docs/FUNCTIONAL_REQUIREMENTS.md`, `docs/BROWSER_TEST.md`, `docs/WINDOWS_INSTALLER.md`, `docs/PORTABILITY_RECOVERY.md`, `docs/ASSISTANCE_POLICY.md` | Actualizar arquitectura/rutas/proceso UX vigente | No borrar informes históricos ni reinterpretar resultados de binarios viejos |

## Pruebas antiguas: sustituir mecanismo, conservar aserción

16 archivos DOM actuales, todos con destino de cobertura:

- `tests/ui/admin_accounts.test.cjs` → personas/recuperación y permisos.
- `tests/ui/ai_settings_journey.test.cjs` → preferencias proveedor/modelo/clave por cuenta.
- `tests/ui/assessment_journey.test.cjs` → editor, previa, intento, entrega, cierre, historial, corrección y notas provisionales.
- `tests/ui/auth_errors.test.cjs` → D3 seguro ES/EN completo.
- `tests/ui/content_edit_journey.test.cjs` → edición canónica/confirmada y fuente.
- `tests/ui/course_source_journey.test.cjs` → extracción/fuentes/revisión/generación parcial.
- `tests/ui/dashboard_startup.test.cjs` → shell gated a identidad, fallo y recuperación.
- `tests/ui/frontend_safety.test.cjs` → sanitización, foco, permisos, errores, APIs seguras.
- `tests/ui/learning_help.test.cjs` → ayuda contextual, estados y aislamiento.
- `tests/ui/portability_journey.test.cjs` → previews, audiencias, importar y backup.
- `tests/ui/practice_option_contract.test.cjs` → opciones clave/texto, pistas y self-check.
- `tests/ui/role_journeys.test.cjs` → matriz de capacidades, recorridos y respuestas tardías.
- `tests/ui/service_worker.test.cjs` → retirada segura de registro/cache legacy, ningún caching privado ni SW runtime nuevo; manifest de assets estáticos aparte.
- `tests/ui/session_progress_locale.test.cjs` → finalizar/pausar/progreso/localización.
- `tests/ui/source_clarification.test.cjs` → clarificaciones antes de material no confiable.
- `tests/ui/tutor_receipts_journey.test.cjs` → recibos/cancelación/idempotencia/límites.

`tests/ui/test_frontend_safety.py` y `test_style_standardization.py` cambian sus selectores/source assertions a invariantes de la UI nueva; no se vacían ni se debilitan. `tests/ui/package.json` y `package-lock.json` se consolidan en el package del frontend al desaparecer todos los CJS legacy. Mantener tests bajo `tests/` según reglas repo; configurar Vitest allí, no esconderlos en `src/`.

Se adaptan los seis archivos `tests/browser/test_*.py`: `test_assessment_feedback_journey.py`, `test_live_journeys.py`, `test_native_zoom.py`, `test_practice_option_preview.py`, `test_service_worker_update.py`, `test_source_clarification_journey.py`; sus fixtures arrancan backend sintético y dist real. `tests/e2e/test_dashboard_flow.py` y `test_smoke.py` actualizan rutas/locators semánticos sin cambiar el resultado exigido. Mantener Playwright Python existente para E2E; no añadir una segunda suite Playwright Node solo por moda.

Mantener y ampliar `tests/integration/test_auth_pages.py`, `test_auth_registration_contract.py`, `test_auth_role_contract.py`, `tests/test_build_package.py`, `test_build_installer.py`, `test_seed_admin.py`, `tests/windows/test_packaged_bootstrap.py`, `test_packaged_recovery.py`, `test_installer_lifecycle.py` y demás suites `tests/trust/`. Los tests nuevos de frontera SPA deben demostrar que APIs/rúbricas/recursos privados no se filtran por fallback ni caché.

## Condición exacta para retirar legacy

Para cada fila: inventario de comportamiento → aserciones antiguas identificadas → componente/ruta nueva → pruebas equivalentes y negativas pasando → vínculo de evidencia y commit. Después, buscar importaciones, `<script>`, CSS classes Bootstrap, `window.AuthService`, `window.SLM*`, handlers inline, URLs `.html` fuera del mapa de compatibilidad, referencias de build/tests y caches. Cero referencias ejecutables legacy en el grafo del candidato final. Mantener solo alias HTTP documentados, endpoint mínimo de retirada de SW y lectura de formatos de borrador compatibles; no una segunda GUI ni un flag perpetuo «modo clásico».
