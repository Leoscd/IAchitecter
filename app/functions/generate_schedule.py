"""
generate_schedule — genera un cronograma Gantt por fases desde un presupuesto.

Toma el output de generate_budget y genera fechas de inicio/fin
para cada fase de obra (cimientos, estructura, instalaciones, etc.).
"""
from datetime import datetime, timedelta
from math import ceil
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.guardrails import with_logging, with_timeout, with_validation


class ScheduleInput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    budget: dict = Field(..., description="Output de generate_budget")
    start_date: str = Field(..., description="Fecha inicio YYYY-MM-DD")
    work_days_per_week: int = Field(default=5, ge=1, le=7)


class Phase(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str = Field(..., description="Nombre de la fase")
    categories: list[str] = Field(..., description="Categorías del presupuesto que abarca")
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    weeks: int = Field(..., ge=1)
    cost: float = Field(..., gt=0)


class ScheduleOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    phases: list[Phase]
    start_date: str
    end_date: str
    total_weeks: int


def add_business_days(start_date: datetime, days: int, work_days_per_week: int) -> datetime:
    """Agrega días hábiles considerando work_days_per_week."""
    current = start_date
    added = 0
    
    while added < days:
        current += timedelta(days=1)
        # Skip weekends based on work_days_per_week
        if work_days_per_week == 5 and current.weekday() >= 5:
            continue
        if work_days_per_week == 6 and current.weekday() == 6:
            continue
        added += 1
    
    return current


@with_logging
@with_validation(input_model=ScheduleInput, output_model=ScheduleOutput)
@with_timeout(seconds=30)
async def generate_schedule(
    project_id: str,
    budget: dict,
    start_date: str,
    work_days_per_week: int = 5,
) -> dict[str, Any]:
    """
    Genera cronograma Gantt desde presupuesto.
    
    Fases en orden: cimientos, estructura, instalaciones, terminaciones, varios.
    Solo incluye fases que tienen ítems en el presupuesto.
    """
    # Fixed phase order
    PHASE_ORDER = ["cimiento", "estructura", "instalaciones", "terminaciones", "varios"]
    PHASE_NAMES = {
        "cimiento": "Cimientos",
        "estructura": "Estructura",
        "instalaciones": "Instalaciones",
        "terminaciones": "Terminaciones",
        "varios": "Varios",
    }
    
    # Extract categories present in budget
    budget_items = budget.get("items", [])
    present_categories = set(item.get("category", "").lower() for item in budget_items)
    
    # Calculate total m2 or fallback
    total_m2 = sum(
        item.get("quantity", 0) 
        for item in budget_items 
        if item.get("unit", "").lower() in ["m²", "m2", "mt2"]
    )
    
    if total_m2 > 0:
        total_estimated_weeks = ceil(total_m2 / 12)
    else:
        total_estimated_weeks = ceil(budget.get("total", 0) / 5_000_000)
        total_estimated_weeks = max(1, total_estimated_weeks)
    
    # Calculate total cost
    total_cost = budget.get("total", 0)
    
    # Build phases
    phases = []
    current_start = datetime.strptime(start_date, "%Y-%m-%d")
    
    for phase_key in PHASE_ORDER:
        # Find categories that match this phase
        phase_categories = [
            cat for cat in present_categories 
            if phase_key in cat.lower()
        ]
        
        if not phase_categories:
            continue
        
        # Calculate phase cost
        phase_cost = sum(
            item.get("total", 0) 
            for item in budget_items 
            if item.get("category", "").lower() in phase_categories
        )
        
        if phase_cost <= 0:
            continue
        
        # Calculate weeks proportionally
        weeks = max(1, round(phase_cost / total_cost * total_estimated_weeks))
        
        # Calculate end date
        end_date = add_business_days(current_start, weeks * 7, work_days_per_week)
        
        phases.append({
            "name": PHASE_NAMES.get(phase_key, phase_key.title()),
            "categories": phase_categories,
            "start_date": current_start.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "weeks": weeks,
            "cost": round(phase_cost, 2),
        })
        
        # Next phase starts after this one
        current_start = end_date + timedelta(days=1)
    
    # Calculate total weeks
    total_weeks = sum(p["weeks"] for p in phases)
    
    return {
        "project_id": project_id,
        "phases": phases,
        "start_date": start_date,
        "end_date": current_start.strftime("%Y-%m-%d") if phases else start_date,
        "total_weeks": total_weeks,
    }