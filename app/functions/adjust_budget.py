"""
adjust_budget — aplica ajustes al presupuesto existente.

Permite modificar precios (inflación, descuentos), cambiar materiales
o aplicar factores de corrección sin regenerar desde cero.
Implementación completa en Fase 3.
"""
from typing import Any

from app.core.guardrails import with_logging, with_timeout


@with_logging
@with_timeout(seconds=30)
async def adjust_budget(
    project_id: str,
    budget: dict,
    adjustments: list[dict],
    reason: str = "",
) -> dict[str, Any]:
    """
    Aplica ajustes al presupuesto y registra en audit_trail.

    Args:
        project_id: UUID del proyecto
        budget: Output de generate_budget (versión base)
        adjustments: Lista de ajustes [{'type': 'inflation'|'discount'|'replace', ...}]
        reason: Motivo del ajuste (queda en audit_trail)

    Returns:
        Presupuesto ajustado con versión incrementada y delta calculado

    TODO: Implementar en Fase 3
    """
    raise NotImplementedError("adjust_budget aún no implementada — Fase 3")
