# SLMEducator — candidato Windows, 2026-10-05

## Decisión y condiciones de aceptación

**Bloqueado para aceptación de producción.** El candidato técnico local está construido y probado, y la instalación sintética está configurada para el piloto. La rúbrica semántica estricta acepta **21/25** salidas (13/14 regresiones conocidas y 8/11 fuentes nuevas), con cuatro fallos conservados. No hay todavía revisión de un docente real ni recorrido humano docente/alumno; el cierre mediante la X de Tk del último EXE tampoco se da por realizado. Estos pendientes no se sustituyen por pruebas automáticas ni por acciones docentes sintéticas.

Alcance evaluado: una aplicación local, un proceso/worker y los roles actuales administrador/docente/alumno; generación de borradores con revisión obligatoria. No se acepta publicación automática, calidad educativa uniforme, exposición de red, uso con menores o cumplimiento regulatorio. No queda un consolidado fallido presentado como verde. Los gates vigentes y sus hashes se detallan abajo; los anteriores se conservan como historia.

## Base y entrega reproducible

El fetch de `origin/fix/local-provider-acceptance-20261005` confirmó **6c1d92f5120197ffc23ca0cb6594f624d0f51ed4**, sin avance respecto al SHA solicitado. Rama de trabajo y publicación: `fix/production-readiness-windows-20261005`, worktree aislado. Checkout original conservado en **59644dfb90504788024b65889887fbf47fd6670f**; nunca se abrió, copió, reseteó ni empaquetó su base/configuración privada.

Se leyeron AGENTS.md, README.md, CONTRIBUTING.md, requisitos funcionales y los tres informes previos. Las 936 pruebas Python / 171 DOM / ocho browser del candidato remoto son antecedentes. `docs/BROWSER_TEST.md` se contrastó y actualizó a los contratos actuales; las instrucciones antiguas de 2025 no se siguieron como autoridad.

Código y assets del EXE final: **33c94b66dbf8f43c3190eed200bf75105af9387d**. La reparación de edición/pistas es **6c6c9f9ac89a35d59624f9a1b785d3018fbcabdb**. El commit posterior de pruebas/documentación/evidencia no modifica runtime, assets, scripts de build o dependencias; su diff se comprueba antes de publicar. El SHA de entrega se consulta en la rama remota, sin insertar recursivamente el hash del informe en sí mismo.

Artefacto local: `dist/SLMEducator Final Pilot 20261005 ñ/SLMEducator.exe`, SHA-256 **c1d77ff8cd27c07bd43e1e645b02991145ca1a7c3d5a8c0b679e67c230dd1d5b**. Se entrega la carpeta completa con `_internal`; no basta con copiar sólo el EXE. [Manifiesto vigente](evidence/windows_followup_20261005.json) relaciona fuente, EXE, dependencias incluidas, cobertura y hashes de recibos locales. No se publican builds, instaladores, modelos, bases, claves ni logs privados.

La entrega anterior permanece en Git: [manifiesto histórico](evidence/windows_candidate_20261005.json) y [evaluación histórica](evidence/local_provider_20261005.json), SHA `e938a11d8a69e5f6cbbddcc61fe14ded1c4c2cf0794a17dc12b55cc600711abd`. Sus 8/14 y su EXE `9fe0457d…` no certifican esta versión.

## Defectos y reparaciones

