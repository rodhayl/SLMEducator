# SUMMARY · Campaña auto-2026-10-08-001 — TERMINADA en este entorno

**Estado: TERMINADA según el criterio del §15.** Las 117 filas tienen evidencia actual o motivo
específico de bloqueo/no aplicabilidad (`NOT_RUN = 0`). No quedan acciones independientes útiles
permitidas en este entorno: lo pendiente exige control de escritorio/VM, Setup vigente, lector de
pantalla, fixtures de escala o correcciones de producto (que abrirían candidato y campaña nuevos).

## 1. Candidato exacto

| | |
|---|---|
| Tipo | Checkout ejecutado como runtime web local. **No** es el Setup instalado ni un portable |
| Rama / HEAD / árbol | `fix/react-functional-continuation-20261007` · `0f3ff15` · `4faf96` |
| Base de producto | `642966a` (árbol `e0a3966`), diferencia solo documental (4 ficheros) |
| Frontend | `src/frontend` compilado en la sesión 1 (26 assets, 29 licencias verificados) |
| Origen | `http://127.0.0.1:8000` vía `src/starter_headless.py`, PID propio |
| Datos | Base sintética desechable nueva en el temporal de la campaña |
| No probado | Setup instalado, portable, Setup histórico `fe954cab4655` (no contiene esta GUI, no abrir) |

Evidencia: `GUI_CDP` (DevTools/CDP por orden de David; la app es web-only). Lo que exige pantalla del
sistema queda BLOCKED, nunca PASS.

## 2. Totales por estado (denominador explícito: 117 filas)

| Estado | Filas | % |
|---|---|---|
| PASS | 45 | 38 % |
| PARTIAL | 41 | 35 % |
| FAIL | 4 | 3 % |
| BLOCKED | 26 | 22 % |
| NOT_APPLICABLE | 1 | 1 % |
| **NOT_RUN** | **0** | **0 %** |

El 38 % de PASS no es una medida de calidad: 41 filas son parciales y 26 están bloqueadas.

Desglose de FAIL (4): `AUTO-GEN-01.leccion`, `AUTO-AI-03.inferencia_real` (fallos directos) y
`PLAN-D3`, `PLAN-A4` (trazabilidad que deriva de ellos).

Desglose de BLOCKED (26): 5 BOOT + LIFE + VIS-04 + VIS-06 + VIS-07 + SCALE/G7 + SW-01 + SW-02
(entorno) + TUT-01..03 + QA-01..03 + AI-04 + GEN-03/04 + TUT/QA/G1/G2 en PLAN (producto:
SLM-AUTO-004/005) + PORT-04 + X2 + G7 (restricción de directorio / entorno).

## 3. Defectos por impacto (detalle en `DEFECTS.md`, 13 registros)

| ID | Sev | Resumen | Estado |
|---|---|---|---|
| SLM-AUTO-004 | **S2** | `/tutor` no se sirve (404 con JSON crudo); el contrato del frontend la declara válida y `SPA_PATH` no la incluye | OPEN — bloquea TUT y QA |
| SLM-AUTO-005 | **S2** | Generar con IA → 500 tras HTTP 200 del proveedor (2/2), sin traza en el log | OPEN — generación inservible |
| SLM-AUTO-001 | S3 | Buscador de Personas pierde caracteres con escritura rápida | OPEN |
| SLM-AUTO-003 | S3 | Claves duplicadas rechazadas sin señalar campo | OPEN |
| SLM-AUTO-008 | S3 | Rúbrica no aplicable al calificar | OPEN |
| SLM-AUTO-012 | S3 | Rechazos de archivo en Fuentes con mensaje genérico indistinguible | OPEN |
| SLM-AUTO-002 | S4 | Biblioteca vacía indistinguible de filtro sin resultados | OPEN |
| SLM-AUTO-006 | S4 | Cursos homónimos indistinguibles | OPEN |
| SLM-AUTO-007 | S4 | Lección con seis encabezados de sección vacíos | OPEN |
| SLM-AUTO-009 | S4 | Editor de evaluación oculta el vínculo con curso (el vínculo sí funciona) | OPEN |
| SLM-AUTO-010 | S4 | Mensajes del servidor en inglés sin declaración (patrón sistémico, 2 ocurrencias) | OPEN |
| SLM-AUTO-011 | S4 | Tras el traspaso, el docente saliente pierde la ficha del estudiante | OPEN |
| SLM-AUTO-013 | S4 | Encabezado `Lesson` en inglés en interfaz española | OPEN |

