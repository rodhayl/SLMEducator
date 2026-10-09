# Defectos y límites de esta continuación

Fecha: 9 de octubre de 2026. Los identificadores SLM-CONT son propios de esta
continuación y no renumeran los defectos de las campañas anteriores.

## SLM-AUTO-014 y SLM-AUTO-015

Estado: reparados en código publicado `9491f1440d60bef465f8b64cd61321dce1f35df0`.
Aceptación nativa Windows: pendiente.

Las lecturas implícitas de JSON del piloto, observaciones y documentación de
pruebas dependían de la configuración regional. Una simulación cp1252 reprodujo
cinco fallos, incluidos textos persistidos con mojibake y errores de decodificación.
Se declara UTF-8 explícitamente en las fronteras pertinentes. La repetición final
focal pasó 85 casos; los datos existentes de usuario no fueron modificados.

## SLM-CONT-001 Operaciones de fuente incompatibles durante una extracción

Estado: reparado en código publicado `f17a37f7ae68621fbdb1a8c0f282265d6eaa3200`.
Aceptación GUI real sobre el nuevo candidato: pendiente.

Mientras una extracción permanecía en vuelo, Recargar y Adoptar una propuesta
anterior seguían disponibles. Una recarga podía limpiar la propuesta y una
respuesta tardía volver a introducirla. También se podía confirmar una operación
incompatible desde un diálogo ya abierto. Los nuevos tests reproducen nueve
fallos antes del cambio y pasan los doce casos después.

La solución bloquea las operaciones incompatibles y sus confirmaciones mientras
se extrae, permite seguir editando texto local, conserva borrador y propuesta
anterior si la nueva extracción falla y mantiene separados extraer, adoptar y
guardar. No se añade un guardado automático. Las fronteras de cuenta, credencial
y navegación conservan sus regresiones.

Verificación del frontend final: 967 tests, tipos, lint y build aprobados. La
revisión independiente pasó 14 casos focales, incluidos dos recorridos de rúbrica
con guardar, salir, volver y preparar un nuevo desglose. Los recuentos se solapan
con la suite completa y no deben sumarse.

## Estados históricos que no se cierran indebidamente

- El 500 original de generación sigue sin causa demostrada.
- La generación de otros cuatro modos, Tutor contextual completo y la aceptación
  nativa no se convierten en PASS por estas pruebas sintéticas.
- SLM-AUTO-011 conserva notas privadas y la política de permisos existente.
- SLM-AUTO-013 conserva los títulos históricos o escritos por el docente.
- El ciclo real de instalación y el primer administrador siguen requiriendo su
  aceptación propia sobre el ejecutable instalado.
