"""Tests para generate_schedule — función core Fase 3."""
import pytest
from datetime import datetime

from app.functions.generate_schedule import generate_schedule


@pytest.mark.asyncio
async def test_generate_schedule_returns_phases(sample_budget):
    """Verifica que genera fases correctamente."""
    result = await generate_schedule(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        start_date="2026-05-01",
        work_days_per_week=5,
    )
    
    assert result["project_id"] == "11111111-1111-1111-1111-111111111111"
    assert len(result["phases"]) > 0
    assert "total_weeks" in result


@pytest.mark.asyncio
async def test_generate_schedule_phases_have_correct_dates(sample_budget):
    """Las fechas de inicio/fin son válidas."""
    result = await generate_schedule(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        start_date="2026-05-01",
        work_days_per_week=5,
    )
    
    for phase in result["phases"]:
        # Verify dates are in YYYY-MM-DD format
        datetime.strptime(phase["start_date"], "%Y-%m-%d")
        datetime.strptime(phase["end_date"], "%Y-%m-%d")
        assert phase["weeks"] >= 1
        assert phase["cost"] > 0


@pytest.mark.asyncio
async def test_generate_schedule_falls_back_to_cost_when_no_m2(sample_budget):
    """Si no hay m², usa el fallback de costo total."""
    # Remove m² units from budget
    budget_no_m2 = {
        **sample_budget,
        "items": [
            {**item, "unit": "gl"} 
            for item in sample_budget["items"]
        ]
    }
    
    result = await generate_schedule(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=budget_no_m2,
        start_date="2026-05-01",
    )
    
    # Should still generate phases using fallback
    assert len(result["phases"]) > 0


@pytest.mark.asyncio
async def test_generate_schedule_total_weeks_matches_phases(sample_budget):
    """total_weeks es la suma de semanas de todas las fases."""
    result = await generate_schedule(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        start_date="2026-05-01",
    )
    
    expected_total = sum(phase["weeks"] for phase in result["phases"])
    assert result["total_weeks"] == expected_total


@pytest.mark.asyncio
@pytest.mark.parametrize("work_days", [5, 6])
async def test_generate_schedule_respects_work_days_per_week(sample_budget, work_days):
    """Respetar work_days_per_week unterschiedlich."""
    result = await generate_schedule(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        start_date="2026-05-01",
        work_days_per_week=work_days,
    )
    
    # Debería generar fases sin errores
    assert "phases" in result


@pytest.mark.asyncio
async def test_generate_schedule_only_includes_present_categories(sample_budget):
    """Solo incluye fases con categorías presentes en el presupuesto."""
    result = await generate_schedule(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        start_date="2026-05-01",
    )
    
    budget_categories = {item["category"].lower() for item in sample_budget["items"]}
    
    for phase in result["phases"]:
        # Cada fase tiene al menos una categoría del presupuesto
        phase_cats_lower = [c.lower() for c in phase["categories"]]
        assert any(cat in budget_categories for cat in phase_cats_lower)