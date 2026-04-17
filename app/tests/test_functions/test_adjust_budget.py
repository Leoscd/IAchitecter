"""Tests para adjust_budget — función core Fase 3."""
import pytest

from app.functions.adjust_budget import adjust_budget, Adjustment


@pytest.mark.asyncio
async def test_inflation_increases_total(sample_budget):
    """Incremento por factor aumenta el total."""
    adjustments = [
        {"operation": "inflation", "factor": 1.15}  # +15%
    ]
    
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=adjustments,
        reason="Inflación mensual",
    )
    
    expected = sample_budget["total"] * 1.15
    assert abs(result["total"] - expected) < 100


@pytest.mark.asyncio
async def test_discount_decreases_total(sample_budget):
    """Descuento global reduce el total."""
    adjustments = [
        {"operation": "discount", "percentage": 10}  # -10%
    ]
    
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=adjustments,
    )
    
    expected = sample_budget["total"] * 0.90
    assert abs(result["total"] - expected) < 100


@pytest.mark.asyncio
async def test_discount_by_category(sample_budget):
    """Descuento solo afecta ítems de esa categoría."""
    adjustments = [
        {"operation": "discount", "percentage": 20, "category": "estructura"}
    ]
    
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=adjustments,
    )
    
    # Solo estructura debería tener descuento
    estructura_items = [i for i in result["items"] if i["category"] == "estructura"]
    terminaciones_items = [i for i in result["items"] if i["category"] == "terminaciones"]
    
    # Estructura tuvo 20% descuento
    for item in estructura_items:
        orig = next(i for i in sample_budget["items"] if i["code"] == item["code"])
        assert item["total"] == orig["total"] * 0.8
    
    # Terminaciones sin cambio
    for item in terminaciones_items:
        orig = next(i for i in sample_budget["items"] if i["code"] == item["code"])
        assert item["total"] == orig["total"]


@pytest.mark.asyncio
async def test_replace_item_price(sample_budget):
    """Nuevo unit_price se refleja en total del ítem."""
    adjustments = [
        {"operation": "replace", "item_code": "EST-001", "new_unit_price": 100000.0}
    ]
    
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=adjustments,
    )
    
    est001 = next(i for i in result["items"] if i["code"] == "EST-001")
    # quantity 120 * new_price 100000 = 12,000,000
    assert est001["unit_price"] == 100000.0
    assert est001["total"] == 120.0 * 100000.0


@pytest.mark.asyncio
async def test_version_incremented(sample_budget):
    """Version se incrementa en 1."""
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=[{"operation": "inflation", "factor": 1.1}],
    )
    
    assert result["version"] == sample_budget["version"] + 1


@pytest.mark.asyncio
async def test_delta_correct(sample_budget):
    """Delta es la diferencia entre nuevo y original."""
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=[{"operation": "inflation", "factor": 1.25}],
    )
    
    expected_delta = result["total"] - sample_budget["total"]
    assert result["delta"] == expected_delta


@pytest.mark.asyncio
async def test_adjustments_applied_in_order(sample_budget):
    """Inflation + discount encadenados dan resultado correcto."""
    adjustments = [
        {"operation": "inflation", "factor": 1.10},  # +10%
        {"operation": "discount", "percentage": 10},  # -10%
    ]
    # Resultado esperado: 1.10 * 0.90 = 0.99 del original
    
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=adjustments,
    )
    
    expected = sample_budget["total"] * 0.99
    assert abs(result["total"] - expected) < 100


@pytest.mark.asyncio
async def test_preserves_currency(sample_budget):
    """La moneda se preserva."""
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=[{"operation": "inflation", "factor": 1.05}],
    )
    
    assert result["currency"] == sample_budget["currency"]


@pytest.mark.asyncio
async def test_reason_included(sample_budget):
    """El reason se incluye en el output."""
    result = await adjust_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        adjustments=[{"operation": "inflation", "factor": 1.1}],
        reason="Ajuste por variación de costos",
    )
    
    assert result["reason"] == "Ajuste por variación de costos"