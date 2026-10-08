# AUTO_TEST · Auditoría autónoma funcional y visual de SLMEducator

Prompt operativo para un agente con control de ordenador. Crear o leer este archivo no ejecuta la campaña.
Cuando David pida ejecutarlo, realiza INICIO–FIN; no necesita `/goal`, copiar el prompt ni confirmar cada clic.

INICIO DEL PROMPT

## 1. Encargo, autonomía y límites

Prueba exhaustivamente la aplicación SLMEducator actual mediante su interfaz real: pantalla, ratón, teclado y capturas inspeccionadas. Actúa tú como operador de los tres roles, descubre todas sus funciones, reproduce regresiones y registra defectos con evidencia. Continúa lo independiente aunque una función falle. Informa solo de resultados importantes, decisiones necesarias y bloqueos; no conviertas el trabajo en una sesión de instrucciones para que David haga cada acción.

- Usa exclusivamente herramientas nativas de visión/control de pantalla, ratón y teclado para los recorridos GUI. NO uses Playwright, Selenium, Cypress, Puppeteer, WebDriver, headless, selectores DOM, evaluación JavaScript, CDP ni llamadas API para simularlos. Tampoco automatices controles leyendo el DOM/árbol de accesibilidad en lugar de observar la pantalla.
- La terminal puede preparar el candidato según el procedimiento mantenido, inventariar fuentes, crear archivos sintéticos, identificar procesos propios, calcular hashes y leer logs saneados. Estas son pruebas TÉCNICAS auxiliares; no acreditan clics, foco, inferencia útil ni GUI completada. No alteres SQL/API para hacer pasar un caso de creación desde pantalla.
- Comprueba al principio que ves la pantalla y puedes actuar. Registra si usas ordenador/navegador de evaluación o el del usuario. Sin acceso GUI, prepara inventario/matriz y declara los recorridos BLOCKED; no inventes capturas, clics ni resultados. No eludas denegaciones mediante otra herramienta, host, túnel, alias o script.
- Este prompt encarga una campaña autónoma NUEVA. MANUAL_TEST1 aporta preparación y MANUAL_TEST2 datos/oráculos; sus pausas de «una acción y esperar a David» y su recorrido básico opcional no rigen aquí. Conserva sus límites de seguridad. Incluye también sus variantes adicionales, hasta donde exista autorización y fixture segura.
- Prueba y reporta; NO repares producto, tests, dist ni configuración del instalado real para ocultar fallos. Puedes corregir preparación propia incorrecta y repetir identificándola. Un cambio posterior de producto abre otro candidato y campaña, nunca reescribe el resultado original.
- No consultes/ejecutes Actions, no merges ni cambios en `main`, no publiques binarios/Releases/datos privados, no OTA, no instales extensiones, no cambies red/firewall/VPN/seguridad global, no descargues modelos ni uses proveedores de pago. Informes saneados pueden publicarse en la rama expresamente autorizada si la autorización vigente cubre esa publicación; no abras PR ni amplíes audiencia sin permiso. Esta campaña no autoriza campañas semánticas masivas ni pruebas de penetración.
- Solo datos sintéticos de personas adultas. No uses bases, nombres, mensajes, evaluaciones, archivos docentes o información de alumnos reales. No copies tokens, contraseñas, claves, hashes de credenciales, bases o configuración privada a informes/capturas/Git. Nunca leas el almacén de contraseñas.
- Respeta las confirmaciones/handoff obligatorios para introducir/enviar credenciales, cambiar acceso, permisos sensibles o borrados irreversibles, incluso en evaluación. No sortees esas reglas con seeders/arneses. Si un paso las necesita, pide únicamente esa intervención y sigue lo independiente. No interpretes silencio como aprobación.

## 2. Seleccionar fuentes y candidato, sin reciclar el binario antiguo

Lee [AGENTS.md](AGENTS.md), [README.md](README.md), [CONTRIBUTING](docs/CONTRIBUTING.md), [contratos React](src/frontend/CONTRACTS.md), [MANUAL_TEST1](MANUAL_TEST1.md) y [MANUAL_TEST2](MANUAL_TEST2.md). Consulta `docs/FUNCTIONAL_REQUIREMENTS.md`, `docs/ASSISTANCE_POLICY.md`, `docs/AI_REQUESTS_AND_OPERATIONS.md`, `docs/WINDOWS_INSTALLER.md` y `docs/BROWSER_TEST.md` para contratos, no para ejecutar sus harnesses de navegador prohibidos aquí.

Lee también `implementation_documents/gui_redesign_20261007_plan.md`, `implementation_documents/react_redesign_20261007/{SOURCE_CHECKPOINT,FUNCTIONAL_CONTINUATION,CONTINUITY_GAPS_20261007}.md` y `implementation_documents/manual_windows_20261007/{REPORT,DEFICIENCIAS,SESSION_LOG}.md`. Si una ruta no existe en el candidato, anota la ausencia y localiza el reemplazo acreditado; no inventes otro manual. Esta revisión parte de MANUAL_TEST1 y 2, no de un supuesto MANUAL_TEST3.

Referencia documental verificada al escribir esta guía: rama `fix/react-functional-continuation-20261007`, HEAD `e911e4321c6ce1cba24fbc5c8b755a2bd4523f4d`, árbol `9d1ebbb418afb8de570d0790c478345cf1769a56`. Producto: `642966a93e7e9c9f9c5e93cce0bc842f538846fb`, árbol `e0a3966bddc8bbd4cfc2ab4041668c3162ce86f7`. Verifica el HEAD remoto/local y diferencias actuales: un descendiente solo documental no exige reconstruir. Si cambió producto respecto al candidato elegido, confirma cuál probar; no fuerces la rama ni elijas `main` por rutina.

La aplicación mantenida es React en `src/frontend`, FastAPI y launcher Tkinter. `src/web` fue retirado (76 archivos legacy); no vuelvas a habilitarlo ni busques los viejos dashboards `.html` como GUI de reserva. Comprueba rutas/componentes y catálogos de ESTE SHA antes de seguir etiquetas.

El Setup histórico `SLMEducator-Setup-2.0.0-fe954cab4655.exe` (31.456.307 bytes; SHA-256 `c02c79e21e6d04d327ed11223203c85ef95fd5b796fbc6a2c771ed5f952a1531`) NO contiene esta GUI React. Sus cinco PASS humanos del tramo A y su fallo de alta docente 422 pertenecen a ese binario. Tampoco 825 DOM, 249 Python y 8 diagnósticos de G1–G5 prueban el nuevo Windows, lector, proveedor o pantalla. No sumes cifras históricas a esta campaña; el agregado Python/cobertura whole-source no está demostrado por ellas.

