# SLMEducator — candidato Windows, 2026-10-05

## Decisión y pendientes concretos

**Bloqueado para aceptación de producción.** Se han implementado reparaciones, construido y probado un nuevo EXE Windows y conservado la instalación sintética configurada. El consolidado técnico final pasa. La evaluación semántica estricta admite **34/36** salidas: 23/25 conocidas y 11/11 nuevas reservadas. Los resultados no favorables se conservan y se detallan abajo; no se convierten en éxito estructural o aprobación docente.

El usuario ha aplazado el piloto hasta resolver los problemas: **no se le pide validar los fallos restantes**. La aceptación humana docente/alumno y el cierre con la X nativa del último EXE siguen sin ejecutarse. No se atribuye al modelo como única causa la definición defectuosa que ya figuraba en una fuente sintética. Tampoco se promete que un generador respete cualquier fuente o corrija cualquier error de origen al 100 %. Alcance: aplicación local, un proceso/worker, roles actuales y borradores con revisión docente previa obligatoria; sin certificación regulatoria, aprendizaje, menores o exposición de red.

## Base, conservación y artefacto exacto

Fetch y SHA remoto de `origin/fix/local-provider-acceptance-20261005`: **6c1d92f5120197ffc23ca0cb6594f624d0f51ed4**, sin avance respecto al solicitado. Rama aislada: `fix/production-readiness-windows-20261005`. Checkout original conservado en **59644dfb90504788024b65889887fbf47fd6670f**; ninguna base/configuración privada se abrió, copió, reseteó o empaquetó. Se leyeron AGENTS.md, README.md, CONTRIBUTING.md, requisitos funcionales y los tres informes previos. Los 936 Python/171 DOM/ocho browser anteriores son antecedentes de su SHA.

Runtime final **cb95fd9b8fc9bcae89083c6bbf7f303b8aa10f03**, prompt `teacher-reviewed-v8-objectives-are-not-evidence`. Respecto a 33c94b6 sólo cambian el método existente `generate_lesson` y la versión de sus metadatos; transporte, generación de ejercicios/evaluaciones, permisos, recuperación y assets permanecen, y los gates técnicos se ejecutaron otra vez. El SHA de entrega documental se verifica en la rama remota sin insertar recursivamente el hash del informe.

Paquete completo local: `dist/SLMEducator Verified RC 20261005 ñ/`, EXE SHA-256 **268245fd2b3e9a9c72b2115cbc0712f20dcf35788f86a7931ffb2eaef83270b3**. Incluye `_internal` (2457 ficheros de runtime inventariados); no depende del venv ni exige instalar librerías manualmente. [Manifiesto final](evidence/windows_objective_20261005.json), SHA **604cf510f48933e0399a99ce4b93a114c4419a0cf7535f7643c1b12efe2632e6**, relaciona fuente, bundle, ejecutable, cobertura y recibos. No se suben builds, modelos, instaladores, bases, configuración, claves o logs privados.

Las entregas/evaluaciones anteriores permanecen: [manifiesto v6](evidence/windows_followup_20261005.json), [inferencia v6](evidence/local_provider_followup_20261005.json), [inferencia original](evidence/local_provider_20261005.json). Sus ejecutables/resultados no certifican los cambios v7/v8.

## Reparación adicional y FAIL antes de FIX

Se investigó el flujo existente fuente/objetivo → prompt → proveedor → parser → guardado → revisión → clase, sin añadir otro motor ni un detector universal de alucinaciones. La tarea anterior abría con el tema y relegaba objetivos; ofrecía campos opcionales que favorecían introducciones y vocabulario no necesarios. La revisión v7 coloca primero los objetivos y limita expansiones. Su prueba contractual falla antes y pasa después (23 pruebas afectadas). Se conservaron las 25 inferencias v7: Zil mejora, pero Teli todavía inventa uso, el contador omite aclaración y aparece una clasificación de Dali como animal y una pregunta genérica innecesaria sobre plantas ficticias.

La revisión v8 distingue peticiones docentes de hechos: una palabra del objetivo no demuestra propiedades, finalidad ni pertenencia a una categoría. Pide aclaración en el cuerpo, separa propiedades compartidas de clasificación y acota preguntas opcionales. Se repitieron los 25 casos conocidos y se ejecutaron por primera vez once fuentes nuevas reservadas, sin ajustar prompts/configuración después de observarlas. Sólo dos reparaciones acotadas y el mismo modelo/parámetros; ninguna selección de ejecución favorable. La omisión residual del contador permanece visible, aunque las dos cifras y la falta de autoridad se describen correctamente.

