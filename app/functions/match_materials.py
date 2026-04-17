"""
match_materials — cruza áreas con el catálogo de materiales.

Devuelve materiales con precios unitarios de referencia por tipología de área.
En Fase 3 se conectará al catálogo real de Supabase.
Por ahora usa catálogo hardcodeado actualizable.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.guardrails import with_logging, with_timeout, with_validation

# Catálogo base de materiales con precios de referencia ARS (actualizar mensualmente)
# Estructura: area_type → quality_tier → lista de materiales
_CATALOG: dict[str, dict[str, list[dict]]] = {
    "losa": {
        "económico": [{"code": "EST-101", "name": "Losa cerámica H-17", "unit": "m²", "unit_price": 65000.0, "category": "estructura"}],
        "standard": [{"code": "EST-102", "name": "Losa hormigón armado H-21", "unit": "m²", "unit_price": 85000.0, "category": "estructura"}],
        "premium": [{"code": "EST-103", "name": "Losa hormigón postensado H-30", "unit": "m²", "unit_price": 125000.0, "category": "estructura"}],
    },
    "mamposteria": {
        "económico": [{"code": "MAM-101", "name": "Ladrillo común 18cm", "unit": "m²", "unit_price": 28000.0, "category": "estructura"}],
        "standard": [{"code": "MAM-102", "name": "Ladrillo hueco 18cm", "unit": "m²", "unit_price": 32000.0, "category": "estructura"}],
        "premium": [{"code": "MAM-103", "name": "Bloque cerámico portante 19cm", "unit": "m²", "unit_price": 48000.0, "category": "estructura"}],
    },
    "revoque": {
        "económico": [{"code": "TER-101", "name": "Revoque grueso a la cal", "unit": "m²", "unit_price": 12000.0, "category": "terminaciones"}],
        "standard": [{"code": "TER-102", "name": "Revoque proyectado grueso+fino", "unit": "m²", "unit_price": 18500.0, "category": "terminaciones"}],
        "premium": [{"code": "TER-103", "name": "Revoque proyectado + enduído plástico", "unit": "m²", "unit_price": 28000.0, "category": "terminaciones"}],
    },
    "cimientos": {
        "económico": [{"code": "FUN-101", "name": "Fundación corrida H-13", "unit": "ml", "unit_price": 95000.0, "category": "estructura"}],
        "standard": [{"code": "FUN-102", "name": "Fundación corrida H-17 armada", "unit": "ml", "unit_price": 145000.0, "category": "estructura"}],
        "premium": [{"code": "FUN-103", "name": "Vigas de fundación H-21 c/ pilotes", "unit": "ml", "unit_price": 220000.0, "category": "estructura"}],
    },
    "carpinteria": {
        "económico": [{"code": "CAR-101", "name": "Ventana aluminio corrediza DVH simple", "unit": "un", "unit_price": 180000.0, "category": "carpinteria"}],
        "standard": [{"code": "CAR-102", "name": "Ventana aluminio DVH templado", "unit": "un", "unit_price": 320000.0, "category": "carpinteria"}],
        "premium": [{"code": "CAR-103", "name": "Carpintería aluminio anodizado + DVH premium", "unit": "un", "unit_price": 580000.0, "category": "carpinteria"}],
    },
}

REFERENCE_DATE = "2026-04"


class MatchMaterialsInput(BaseModel):
    model_config = ConfigDict(strict=False)

    project_id: str
    areas: list[dict] = Field(..., min_length=1)
    quality_tier: str = Field(default="standard", pattern="^(económico|standard|premium)$")


class MatchMaterialsOutput(BaseModel):
    model_config = ConfigDict(strict=False)

    project_id: str
    materials: list[dict]
    quality_tier: str
    reference_date: str
    catalog_source: str


@with_logging
@with_validation(input_model=MatchMaterialsInput, output_model=MatchMaterialsOutput)
@with_timeout(seconds=30)
async def match_materials(
    project_id: str,
    areas: list[dict],
    specs: dict | None = None,
    quality_tier: str = "standard",
) -> dict[str, Any]:
    """
    Cruza áreas con materiales del catálogo y devuelve lista de materiales con precios.

    Args:
        project_id: UUID del proyecto
        areas: Output de extract_areas (lista con type, quantity, unit)
        specs: Especificaciones adicionales (marca preferida, normas, etc.)
        quality_tier: 'económico' | 'standard' | 'premium'

    Returns:
        {'project_id', 'materials': [...], 'quality_tier', 'reference_date', 'catalog_source'}
    """
    if quality_tier not in ("económico", "standard", "premium"):
        quality_tier = "standard"

    matched_materials = []
    for area in areas:
        area_type = area.get("type", "")
        if area_type not in _CATALOG:
            continue

        tier_materials = _CATALOG[area_type].get(quality_tier, _CATALOG[area_type]["standard"])
        for material in tier_materials:
            enriched = {
                **material,
                "area_type": area_type,
                "description": material.get("description", material["name"]),
            }
            matched_materials.append(enriched)

    if not matched_materials:
        raise ValueError(
            f"No se encontraron materiales para las áreas: "
            f"{[a.get('type') for a in areas]}. "
            f"Verificar que los tipos de área coincidan con el catálogo."
        )

    return {
        "project_id": project_id,
        "materials": matched_materials,
        "quality_tier": quality_tier,
        "reference_date": REFERENCE_DATE,
        "catalog_source": "builtin_v1",
    }
