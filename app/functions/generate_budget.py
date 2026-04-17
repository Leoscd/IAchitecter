"""
generate_budget — genera un presupuesto detallado de obra.

Recibe áreas y materiales ya procesados, aplica precios unitarios
y devuelve estructura completa de ítems con totales por categoría.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.guardrails import with_logging, with_timeout, with_validation


class BudgetItem(BaseModel):
    model_config = ConfigDict(strict=True)

    code: str = Field(..., description="Código de ítem (ej: 'EST-001')")
    description: str
    unit: str = Field(..., description="Unidad de medida (m², ml, kg, gl)")
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    total: float = Field(..., gt=0)
    category: str = Field(..., description="Categoría (estructura, terminaciones, instalaciones, etc.)")


class BudgetInput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    areas: list[dict] = Field(..., min_length=1)
    materials: list[dict] = Field(..., min_length=1)
    currency: str = Field(default="ARS")
    reference_date: str = Field(..., description="Fecha de referencia de precios YYYY-MM")


class BudgetOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    items: list[BudgetItem]
    subtotals: dict[str, float]
    total: float
    currency: str
    reference_date: str
    version: int = 1


@with_logging
@with_validation(input_model=BudgetInput, output_model=BudgetOutput)
@with_timeout(seconds=30)
async def generate_budget(
    project_id: str,
    areas: list[dict],
    materials: list[dict],
    currency: str = "ARS",
    reference_date: str = "",
) -> dict[str, Any]:
    """
    Genera presupuesto detallado cruzando áreas con materiales y precios.

    Los precios unitarios vienen en `materials` (campo `unit_price`).
    Las cantidades se calculan desde `areas` (campo `quantity` en unidad del material).
    """
    items: list[dict] = []
    subtotals: dict[str, float] = {}

    for material in materials:
        area = next(
            (a for a in areas if a.get("type") == material.get("area_type")),
            None,
        )
        if not area:
            continue

        quantity = float(area.get("quantity", 0))
        unit_price = float(material.get("unit_price", 0))
        total = round(quantity * unit_price, 2)
        category = material.get("category", "general")

        items.append({
            "code": material.get("code", f"ITEM-{len(items)+1:03d}"),
            "description": material.get("description", material.get("name", "")),
            "unit": material.get("unit", "m²"),
            "quantity": quantity,
            "unit_price": unit_price,
            "total": total,
            "category": category,
        })
        subtotals[category] = subtotals.get(category, 0) + total

    return {
        "project_id": project_id,
        "items": items,
        "subtotals": {k: round(v, 2) for k, v in subtotals.items()},
        "total": round(sum(subtotals.values()), 2),
        "currency": currency,
        "reference_date": reference_date,
        "version": 1,
    }
