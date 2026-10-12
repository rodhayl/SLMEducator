# SUMMARY · auto-2026-10-12-001 (noche + continuación diurna 002)

Decisiones del propietario aplicadas: zona horaria Madrid, subir el tope del
tutor (modelo local, sin límites para esta prueba), ejecutar todo lo restante
resolviendo en vez de declarar bloqueos.

## Cambios autorizados (con prueba previa y regresión)

1. **Tope del tutor 1200 → 4000** (`src/core/services/ai_service.py:93` + 3
   fijaciones de test). Línea base 137 PASS con 1200; regresión 180 PASS;
   verificación extremo a extremo con inferencia real (contextual 200,
   1775 tokens, respuesta útil en 81.5 s).
2. **Tests de objetivo diario herméticos (Madrid)** sin tocar el default UTC
   documentado del producto. Nueva regresión de frontera Madrid en verde
   (89 PASS en temporal+objetivo+scoring). Zona Madrid aplicada por GUI y
   sellos `(Europe/Madrid)` verificados.
3. **Hook de captura del fixture** (SLM-AUTO-019): body vacío → `None`;
   regression test con 3 casos; catálogo verificado en vivo
   («3 nombres de modelos recibidos»).

No aplicado (requiere decisión explícita): presupuesto de `grade_answer`
(1000) y default UTC global (alcance de refactorización).

## Cobertura (COVERAGE.csv, 152 casos)

| Estado | Casos |
|---|---|
| PASS | 141 |
| PARTIAL | 6 |
| BLOCKED | 5 |
| NOT_RUN | 0 |
| FAIL | 0 |

- Los 5 BLOCKED exigen la instalación/destino del propietario o su primera
  cuenta (AUTO-BOOT-01/05/06, LIFE-01, TECH-SETUP-INSTALL): insolubles sin
  tocar su instalación, con requisito exacto documentado.
- Los 6 PARTIAL tienen vía de cierre identificada: lector acústico humano
  (VIS-06), menú nativo 100/200/400% humano (VIS-04), resto 018 (modelo o
  presupuesto de grading), suite r2 (sin fallos nuevos).

## Ejecutado en la continuación 002 (evidencia propia)

- **Cadena de evaluación completa**: borrador → previa sin consumo → política
  IA desactivada → publicación → asignación → intento con diálogo de reserva →
  borrador local + recuperación exacta tras recarga → envío único (doble
  imposible) → Q1 5/5 auto → calificación con rúbrica 2/2/1 + feedback →
  final 10/10 → feedback visible con desglose. Hallazgo de arnés: vaciar el
  borrador de rúbrica antes de guardar (bloqueo silencioso documentado).
- **Lote GEN-03 completo**: parcial real (Lección Fallido + Ejercicio En
  curso) → cancelación → reintento que reutiliza sin duplicar → parada
  solicitada y cumplida → todo Listo (materiales 4–7 únicos).
- **Tutor contextual con tope 4000**: 200 verificado por recibo.
- **Aula**: nota + anotación guardadas, recuperación exacta de borrador,
  sesión completada en solo lectura, prácticas no incluidas (material de
  ejercicio en curso sin asignar: LEARN-03 se mantiene del run anterior).
- **Mensajería**: archivado/desarchivado compartido en ambas cuentas.
- **Portabilidad**: importación vacía/malformada rechazada sin parciales.
- **Cursos homónimos**: IDs 3 y 4 estables.
- **Contraseña**: rotación con negativo, confirmación, revocación, reentrada
  OK y vieja 401.
- **Legacy designer**: instantánea, restauración y descarte verificados.
- **Admin**: restauración solo por procedimiento, sin botón GUI.
- **SW-01/02**: migración viva de dos pestañas con fixture mantenido
  (14/14: espera sin tocar sucia, activación al cerrar última, retiro
  selectivo, testigos y borradores).
- **VIS-04**: equivalencias 200/400/320 sin desbordamiento ni pérdida de foco.
- **VIS-06**: árbol AX (147 nodos, 0 sin nombre); Narrator presente sin canal
  de captura → pasada acústica humana pendiente.
- **G6**: inventario de código compartido entregado, sin refactor.

## Suites

- pytest r2 (tras cambios): **5 failed, 1794 passed, 29 skipped** (3917 s).
  10 fallos previos resueltos. Restan: 2 de limpieza Windows (017), 3 de
  modelo sustituto (resto 018).
- vitest r2: **967/967 PASS** con los cambios.

## Defectos (DEFECTS.md)

| ID | Estado |
|---|---|
| SLM-AUTO-016 | REPARADO EN TESTS (Madrid hermético; default UTC intacto) |
| SLM-AUTO-017 | OPEN (arnés, limpieza Windows) |
| SLM-AUTO-018 | PARCIALMENTE RESUELTO (tope 4000 verificado; resto: grading-1000 y modelo) |
| SLM-AUTO-019 | REPARADO EN EL ARNÉS (unit + vivo) |
| SLM-AUTO-020 | NEEDS_REPRO (40+ envíos sin reproducción; lockout verificado de paso) |

Sin pérdida de datos, exposición ni falso éxito en ningún camino. Prácticas de
estudiante (LEARN-03 con material de ejercicio) y lector acústico quedan como
únicas vías humanas pendientes junto a instalación/primera cuenta.
