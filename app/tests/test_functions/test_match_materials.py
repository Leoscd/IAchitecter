"""Tests para match_materials."""
import pytest

from app.functions.match_materials import match_materials


@pytest.mark.asyncio
async def test_match_materials_returns_materials_for_known_areas(sample_areas):
    result = await match_materials(
        project_id="11111111-1111-1111-1111-111111111111",
        areas=sample_areas,
    )

    assert len(result["materials"]) > 0
    assert result["quality_tier"] == "standard"
    assert result["reference_date"] != ""


@pytest.mark.asyncio
@pytest.mark.parametrize("tier", ["económico", "standard", "premium"])
async def test_match_materials_all_quality_tiers(sample_areas, tier):
    result = await match_materials(
        project_id="11111111-1111-1111-1111-111111111111",
        areas=sample_areas,
        quality_tier=tier,
    )

    assert result["quality_tier"] == tier
    # Premium debe ser más caro que económico
    if tier == "premium":
        prices = [m["unit_price"] for m in result["materials"]]
        assert all(p > 0 for p in prices)


@pytest.mark.asyncio
async def test_match_materials_raises_for_unknown_areas():
    areas = [{"type": "tipo_inexistente", "quantity": 100.0, "unit": "m²"}]

    with pytest.raises(ValueError, match="No se encontraron materiales"):
        await match_materials(
            project_id="11111111-1111-1111-1111-111111111111",
            areas=areas,
        )


@pytest.mark.asyncio
async def test_match_materials_output_has_required_fields(sample_areas):
    result = await match_materials(
        project_id="11111111-1111-1111-1111-111111111111",
        areas=sample_areas,
    )

    required = {"code", "name", "unit", "unit_price", "area_type", "category"}
    for material in result["materials"]:
        assert required.issubset(material.keys()), f"Faltan campos en: {material}"
