# Plan de ejecución — App conversacional arquitectura con MiniMax + guardrails

---

## Estado actual — 2026-04-17

### ✅ Fase 1 — Fundaciones (COMPLETA)
### ✅ Fase 2 — Integración MiniMax (COMPLETA)
### ✅ Fase 3 — Funciones restantes + tests (COMPLETA)
- [x] `generate_schedule.py` — cronograma Gantt por fases
- [x] `adjust_budget.py` — operaciones: inflation, discount, replace
- [x] `export_pdf.py` — genera PDF profesional con weasyprint
- [x] Tests: 52/52 passing (100% verde)

### ⚙️ Fase 3b — Mejoras pendientes (PENDIENTE)
- [ ] Endpoint `/api/replay/{execution_id}`
- [ ] Endpoint `/api/errors`
- [ ] Alertas: 3 fallos en 1h → email admin

### 🔲 Fase 4 — Chat web Next.js (PENDIENTE)

---

## Criterios de aceptación (Fase 3 - VERIFICADOS)
- ✅ `pytest app/tests/` corre sin errores (52/52 passing)
- ✅ Las 3 funciones tienen modelos Pydantic Input + Output con `ConfigDict(strict=True)`
- ✅ Orden de decoradores correcto en las 3 funciones (`@with_logging` → `@with_validation` → `@with_timeout`)
- ✅ `adjust_budget` no muta el dict `budget` recibido (usa copia profunda)
- ✅ `generate_schedule` solo incluye fases con ítems reales en el presupuesto
- ✅ `export_pdf` genera PDF sin hacer llamadas reales a Supabase en tests
- ✅ Ningún `print()` ni `logger.debug()` extra
- ✅ 11 archivos modificados/creados en esta fase

---

*Última actualización: 2026-04-17 por Alfred*