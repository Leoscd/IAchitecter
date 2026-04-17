"""
generate_schedule — genera cronograma de obra desde el presupuesto.

Devuelve fases de obra con duración estimada en semanas (Gantt simplificado).
Implementación completa en Fase 3.
"""
from typing import Any

from app.core.guardrails import with_logging, with_timeout


@with_logging
@with_timeout(seconds=30)
async def generate_schedule(
    project_id: str,
    budget: dict,
    start_date: str,
    work_days_per_week: int = 5,
) -> dict[str, Any]:
    """
    Genera cronograma de obra basado en el presupuesto.

    Args:
        project_id: UUID del proyecto
        budget: Output de generate_budget
        start_date: Fecha de inicio de obra (YYYY-MM-DD)
        work_days_per_week: Días laborables por semana

    Returns:
        {'project_id': str, 'phases': [...], 'start_date': str, 'end_date': str, 'total_weeks': int}

    TODO: Implementar en Fase 3
    """
    raise NotImplementedError("generate_schedule aún no implementada — Fase 3")