**Regresión histórica cerrada**: `H-D3` (alta con correo inválido) — corregida en este candidato.

## 4. Funciones realmente observadas con éxito

Cuentas y permisos · matrícula con confirmación · búsqueda que sobrevive a la navegación · ciclo
borrador→revisado→publicado→asignado con orden persistido · revisión independiente · autoría de
material y evaluación con validaciones por campo · fuentes TXT/MD/PDF con extracción declarada ·
sesión de estudio con notas y progreso · práctica sin revelar clave y con borrador restaurable ·
entrega única · corrección 9/10 coherente · ayuda con respuesta y resolución separadas · mensajes con
ID y archivo reversible · aislamiento de S2 en 5 recursos · cierre sin envío y vencimiento con estados
distintos · desactivar/reactivar verificado · traspaso con autoría conservada · persistencia tras dos
reinicios · conexión real a LM Studio y catálogo · idioma, tema, zona horaria y objetivo diario.

## 5. IA real por cuenta

| Cuenta | Proveedor / modelo | Resultado |
|---|---|---|
| `docente_auto08` | `lm_studio` / `slm-production-evaluation` | Conexión OK (16 951 ms) · catálogo OK (4) · **generación FAIL · tutor inaccesible** |
| admin, S1, S2 | sin configurar | Sin pruebas de IA bajo esas cuentas |

Ningún texto del modelo llegó a pantalla: **sin evidencia de utilidad educativa**.

## 6. Diferencias respecto a informes anteriores

- `H-D3`: **corregido**. Los PASS históricos del binario `fe954cab4655` no se transfieren (no contiene
  esta GUI). Las cifras 825/249/8 no se suman. `SLM-AUTO-004` es hallazgo nuevo, no figura en
  DEFICIENCIAS ni en G1–G5.

## 7. Evidencias por tipo

| Tipo | Estado |
|---|---|
| GUI (14 capturas inspeccionadas) | Sí |
| Técnica (hashes, logs saneados, inventario) | Sí |
| Proveedor real | Parcial: conexión y catálogo; generación no |
| Humana / lector / hardware | No disponibles |
| Installer / ciclo de vida / SW / escala | No ejecutados (BLOCKED con motivo) |

## 8. Lo que este informe NO afirma

No se afirma «100 % funcional», «sin bugs», «seguro», «accesible», «Windows certificado» ni
compatibilidad de proveedores. Sin zoom nativo, lector, contraste medido, rendimiento a escala,
migración ni instalador. Calidad educativa, menores y normativa no se certifican.

## 9. Qué falta y su acción mínima

| Pendiente | Acción mínima |
|---|---|
| BOOT/LIFE/VIS-04/06/07 | Control de escritorio/VM + Setup vigente (MANUAL_TEST1) |
| SLM-AUTO-004/005 | Corrección de producto → candidato y campaña nuevos |
| PORT-02/04, PORT-03 (descarga) | Autorizar directorio de descargas o revisarlo David |
| SCALE/G7, SW-01/02 | Fixtures de escala y legacy autorizadas |
| QA/TUT completos, GEN-03/04 | Dependen de SLM-AUTO-004/005 |

## 10. Publicación

Nada publicado ni commiteado. Todo local en
`implementation_documents/auto_testing_2026-10-08_001/`. Sin autorización vigente para publicar en
ninguna rama.