Identifica el candidato real: SHA/árbol, rama, cambios locales, dist/manifest, Setup y EXE con rutas/tamaños/SHA-256, versión/build, perfil, base/config/uploads efectivos, proceso y origen/puerto del launcher. No deduzcas URL del README ni del smoke. Checkout, paquete instalado y portable son candidatos distintos; cada resultado lleva su identidad.

Si falta un candidato vigente y hay Windows compatible autorizado, prepara uno siguiendo MANUAL_TEST1 y su cadena `build_installer.bat` → builder mantenido → Inno Setup, con staging/salida nuevos y payload prístino preservado. Respeta sus preflight/dependencias/credenciales y ejecuta solo verificaciones técnicas pertinentes permitidas. No simules Windows con Linux/freezer mock, ni sustituyas Setup por ZIP. Si Windows/build está bloqueado, no abras el EXE antiguo: conserva el bloqueo y prueba únicamente otro candidato ya autorizado, con identidad/alcance aparte.

Usa perfil Windows/VM y base sintética aislados. Una carpeta diferente NO aísla AppId, registro HKCU, accesos directos, navegador ni rutas compartidas. Conserva instalaciones/portables anteriores; no actualices in-place ni desinstales al usuario. Ante colisión, bloquea lifecycle hasta disponer de aislamiento autorizado. Nunca empaquetes la base o configuración existente. El bootstrap `scripts/seed_admin.py` crea solo cuentas ausentes, no recupera ni resetea cuentas existentes.

## 3. Evidencia desde el primer minuto y recuperación de la sesión

Crea `implementation_documents/auto_testing_<AAAA-MM-DD>_<run-id>/`, nuevo, con fecha real. Los archivos empiezan locales; publica únicamente informes saneados en la rama autorizada si la autorización vigente lo permite. En otro caso, conserva los archivos y pide la autorización concreta; no publiques capturas privadas, bases o configuración. Guarda:

- `RUN.md`: candidato(s), fuentes, entorno/Windows, navegador/versión, resolución/escala, herramientas GUI, perfil/datos aislados, disponibilidad real de proveedor/modelo y límites de acceso, todo saneado.
- `COVERAGE.csv`: `case_id,manual_step,plan_id,historical_id,source_surface,role,candidate,variant,status,expected,observed,evidence_type,evidence_path,defect_id,timestamp,next_step`.
- `DEFECTS.md`: UN registro de defectos de esta ejecución, con IDs únicos `SLM-AUTO-001` en adelante; no sobrescribas los D/G históricos ni abras un archivo distinto por cada bug.
- `SESSION_LOG.md`: secuencia realmente realizada, IDs sintéticos, cambios reversibles de preparación, duraciones y recursos propios. No registres secretos.
- `RESUME.json`: run-id, identidad exacta, último caso/subcaso, rol/página, IDs, pendientes, bloqueos, siguiente acción concreta y recursos propios abiertos; nada de passwords/tokens.
- `SUMMARY.md` y `evidence/`: cierre honesto, capturas originales realmente inspeccionadas y comprobaciones técnicas necesarias saneadas. Conserva primera evidencia antes de reintentar.

Cada caso/variante empieza NOT_RUN. Estados: PASS (oráculo observado), FAIL (discrepancia), BLOCKED (falta requisito/permiso), PARTIAL (solo parte demostrada), NOT_RUN, NOT_APPLICABLE (contrato comprobado y motivo). Una ausencia que el producto promete se investiga como defecto, no se elimina de cobertura. Un error esperado legible puede pasar el caso negativo; nunca convierte el alta/inferencia fallida en éxito.

Separa evidencia GUI, TÉCNICA, PROVEEDOR_REAL y HUMANA/LECTOR/HARDWARE. Un HTTP 200, aria-label, captura no inspeccionada, mock, petición enviada o texto generado por ti no bastan para PASS GUI. Conserva versión/origen y subcaso con cada evidencia; una captura redimensionada no prueba responsive/zoom.

Guarda tras cada caso y antes de logout/reinicio. Si hay corte, verifica nuevamente candidato, procesos, cuenta, origen y archivos, lee RESUME y continúa desde el siguiente caso elegible; no repitas toda la batería, resembres usuarios ni borres locks sin demostrar que son propios y su dueño terminó. Un texto que solo estaba en memoria puede haberse perdido: no lo reconstruyas como resultado observado.

## 4. Inventario y método repetible para agentes pequeños

1. Lee `src/frontend/src/app/{route-contracts,feature-routes}.ts`, `features/*/routes.tsx`, controles/componentes y `features/*/locales.ts` pertinentes. Haz un mapa pantalla → rol → acciones → guardado/confirmación → caso. El código sirve de mapa/oráculo, no de aceptación GUI.
2. Expande la matriz con cada pestaña, editor, diálogo, empty/error/loading, menú y formato realmente existente, incluidos controles descubiertos durante el recorrido. Usa los casos siguientes como mínimo; ninguna función queda sin fila aunque sea bloqueada. Mantén subIDs estables (`AUTO-PEO-01.valid`, `.invalid`, etc.).
3. Observa pantalla/rol/datos; localiza la etiqueta visible; realiza UNA acción; espera estado/resultado; vuelve a observar antes de actuar. Reubica controles tras scroll, zoom, navegación o modal; no encadenes coordenadas ciegas.
4. Comprueba datos resultantes y reabre cuando haya persistencia. Toast «guardado» no sustituye lectura posterior. Un listado vacío exige distinguir vacío real, filtro activo, carga, error y falta de permiso.
5. Ante fallo, captura primero, registra esperado/observado, reproduce una vez si es seguro y hay hipótesis concreta. No borres evidencia ni repitas envíos inciertos: consulta el registro visible/lista/Enviados antes de decidir. Continúa casos sin esa dependencia.
6. Esperas iniciales: transición 15 s, guardado 30 s, inferencia local 120 s; amplía solo con progreso medible y motivo registrado. Mide inicio/fin; no fuerces cierres por un timeout arbitrario ni mantengas retries infinitos. Nunca mates procesos por nombre.

Aplicación transversal por formulario: válido, vacío, espacios, acentos/ñ, texto largo razonable, límites publicados, duplicado, error/corrección, cancelar, cambios sin guardar, doble clic y reapertura. No hagas fuzzing ilimitado. Diálogo: foco inicial, Tab/Shift+Tab, Escape si procede, cancelar/confirmar, retorno de foco y reapertura. Lista: vacío/uno/varios, sin resultados, limpiar filtro, selección, scroll real, detalle y volver.