La fuente conocida `followup-level` dice literalmente «Half means two groups with the same number». La definición mala ya estaba en la fuente. El 21/25 histórico y sus puntuaciones no se borran: se añade una corrección de interpretación que separa fidelidad a fuente de exactitud educativa. En v8 se sigue puntuando la inexactitud, sin presentarla como pérdida de fuentes o fallo de transporte. El nuevo caso de nivel usa una definición inequívoca de un tercio. No se modifica silenciosamente la fuente antigua ni se elimina el caso incómodo.

El consolidado v7 iniciado mientras se depuraba quedó cancelado y marcado como **no consolidado**, con log parcial conservado. Después se congeló v8 y se completó el consolidado final sin editar código/assets durante su ejecución. No se emplea un pase enfocado para ocultar un consolidado fallido.

## Reparaciones anteriores conservadas

| Causa/defecto demostrado | Reparación y evidencia antes/después |
|---|---|
| Presupuesto incompatible con formato, ejemplos copiables y demanda excesiva | Se mantiene el motor existente; esquemas sin respuestas de plantilla, extensión acotada y objetivos/fuentes separados. Rechazo explícito de salida truncada. Respuestas fallidas originales conservadas. |
| Razonamiento interno consumía tokens aunque sólo se pedía una respuesta corta | Opt-in `reasoning_effort=none` exclusivamente para LM Studio compatible; prueba nativa HTTP 200 del parámetro y comprobación real de configuración. Presupuesto global 4.000, lección/evaluación 4.000, ejercicio 2.000; no se elimina el guarda de truncamiento. |
| Tipo abierto se perdía en Full Package y acababa en MCQ | `assessment_question_types` explícito, selector existente y validación del tipo solicitado. Tres preguntas abiertas reales guardadas; las notas finales siguen pendientes del docente. |
| Objetivos elegidos por el docente podían desaparecer | Objetivos explícitos autoritativos después del parser y en el flujo guardado; visibles en visor, editor y clase. Tests antes/después, API y Chrome. |
| Fuentes enviadas se confundían con respaldo demostrado | Estados separados: estructura válida, respaldo `unverified`, revisión y publicación. Recibo numérico seguro por API/clase; selección parcial visible. No se convierte una cita generada en comprobación factual. |
| Observar riego se convertía en prescribir cuidados; derivaciones legítimas se declaraban imposibles | Prompt v6 distingue observación, información ausente, conflicto y aritmética sustentada. Sus cuatro resultados no aceptados permanecen como antecedentes; la reparación y evaluación v8 se detallan arriba y abajo. No se ocultan con heurísticas de palabras prohibidas. |
| Guardar una lección descartaba objetivos/vocabulario/resumen y trazabilidad; editar ejercicio destruía su pregunta/opciones/clave | Lección completa editable como Markdown, con metadatos de origen preservados; controles estructurados de ejercicio y respuesta. Visor/editor/clase comparten `lessonText`. FAIL DOM conservado, seis regresiones DOM actuales y recorrido Chrome con PUT/GET reales. Error/reintento conserva texto; doble clic no duplica el guardado. |
| La clase ignoraba `hints[]` y perdía avance de pistas al interrumpir | Pistas progresivas, una por clic, sin revelar todas; estado del mismo usuario/intento recuperable junto con respuestas. Tests de primera pista, agotamiento y restauración. |
| Campos docentes de ejemplo/repaso y preguntas de discusión no llegaban a clase/tutor | Lista explícita de campos instructivos y validación de texto, representación canónica compartida. Siete pruebas Python comprueban visibilidad y exclusión de rúbricas/objetos privados. |
| Selector de fase ofrecía siempre Phase 1; list/detail no contienen fases | Consulta al contrato autorizado `/tree`, fases reales, errores visibles y bloqueo mientras no estén disponibles; resultados tardíos no pisan otra selección. Nivel adulto principiante disponible sin forzar Universidad. Chrome comprueba dos fases y DOM el fallo/resultado obsoleto. |
| Preview no mostraba las preguntas de `assessment.questions`; textos de guardado/error seguían en inglés | Usa el contrato actual y traducciones ES/EN existentes. La prueba que esperaba el error inglés falló en ES: se actualizó su expectativa bilingüe conservando detalle/error/reintento, y pasaron los 12 recorridos. |
| Tipos de fábrica global no admitían RuntimeAIConfig | Unión explícita coherente con AIService. Dos errores de mypy antes; ocho archivos sin errores después. No altera selección de proveedor. |
| Fixture frozen pretendía reservar 8000 aunque ya estaba ocupado | Ocupa el siguiente puerto que el launcher elegiría; comprueba que ese listener sobrevive a arranque/cierre. FAIL 13/14 conservado; repetición 14/14 y repetición final 14/14. No se cerró la app ajena ni se retiró la prueba. |
| Worker podía instalar parcialmente/mezclar cachés; menú móvil fallaba al inicializar tarde | Instalación atómica, caché propia, actualización esperando cierre de clientes y 503 ante recurso ausente. Inicializador compatible con DOM cargado. Browser actual v14→v20, offline→conexión y zoom nativo 200 %. |
| Restauración interrumpida dejaba destino parcial y EXE sin consola no ofrecía recibo | Temporal+fsync+promoción create-only en NTFS; `--recovery --result-file` separado. Proceso interrumpido realmente, reintento íntegro, rechazo de archivo inválido/destino existente y reapertura por API frozen. |

