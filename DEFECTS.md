# DEFECTS · SLMEducator — registro consolidado para reparación

Índice único para el propietario. Los informes por campaña (con evidencia
completa) viven en `implementation_documents/auto_testing_*/DEFECTS.md`; este
archivo los referencia y no reescribe su historia.

Estado de los IDs históricos al cierre de la campaña **auto-2026-10-12-001**
(noche, candidato producto `29df5ed`, checkout `dfbc15a`):

| ID | Estado | Clase | Severidad | Resumen | Informe |
|---|---|---|---|---|---|
| SLM-AUTO-001 | REPAIRED en 29df5ed (GUI re-verificada 10-09) | producto | — | Búsqueda rápida sin pérdida de caracteres | auto_testing_2026-10-09_002 |
| SLM-AUTO-004 | REPAIRED en 29df5ed | producto | — | `/tutor` servido como SPA | auto_testing_2026-10-09_002 |
| SLM-AUTO-005 | ABIERTO como límite de presupuesto (reproducido honestamente 10-12) | producto/entorno | S3 | `finish=length` con 0 contenido; el producto rechaza sin éxito falso | auto_testing_2026-10-12_001 |
| SLM-AUTO-014 | REPAIRED en 29df5ed (39 tests GREEN) | producto/tests | S4 | `read_text` sin encoding en tests | auto_testing_2026-10-09_002 |
| SLM-AUTO-015 | REPAIRED en 29df5ed (bytes `c3 b3` verificados) | producto/scripts | S3 | Mojibake en `seed_pilot` | auto_testing_2026-10-09_002 |
| **SLM-AUTO-016** | **OPEN** | producto | **S3** | El objetivo diario usa una base de fechas distinta al día local del usuario (cruce de medianoche) | auto_testing_2026-10-12_001 |
| **SLM-AUTO-017** | **OPEN** | arnés | **S4** | `test_pytest_database_isolation` falla al limpiar temporales en Windows (WinError 32) | auto_testing_2026-10-12_001 |
| **SLM-AUTO-018** | **OPEN** | entorno/proveedor | **S3** | Tutor contextual y 11 AI e2e no completan con el modelo local sustituto (razonador); producto honesto | auto_testing_2026-10-12_001 |
| **SLM-AUTO-019** | **OPEN** | arnés | **S3** | El hook de captura del fixture rompe el catálogo (`json.loads` sobre GET sin body) → 500; evidencia histórica del catálogo a revisar | auto_testing_2026-10-12_001 |
| **SLM-AUTO-020** | **NEEDS_REPRO** | producto (sin confirmar) | S3/S4 | 403 en envío de mensaje con el mensaje creado; 0/28 reproducciones posteriores | auto_testing_2026-10-12_001 |

## Orden sugerido de reparación

1. **Arnés primero** (no tocan producto, desbloquean evidencia):
   - SLM-AUTO-017: cerrar el handler de logging antes del `rmtree` (prueba
     fallida primero).
   - SLM-AUTO-019: guardia en el hook de captura para requests sin body;
     repetir AUTO-AI-02 catálogo y revisar el PASS histórico.
2. **Decisiones de producto** (requieren criterio del propietario):
   - SLM-AUTO-016: ¿el «día» del objetivo diario debe usar la zona horaria de
     la cuenta (`/ajustes/zona-horaria`)?
   - SLM-AUTO-018: ¿subir `TUTOR_MAX_OUTPUT_TOKENS` (hoy 1200, verificado) o
     configurar un modelo local no razonador? (No descargar modelos sin
     permiso.)
3. **Reproducción**:
   - SLM-AUTO-020 con sonda autorizada y bitácora del intento fallido.

## Reglas respetadas por estas campañas

- Sin credenciales, tokens ni datos de personas reales en informes o Git.
- Datos sintéticos desechables; la instalación y los datos del propietario se
  conservan intactos.
- Ninguna afirmación de «aceptación completa»: los PASS heredados son
  resultados comunicados de su campaña, no reejecuciones independientes.
