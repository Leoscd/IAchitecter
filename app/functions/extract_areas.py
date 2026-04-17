"""
extract_areas — extrae áreas constructivas desde datos del proyecto.

Recibe descripción del proyecto o archivo procesado y devuelve
lista de áreas por tipología con cantidades y unidades.
Implementación completa en Fase 2.
"""
from typing import Any

from app.core.guardrails import with_logging, with_timeout


@with_logging
@with_timeout(seconds=30)
async def extract_areas(
    project_id: str,
    project_description: str,
    project_type: str,
    total_m2: float | None = None,
    raw_data: dict | None = None,
) -> dict[str, Any]:
    """
    Extrae áreas constructivas (m² por tipología, ml, unidades).

    Args:
        project_id: UUID del proyecto
        project_description: Descripción textual del proyecto
        project_type: 'residencial' | 'comercial' | 'industrial'
        total_m2: Superficie total opcional (ayuda a calibrar)
        raw_data: Datos crudos de plano/CSV si ya fueron parseados

    Returns:
        {'project_id': str, 'areas': [{'type': str, 'quantity': float, 'unit': str}]}

    TODO: Implementar en Fase 2
    """
    raise NotImplementedError("extract_areas aún no implementada — Fase 2")
