"""Fixtures compartidas para todos los tests."""
import pytest


@pytest.fixture
def sample_project():
    return {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Casa Unifamiliar 120m²",
        "type": "residencial",
        "total_m2": 120.0,
    }


@pytest.fixture
def sample_areas():
    return [
        {"type": "losa", "quantity": 120.0, "unit": "m²"},
        {"type": "mamposteria", "quantity": 180.0, "unit": "m²"},
        {"type": "revoque", "quantity": 360.0, "unit": "m²"},
        {"type": "cimientos", "quantity": 45.0, "unit": "ml"},
    ]


@pytest.fixture
def sample_materials():
    return [
        {
            "code": "EST-001",
            "name": "Hormigón H-21 losa",
            "description": "Hormigón armado para losa",
            "unit": "m²",
            "unit_price": 85000.0,
            "area_type": "losa",
            "category": "estructura",
        },
        {
            "code": "MAM-001",
            "name": "Ladrillo común 18cm",
            "description": "Mampostería ladrillo común",
            "unit": "m²",
            "unit_price": 32000.0,
            "area_type": "mamposteria",
            "category": "estructura",
        },
        {
            "code": "TER-001",
            "name": "Revoque fino proyectado",
            "description": "Revoque interior grueso+fino",
            "unit": "m²",
            "unit_price": 18500.0,
            "area_type": "revoque",
            "category": "terminaciones",
        },
    ]


@pytest.fixture
def sample_budget(sample_areas, sample_materials):
    return {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "items": [
            {
                "code": "EST-001",
                "description": "Hormigón armado para losa",
                "unit": "m²",
                "quantity": 120.0,
                "unit_price": 85000.0,
                "total": 10200000.0,
                "category": "estructura",
            },
            {
                "code": "MAM-001",
                "description": "Mampostería ladrillo común",
                "unit": "m²",
                "quantity": 180.0,
                "unit_price": 32000.0,
                "total": 5760000.0,
                "category": "estructura",
            },
            {
                "code": "TER-001",
                "description": "Revoque interior grueso+fino",
                "unit": "m²",
                "quantity": 360.0,
                "unit_price": 18500.0,
                "total": 6660000.0,
                "category": "terminaciones",
            },
        ],
        "subtotals": {"estructura": 15960000.0, "terminaciones": 6660000.0},
        "total": 22620000.0,
        "currency": "ARS",
        "reference_date": "2026-04",
        "version": 1,
    }