Trabaja en tres pasadas, actualizando cobertura en cada una: I) funcional por administrador → docente → estudiante y vuelta al docente/estudiante; II) visual/teclado/idiomas/temas/responsive por rol; III) reinicio, persistencia, errores/retornos y regresiones. La segunda no sustituye la primera ni repetir el mismo éxito cuenta como una nueva superficie cubierta.

## 5. Datos sintéticos y dependencias

Usa sufijo de sesión único y datos de MANUAL_TEST2: T1 Docente Demo, S1 Alba Demo, S2 Bruno Demo; T2 Docente Contraste solo para reasignación. Usuarios/correos únicos `docente_<run>` / `docente.<run>@example.com`; `.invalid` se reserva para el negativo de correo. Las cuentas ya existentes no se adoptan ni resetean. Contraseñas se crean/introducen por la vía privada autorizada; no incluyas una contraseña común en este prompt o informe.

Curso privado «Fracciones cotidianas | <run>», unidad de práctica, tres lecciones L1 Partes iguales, L2 Comparar fracciones, L3 Comprobar la unidad; PR1 Denominador (en 3/8 el 8 es el total de partes iguales), PR2 Comparación (6/9 > 2/9 de la misma unidad). Conserva las claves solo en pantallas docentes. Usa la nota y solicitud «Misma unidad» del manual; sin datos de menores.

Evaluación manual de dos preguntas: opción múltiple 7/10 frente a 4/10 y respuesta corta sobre 2/5/partes iguales; 5 puntos cada una, 2 intentos, sin límite temporal, aprobado 60; rúbrica Numerador 2 / Denominador 2 / Partes iguales 1; política IA desactivada guardada por separado. La abierta lleva respuesta no vacía para probar revisión; un cero automático de respuesta vacía no demuestra ese flujo.

Prepara aparte archivos locales TXT/MD/PDF breves sintéticos, uno vacío/tipo rechazado, uno de extracción incompleta si existe fixture mantenida; nombres largos y homónimos diferenciados por usuario/ID. Las fixtures de escala 1/50/500 elementos y 100 lecciones solo van en base nueva documentada. Declara qué se sembró: no atribuyas a GUI la creación sembrada. El corte vertical mínimo crea y enlaza sus objetos DESDE LA GUI.

Orden de dependencias: BOOT/AUTH → PEO → CRS/MAT/EVA autoría → asignación → LEARN/EVA intento → GRADE/HELP → feedback/PORT. AI solo bloquea inferencia/generación, no estudio/manual/Q&A propio/ayuda al docente. Una cuenta inaccesible bloquea su rol, no los restantes. Reserva operaciones de reasignación/desactivación para después del corte básico.

## 6. Pasada I · Arranque, cuenta y administración

- AUTO-BOOT-01 · Setup actual: verificar identidad/handoff, abrir asistente por GUI, destino y perfil nuevos, finalizar e iniciar acceso directo.
  Oráculo: build correcto instalado sin tocar instalación previa; registrar cada advertencia. No eludir SmartScreen/certificado ni aceptar permisos imprevistos.
- AUTO-BOOT-02 · Arranque instalado desde fuera del checkout, sin Python/Node de desarrollo: observar launcher, espera/listo/error y «Dirección local»; abrir mediante «Abrir SLMEducator».
  Verificar proceso/ruta/puerto propios como evidencia técnica aparte; nada de URL asumida.
- AUTO-BOOT-03 · X NATIVA: guardar trabajo, pulsar X del launcher, observar confirmación, cancelar una vez, volver a X y confirmar si está autorizado.
  Debe cerrar ventana y SU árbol/puerto; cerrar pestaña o terminar un PID no equivale a X.
- AUTO-BOOT-04 · Reabrir acceso directo, comprobar misma cuenta/datos; «Detener» → cancelar/confirmar → detenido → «Iniciar» → listo → abrir.
  Registrar X y Detener separados, ausencia de procesos/puertos huérfanos y persistencia.
- AUTO-BOOT-05 · Puerto ocupado, arranque lento/fallido, apertura de URL por teclado y DPI: solo fixture/instancia propia aislada; observar estado y recuperación sin terminar ocupantes ajenos.
  Si no se puede preparar, BLOCKED por variante, no PASS inferido de tests.
- AUTO-AUTH-01 · Acceso válido y rechazo controlado inválido/vacío; comprobar rol/nombre, errores claros y no perder usuario.
  No fabricar lockout ni publicar secretos. Entrar como T1/S1/S2 solo con credenciales privadas autorizadas.
- AUTO-AUTH-02 · Cuenta y ajustes → Perfil: leer/editar datos sintéticos válidos, cancelar, guardar/reabrir; cabecera actualizada y ninguna cuenta diferente afectada.
  Contraseña: aviso de revocación, validaciones y reentrada tras rotación, con handoff antes de introducir/confirmar/enviar credenciales según política.
- AUTO-AUTH-03 · Logout con trabajo pendiente: cancelar mantiene trabajo; «Salir y conservar mis borradores aquí» conserva únicamente borradores soportados del propietario.
  Alternativa de borrarlos solo con autorización aplicable; cambiar a otra cuenta nunca muestra borradores privados anteriores. No prometas persistencia permanente del tutor.
- AUTO-PEO-01 · Admin → Personas → Crear cuenta T1: campos/rol válidos; negativo correo `@example.invalid`, corrección a `@example.com`, alta y detalle/ID.
  Un 422 debe indicar el campo sin `[object Object]`, JSON crudo ni error vacío; si lo frena el navegador, solo prueba validación local. Admin continúa conectado; no adoptes una cuenta existente.
- AUTO-PEO-02 · Admin crea S1, «Elegir docente responsable» → T1 → «Guardar matrícula» y confirmar identidad.
  T1 → Mis estudiantes ve S1; T1 crea S2 y queda a su cargo sin selector de rol de personal ni cambio a sesión de S2. Alta y matrícula tienen resultados separados.
- AUTO-PEO-03 · Buscar Demo, filtrar rol/estado disponibles, abrir ficha, Atrás del navegador y «Volver a la lista»; conservar filtros, selección y scroll real.
  Repetir Crear cuenta desde lista filtrada → Abrir cuenta → Volver; visita directa al detalle tiene retorno local seguro. G4.
- AUTO-PEO-04 · Tras el corte básico, T2 sintético: reasignar S1 T1→T2 con confirmación; matrícula cambia, asignación anterior permanece, T1 conserva autoría de evaluación/corrección y T2 no hereda notas privadas de T1.
  Verificar desde cada cuenta, sin suponer que pertenencia y autoría son iguales.