No se añadió otro motor, detector universal de alucinaciones, juez LLM, permisos paralelos, microservicios ni multitenancy. Se comprobaron consumidores antes de eliminar la duplicación de renderizado. Los campos desconocidos de autor se conservan; las representaciones del alumno siguen usando allowlist.

## Requisitos por rol y recorrido

| Rol/recorrido | Cerrado técnicamente con datos sintéticos | Pendiente/límite |
|---|---|---|
| Administrador | Bootstrap create-only, cambio de contraseña, reinicio que conserva estado/desactivación, recuperación y permisos; primer login de EXE real | X nativa del artefacto final durante piloto; no cuenta universal que omita permisos |
| Dos docentes/dos alumnos | Usuarios separados, IDs ajenos, roster, matrícula/retirada, escritura sin rol, sesión caducada/revocada, desactivación, reintento y aislamiento | No aislamiento SaaS/múltiples procesos |
| Importación TXT/Markdown/PDF | Fuente/hash/extracción, vacío/dañado/hostil, tamaño y límites | PDF escaneado sin OCR o extracción parcial requiere fuente corregida |
| Temario/fuentes/revisiones | Crear/editar, reemplazar fuente invalida revisión, copias asignadas inmutables, versión y fragmento trazables | Enviar fuente no demuestra fidelidad de respuesta |
| Generación parcial | Guardar elementos correctos, repetir mismos IDs, reintentar sólo fallidos, no aprobar por éxito estructural | Error semántico puede entrar en borrador; docente debe detectarlo |
| Revisión/publicación/asignación | Borrador sin revisar devuelve 409; evaluación vinculada se publica primero; curso revisado después; acceso se retira | Revisión humana efectiva pendiente |
| Clase | Orden/objetivos, práctica/pistas progresivas, respuesta, notas, progreso, pausa/recarga/reanudación | Comprensión y utilidad educativa requieren participante/educador |
| Corrección | MCQ automática con clave, pregunta abierta manual/AI-assisted pendiente, `null` distinto de cero, feedback/revisión/recarga | Sugerencia IA no es nota final ni criterio pedagógico validado |
| Exportar/importar | Permisos, integridad, remapeo de relaciones, otra instalación limpia y entrada privada como borrador | No publica/matricula automáticamente; handout excluye claves/rúbricas |
| Backup/restore | Archivo cifrado, clave coincidente, otra ruta/instalación, cinco cuentas, fuentes/cursos/asignaciones/progreso/notas | Conservar clave aparte; sin sobreescribir destino ni prometer recuperación sin clave |

## Inferencia real final y evaluación semántica

LM Studio nativo **0.4.25.0**, CLI local, llama.cpp CUDA12 avx2 **2.51.0**, adaptador `lm_studio` de la aplicación, `/v1/chat/completions`. No es la prueba anterior de Qwen 0,5B ni certifica Ollama nativo. Modelo existente [unsloth/gemma-4-12B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF/tree/980b060c40a8539ac159e0501a3e0f66a6365af3), revisión **980b060c40a8539ac159e0501a3e0f66a6365af3**; `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf`, 6.716.356.800 bytes, SHA **90fd44e29e0d7cffeb0fd00dc73cfdab9ed0b0e95306ecf7821ea634c940c370**.

