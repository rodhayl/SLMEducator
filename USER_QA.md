# USER_QA — prepara tú; el usuario solo confirma lo imprescindible

## Prompt para el agente

Quiero terminar las comprobaciones pendientes de SLMEducator con el
mínimo esfuerzo humano. Tú preparas y manejas el entorno, abres la pantalla
correcta, ejecutas las comprobaciones técnicas y conservas la evidencia. Yo solo
hago el clic o escucho lo que de verdad necesite una persona. Háblame en español
sencillo, una acción o pregunta por mensaje, y espera mi respuesta.

No me pidas consola, comandos, DevTools, rutas, configuraciones, instalar nada,
preparar cuentas ni diagnosticar errores. No me recites el plan. No conviertas
una limitación tuya en instrucciones técnicas para mí. Si falta acceso o permiso,
explica el bloqueo en una frase y pide únicamente la autorización imprescindible;
eso no es una prueba ni un PASS. No eludas una denegación.

### 1. Antes de preguntarme nada: trabajo del agente

- Lee las instrucciones del repositorio y contrasta el HEAD actual de
  `fix/react-functional-continuation-20261007`, `MANUAL_TEST2.md`,
  `implementation_documents/gui_launcher_20261007_report.md` y los archivos
  `RESUME.json`, `COVERAGE.csv`, `SESSION_LOG.md` y
  `evidence/package_acceptance_20261014.md` de
  `implementation_documents/auto_testing_2026-10-13_001/`.
- Referencia verificada el 14-10-2026: producto
  `a9793fe14969a61f60d4c133dc7aa2ee57a5e3bc`, árbol
  `9c56aa1a91bab0ed7fbf16d7bdab531e41f1df85`; evidencia posterior
  `c74a6ec575e44aedd113a562736e0bb2056a358a` solo documental. No confundas el
  commit que añade este documento con un nuevo binario. Si el producto cambia,
  identifica el nuevo candidato y revisa únicamente el impacto pertinente.
- Paquete de referencia: 2.442 archivos; EXE de 78.477.778 bytes, SHA-256
  `d39864267fdf4ab3019d9fea3f4439c6bda9eb7277c08bc493ac834ad79f69bf`;
  manifiesto SHA-256
  `45c7376f17f20d935b6404c9335942177cd39b49d24c56008f958498b5df1f51`.
  Verifica tú el artefacto disponible, su procedencia y el proceso/origen servido.
  Una captura, `/api/status` o el nombre de una carpeta no bastan para identificarlo.
- Usa el entorno Windows de pruebas existente, autorizado y desechable. Antes
  de arrancar, comprueba aislamiento efectivo de HOME, USERPROFILE, APPDATA,
  LOCALAPPDATA, base de datos, configuración y navegador. No leas claves ni datos
  del perfil personal. La instalación personal documentada es `29df5ed`: no la
  ejecutes, sustituyas, desinstales ni modifiques sin autorización específica.
  No cambies navegador predeterminado, permisos o seguridad para salvar un bloqueo.
- Distingue copia empaquetada de instalación real. Para aceptar LEARN-03 en el
  candidato instalado necesitas un instalador identificado y un destino de
  instalación aislado autorizado. Si no existen, deja ese gate BLOCKED y prepara
  tú la solución permitida; no me encargues construir o instalar. Este prompt no
  autoriza publicar código, descargar modelos, hacer inferencias ni alterar mi
  instalación. Los permisos adicionales se resuelven antes de la acción afectada.

### 2. Reutiliza lo aprobado; no vuelvas a examinarme

Reutiliza con su candidato y alcance originales las 87 pruebas sintéticas del
launcher, arranque frío y fallback de puerto, zoom nativo 200%/400% y reset,
pruebas de instalación históricas, resultados de Gemma y recuperación del tutor,
y las capturas verificadas de listas claras/oscuras, numeradas, anidadas y
navegación de `a9793fe`. No repitas suites completas, inferencias, zoom, colores,
listas ni la ruta extensa A–F para conseguir otro resultado verde.

La rúbrica 35/36 y el caso reservado objective-hostile quedan documentados;
no son una prueba que deba resolver yo ni una autorización para ajustar el modelo.

### 3. Completa tú primero lo observable por herramientas

- BOOT-02: prepara el launcher nativo del candidato y un navegador de prueba
  aislado. Comprueba el botón real «Abrir SLMEducator» y que abre el origen del
  proceso correcto. Si puedes realizar y observar ese clic, hazlo tú: no necesitas
  que yo lo repita. Si requiere mi intervención, deja el botón delante de mí y
  pide solo: «Pulsa Abrir SLMEducator». Tú verificas después la pestaña y el origen.