- AUTO-PEO-05 · En cuentas sintéticas prescindibles y con aprobación aplicable: desactivar/reactivar y observar historia/sesión; recuperación/reset requiere handoff.
  Auto-desactivación/último admin se prueba solo con fixture aislada segura y permiso, nunca dejando al usuario sin acceso. Registrar cada variante bloqueada por separado.
- AUTO-ADMIN-01 · Admin → Estado de la aplicación → actualizar: estado y versión honestos, sin afirmar diagnóstico completo; otro rol no dispone de la acción administrativa.
  No consultar recursos reales ajenos para demostrarlo.

## 7. Pasada I · Cursos, biblioteca, fuentes y generación

- AUTO-CRS-01 · T1 sin cursos: Cursos y materiales → Biblioteca de materiales → Crear material/Generar con IA y volver a Cursos.
  Admin repite descubribilidad; estudiante solo lectura autorizada. No escribir URL como sustituto de encontrar la función desde navegación. G3.
- AUTO-CRS-02 · Crear curso privado, título/descripción, unidad, crear L1/L2/L3 y guardarlas; guardar borrador DEL CURSO y reabrir estructura.
  Distinguir material guardado de posición/unidad guardada; cancelar edición y salida sucia no descartan sin aviso.
- AUTO-CRS-03 · Añadir material existente, unidades, orden y retirada de una referencia mediante controles realmente disponibles; volver a guardar/reabrir y comprobar títulos/orden/IDs sin borrar el material compartido.
  Aplicar negativos y doble envío a borrador separado.
- AUTO-CRS-04 · Revisar contenido → Marcar revisado → publicar con «Hacer público el curso» desmarcado → asignar solo a S1 y confirmar ID.
  Borrador/revisado/publicado/asignado son estados distintos; S2 no recibe acceso. Reabrir y comprobar contadores reales sin repetir asignación para cambiar cifras.
- AUTO-CRS-05 · Curso asignado queda solo lectura; Crear revisión → nuevo ID/borrador, originales/materiales/asignaciones preservados según contrato de copia.
  No publicar ni reasignar la revisión automáticamente. Evaluación publicada vinculada tampoco cambia silenciosamente.
- AUTO-CRS-06 · Buscar Fracciones → detalle → Atrás y enlace «Todos los cursos»; filtro/selección/scroll se conservan.
  Probar búsqueda sin resultados/limpiar y navegación directa segura. Scroll solo pasa con desplazamiento real. G4.
- AUTO-MAT-01 · Biblioteca: vacío/lista/filtro, lectura/detalle y editores de cada tipo ofrecido.
  Crear lección manual y prácticas PR1/PR2 con claves/opciones/explicación, Vista previa → guardar/reabrir → añadir al curso. Repetir tipos reales descubiertos; no inventar controles de vídeo/audio ausentes.
- AUTO-MAT-02 · Práctica: opciones con claves únicas, respuesta correcta válida, pregunta vacía/larga, eliminar opción seleccionada y corregir; tipos de ejercicio y límites según editor.
  Vista previa docente y render alumno sin revelar clave antes de responder. Material sin permiso no debe ofrecer edición ni contenido privado.
- AUTO-SRC-01 · Fuentes del curso: cargar TXT/MD/PDF sintético mediante selector nativo; observar propuesta extraída, nombre/cobertura/páginas ilegibles/truncamiento.
  Adoptar propuesta y guardar fuente son acciones distintas; editar texto, cancelar sustitución, recargar guardado y reabrir sin pérdida silenciosa.
- AUTO-SRC-02 · Fuente vacía/tipo no admitido y límite documentado (UI actual admite PDF/TXT/MD hasta 10 MiB): error legible sin reemplazar lo guardado.
  No subir archivos reales ni cargas enormes. Curso publicado/asignado respeta inmutabilidad y exige revisión; contenido sintético con marcas/listas se renderiza sin ejecutar código.
- AUTO-GEN-01 · Con proveedor local real permitido: Generar con IA → Lección individual, Matemáticas, Fracciones de la misma unidad, Personas adultas/iniciación; obtener propuesta, inspeccionar utilidad/coherencia y editarla antes de guardar borrador.
  Propuesta visible no significa publicada/asignada ni verificada por docente.
- AUTO-GEN-02 · Inventariar todos los modos realmente ofrecidos (lección, práctica/evaluación, esquema/paquete según candidato) y sus campos de fuente/curso/objetivos.
  Ejecutar petición pequeña de cada modo accesible; salida malformada debe ser error sin inventar contenido ni corromper trabajo previo. Separar fallo del modelo de fallo de flujo.
- AUTO-GEN-03 · Parcial 3/5, fallo de un elemento, parar/reintentar, edición humana mientras llega otro resultado y «Actualizar trabajos guardados»: solo fixture mantenida aislada o condición real segura, nunca cinco llamadas para forzar el patrón.
  Conservar ítems confirmados/edición y mostrar pendiente/fallido por elemento; no duplicar guardados ni reiniciar toda la operación. Fixture/mocks no son inferencia real.
- AUTO-GEN-04 · Esquema/curso generado, selección de unidades y guardado de fuente, recuperación del borrador local y recarga: revalidar propietario/curso/fuente antes de adoptar; no sobrescribir fuente revisada o texto humano al llegar una respuesta tardía.
  Operaciones de resultado incierto requieren lectura visible previa a reintentar.

## 8. Pasada I · Estudio, preguntas, tutor y progreso

- AUTO-LEARN-01 · S1 Inicio distingue continuar curso de reanudar intento; Mis cursos abre asignación correcta.
  S2 sin curso muestra vacío útil, sin datos de S1. Un alumno sin docente/proveedor puede escribir preguntas propias y leer lo que tenga autorizado.
- AUTO-LEARN-02 · S1 abre L1, lee, crea/edita/guarda nota, oculta/reabre herramienta, pausa y vuelve por Inicio; misma lección/nota y estado coherente.
  Cambiar a L2/L3, Anterior, volver, completar: posición y progreso correctos; no confundir pasar página/tiempo transcurrido con aprendizaje demostrado.
- AUTO-LEARN-03 · PR1 correcta e incorrecta, explicación y nuevo intento cuando exista; PR2 independiente.
  Respuesta/borrador/resultado y nota de práctica no se convierten en evaluación oficial. Cancelar/recargar y cambio de idioma conservan estado conforme al contrato y al propietario.
- AUTO-LEARN-04 · Aula con texto largo, encabezados, listas, enlaces/código inocuos y panel auxiliar: lectura principal accesible, solo herramienta seleccionada, scroll/foco y controles no perdidos.
  Ayuda contextual identifica curso/material; ocultarla no equivale a enviar otra petición ni a cancelación explícita.