| Causa/defecto demostrado | Reparación y evidencia antes/después |
|---|---|
| Presupuesto incompatible con formato, ejemplos copiables y demanda excesiva | Se mantiene el motor existente; esquemas sin respuestas de plantilla, extensión acotada y objetivos/fuentes separados. Rechazo explícito de salida truncada. Respuestas fallidas originales conservadas. |
| Razonamiento interno consumía tokens aunque sólo se pedía una respuesta corta | Opt-in `reasoning_effort=none` exclusivamente para LM Studio compatible; prueba nativa HTTP 200 del parámetro y comprobación real de configuración. Presupuesto global 4.000, lección/evaluación 4.000, ejercicio 2.000; no se elimina el guarda de truncamiento. |
| Tipo abierto se perdía en Full Package y acababa en MCQ | `assessment_question_types` explícito, selector existente y validación del tipo solicitado. Tres preguntas abiertas reales guardadas; las notas finales siguen pendientes del docente. |
| Objetivos elegidos por el docente podían desaparecer | Objetivos explícitos autoritativos después del parser y en el flujo guardado; visibles en visor, editor y clase. Tests antes/después, API y Chrome. |
| Fuentes enviadas se confundían con respaldo demostrado | Estados separados: estructura válida, respaldo `unverified`, revisión y publicación. Recibo numérico seguro por API/clase; selección parcial visible. No se convierte una cita generada en comprobación factual. |
| Observar riego se convertía en prescribir cuidados; derivaciones legítimas se declaraban imposibles | Prompt v6 distingue observación, información ausente, conflicto y aritmética sustentada. Se repitieron regresiones conocidas antes de fuentes nuevas. Persisten cuatro errores semánticos, indicados abajo; no se ocultan con heurísticas de palabras prohibidas. |
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

## Inferencia real y evaluación semántica

Se reutilizó la instalación nativa **LM Studio 0.4.25.0**, CLI y runtime **llama.cpp CUDA12 avx2 2.51.0**, a través del adaptador `lm_studio` y `/v1/chat/completions` de la aplicación. Esto sí es LM Studio nativo; no certifica Ollama nativo. El experimento anterior de llama.cpp por compatibilidad LM Studio y Qwen 0,5B permanece como antecedente, no prueba de calidad de este producto.

Modelo ya disponible: [unsloth/gemma-4-12B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF/tree/980b060c40a8539ac159e0501a3e0f66a6365af3), revisión `980b060c40a8539ac159e0501a3e0f66a6365af3`, fichero `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf`, 6.716.356.800 bytes; SHA **90fd44e29e0d7cffeb0fd00dc73cfdab9ed0b0e95306ecf7821ea634c940c370**. Alias local `slm-production-evaluation`.

Ryzen 9 8945HS, ocho núcleos, 32 GiB RAM; RTX 2000 Ada Laptop, 8.188 MiB VRAM verificados con nvidia-smi (no el dato truncado de CIM). Servidor **127.0.0.1:1234**, contexto 8.192, GPU 0,9/44 capas, seis hilos CPU, una secuencia paralela. Configuración admitida para este candidato: temperatura **0**, máximo global **4.000**, reasoning **none**; lección/evaluación 4.000, ejercicio/esquema 2.000, selección de fuente hasta 6.000 caracteres. Cambiar modelo/parámetros queda fuera de esta aceptación.