- BOOT-05: reutiliza la cobertura sintética. Para los restantes estados nativos,
  prepara únicamente fixtures controladas permitidas de arranque lento/fallido y
  recuperación Detener→Iniciar. Observa estado, timeout, recuperación, URL por
  teclado y legibilidad al DPI disponible. No mates procesos ajenos, cambies
  escala global ni manipules la red. Si un subcaso no puede reproducirse con
  seguridad, déjalo pendiente con motivo; no pidas que yo fabrique el fallo.
  No declares probado otro DPI por una captura redimensionada.
- LEARN-03: si hay instalación aislada válida, prepara datos ficticios y completa
  tú mediante la GUI real un recorrido mínimo de curso/lección, práctica y un
  intento enviado con resultado/calificación verificable. Las operaciones que se
  evalúan deben pasar por la aplicación, no simularse escribiendo su resultado
  por API/SQL. Usa contenido ya preparado, sin IA nueva. Conserva la diferencia
  entre autoevaluación/borrador y envío/calificación. Un recorrido parcial no
  acredita toda la matriz de aprendizaje ni la instalación personal.
- Si el alcance exige observar instalación/desinstalación interactiva, hazlo tú
  solo en el destino autorizado; no repitas el caso histórico silencioso como
  sustituto. La actualización in-place se rechaza por diseño: no prometas probar
  una migración que el producto no ofrece. Los subcasos no ejecutados siguen abiertos.

### 4. Mi participación: como máximo tres intervenciones breves

Reserva las preguntas para observaciones humanas irreducibles. Si puedes resolver
el clic de BOOT-02, no lo cuentes como una tarea para mí. Combina la escucha con
las pantallas del recorrido anterior; evita visitas repetidas.

El contrato vigente de `AUTO-VIS-06.lector` en `COVERAGE.csv` pide:
«Lector de pantalla real identificado por producto/versión: login, formulario,
aula, intento y modal; lectura, errores, estado y foco». La nota estima una
pasada de unos cinco minutos; no es un cronómetro ni exige cinco cuestionarios.
Cubre esos contextos en dos bloques guiados, reutilizando el recorrido instalado:

1. **Escucha de acceso y formulario.** Activa tú Narrator mediante acceso
   permitido, registra versión y prepara el acceso sintético. Explica una vez:
   «Voy a manejarlo yo. Escucha los nombres de los campos y el aviso de error».
   Recorre tú el foco del login y provoca una validación inocua en un formulario
   de prueba, sin exponer contraseñas. Al acabar pregunta: «¿Has oído claramente
   los campos y el aviso de error? Sí/no». Registra controles, error y orden del
   foco concretos. Tú resuelves configuración/acceso; el usuario solo escucha.
2. **Escucha de aprendizaje y diálogo.** Desde el aula preparada, recorre tú el
   contenido, el intento sintético y su cambio de estado; abre y cierra un modal
   real seguro y comprueba el retorno del foco. Antes di: «Escucha el contenido,
   el resultado y cómo se abre y cierra el diálogo». Después pregunta: «¿Has oído
   claramente todo ese recorrido, sin perder dónde estabas? Sí/no». Conserva los
   eventos concretos observados para aula, intento, estado y modal. No generes
   contenido con IA ni uses ventanas de otras aplicaciones como sustituto.
3. **Solo si aún es imprescindible**, el clic del launcher descrito arriba. Si
   ya lo hiciste y observaste tú, omítelo. No añadas una tercera pregunta por cuota.

Una respuesta negativa o ambigua detiene el bloque afectado: registra el límite
sin pedir al usuario que depure. No presupongas que oyó un evento porque existe en
el árbol AX. Puedes marcar VIS-06 PASS para este candidato y alcance si ambos
bloques se ejecutan y confirman, con evidencia de todos los contextos requeridos.
Si falta alguno, registra PARTIAL e identifica cuál; no alargues esta sesión sin
acordarlo. Esto no certifica accesibilidad completa ni sustituye otros gates.

### 5. Fallos, evidencia y final

Si algo falla, conserva la evidencia y detén el caso afectado. No me pidas depurar,
repetir clics a ciegas ni contestar veinte preguntas. Continúa solo comprobaciones
independientes ya preparadas y seguras. Si digo «para», detente inmediatamente.

Registra en un único informe de sesión el candidato, hashes, instalación o copia,
aislamiento, Windows/navegador/Narrator, origen y acciones reales; adjunta evidencia
saneada y mis respuestas breves literales. No guardes credenciales, ni siquiera
sintéticas. Separa evidencia histórica, observación técnica nueva y confirmación
humana. Usa PASS, FAIL, PARTIAL, BLOCKED y NOT RUN por subcaso. No publiques
automáticamente el informe ni modifiques código para hacer pasar la sesión.

Al terminar, restaura únicamente los cambios temporales de esta prueba, incluido
Narrator si tú lo activaste, y detén solo tus procesos. No borres backups, datos
personales ni evidencia. Dame un resumen de como máximo cinco líneas: qué quedó
comprobado, qué falló o sigue pendiente, si necesito decidir algo y dónde está el
informe. No declares SLMEducator cerrado mientras queden gates obligatorios.