- AUTO-QA-01 · Tutor y preguntas → Mis preguntas: crear pregunta personal manual, título/texto/respuesta propia/audiencia; guardar, editar y reabrir.
  Cambio de pestaña Tutor↔Mis preguntas conserva los cuatro campos NO guardados en nueva y existente; cancelar descarte/reselección no pierde texto. G1.
- AUTO-QA-02 · Compartir con docente según audiencia, volver a privado, comprobar visibilidad desde T1/S2; compartir NO envía un mensaje.
  Sugerencia de IA no se aplica/guarda sola: aceptar/editar/guardar explícitamente, sin machacar respuesta escrita mientras estaba pendiente.
- AUTO-QA-03 · Guardado pendiente/incierto al ocultar pestaña: conserva buffer, no replay POST/PUT, lectura con control visible antes de otro Guardar.
  Cambio real de pregunta/permiso/cuenta revalida y oculta lo ajeno. Borrar solo pregunta sintética propia con permiso/confirmación aplicable; cancelar conserva registro.
- AUTO-TUT-01 · Tutor libre y contextual con material verificado: preguntar, recibir respuesta real, otra pregunta que use historia; visitar Mis preguntas y volver conserva intercambio completado en misma cuenta/contexto.
  No exigir almacenamiento permanente tras salir del workspace/logout. G2.
- AUTO-TUT-02 · Repetir cambio de pestaña mientras petición sigue pendiente: puede terminar oculta y aparecer al volver, sin segunda petición ni conversación duplicada.
  Cancelar explícitamente es caso distinto; su respuesta tardía no reaparece ni se atribuye a otro contexto/cuenta. G2.
- AUTO-TUT-03 · Cambiar material/contexto, revisión de fuente o política de ayuda mientras hay respuesta pendiente: no entregar contenido obsoleto/prohibido.
  Solo provocar con fixture/acciones sintéticas permitidas; si no hay control reproducible, BLOCKED. Reintentar por control visible conserva identidad de solicitud cuando el contrato lo exige.
- AUTO-PROG-01 · Mi progreso: resumen, repasos, actividad, objetivo diario y participación/clasificación; abrir cada pestaña.
  Sesiones/minutos conocidos, duraciones desconocidas, autoevaluación y evidencia de evaluación FINAL se distinguen; cero no aparece como ausente ni progreso como garantía de dominio.
- AUTO-PROG-02 · Guardar objetivo diario válido, límites/vacío/corrección y reabrir; repaso conduce al material correcto; XP, insignias, rachas, periodos semanal/mensual/histórico y alcance por rol respetan contrato/privacidad.
  Registrar fechas legacy desconocidas como tales, sin asumir UTC a ciegas.

## 9. Pasada I · Evaluación, correcciones, solicitudes y mensajes

- AUTO-EVA-01 · T1 crea evaluación sintética vinculada al ID REAL del curso: dos preguntas, opciones/claves, puntos, rúbrica, intentos/tiempo/aprobado.
  Guardar borrador y reabrir no publica. Probar cada tipo real, validaciones/límites y borrar/reordenar solo borrador propio; no pegar JSON para saltar el editor.
- AUTO-EVA-02 · Guardar política de ayuda por separado, revisar definición, publicar y confirmar.
  Evaluación no tiene «Marcar revisado» del curso. Previa alumno no inicia intento ni consume límite; iniciar sí lo hace. Inicio diferencia curso e intento activos.
- AUTO-EVA-03 · S1 responde ambas preguntas, cambia página, revisa, vuelve y envía una vez; doble clic no crea doble entrega.
  Durante intento IA desactivada no filtra respuestas por tutor/Q&A/ayuda alternativa; práctica ordinaria fuera de intento mantiene su contrato.
- AUTO-EVA-04 · Variante temporizada separada con fixture pequeña: reloj, navegación/recarga/reanudación, vencimiento, respuesta local, desconexión y resultado incierto.
  No alterar reloj global ni repetir envíos a ciegas. Conservar estado y distinguir límite agotado de fallo de red; cada variante requiere evidencia propia.
- AUTO-EVA-05 · Cerrar sin enviar con confirmación, cancelar cierre, alcanzar máximo de intentos y consultar historial.
  Estado cerrado/enviado/provisional/final y puntuación cero son distintos; nunca reemplazar cero por «sin nota». No deducir estos casos de una entrega correcta.
- AUTO-GRADE-01 · T1 Correcciones → filtrar curso/estado → entrega S1; calificar pregunta abierta con feedback/rúbrica, revisar última pregunta y total, guardar y finalizar explícitamente.
  Pregunta objetiva puede autocorregirse incluso en modo manual; nota subjetiva IA sigue provisional hasta aprobación docente.
- AUTO-GRADE-02 · Variantes total/cero, modificar calificación permitida, sugerencia IA revisada/aceptada cuando disponible, recarga y retorno con filtros.
  No filtrar rúbrica/clave privada al alumno ni otorgar permiso por matrícula actual a quien no es autor; T2 y S2 se contrastan con sus cuentas sintéticas.
- AUTO-GRADE-03 · S1 abre feedback/historial: respuestas/notas/finalidad coinciden con corrección, ayuda liberada conforme al fin del intento; detalle/enlaces y fechas correctos.
  Consulta de historial no inicia intento ni altera resultados.
- AUTO-HELP-01 · S1 Solicitudes de ayuda → crear «Misma unidad» con contexto → guardar/enviar; continuar estudiando sin esperar al docente.
  T1 Solicitudes abre caso, responde; respuesta y resolver son acciones SEPARADAS. S1 ve respuesta/estado y enlace correctos, S2 no ve solicitud privada.
- AUTO-HELP-02 · Filtros/retorno, solicitud sin contexto permitido, cancelación, respuesta vacía/duplicada y resolución/reapertura si existe control; estados/permiso y contador coherentes.
  Mensaje enviado no resuelve silenciosamente ni borra historia.
- AUTO-MSG-01 · Entre cuentas ficticias locales: Mensajes → Escribir mensaje → buscar por nombre/usuario → elegir ID correcto → asunto/cuerpo → enviar → Enviados y receptor.
  Homónimos deben distinguirse; comprobar no leído/leído y retorno; sin contactos externos ni notificaciones a buzones reales.
- AUTO-MSG-02 · Selección individual/masiva, cancelación y resultado parcial con fixture mantenida: indicar éxitos/fallos reales sin duplicar envíos.
  Archivar afecta a ambos participantes según contrato actual; verificar ambos. No usar borrado irreversible para cubrir selección: requiere aprobación específica y prescindible tras Cancelar.

