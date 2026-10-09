# DEFECTS · Campaña auto-2026-10-09-002

Registro único de defectos observados en ESTA ejecución. No renumera ni sobrescribe el
DEFECTS.md histórico `auto-2026-10-08-001` ni sus IDs `SLM-AUTO-001..013`; las
reproducciones de esos defectos en este candidato se enlazan desde aquí con su ID
histórico cuando exista evidencia nueva.

Severidad: S1 pérdida/exposición grave o arranque esencial bloqueado · S2 flujo esencial
roto · S3 función degradada · S4 presentación menor.

---

## SLM-AUTO-014 · Dos pruebas Python no portables a locale ANSI en Windows (read_text sin encoding)

- **Estado**: OPEN
- **Severidad**: S4 (la suite de pruebas falla en Windows con locale cp1252; el producto
  no está afectado: los ficheros fuente/dañados no existen, solo la lectura del test)
- **Prioridad**: Baja (bloquea la puerta «todo verde» en Windows, no la funcionalidad)
- **Fecha/run**: 2026-10-09 · `auto-2026-10-09-002`
- **Candidato**: rama `fix/react-functional-continuation-20261007`, HEAD
  `19909e6038c180ce15f5e987928934d34dfc797e`, árbol `e13ba1248a22294582670eade6e27754af8b94a0`
- **Entorno**: Windows 10/11 (10.0.26200), Python 3.14.7 (`venv` del repo),
  `locale.getpreferredencoding(False) = cp1252`
- **Rol**: n/a (suite técnica)
- **Caso relacionado**: puerta AGENTS.md/CONTRIBUTING (pruebas afectadas); plan
  `tests/test_first_run_setup.py`, `tests/test_operational_documentation.py`
- **Precondiciones**: clon UTF-8 estándar; sin variables `PYTHONUTF8`/`PYTHONIOENCODING`
  (configuración de usuario típica en Windows)

### Hecho observado (literal)

Reproducción 1 — `python -m pytest tests/test_first_run_setup.py -q`:

```
FAILED tests/test_first_run_setup.py::test_native_errors_are_allowlisted_and_password_fields_are_masked
tests\test_first_run_setup.py:127: AssertionError
1 failed, 353 passed, 1 warning in 112.05s
```

La línea 126 hace `source = Path(first_run_setup.__file__).read_text()` SIN
`encoding='utf-8'` y la 127 busca el subtexto `show='' if key == 'username' else '•'`.
Diagnóstico técnico (sonda local, sin modificar nada):

- `src/first_run_setup.py` contiene los bytes UTF-8 del bullet (`e2 80 a2`): VERDADERO
- `locale.getpreferredencoding(False)` → `cp1252`
- subtexto presente decodificando como UTF-8 → VERDADERO; decodificando como cp1252 →
  FALSO (el bullet se corrompe y el assert falla)

Reproducción 2 — `python -m pytest tests/test_operational_documentation.py -q`:

```
FAILED tests/test_operational_documentation.py::test_active_ui_guides_do_not_prescribe_removed_qt_modules
E  UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 10384
tests\test_operational_documentation.py:93: (ROOT / "docs/CONTRIBUTING.md").read_text()
1 failed, 153 passed, 1 warning in 22.12s
```

Misma causa: `read_text()` sin `encoding` decodifica UTF-8 como cp1252 y esta vez lanza
la excepción en lugar de corromper en silencio.

### Esperado / Observado

- Esperado: la suite completa pasa en Windows con locale ANSI (la verificación publicada
  en `returned_defects_repair_20261008/VERIFICATION.json` declara 0 fallos, pero su
  ejecución fue en Linux, donde el codec por defecto es UTF-8).
- Observado: 2 FAILED en Windows con los mismos ficheros intactos.

### Frecuencia y efecto

- Frecuencia: 100% en Windows con locale cp1252 (reproducido 2/2).
- Efecto: ninguna sobre datos ni funcionalidad; sí sobre la puerta de pruebas y sobre
  cualquier claim de «suite verde en Windows».

### Hecho observado vs causa comprobada

- Hecho: los dos tests fallan por decodificación locale; verificado con sondas que
  decodifican los mismos bytes con ambos codecs.
- Causa comprobada: ausencia de `encoding='utf-8'` en `Path.read_text()` dentro de los
  tests (código del test, no del producto).
- Hipótesis de por qué no apareció antes: la verificación del candidato se ejecutó en
  Linux; ningún gate previo corrió estos ficheros en Windows con ANSI.

### Alternativa temporal segura

- Ejecutar con `set PYTHONUTF8=1` (o `PYTHONIOENCODING=utf-8`) en Windows mientras el
  arreglo de test no exista. No aplica a productos ni a instalaciones finales.

### Evidencia

- Lotes locales `C:\builds\slm-pytest-batchA.log` y `C:\builds\slm-pytest-batchB.log`
  (fuera de Git; se publicará solo un extracto saneado con hashes en la evidencia de la
  campaña).
- Sonda `C:\builds\probe_encoding.py` con su salida reproduciendo ambos codecs.
- Qué NO se verificó: el mismo test en Linux (no disponible en este entorno).
