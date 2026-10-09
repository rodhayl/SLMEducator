# Continuación técnica de SLMEducator — 9 de octubre de 2026

## Alcance y procedencia

Rama única: `fix/react-functional-continuation-20261007`. Punto de partida publicado:
`abd33afd1bf2708064f3f80466fa993f360d3490`. La campaña anterior probó código
`19909e6038c180ce15f5e987928934d34dfc797e`; sus commits posteriores sólo añadían
informes y evidencia. Esta continuación usa código recuperado y comprobado contra
los hashes Git de sus archivos, en un entorno Linux con datos sintéticos.

La aceptación global sigue incompleta. Un resultado de pruebas técnicas no
certifica el ejecutable instalado en Windows, entrada física, acústica, lector de
pantalla, ni una nueva llamada a LM Studio. No se han modificado bases de usuario,
credenciales, configuración privada, permisos ni artefactos históricos.

## Conciliación de la campaña anterior

`COVERAGE_RECONCILIATION.json` conserva los recuentos originales: 126 filas,
7 PASS, 1 PARTIAL, 2 FAIL, 2 BLOCKED y 114 NOT_RUN. La revisión clasifica
`AUTO-GEN-02.modos` como PARTIAL: se inventariaron cinco modos y se ejecutó sólo
Lección individual. El recuento interpretado es 6 PASS y 2 PARTIAL, con los otros
estados intactos. La captura `evidence/shot-generar.png` referenciada por esa fila
no figura en el árbol publicado. No se sustituye por otra captura como prueba de
los cuatro modos no ejecutados.

El `RESUME.json` histórico conserva 118 filas NOT_RUN y acciones ya realizadas;
no debe usarse como estado actual. La generación de lección mediante Chrome
CDP sí está informada como realizada. CDP no acredita ratón/teclado nativos.
El candidato del checkout tampoco acredita que se haya instalado ese candidato.

## Contratos que deben conservarse

- Los JSON de piloto y observaciones son UTF-8. `PYTHONIOENCODING` sólo controla
  flujos estándar y no resuelve por sí mismo una lectura `Path.read_text()` que
  use la configuración regional. La solución es declarar la codificación en
  cada frontera de lectura pertinente, con regresiones que simulan cp1252.
- El límite efectivo es el mínimo entre el presupuesto de la cuenta y el de la
  operación. Cuenta 1000→4000 significa Lección 1000→4000 y Tutor 1000→1200.
  No implica que el Tutor disponga de 4000 tokens. Esta continuación no aumenta
  presupuestos ni modifica valores predeterminados.
- El fallo 500 histórico de generación mantiene causa desconocida: el log
  original citado no está disponible. Las pruebas de truncamiento, respuesta
  vacía y error de proveedor no demuestran retrospectivamente esa causa.
- Las notas privadas del docente saliente se conservan almacenadas; no se
  transfieren al nuevo docente. El escenario 011 debe crear la nota de T1 antes
  de cambiar el docente responsable de la matrícula. No equivale a reasignar
  un curso ni autoriza ampliar permisos.
- Los títulos históricos o escritos por el docente, incluido «Lesson», se
  conservan literalmente. Sólo se aplica la normalización vigente a contenidos
  nuevos. No hay una migración de títulos históricos.
- Una rúbrica reabierta comienza un nuevo borrador de desglose, según el contrato
  visible. Sus resultados no se guardan automáticamente ni se usan para borrar
  comentarios o desgloses anteriores del docente.

## Próxima aceptación, sin repetir trabajo ya documentado

1. Sobre el próximo candidato publicado, repetir las reparaciones 014/015 con
   un piloto sintético nuevo y comprobar los textos acentuados. No reescribir
   automáticamente datos antiguos que ya contengan mojibake.
2. Recorrer Personas con escritura rápida y dos cursos homónimos; la búsqueda
   de Cursos ya observada no acredita el recorrido original de Personas.
3. Completar rúbrica → guardar → volver a abrir, enlaces de evaluación,
   avisos traducidos y recuperación de fuente inválida → válida. La adopción
   de texto extraído y su guardado deben seguir siendo dos acciones explícitas.
4. Completar Tutor libre/contextual y los otros cuatro modos de generación
   cuando haya proveedor y entorno autorizados. Conservar truncamientos y
   respuestas no utilizables; no fabricar PASS ni aumentar límites en silencio.
5. Validar el ciclo de instalación/desinstalación en un destino identificado,
   con respaldo recuperable. La creación del primer administrador requiere que
   el propietario introduzca sus credenciales localmente; no se solicitan por chat.
6. Repetir los recorridos nativos de foco, teclado, escala y lector sobre el
   ejecutable realmente instalado, con identidad y evidencias propias.

Las nuevas pruebas técnicas se registran aparte de las 126 filas de la campaña
GUI. Ninguna fila histórica NOT_RUN cambia a PASS por ejecutar tests de código.
