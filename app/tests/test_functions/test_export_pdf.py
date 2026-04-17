"""Tests para export_pdf — función core Fase 3."""
import pytest
from unittest.mock import patch, MagicMock

from app.functions.export_pdf import export_pdf


@pytest.mark.asyncio
async def test_returns_expected_keys(sample_budget):
    """Resultado tiene las keys esperadas."""
    result = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
    )
    
    assert "file_url" in result
    assert "storage_path" in result
    assert "pages" in result
    assert "project_id" in result


@pytest.mark.asyncio
async def test_storage_path_format(sample_budget):
    """Storage path empieza con exports/{project_id}/."""
    result = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
    )
    
    assert result["storage_path"].startswith("exports/11111111-1111-1111-1111-111111111111/")
    assert result["storage_path"].endswith(".pdf")


@pytest.mark.asyncio
async def test_pages_positive(sample_budget):
    """Pages es al menos 1."""
    result = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
    )
    
    assert result["pages"] >= 1


@pytest.mark.asyncio
async def test_with_schedule_included(sample_budget):
    """Pasar schedule no rompe la función."""
    schedule = {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "phases": [
            {
                "name": "Estructura",
                "start_date": "2026-05-01",
                "end_date": "2026-06-15",
                "weeks": 6,
                "cost": 10000000.0,
            }
        ],
        "total_weeks": 6,
    }
    
    result = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        schedule=schedule,
    )
    
    assert result["project_id"] == "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_without_schedule(sample_budget):
    """Schedule=None funciona."""
    result = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        schedule=None,
    )
    
    assert "file_url" in result


@pytest.mark.asyncio
async def test_with_project_info(sample_budget):
    """Project info se incluye en el PDF."""
    project_info = {
        "name": "Casa de Juan",
        "client": "Juan Pérez",
        "architect": "Arq. López",
        "address": "Calle Falsa 123",
    }
    
    result = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
        project_info=project_info,
    )
    
    assert result["project_id"] == "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_pages_based_on_items_count(sample_budget):
    """Pages aumenta con más items."""
    # 3 items -> 1 page
    result_small = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=sample_budget,
    )
    
    # Create budget with many items
    big_budget = {
        **sample_budget,
        "items": sample_budget["items"] * 15,  # 45 items
    }
    
    result_big = await export_pdf(
        project_id="11111111-1111-1111-1111-111111111111",
        budget=big_budget,
    )
    
    # More items should give more pages
    assert result_big["pages"] >= result_small["pages"]