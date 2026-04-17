"""
adjust_budget — ajusta un presupuesto existente con múltiples operaciones.

Soporta:
- inflation: incremento por factor (ej: 1.15 = +15%)
- discount: descuento % (global o por categoría)
- replace: reemplazar precio de un ítem específico
"""
import copy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.guardrails import with_logging, with_timeout, with_validation


class Adjustment(BaseModel):
    """Representa un ajuste individual al presupuesto."""
    model_config = ConfigDict(strict=True)
    
    operation: str = Field(..., description="inflation | discount | replace")
    # Para 'inflation': factor: float (ej: 1.15 = +15%)
    # Para 'discount': percentage: float (0-100), category: str | None (None = global)
    # Para 'replace': item_code: str, new_unit_price: float
    factor: float | None = None
    percentage: float | None = Field(default=None, ge=0, le=100)
    category: str | None = None
    item_code: str | None = None
    new_unit_price: float | None = Field(default=None, gt=0)


class AdjustInput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    budget: dict = Field(..., description="Output de generate_budget")
    adjustments: list[Adjustment] = Field(..., min_length=1)
    reason: str = ""


class AdjustOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    items: list[dict]
    subtotals: dict[str, float]
    total: float
    currency: str
    reference_date: str
    version: int
    delta: float
    reason: str


@with_logging
@with_validation(input_model=AdjustInput, output_model=AdjustOutput)
@with_timeout(seconds=15)
async def adjust_budget(
    project_id: str,
    budget: dict,
    adjustments: list[dict],
    reason: str = "",
) -> dict[str, Any]:
    """
    Ajusta presupuesto con múltiples operaciones en secuencia.
    
    Operaciones:
    - inflation: multiplica precios por factor
    - discount: aplica descuento (global o por categoría)
    - replace: reemplaza precio de ítem específico
    """
    # Copia profunda para no mutar el original
    working_budget = copy.deepcopy(budget)
    
    original_total = working_budget.get("total", 0)
    items = working_budget.get("items", [])
    
    # Aplicar ajustes en orden
    for adj in adjustments:
        operation = adj.get("operation", "").lower()
        
        if operation == "inflation":
            factor = adj.get("factor", 1.0)
            for item in items:
                item["unit_price"] = round(item.get("unit_price", 0) * factor, 2)
                item["total"] = round(item.get("quantity", 0) * item["unit_price"], 2)
        
        elif operation == "discount":
            percentage = adj.get("percentage", 0)
            category = adj.get("category")  # None = global
            
            if category is None:
                # Descuento global
                for item in items:
                    item["total"] = round(item.get("total", 0) * (1 - percentage/100), 2)
            else:
                # Descuento por categoría
                for item in items:
                    if item.get("category", "").lower() == category.lower():
                        item["total"] = round(item.get("total", 0) * (1 - percentage/100), 2)
        
        elif operation == "replace":
            item_code = adj.get("item_code")
            new_price = adj.get("new_unit_price")
            
            for item in items:
                if item.get("code") == item_code:
                    item["unit_price"] = new_price
                    item["total"] = round(item.get("quantity", 0) * new_price, 2)
    
    # Recalcular subtotals y total
    subtotals = {}
    for item in items:
        category = item.get("category", "general")
        subtotals[category] = subtotals.get(category, 0) + item.get("total", 0)
    
    new_total = round(sum(subtotals.values()), 2)
    delta = round(new_total - original_total, 2)
    
    return {
        "project_id": project_id,
        "items": items,
        "subtotals": {k: round(v, 2) for k, v in subtotals.items()},
        "total": new_total,
        "currency": working_budget.get("currency", "ARS"),
        "reference_date": working_budget.get("reference_date", ""),
        "version": working_budget.get("version", 1) + 1,
        "delta": delta,
        "reason": reason,
    }