## 10. IA real disponible, ajustes y portabilidad

La fuente actual ofrece `ollama`, `lm_studio`, `openai`, `openrouter` en `features/settings/{AISettingsPage.tsx,contracts.ts}`. Esto demuestra adaptadores/opciones, NO servidores ni modelos instalados. La disponibilidad de LM Studio en una prueba de AAC no acredita este host, endpoint o configuración SLM. Descubre destino/modelo mediante UI/configuración documentada saneada; no adivines puertos, ID, API key ni compatibilidad.

Usa solo runtime local ya disponible/autorizado y un modelo existente compatible. No claves nuevas, proveedores de pago, modelos/descargas masivas o cambios de servicio compartido. Si falta, IA queda BLOCKED y prosigue lo demás. No cambies globalmente el proveedor ni envíes datos reales para obtener un PASS. Configuración de IA es por cuenta; guarda qué cuenta efectuó cada petición.

- AUTO-AI-01 · Cuenta y ajustes → Proveedor y modelo: observar valores guardados, proveedor/modelo/endpoint/temperatura/límite y opción reasoning de LM Studio si procede.
  Guardar/reabrir/reiniciar y comprobar misma cuenta; otra cuenta no hereda configuración. Cambiar destino puede retirar clave guardada: no hacerlo sin decisión/handoff aplicable.
- AUTO-AI-02 · Probar conexión explícitamente con destino local permitido; registrar proveedor/modelo/latencia.
  Este control usa campos del formulario y NO los guarda. Catálogo es otra acción explícita, desde destino guardado coincidente; vacío/error/obsoleto no se presenta como lista válida de otro proveedor. Nunca cargar/probar cloud en segundo plano.
- AUTO-AI-03 · Solicitud pequeña real iniciada en GUI (tutor libre/contextual, Q&A, ayuda, generación/calificación según rol y cobertura): correlacionar acción, actividad del runtime y respuesta visible, sin publicar payloads privados.
  Un health check, catálogo, fixture, conexión o texto fijo no prueba inferencia ni utilidad educativa.
- AUTO-AI-04 · Respuesta breve/larga ES/EN, caracteres, código/listas inocuos, modelo lento, Cancelar, no disponible y recuperación: sin doble petición ni entrega tardía a otro contexto.
  Separar respuesta errónea del modelo, formato rechazado, fallo de transporte y pérdida de trabajo de UI. Error seguro no equivale a respuesta útil.
- AUTO-SET-01 · Apariencia e idioma: todos los controles reales, guardar/cancelar/reabrir; diferenciar controles de cabecera locales al navegador de ajustes de cuenta guardados.
  Tamaños de lectura no equivalen a zoom. Zona horaria válida/inválida, fecha local y mensajes/historial: persistencia y formatos, sin cambiar reloj/OS.
- AUTO-PORT-01 · S1 Exportar curso → Copia de lectura HTML/Markdown/JSON: preview por audiencia, inclusiones/exclusiones, descargar con confirmación y abrir archivo local.
  Legible, curso correcto, sin claves/rúbricas privadas, trabajos de otros, contraseñas ni configuración. Cambiar selección/formato invalida preview anterior; sin preview vigente no descargar otro destino.
- AUTO-PORT-02 · T1 exporta paquete docente JSON propio tras preview: contiene material docente según contrato y se mantiene privado.
  Importar ese paquete → validar preview → crear nuevo borrador explícito → nuevo ID; original/asignaciones intactos. Archivo vacío/malformado/tipo de lectura incorrecto produce error, no importación parcial silenciosa.
- AUTO-PORT-03 · Admin Copias de seguridad → preview/alcance → descarga local sintética `.slmbackup`; otros roles no tienen acceso.
  Backup de base no equivale a instalador completo ni handout; puede contener material sensible aun sintético. No adjuntarlo/publicarlo. Restauración solo procedimiento mantenido en destino sintético nuevo, no inventar botón GUI de restore.
- AUTO-PORT-04 · Reabrir copias/exportaciones con visor nativo e inspección técnica saneada complementaria, con identidades/cantidades esperadas.
  Cancelar diálogo/descarga, pérdida de sesión y cambio de cuenta invalidan preview/entrega; ninguna descarga antigua se entrega bajo otra identidad.

## 11. Pasada II · Apariencia real, accesibilidad y escalas

Revisa como mínimo login, Inicio de los tres roles, alta/ficha Personas, Cursos/biblioteca/editor, aula, intento/feedback, Correcciones, Tutor/Mis preguntas, solicitudes/mensajes, ajustes/exportación y launcher. Captura estados vacío/contenido/error/diálogo relevantes. Evalúa jerarquía, anchura útil, densidad, alineación, consistencia, contraste, legibilidad, acciones primarias/destructivas, scroll y textos largos, no solo «se ve moderno».

- AUTO-VIS-01 · Menú por rol agrupa trabajo comprensible; página activa/título/migas/volver permiten orientarse sin URLs adivinadas.
  Alta/editor no son absurdamente estrechos; no hay solapamientos, recortes, controles invisibles ni acciones fuera de alcance. Cubre D1/D2 históricos con evidencia actual, no con opinión sobre el CSS.
- AUTO-VIS-02 · Español/English en cabecera y ajustes, claro/oscuro/sistema, tamaños de lectura y errores/estados/modales: etiquetas completas, sin claves de traducción ni mezcla imprevista; contenido del usuario permanece original.
  Registra preferencia inicial real y restaura solo lo cambiado por la prueba.
- AUTO-VIS-03 · Solo teclado en un recorrido por rol: Tab/Shift+Tab, Enter/Espacio según control, flechas cuando procedan, Escape, skip-link, apertura/cierre de navegación y diálogos.
  Orden/foco visibles, sin trampas, vuelta al invocador y ningún envío accidental; no usar clics para salvar el subcaso teclado.
- AUTO-VIS-04 · Zoom NATIVO 100→200→400%, acreditado por menú del navegador, en las pantallas críticas; reflujo y controles/foco accesibles.
  Luego zoom 100% y viewport de 320 CSS px medido con la UI responsive del navegador si está disponible y permitida; repetir anchuras medias/escritorio. No ejecutar JS ni CSS zoom; sin medición fiable, BLOCKED/PARTIAL.
- AUTO-VIS-05 · G5: guardar animaciones desactivadas, ir Inicio, recargar/reabrir sin visitar Ajustes; observar comportamiento reducido y luego confirmar valor.
  Cambiar cuenta no hereda preferencia previa; reducción del OS prevalece según contrato. Una casilla desmarcada NO prueba aplicación visual; si no hay movimiento observable, registra límite técnico/visual, no inventes PASS.
