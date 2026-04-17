"""Tests para generate_budget — función core Fase 1."""
import pytest

from app.functions.generate_budget import generate_budget


@pytest.mark.asyncio
async def test_generate_budget_returns_correct_total(sample_areas, sample_materials):
    # Arrange
    project_id = "11111111-1111-1111-1111-111111111111"

    # Act
    result = await generate_budget(
        project_id=project_id,
        areas=sample_areas,
        materials=sample_materials,
        currency="ARS",
        reference_date="2026-04",
    )

    # Assert
    assert result["project_id"] == project_id
    assert result["total"] > 0
    assert result["currency"] == "ARS"
    assert len(result["items"]) == len(sample_materials)


@pytest.mark.asyncio
async def test_generate_budget_subtotals_sum_to_total(sample_areas, sample_materials):
    # Arrange / Act
    result = await generate_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        areas=sample_areas,
        materials=sample_materials,
        reference_date="2026-04",
    )

    # Assert
    assert abs(sum(result["subtotals"].values()) - result["total"]) < 0.01


@pytest.mark.asyncio
async def test_generate_budget_skips_unmatched_materials(sample_areas):
    # Arrange — material con area_type que no existe en areas
    materials_no_match = [
        {
            "code": "XXX-001",
            "name": "Material sin área",
            "unit": "m²",
            "unit_price": 1000.0,
            "area_type": "tipo_inexistente",
            "category": "estructura",
        }
    ]

    # Act
    result = await generate_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        areas=sample_areas,
        materials=materials_no_match,
        reference_date="2026-04",
    )

    # Assert — no hay ítems porque no hubo match
    assert result["items"] == []
    assert result["total"] == 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ["ARS", "USD"])
async def test_generate_budget_preserves_currency(sample_areas, sample_materials, currency):
    # Act
    result = await generate_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        areas=sample_areas,
        materials=sample_materials,
        currency=currency,
        reference_date="2026-04",
    )

    # Assert
    assert result["currency"] == currency


@pytest.mark.asyncio
async def test_generate_budget_item_total_equals_quantity_times_price(sample_areas, sample_materials):
    # Act
    result = await generate_budget(
        project_id="11111111-1111-1111-1111-111111111111",
        areas=sample_areas,
        materials=sample_materials,
        reference_date="2026-04",
    )

    # Assert — cada ítem: total = quantity * unit_price
    for item in result["items"]:
        expected = round(item["quantity"] * item["unit_price"], 2)
        assert abs(item["total"] - expected) < 0.01, (
            f"Ítem {item['code']}: total {item['total']} != {expected}"
        )
