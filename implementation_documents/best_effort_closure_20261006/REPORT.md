# Cierre funcional best-effort

Fecha: 2026-10-06. Base exacta: `6109c496c48cceb7482d921887be1cb604460a37`.
Patch de ocho archivos revisado: SHA256 `880b6fb69de47e85a40631697720f83d4e4ff065860ab272c98117d8f9fb7399`.
Identidades de archivos y resultados: [verification.json](verification.json).

## Resultado y alcance

El tutor muestra el motivo de fallo y conserva la pregunta. Solo una nueva
acción explícita solicita otro intento; no se añadió reintento automático.
Q&A reutiliza el aviso EN/ES de sugerencia no verificada y el saneador existente.

Tutor/Q&A admite prosa no vacía cuando falla el parser estructurado, con una
frontera conservadora: delimitadores estructurales, fences, comillas iniciales,
literales escalares completos y secuencias numéricas no se convierten en prosa.
No se añadió extracción interior ni raw_decode. El comportamiento histórico del
parser compartido no cambió; no se afirma conformidad JSON estricta universal.
Errores de transporte, envelopes sin respuesta y límites explícitos de salida
siguen fallando. El texto natural parecido a un error no se clasifica por su
significado: una sugerencia visible no demuestra instrucción útil o correcta.

Lecciones, ejercicios, correcciones, roles, revisión/publicación y notas
provisionales conservan sus contratos. No se añadió creación autónoma de cursos
por alumnos. El tutor ya permite ayuda sin profesor conectado.

README y requisitos describen best-effort con modelos/endpoints configurables
mediante adaptadores compatibles. Los resultados históricos permanecen intactos:
v11 30/44 históricos, 10/12 desarrollo y 61/61 trazas. Son diagnósticos de la
configuración evaluada, sin puerta de aceptación de exactitud perfecta.

## Verificación ejecutada

Dependencias directas fijadas del proyecto en entorno aislado; jsdom 26.1.0.
Solo datos y transportes sintéticos, sin inferencias ni llamadas a Actions.

- Python afectado: **216/216 PASS**; tutor, generación, ciclo de solicitudes,
  asistencia, privacidad, transporte, lecciones, ejercicios y calificación.
- DOM completo: **197/197 PASS**; contratos fuente/UI Python: **18/18 PASS**.
- Flake8, mypy de ai_service, sintaxis JS y comprobación de diff: **PASS**.
- Revisión independiente: sin hallazgos bloqueantes; **153** pruebas Python,
  **20** casos adicionales de frontera y **87** pruebas DOM pasan. Estas cifras
  se solapan con las anteriores y no representan pruebas únicas adicionales.

RED previo reprodujo tres fallos de pruebas UI, dos casos de prosa y el posterior
problema de escalares antes de corregirlos. Una expectativa antigua que prohibía
prosa del tutor se actualizó al contrato aprobado; las demás operaciones siguen
rechazándola. No se modificaron puntuaciones ni oráculos históricos de modelos.
El caso ambiguo `tru` no se usa como criterio de error semántico.

## Límites y parada

El smoke de Chromium **no se ejecutó**: el proceso falló con EPERM antes de las
comprobaciones. La emulación DOM no certifica navegador real, accesibilidad o
Windows. No se construyó EXE ni se usaron datos reales. No hubo nueva campaña de
modelos, descargas de modelos, cambios en main ni despliegue.

El siguiente trabajo puede limitarse a verificar en Windows esta revisión exacta:
recorrido funcional con cuentas sintéticas y profesor desconectado, respuesta
simulada estructurada/prosa, fallo explícito y reintento, aviso EN/ES y límites de
roles; después construir en directorio nuevo y comprobar arranque/login/reinicio.
Mantener bases/configuración reales y aplicaciones ajenas intactas. Usar el
procedimiento de bootstrap existente sin publicar credenciales. No convertirlo
en otra selección de modelos o campaña de exactitud; finalizar con evidencia
funcional y límites concretos del paquete.