- AUTO-VIS-06 · Lector de pantalla real disponible: identificar producto/versión, recorrer login/formulario/aula/intento/modal, labels/errores/estado/foco y lectura sin duplicaciones.
  Solo PASS si su salida fue realmente percibida/registrada. ARIA/código/capturas no prueban pronunciación/lectura; sin acceso acústico o salida verificable, BLOCKED.
- AUTO-VIS-07 · Launcher/Setup con escala Windows/DPI y navegación por teclado disponibles sin cambiar configuración sensible: texto/URL/estado completos, botones distinguibles.
  Hardware, audio/salida acústica, lector y compatibilidad Windows son evidencias propias, nunca deducidas de web/API. No inventes pruebas de audio de una función SLM inexistente.
- AUTO-SCALE-01 · Fixtures sintéticas 1/50/500 elementos y curso de 100 lecciones: búsqueda/filtros/scroll/abrir/volver/estructura; medir tiempos reales en hardware/estado identificado.
  Objetivos del plan: interacción <100 ms e inicio útil <2,5 s; instrumentación auxiliar permitida sin automatizar GUI o estimación marcada como tal. Sensación de rapidez no verifica esos umbrales. G7 permanece abierto si no se mide.

## 12. Pasada III · Persistencia, aislamiento y fallos

- AUTO-REG-01 · Reabrir tras guardar y tras cerrar/reiniciar instancia propia: cuenta rotada, matrícula, curso/unidad/orden, asignación, notas, evaluación/entrega/feedback, pregunta, mensajes, preferencias y exportaciones coinciden.
  El tutor conserva pestañas durante workspace, NO promete historia permanente al salir/reautenticar; expectativas por dato, no «todo persiste».
- AUTO-REG-02 · Repetir G1 nueva/existente con cuatro campos sin guardar, G2 completada/pendiente/libre/contextual, G3 docente/admin sin cursos y estudiante, G4 Cursos/Personas (Atrás/enlace/crear→detalle/scroll), G5 reapertura/cambio cuenta.
  Registrar cada variante, no cerrar todos por un caso feliz.
- AUTO-REG-03 · Reautenticación misma cuenta/otra cuenta, sesión expirada/403 y pestaña previamente abierta: usar mecanismos ordinarios/fixture permitida, nunca forjar tokens ni cambiar credenciales para saltar política.
  Misma cuenta revalida recurso antes de mostrar buffer; distinta cuenta oculta privados; no replay de mutaciones/inferencia. BFCache/otra pestaña/storage fallido son variantes separadas y requieren observación real.
- AUTO-REG-04 · S2 abre enlace real conocido de curso/entrega/pregunta de S1 dentro del mismo origen mediante barra nativa, solo recursos sintéticos de esta campaña: sin contenido privado y error útil.
  Menú oculto solo prueba presentación. Una filtración detiene esa rama y conserva evidencia mínima; no continuar explorando datos ni convertirlo en auditoría ofensiva.
- AUTO-REG-05 · Separar tres indisponibilidades: Internet ausente con app/modelo locales funcionando; proveedor caído con app accesible; servidor propio detenido con navegador abierto.
  Preparar solo aislamiento autorizado, sin tocar red global ni servicios compartidos. Verificar mensajes diferentes, trabajo conservado y recuperación explícita; export HTML legible no prueba API offline.
- AUTO-REG-06 · Guardado/envío de resultado incierto, errores 422/403/409/5xx accesibles, carga lenta/vacía: mensajes comprensibles, valores preservados, control de lectura/reconciliación antes de reintento, sin duplicados.
  No inyectar respuestas con scripts/DOM ni fingir red caída; sin fixture segura, marcar el subcaso pendiente.
- AUTO-REG-07 · Navegación atrás/adelante, recarga, deep-link real/404, enlace legacy documentado y destino inexistente: ruta React válida o error real, sin segunda GUI, datos ajenos o fallback HTML que simule éxito de API.
  No levantar `src/web` ni probar rutas de seguridad previamente denegadas.
- AUTO-SW-01 · Instalación fresca: no registrar SW como si existiera offline API.
  Migración solo con perfil sintético y fixture legacy mantenida autorizada: pestaña antigua con borrador + segunda pestaña, esperar ciclo normal, cerrar segunda no destruye primera, guardar antes de cerrar última y reabrir; nada de `skipWaiting`, unregister o borrar datos a mano.
- AUTO-SW-02 · Verificación técnica separada por UI del navegador/observación permitida: verificar que la aplicación retira solo `slm-educator-v22-session-locale` y `slm-educator-v22-session-locale-auth-validation`, conservar caches ajenos/borradores.
  Fallo de red durante transición requiere variante propia. Sin fixture antigua legítima, BLOCKED; no instalar legacy en perfil del usuario.
- AUTO-LIFE-01 · Solo perfil Windows desechable autorizado: rechazo de instalación in-place, portable ajeno preservado, desinstalar/reinstalar exclusivamente copia propia con permisos aplicables, conservar base/config sintética distintas del seed.
  AppId/HKCU/accesos y datos son comprobaciones distintas; sin aislamiento lifecycle queda BLOCKED y no se limpia registro para avanzar.

## 13. Trazabilidad obligatoria: manuales, plan y defectos históricos

Expande a UNA FILA POR SUBPASO/VARIANTE del manual y cada control descubierto; los rangos siguientes son mapas, no resultados globales. Todas las filas nuevas empiezan NOT_RUN. Conservar IDs del manual aunque esta campaña la opere el agente. No copiar la obligación humana de esperar cada campo.

