"""Tests para extract_areas."""
import pytest

from app.functions.extract_areas import extract_areas


@pytest.mark.asyncio
async def test_extract_areas_from_explicit_m2():
    result = await extract_areas(
        project_id="11111111-1111-1111-1111-111111111111",
        project_description="Casa unifamiliar de dos plantas",
        project_type="residencial",
        total_m2=120.0,
    )

    assert result["total_m2"] == 120.0
    assert result["project_type"] == "residencial"
    assert len(result["areas"]) > 0
    assert all("type" in a and "quantity" in a and "unit" in a for a in result["areas"])


@pytest.mark.asyncio
async def test_extract_areas_parses_m2_from_text():
    result = await extract_areas(
        project_id="11111111-1111-1111-1111-111111111111",
        project_description="Vivienda unifamiliar de 95 m² en planta baja",
        project_type="residencial",
    )

    assert result["total_m2"] == 95.0
    assert result["extraction_method"] == "text_parsing"


@pytest.mark.asyncio
async def test_extract_areas_raises_without_m2_info():
    with pytest.raises(ValueError, match="superficie total"):
        await extract_areas(
            project_id="11111111-1111-1111-1111-111111111111",
            project_description="Una casa bonita sin medidas",
            project_type="residencial",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("project_type", ["residencial", "comercial", "industrial"])
async def test_extract_areas_all_project_types(project_type):
    result = await extract_areas(
        project_id="11111111-1111-1111-1111-111111111111",
        project_description="Proyecto genérico",
        project_type=project_type,
        total_m2=200.0,
    )

    assert result["project_type"] == project_type
    assert result["total_m2"] == 200.0


@pytest.mark.asyncio
async def test_extract_areas_from_raw_data():
    raw = {
        "total_m2": 150.0,
        "areas": [{"type": "losa", "quantity": 150.0, "unit": "m²"}],
    }

    result = await extract_areas(
        project_id="11111111-1111-1111-1111-111111111111",
        project_description="ignorado",
        project_type="residencial",
        raw_data=raw,
    )

    assert result["extraction_method"] == "raw_data"
    assert result["areas"] == raw["areas"]
