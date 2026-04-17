"""
extract_areas — extrae áreas constructivas desde la descripción de un proyecto.

Parsea lenguaje natural o datos estructurados para devolver
lista de áreas por tipología con cantidades y unidades.
"""
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.guardrails import with_logging, with_timeout, with_validation

# Patrones de extracción de m² desde texto libre
_AREA_PATTERNS = [
    # "120 m²" / "120m2" / "120 metros cuadrados"
    (r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|metros?\s+cuadrados?)", "total"),
    # "planta baja 80m²"
    (r"planta\s+baja\s+(\d+(?:[.,]\d+)?)\s*(?:m²|m2)", "planta_baja"),
    # "primer piso 60m²"
    (r"(?:primer|1er)\s+piso\s+(\d+(?:[.,]\d+)?)\s*(?:m²|m2)", "primer_piso"),
    # "local comercial 200m²"
    (r"local\s+comercial\s+(\d+(?:[.,]\d+)?)\s*(?:m²|m2)", "local_comercial"),
]

# Factores estándar por tipo de proyecto para estimar subáreas
_AREA_FACTORS: dict[str, dict[str, float]] = {
    "residencial": {
        "losa":        1.0,   # factor sobre total_m2
        "mamposteria": 1.5,   # paredes suelen ser ~1.5x la planta
        "revoque":     3.0,   # dos caras + cielorrasos
        "cimientos":   0.4,   # ml de fundaciones (aprox perímetro)
        "carpinteria": 0.08,  # % del total en unidades
    },
    "comercial": {
        "losa":        1.0,
        "mamposteria": 1.2,
        "revoque":     2.5,
        "cimientos":   0.35,
        "carpinteria": 0.06,
    },
    "industrial": {
        "losa":        1.0,
        "mamposteria": 0.8,
        "revoque":     1.5,
        "cimientos":   0.5,
        "carpinteria": 0.03,
    },
}

_UNIT_MAP = {
    "losa": "m²",
    "mamposteria": "m²",
    "revoque": "m²",
    "cimientos": "ml",
    "carpinteria": "un",
}


class ExtractAreasInput(BaseModel):
    model_config = ConfigDict(strict=False)

    project_id: str
    project_description: str = Field(..., min_length=5)
    project_type: str = Field(..., pattern="^(residencial|comercial|industrial)$")
    total_m2: float | None = Field(default=None, gt=0)


class ExtractAreasOutput(BaseModel):
    model_config = ConfigDict(strict=False)

    project_id: str
    project_type: str
    total_m2: float
    areas: list[dict]
    extraction_method: str


@with_logging
@with_validation(input_model=ExtractAreasInput, output_model=ExtractAreasOutput)
@with_timeout(seconds=30)
async def extract_areas(
    project_id: str,
    project_description: str,
    project_type: str,
    total_m2: float | None = None,
    raw_data: dict | None = None,
) -> dict[str, Any]:
    """
    Extrae áreas constructivas del proyecto.

    Si `total_m2` no se proporciona, intenta extraerlo del texto.
    Luego aplica factores estándar por tipo de proyecto para estimar subáreas.

    Args:
        project_id: UUID del proyecto
        project_description: Descripción textual del proyecto
        project_type: 'residencial' | 'comercial' | 'industrial'
        total_m2: Superficie total opcional (si se conoce exacta)
        raw_data: Datos crudos si ya fueron parseados (prioridad sobre descripción)

    Returns:
        {'project_id', 'project_type', 'total_m2', 'areas': [...], 'extraction_method'}
    """
    extraction_method = "manual"

    # 1. Prioridad: raw_data provisto
    if raw_data and "areas" in raw_data:
        return {
            "project_id": project_id,
            "project_type": project_type,
            "total_m2": raw_data.get("total_m2", total_m2 or 0),
            "areas": raw_data["areas"],
            "extraction_method": "raw_data",
        }

    # 2. Si total_m2 no se dio, intentar extraerlo del texto
    if total_m2 is None:
        total_m2 = _extract_m2_from_text(project_description)
        extraction_method = "text_parsing"

    if total_m2 is None or total_m2 <= 0:
        raise ValueError(
            "No se pudo determinar la superficie total del proyecto. "
            "Por favor indicar los m² totales explícitamente."
        )

    # 3. Calcular subáreas con factores estándar
    factors = _AREA_FACTORS.get(project_type, _AREA_FACTORS["residencial"])
    areas = []
    for area_type, factor in factors.items():
        quantity = round(total_m2 * factor, 2)
        areas.append({
            "type": area_type,
            "quantity": quantity,
            "unit": _UNIT_MAP.get(area_type, "m²"),
            "description": f"{area_type.capitalize()} estimada (factor {factor}x)",
        })

    return {
        "project_id": project_id,
        "project_type": project_type,
        "total_m2": total_m2,
        "areas": areas,
        "extraction_method": extraction_method,
    }


def _extract_m2_from_text(text: str) -> float | None:
    """Intenta extraer superficie en m² del texto usando regex."""
    text_lower = text.lower()
    for pattern, _ in _AREA_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            value_str = match.group(1).replace(",", ".")
            return float(value_str)
    return None