| Origen | Casos AUTO mínimos |
|---|---|
| M1 punto de partida/límites; §1.1–4; §2.1–5; §3.1–7; §4 handoff | RUN/candidato y preparación §2–5; BOOT-01–05, AUTH-01–02, LIFE-01; checks técnicos con fila propia, nunca PASS GUI |
| M2 A.1.a–c, A.2.a–e, A.3.a–k, A.4.a–d, A.5.a–e | BOOT-01–04, AUTH-01–02; incluir todos los campos/confirmaciones y separar X de Detener |
| M2 B.1.a–t y G4; B.2.a–o; B.3.a–t; B.4.a–h; B.5.a–e | PEO-01–03, CRS-01–06, MAT-01–02, EVA-01–02 |
| M2 C.1–5 | AI-01–04; proveedor existente por cuenta, sin copiar una confirmación vieja de AAC |
| M2 D.1.a–j, D.2.a–f, D.3.a–f; D.4.a–i, D.5.a–l; D.6–7 | LEARN-01–04, HELP-01, QA-01–03, TUT-01–03, REG-02–03/05–06; D.7 es control de cobertura, no permiso para omitir variantes |
| M2 E.1.a–f, E.2.a–f, E.3; E.4.a–j, E.5.a–d | EVA-02–05, GRADE-01–03, HELP-01–02; distinguir previa/inicio/cierre/envío/provisional/final |
| M2 F.1.a–e, F.2.a–e, F.3, F.4.a–i, F.5 | CRS-01, REG-04, QA-02, PORT-01–04, REG-05, SW-01–02, VIS-01–07, REG-01 y cierre §15 |
| M2 datos, navegación/cambio cuenta, incidencia y adicionales | Fixtures §5; AUTH-03, PEO-04–05, GEN-01–04, MSG-01–02, PORT-02, SCALE-01; aplicar método §4 a todos |
| Plan E1 / E2 / E3 / E4 | LEARN-01 + AI; EVA-02 + LEARN-01; LEARN-02–03; AUTH-03 + REG-03 |
| Plan E5 / E6 / E7 / E8 | EVA-03–04; EVA-05 + GRADE-03; TUT-01–03 + LEARN-04; QA-01–03 + PORT-01 |
| Plan D1 / D2 / D3 / D4 | PEO-01–02; CRS-02–04 + LEARN-02 (corte GUI íntegro); GEN-01–04; CRS-05 + PORT-02 |
| Plan D5 / D6 / D7 | GRADE-01–03; HELP-01–02; MSG-01–02 |
| Plan A1 / A2 / A3 / A4 | AUTH-02 + PEO-05 + ADMIN-01; PEO-04 + GRADE-02; PORT-01–04 + LIFE-01; AI-01–04 |
| Plan X1 / X2 / X3 / X4 | VIS-01–03/05–07; VIS-04 + SCALE-01; REG-05–06; BOOT-01–05 + REG-01/07 + SW-01–02 + LIFE-01 |
| DEFICIENCIAS histórico D1 / D2 / D3 | VIS-01 (jerarquía) / VIS-01–04 (estilos/anchura/tema) / PEO-01 (alta válida + 422 legible); prefijo H-D evita confundirlos con Plan D1–D7 |
| G1 / G2 / G3 / G4 / G5 | QA-01–03 / TUT-01–03 / CRS-01 / PEO-03 + CRS-06 / VIS-05; repetir variantes en REG-02 |
| G6 / G7 | G6 es deuda de código compartido: inventario/diagnóstico técnico, no PASS GUI ni refactor de campaña; G7 → SCALE-01, sin prometer rendimiento no medido |

Los 23 escenarios E1–E8, D1–D7, A1–A4 y X1–X4 deben aparecer individualmente en COVERAGE. Si dispones de `PLAN_MATRIX.json`/`REVIEW.md` del audit de gaps, úsalos como mapa histórico, no como resultados del candidato actual. No dependas de rutas privadas externas al repositorio para poder ejecutar este prompt.

## 14. Cómo registrar cada defecto

Añade al único DEFECTS.md una entrada en cuanto exista evidencia. Agrupa reproducciones del mismo bug y relaciona casos, sin borrar su primera observación. Problema de entorno/permiso no demostrado como fallo de producto se registra como bloqueo, no se inventa como bug.

Formato mínimo por `SLM-AUTO-NNN`:
- Título específico; estado `OPEN` / `NEEDS_REPRO` / `NOT_REPRODUCED_CURRENT`; severidad y motivo: S1 pérdida/exposición grave o arranque esencial bloqueado, S2 flujo esencial roto, S3 función degradada, S4 presentación menor. Prioridad separada de severidad.
- Fecha/run, candidato/Setup/SHA, Windows/navegador/escala/idioma/tema, rol y fixtures/IDs no secretos, precondiciones y caso/manual/plan/regresión relacionados.
- Pasos numerados ejecutables desde pantalla conocida, datos sintéticos exactos, esperado y observado literalmente; frecuencia/reintento acotado y efecto sobre datos/flujo.
- Captura antes/después/error realmente vista, referencia de log técnico saneado si aporta, tiempos y qué NO pudo verificarse. No poner bases ni secretos como prueba.
- Hecho observado separado de causa comprobada e hipótesis de diagnóstico; alternativa temporal segura si existe. No llamar «arreglado» a algo porque pasa un test histórico ni cambiar producto durante la campaña.

Ejemplo de distinción: «la UI muestra [object Object] al enviar» es observación; «POST 422 correlacionado» es técnica; «falló el dominio del correo» necesita evidencia concreta, no se deduce del viejo log. Cada nueva regresión enlaza H-D3/G1/etc. sin renumerar o cerrar el informe histórico.

## 15. Cierre, pausa y criterio de terminado

Termina cuando todo caso/variante inventariado tenga evidencia actual o un motivo específico de bloqueo/no ejecución/no aplicabilidad, y no queden acciones independientes útiles permitidas. Un smoke, una pasada, un rol o el primer fallo no son la campaña completa. Si una aprobación es esencial, conserva pregunta pendiente, cobertura y siguiente acción; no simules consentimiento ni abandones silenciosamente el resto.

SUMMARY incluye: candidatos exactos; totales por estado/rol/superficie/pasada y denominador explícito; cobertura manual/23 escenarios; defectos por impacto con links locales; funciones realmente observadas, IA real por cuenta/proveedor/modelo y límites; diferencias respecto a informes antiguos; build/Windows/GUI/lector/hardware/SW/rendimiento/proveedor como evidencias separadas; bloqueos con mínima acción necesaria y ruta RESUME.

No declares «100% funcional», «sin bugs», «seguro», «accesible», «Windows certificado», «80% de cobertura» o «todos los proveedores compatibles» sin la prueba específica. Calidad educativa best effort, adecuación para menores, eficacia de aprendizaje y cumplimiento normativo no se certifican aquí. La evaluación visual debe explicar problemas concretos, no vender una auditoría como aprobación automática.

Guarda todo, restaura solo preferencias/zoom y recursos propios de preparación cuando sea seguro; conserva datos y capturas de evaluación. No borres instalaciones, cuentas, mensajes o evidencia por limpieza automática; no cierres trabajos ajenos ni detengas un runtime compartido. Si David dice «para», detén nuevas acciones, guarda el punto exacto y entrega informe parcial. No programes nuevas campañas. Si existe autorización vigente para entregar informes en una rama, publica solo el informe saneado, verifica bytes/commit y entrega el enlace; de lo contrario, conserva su ruta y solicita la autorización concreta. Nunca publiques evidencia privada o binarios.

FIN DEL PROMPT