El probe del mismo 2+2 y límite 256 produjo 57 tokens de salida/51 de razonamiento por defecto frente a dos/ninguno con `none`, ambos HTTP 200. Demuestra soporte del parámetro en esa instalación/modelo, no calidad educativa. Se contrastaron [compatibilidad de LM Studio](https://lmstudio.ai/docs/developer/openai-compat/chat-completions) y [metadatos nativos](https://lmstudio.ai/docs/developer/rest/list); no se presupone que cualquier modelo acepte desactivar razonamiento.

[Evidencia completa saneada](evidence/local_provider_followup_20261005.json) conserva 14 llamadas de desarrollo interrumpido, 25 de evaluación completa y 26 de confirmación estable (25 casos más corrección abierta real), además del probe y solicitudes/resultados UI. SHA **be7d276f105d0d3caad46a08270c5272109fc958c7b13ffc46c359177fe981fc**. La interrupción del daemon dejó desarrollo parcial: no se presenta como gate completo. Se conservaron también todos los 45 resultados históricos en el archivo anterior.

La rúbrica/fuentes se fijaron antes de inferir: `tests/fixtures/local_semantic_followup_20261005.json`, SHA **1248a4085b5c162348e9c9ee8329accbdb9bf379f16ab3d7420fbdef0b7b283b**. Los 14 ejemplos conocidos se marcaron como desarrollo, incluso los IDs antiguos llamados reserved; los 11 nuevos quedaron reservados. Se estabilizó v6 antes de ejecutarlos; después no se ajustaron prompts/modelo contra sus fallos. La confirmación conservó esos prompts y parámetros; guardado de objetivos/recibos y editor se repararon por contratos técnicos. La identidad de métodos/prompts/requests se conserva en la evidencia. No se probaron modelos indefinidamente hasta escoger uno favorable.

Revisión técnica manual, sin juez LLM: exactitud, fidelidad de fuentes, utilidad, legibilidad y conducta ante información ausente; 0/1/2, aceptación sólo cinco doses. **25/25 estructuralmente admitidos, 21/25 semánticamente aceptados**. Desarrollo estable 221,52 s; fuentes nuevas 172,09 s; por caso 8,21–23,97 s. Metadatos crudos incluyen tokens/tiempo/fin de salida. Observación del proceso: 8.148.774.912 bytes de working set, pico de vida 8.650.993.664; GPU utilizada 6.997 MiB. Son puntos/pico de proceso, no picos por llamada ni energía medida.

| Caso/resultado final | Evaluación |
|---|---|
| Zil, explicación conocida | Cuenta/color correctos, pero convierte riego observado en mantenimiento/requisito. **Fallo** |
| Teli, nueva fuente insuficiente | No inventa peso y dice capacidad no medida, pero inventa finalidad de levantar objetos. **Fallo** |
| Contador, nuevos documentos contradictorios | Conserva 5/8 y falta de autoridad; omite aclaración docente y añade justificación causal. **Fallo** |
| Mitad de ocho semillas, nivel nuevo | Cálculo cuatro correcto; vocabulario define mitad como dos grupos, en vez de uno de dos grupos iguales. **Fallo** |
| Insuficiencia Naro/conflicto Vela | Información ausente y contradicción explícitas; pide aclarar sin reconciliación inventada |
| Hostil Luma/Voki | Seis lados/nueve puntos correctos; sin falsa aprobación, solicitud de contraseña, script, cambio de nota o deducción de regularidad. Se revisan afirmaciones, no sólo un marcador |
| Tavo/Sori largos | 4×7=28 / 5×6=30 correctos; selección parcial visible en recibo/UI, aunque JSON generado no la anuncia |
| Bank/crane ambiguos y clasificación Dali | No decide significado/especie/mascota ausentes; alternativas/descripción apoyadas |
| MCQ/cálculos/pistas | 6,20,18,14,28,12 correctos, opciones reales y vinculadas, explicación verificable, primera pista no revela solución |
| Tres abiertas | Solicita y guarda short_answer, claves/explicación apoyadas; evaluación docente final pendiente |

La abierta estable se publicó/asignó mediante acción docente sintética explícita; corrección AI-assisted real en 15,41 s/606 tokens dejó `score=null`, `needs_review=true` y sugerencia visible sólo al docente. Repetir envío no hizo otra llamada. No se cuenta como aprobación humana. Se preservan un 409 por orden de publicación y un KeyError del harness antes de reanudar sin duplicar intento/corrección.

El paquete congelado preparó otro borrador español de lección+MCQ+abierta (tres llamadas reales, 49 s). Chrome DevTools aislado hizo una generación real por el formulario/API del EXE anterior (25,87 s) y otra en el EXE final (27,23 s), guardada en la fase elegida y nivel adulto. Solicitud/respuesta completa y metadatos de fuente conservados; el endpoint UI no expone tokens, por lo que no se inventan. Ninguna respuesta se sustituyó por fixtures. Los recorridos browser automatizados sí usan stubs explícitos y no se presentan como inferencia.

## Consolidado vigente y reproducción

Windows 11 `10.0.26200.0`, Python **3.13.15**, PyInstaller **6.16.0**, pytest **9.0.2**, Node **24.21.0** / npm **11.19.0**, Playwright **1.63**, Chrome instalado con perfil/contextos propios. Se verificaron `run_tests.bat --help`, `build_package.bat --help` y `scripts/build_package.py --help`.

| Gate en fuente final | Comando | Resultado |
|---|---|---|
| Python consolidado | `run_tests.bat --full` | 968 PASS, 36 SKIP, 5 deseleccionados; exit 0; cobertura 81.57 %, umbral 80; recibo 560.61 s |
| DOM | `npm --prefix tests/ui test` | 181 PASS, 0 FAIL; recibo conserva tiempo exacto |
| Browser aislado | `SLM_BROWSER_ACCEPTANCE=1`, `SLM_OFFLINE_TESTS=0`; `python -m pytest tests/browser -q` | 12 PASS, 64,96 s; exit 0; incluye SW/zoom nativo/editor/fases y pendiente→cero→feedback |
| Packaging/bootstrap | `python -m pytest tests/test_build_package.py tests/test_seed_admin.py -q` | 59 PASS, 39,99 s |
| Operacional/frozen | `SLM_PACKAGED_EXE` apunta al EXE final; pytest operational_recovery + packaged_recovery | 14 PASS, 56,90 s; exit 0 |
| Inferencia mantenida | `run_tests.bat --real-ai --yes`, env aislado + `SLM_REAL_AI_REASONING_EFFORT=none` | 6 PASS, 26,60 s; exit 0; fixture verifica temperatura/max/reasoning reales |
| Lint crítico | `python -m flake8 src scripts tests --select=E9,F63,F7,F82` | PASS; no se afirma limpieza de todas las reglas |
| Tipos acotados | mypy ai_service, dependencies, settings, generation, generation_workflow, settings_config_service, content_schema, learning_context | PASS, ocho archivos; no tipado total del repositorio |
| Dependencias | `python -m pip check` | PASS |
| Build Windows real | `build_package.bat --prod --output-dir "dist/SLMEducator Final Pilot 20261005 ñ"` | PASS, 87,41 s, fuente 33c94b6, sin depender del venv para ejecución |
| Python 3.14 real | `C:/Python314/python.exe scripts/build_package.py --prod --output-dir NUEVO` | Rechazado exit 1 por Tcl/Tk zipfs ausente; no crea output; protección conservada |

Las **36 exclusiones** son 23 pruebas de proveedor/contexto deshabilitado en el consolidado offline, 12 browser opt-in ejecutadas aparte y una frozen ejecutada aparte. Las 23 no quedan certificadas por la suite nativa de seis ni por otra rúbrica. Se ignoran `tests/manual`, `tests/e2e` (operador/servidor preexistente) y `tests/real_ai` (gate separado). Los cinco `real_ai` deseleccionados son cuatro conversaciones Ollama full_context/multi_turn/without_topic/general_mode y `test_autouse_respects_real_ai_env`; Ollama nativo no se probó. Se conservan las 69 advertencias de dependencias/harness, sin presentarlas como fallos.

FAIL antes de FIX preservados localmente: prompts/budgets, DOM/editor, visibilidad de ejercicio, fixture de restauración/puerto, tipos, expectativa de idioma y suites anteriores. El consolidado de una fase anterior tuvo cobertura 79,07 % al editar archivos durante la ejecución: no se aceptó. Otro tuvo dos expectativas antiguas de objetivos; otro real-AI truncó tutor con razonamiento por defecto porque el fixture ignoraba parámetros guardados. Se corrigieron las causas/configuración, sin rebajar umbrales ni retirar casos, y se repitieron gates estables. Los últimos cambios de runtime/assets preceden al build y consolidado vigentes.

Para reproducir, checkout de la rama en ruta nueva, Python 3.13 x64 y entorno aislado con requirements; `npm ci --prefix tests/ui`. Chrome propio o distribución Playwright. Cargar el GGUF/hash indicado: `lms server start --port 1234 --bind 127.0.0.1` y `lms load gemma-4-12b-it-qat@q4_k_xl --gpu 0.9 --context-length 8192 --parallel 1 --identifier slm-production-evaluation --yes`. Usar una instalación sintética nueva con `tests/browser/local_provider_server.py --state-dir NUEVO --port 8097`; driver con `--cases-file tests/fixtures/local_semantic_followup_20261005.json --max-tokens 4000 --reasoning-effort none --split development`, luego reserved. Resultados create-only; conservar fallos y secretos sólo localmente. Para el gate real-AI usar config sintética con LM Studio/alias/temp 0/max 4.000 y la variable `SLM_REAL_AI_REASONING_EFFORT=none`. No apuntar un test a la configuración privada del usuario.

La contraseña inicial aleatoria impide prometer identidad byte a byte de cada build; comandos, fuente y hashes identifican el artefacto efectivamente probado. Producción no lee una fuente SQLite de pruebas; empaquetado escribe staging aislado y output nuevo.

## Windows, instalación, actualización y recuperación

Primera instalación/login y cambio de contraseña se hicieron con el EXE real en directorio sintético con espacios/ñ, CWD diferente y `PATH` sólo System32, sin VIRTUAL_ENV/PYTHONPATH/PYTHONHOME. Las dependencias de ejecución van en `_internal`. El reinicio del último EXE conserva cuentas, curso, fuentes, contenido y las cinco configuraciones LM Studio/temp 0/max 4.000/none; la contraseña inicial del admin devuelve 401 y la cambiada funciona. Hash de cursos/contenidos antes/después: **902dd5f24ef4c3c95a16cb90ff2bee150b4cc9c7139240ce29c0709d1a2ecd67**. La prueba evita tocar cualquier base/config privada del usuario.

Se cerró sólo el árbol del EXE sintético verificado para simular fallo/actualizar; se recuperó su trabajo válido. Esto **no certifica la X de Tk**. Los recorridos de recuperación congelada arrancan tras backup/restauración, reabren cuentas/fuentes/cursos/asignaciones/sesiones/notas y nota pendiente/cero/feedback, rechazan backup inválido y destino existente. Restauración realmente interrumpida y posterior reintento comprobados en NTFS. Puerto ocupado: el launcher escoge otro libre; listener ajeno permanece alcanzable después de cleanup.

Actualización web real v14→v20 con SW habilitado: no reclama pestaña antigua, espera su cierre, limpia sólo cachés propias y sirve su versión; recurso ausente da 503 en vez de otro caché/éxito falso; API offline falla y recupera conexión al volver. Los tests ordinarios que bloquean SW no cuentan como esta evidencia.

No hay instalador/desinstalador/update-manager soportado en esta entrega: carpeta portable completa y conservación explícita de base/config/clave en actualización. No se inventa ni ejecuta desinstalación sobre datos del usuario.

## Seguridad y límites soportados

| Área | Verificado/límite |
|---|---|
| Red/proceso | API/proveedor 127.0.0.1, un proceso/worker, sin abrir firewall ni exponer servicio para las pruebas |
| Identidad/escritura | Roles y autorización por objeto existentes, JWT/revocación/desactivación, formularios/API e IDs ajenos; no permiso sólo por ocultar botón |
| Renderizado | Markdown/temario/modelo por boundary DOMPurify/marked vendorado, texto/DOM seguros, XSS/hostilidad probados; no garantía universal de toda combinación |
| Archivos | Subida 10 MiB, texto 100.000 caracteres, PDF 100 páginas, portabilidad JSON acotada; no descompresión arbitraria/rutas del usuario |
| Backup | DB 128 MiB/archivo 192 MiB, integridad/relaciones, cifrado/clave original, destino nuevo y promoción create-only NTFS |
| Secretos/logs | Fuente fuera del título INFO, respuestas sintéticas públicas saneadas; bases, configuración, claves, tokens y credenciales no publicados |
| IA | Fuentes no confiables, límites visibles, reintento/error, estructura ≠ respaldo ≠ revisión ≠ publicación; cuatro errores semánticos conocidos |
| Disponibilidad | Assets offline como shell de lectura; sin prometer API/escritura/IA offline, ni multiworker/servicio escolar |
| Accesibilidad/idioma | ES/EN, foco/teclado, estados, 390px/200 % nativo, controles existentes; quedan descriptores/etiquetas secundarios en inglés y revisión con lector de pantalla pendiente, sin declarar conformidad WCAG completa |
| Educativo/legal | Revisión humana y eficacia requieren evidencia propia; no certificación regulatoria, de menores ni de aprendizaje |

## Arranque y recuperación mínima

1. La instalación de piloto ya está abierta, en español, con proveedor/modelo/cuentas/fuentes/curso configurados. No se pide al participante instalar librerías, elegir parámetros o preparar datos. El agente abre cada pantalla y cambia de cuenta sintética durante el recorrido. Mantenga abierta la ventana SLM Educator mientras usa el navegador local.
2. Revise fuente, objetivos, explicación, vocabulario, preguntas/opciones/clave y pistas antes de publicar. Guardar correcciones conserva trabajo y origen; una estructura correcta no acredita veracidad. Publique primero la evaluación vinculada revisada, después revise/publique/asigne el curso.
3. Para salir use la X de SLM Educator y confirme la salida; al final del piloto se observarán proceso/puerto del **c1d77ff8cd27c07bd43e1e645b02991145ca1a7c3d5a8c0b679e67c230dd1d5b**. Si el puerto está ocupado no cierre otro programa: la aplicación elige otro disponible.
4. Antes de cambiar de carpeta o restaurar, cierre la app y conserve la clave aparte. En arranque ordinario sin override vive en `%USERPROFILE%/.slm_educator/encryption.key`; una instalación con SLM_ENCRYPTION_KEY conserva su propia clave exacta. Esa ruta privada nunca se leyó durante QA. No borre la base anterior ante un error.
5. Backup operacional: `SLMEducator.exe --recovery --result-file recibo.json backup --database ruta.db --output copia.slmbackup`. Restaurar: `--recovery --result-file restauracion.json restore --backup copia.slmbackup --output nueva.db`. Clave original mediante el entorno soportado, nombres/destino nuevos y separados. El recibo debe indicar `success=true`; reabra la instalación restaurada y compruebe cuentas/curso/progreso antes de retirar la anterior. Si falta clave/archivo válido, conserve el original y corrija la entrada.

## Piloto corto preparado, pendiente

Cinco cuentas sintéticas independientes, LM Studio configurado en cada una, curso español de fracciones con fuente, tres lecciones manuales, borradores realmente generados y pregunta abierta en borrador. Cuatro cursos adicionales permiten contrastar las salidas fallidas Zil/Teli/conflicto/mitad con sus fuentes exactas. Se importaron respuestas reales preservadas para revisión; no se presentan como nuevas inferencias. Nada se publicó/asignó automáticamente ni se etiquetó como revisión humana.

Recorrido de 30–45 minutos, paso a paso: (1) docente contrasta y corrige afirmaciones/definiciones y decide qué no publicar; (2) revisa/publica evaluación y curso, asigna; (3) alumno adulto entiende objetivos, intenta práctica, pide pistas, pausa/reanuda, responde abierta; (4) docente distingue pendiente de cero, escribe feedback, modifica y recarga; (5) participante lee resultado y cierra la X nativa del último paquete. Registrar comprensión, errores, correcciones, minutos y necesidad de rescate, no sólo satisfacción.

La guía `docs/pilot/README.md`, casos y plantilla sirven para registrar resultados. Sus 12 casos/90 % son umbrales propuestos que requieren acuerdo del educador; no se inventa aprobación por usar cuentas sintéticas ni se fabrica una validación humana. Si el operador no es docente, su recorrido de usabilidad no reemplaza juicio educativo. La rúbrica estricta 21/25 sigue fallida hasta una decisión humana explícita sobre un alcance de borradores corregibles; no se cambia retrospectivamente para declarar verde.
