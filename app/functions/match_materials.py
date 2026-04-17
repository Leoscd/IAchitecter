"""
match_materials — cruza áreas con materiales del catálogo.

Recibe áreas extraídas y especificaciones del proyecto,
devuelve lista de materiales con cantidades y precios unitarios.
Implementación completa en Fase 2.
"""
from typing import Any

from app.core.guardrails import with_logging, with_timeout


@with_logging
@with_timeout(seconds=30)
async def match_materials(
    project_id: str,
    areas: list[dict],
    specs: dict | None = None,
    quality_tier: str = "standard",
) -> dict[str, Any]:
    """
    Cruza áreas con materiales disponibles respetando especificaciones.

    Args:
        project_id: UUID del proyecto
        areas: Output de extract_areas (lista de áreas)
        specs: Especificaciones adicionales (marca preferida, normas, etc.)
        quality_tier: 'económico' | 'standard' | 'premium'

    Returns:
        {'project_id': str, 'materials': [{'code', 'name', 'unit', 'unit_price', 'area_type', 'category'}]}

    TODO: Implementar en Fase 2
    """
    raise NotImplementedError("match_materials aún no implementada — Fase 2")