Ryzen 9 8945HS/ocho núcleos, 32 GiB RAM, RTX 2000 Ada Laptop/8.188 MiB VRAM verificados con nvidia-smi. Servidor **127.0.0.1:1234**, alias `slm-production-evaluation`, contexto **8.192**, GPU 0,9/44 capas, seis hilos CPU, paralelo uno. Configuración admitida: temperatura **0**, máximo global **4.000**, `reasoning_effort=none`; lección/evaluación 4.000, ejercicio/esquema 2.000, selección de fuente hasta 6.000 caracteres. Cambiar modelo/configuración queda fuera de esta aceptación. Se verificó el parámetro mediante petición nativa HTTP 200 y metadatos, sin presuponer soporte universal; documentación contrastada de [compatibilidad](https://lmstudio.ai/docs/developer/openai-compat/chat-completions) y [metadatos LM Studio](https://lmstudio.ai/docs/developer/rest/list).

Rúbrica fijada antes de inferencia: `tests/fixtures/local_semantic_objective_20261005.json`, SHA **cf3c6d9c6e0e02004368aaabd0c86332a56429b13b059e17d8d14fdc93ddf107**. Los 25 anteriores son desarrollo conocido; once nuevos reservados cubren explicación, cálculo, insuficiencia, contradicción, temario malicioso, texto largo, ambigüedad, nivel, MCQ, pistas y abierta. Cinco dimensiones manuales técnicas 0/1/2: exactitud, fidelidad, utilidad, legibilidad, ausencia de información; aceptado sólo con cinco doses. No juez LLM ni aceptación educativa humana. Se inspeccionan hechos/opciones/claves/explicaciones y conducta, no sólo marcadores de ataque.

[Todas las solicitudes/respuestas sintéticas y puntuaciones](evidence/local_provider_objective_20261005.json), SHA **576e2d0ed3c0bb589a222d1c744882639a23bea97729d03544f1d9bdc4fd32e1**: 25 llamadas v7 y 36 v8, más dos capturas Chrome del EXE/API reales. Los 65 resultados nativos v5/v6 y los 45 anteriores siguen en sus archivos históricos. No se sustituyen respuestas reales por fixtures. Los browser automatizados usan stubs declarados y se reportan aparte.

V8: 34/36 aceptación estricta; 23/25 conocidos, 11/11 reservados. Tiempo de desarrollo 320.48 s, reservado 138.61 s; llamadas por caso 6.06–19.22 s. Los tokens/fin de salida se conservan crudos. Muestra de proceso: working set 9.806.991.360 bytes, pico de vida 10.505.052.160, VRAM 7.009 MiB durante evaluación/pruebas concurrentes; no es pico por llamada ni energía medida.

| Caso final no aceptado | Evidencia y condición restante |
|---|---|
| `followup-conflict` | Correct 5 versus 8 and neither authoritative, no invented reconciliation; still omits the mandatory direct teacher clarification request. Retained incomplete behaviour. |
| `followup-level` | Body/summary say a half means/consists of two equal groups, repeating the source educational error; 8/2=4 correct. Source must be corrected by teacher; not a transport/source-loss defect. |

Las repeticiones por API reutilizan IDs listos y no duplican contenido; publicar sin revisar devuelve 409. La pregunta abierta se solicita explícitamente como `short_answer` y queda en borrador. El recorrido nativo AI-assisted anterior conservado dejó `score=null`, `needs_review=true`, sugerencia sólo al docente y replay sin llamada adicional; el método correspondiente no cambió en esta reparación. No es una nota final ni revisión humana.

Chrome DevTools aislado ejecutó el formulario/API del EXE v7 y del EXE final v8 (16,07/16,06 s), fuente guardada 335/335, nivel adulto, objetivos españoles y fase elegida; v8 generó una explicación correcta de numerador 3/denominador 8 y guardó ID 14 como borrador, `source_support=unverified`. El API UI no expone tokens, por lo que no se inventan. La fuente enviada no demuestra fidelidad por sí misma.

## Consolidado final y reproducción

Windows 11 `10.0.26200.0`; Python **3.13.15**, PyInstaller **6.16.0**, pytest **9.0.2**, Node **24.21.0**/npm **11.19.0**, Playwright **1.63**, Chrome propio aislado. Help de ambos BAT y del builder Python verificado.

| Gate final | Comando/alcance | Resultado |
|---|---|---|
| Python | `run_tests.bat --full` | 969 PASS, 36 SKIP, 5 deseleccionados; exit 0, 81.57 % cobertura; 627.66 s |
| DOM | `npm --prefix tests/ui test` | 181 PASS |
| Browser | pytest `tests/browser`, Chrome propio, opt-in | 12 PASS; 73.14 s; SW real/200 %/editor/fases/pendiente→cero→feedback |
| Packaging/bootstrap | pytest test_build_package + test_seed_admin | 59 PASS |
| Operacional/frozen | pytest operational_recovery + packaged_recovery con EXE final | 14 PASS; 59.60 s |
| Inferencia mantenida | `run_tests.bat --real-ai --yes`, config sintética y reasoning none | 6 PASS; 27.87 s |
| Lint | flake8 src/scripts/tests E9,F63,F7,F82 | PASS crítico, sin afirmar todas las reglas |
| Tipos | mypy ocho archivos afectados, follow-imports=silent | PASS, sin afirmar todo el repo |
| Dependencias | pip check | PASS |
| Build nativo | `build_package.bat --prod --output-dir "dist/SLMEducator Verified RC 20261005 ñ"` | PASS; 88.93 s |
| Python 3.14 real | builder --prod con C:/Python314/python.exe | exit 1, Tcl/Tk zipfs ausente, output no creado; protección conservada |

36 skips: 23 proveedor/contexto deshabilitados offline, 12 browser opt-in y uno frozen (estos dos últimos ejecutados aparte). Las 23 no se certifican por seis tests nativos. Se ignoran manual/e2e (requieren operador/servidor previo) y real_ai (gate separado). Cinco deseleccionados: cuatro conversaciones Ollama full_context/multi_turn/without_topic/general_mode y test_autouse_respects_real_ai_env. Native Ollama sin certificar. Advertencias de dependencias/harness preservadas. Todos los FAIL históricos de editor, visibilidad, idioma, tipos, presupuesto, fixture de puerto/restore y expectativas de objetivos se mantienen en los recibos/manifiestos históricos; no se rebajaron umbrales ni eliminaron casos.

Reproducir en checkout/entorno nuevos: Python 3.13 x64 + requirements, `npm ci --prefix tests/ui`; proveedor/modelo/hash anteriores. `lms server start --port 1234 --bind 127.0.0.1`; `lms load gemma-4-12b-it-qat@q4_k_xl --gpu 0.9 --context-length 8192 --parallel 1 --identifier slm-production-evaluation --yes`. Iniciar `tests/browser/local_provider_server.py --state-dir NUEVO --port 8097`; driver `evaluate_local_provider.py --state-dir NUEVO --cases-file tests/fixtures/local_semantic_objective_20261005.json --max-tokens 4000 --reasoning-effort none --split development`, luego reserved. Resultados create-only; preservar también fallos. Gate real-AI con configuración sintética y SLM_REAL_AI_REASONING_EFFORT=none; nunca configuración privada.

Construcción con contraseña inicial aleatoria no promete identidad byte a byte: fuente/comandos/hashes identifican el artefacto probado. Producción no lee un SQLite de pruebas; staging y output son aislados/nuevos.

## Windows, instalación, cierre, actualización y recuperación

EXE real: primera instalación/login/cambio de contraseña, CWD distinto con espacios/ñ, PATH sólo System32, sin VIRTUAL_ENV/PYTHONPATH/PYTHONHOME. Runtime incluido en `_internal`. Actualización de la instalación sintética conserva cursos/contenidos, cinco cuentas/configuraciones y contraseña admin cambiada; la inicial devuelve 401. Hash de cursos/contenidos antes/después de sustituir el EXE: **7c426f0071128d14318525df654940092e1d0b82725b137029309a5657ddb0cd**. La generación posterior añade el nuevo borrador, conservando anteriores.

Para actualizar/simular fallo se terminó exclusivamente el árbol del EXE propio con PID/ruta verificados. Esto **no certifica la X de Tk**. El conector nativo no permite esa acción; el usuario aplazó la prueba. Puerto ocupado: selecciona otro libre y el listener ajeno sigue accesible. Backup/restore operacional en otra instalación sintética reabre cinco cuentas, fuentes/cursos/asignaciones/progreso/notas, pendiente/cero/feedback. Rechaza inválidos/destino existente; interrupción real de restauración NTFS y reintento verificados en el paquete final.

Assets v20 sin cambios respecto a la entrega anterior; los browser finales repiten SW habilitado, actualización real v14→v20, recarga, offline/reconexión. No reclama pestaña antigua; espera su cierre, limpia sólo cachés propias, recurso ausente da 503, API offline falla sin éxito falso y vuelve al reconectar. Los ocho tests antiguos con SW desactivado no se usan para certificar esto.

No hay instalador/desinstalador/update-manager soportado: carpeta portable completa; conservar base/config/clave al cambiar binarios. Sin acciones destructivas sobre instalación del usuario.

## Seguridad y límites soportados

| Área | Verificado/límite |
|---|---|
| Red/proceso | API/proveedor 127.0.0.1, un proceso/worker, sin abrir firewall ni exponer servicio para las pruebas |
| Identidad/escritura | Roles y autorización por objeto existentes, JWT/revocación/desactivación, formularios/API e IDs ajenos; no permiso sólo por ocultar botón |
| Renderizado | Markdown/temario/modelo por boundary DOMPurify/marked vendorado, texto/DOM seguros, XSS/hostilidad probados; no garantía universal de toda combinación |
| Archivos | Subida 10 MiB, texto 100.000 caracteres, PDF 100 páginas, portabilidad JSON acotada; no descompresión arbitraria/rutas del usuario |
| Backup | DB 128 MiB/archivo 192 MiB, integridad/relaciones, cifrado/clave original, destino nuevo y promoción create-only NTFS |
| Secretos/logs | Fuente fuera del título INFO, respuestas sintéticas públicas saneadas; bases, configuración, claves, tokens y credenciales no publicados |
| IA | Fuentes no confiables, límites visibles, reintento/error, estructura ≠ respaldo ≠ revisión ≠ publicación; límites semánticos conservados abajo |
| Disponibilidad | Assets offline como shell de lectura; sin prometer API/escritura/IA offline, ni multiworker/servicio escolar |
| Accesibilidad/idioma | ES/EN, foco/teclado, estados, 390px/200 % nativo, controles existentes; quedan descriptores/etiquetas secundarios en inglés y revisión con lector de pantalla pendiente, sin declarar conformidad WCAG completa |
| Educativo/legal | Revisión humana y eficacia requieren evidencia propia; no certificación regulatoria, de menores ni de aprendizaje |

## Arranque/recuperación mínima y piloto aplazado

1. Instalación sintética ya abierta en `http://127.0.0.1:8000`, español, proveedor/modelo/cinco cuentas/fuentes/curso preparados. No se pide al usuario configurar nada ni probar ahora. Una futura aceptación humana será guiada paso a paso, con pantallas y cuentas preparadas por el agente.
2. Guardar es crear borrador. Antes de publicar, contrastar fuente/objetivos/afirmaciones/definiciones, opciones/clave/explicación/pistas y corregir. Publicar primero la evaluación vinculada revisada, después revisar/publicar/asignar curso. No asignar los ejemplos fallidos de evaluación.
3. Mantener SLM Educator abierto al usar navegador; para salir X y confirmar. Esa comprobación del EXE SHA **268245fd2b3e9a9c72b2115cbc0712f20dcf35788f86a7931ffb2eaef83270b3** continúa pendiente, no se ha pedido repetir al usuario.
4. Conservar clave aparte de backups; arranque ordinario sin override usa `%USERPROFILE%/.slm_educator/encryption.key` (ruta privada no inspeccionada). La instalación sintética usa su clave propia por entorno. No borrar la base ante un fallo.
5. Backup: `SLMEducator.exe --recovery --result-file recibo.json backup --database ruta.db --output copia.slmbackup`. Restore: `--recovery --result-file restauracion.json restore --backup copia.slmbackup --output nueva.db`. Clave original, destino/nombres nuevos; recibo `success=true`; reabrir y comprobar cuentas/curso/progreso antes de retirar original.

Piloto de 30–45 minutos preparado, **no realizado y aplazado por petición del usuario**. Docente adulto contrasta y corrige borradores, revisa/publica evaluación y curso, asigna; alumno entiende objetivos, practica con pistas, pausa/reanuda y responde abierta; docente distingue pendiente/cero, feedback/modifica/recarga; participante comprueba resultado y cierra X. Registrar comprensión, errores, minutos y rescates. Si operador no es educador, usabilidad no reemplaza juicio educativo. Los cuatro cursos de salidas históricas conservan fuentes/respuestas exactas como borradores de revisión; no son nueva inferencia ni material aceptado.

La guía y plantilla `docs/pilot/README.md` proponen 12 casos/90 %, sujetos a acuerdo previo del educador; no se usan para cambiar retrospectivamente la rúbrica técnica estricta. La aceptación humana no es la única pendiente mientras queden los resultados semánticos no aceptados arriba. Esta entrega conserva y verifica lo reparado, sin certificar «PROD-ready» ni 100 % de calidad generativa.
