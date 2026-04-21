"""Tests para endpoints de logs y errors usando TestClient (sin Supabase real)."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _mock_client_logs(data):
    """Helper: mockea get_client().table().select()...execute() → data."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value \
        .eq.return_value.order.return_value \
        .limit.return_value.execute.return_value.data = data
    return mock_client


def test_get_logs_returns_200_with_mocked_db():
    with patch("app.api.logs.get_client", return_value=_mock_client_logs([
        {"id": "abc", "function_name": "extract_areas", "status": "success",
         "duration_ms": 120, "error_msg": None, "start_time": "2026-04-20T10:00:00"}
    ])):
        resp = client.get("/api/v1/logs/11111111-1111-1111-1111-111111111111")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_get_logs_returns_503_when_no_client():
    with patch("app.api.logs.get_client", return_value=None):
        resp = client.get("/api/v1/logs/11111111-1111-1111-1111-111111111111")
    assert resp.status_code == 503


def test_get_errors_returns_200_with_mocked_db():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value \
        .order.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.logs.get_client", return_value=mock_client):
        resp = client.get("/api/v1/errors")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_get_errors_returns_503_when_no_client():
    with patch("app.api.logs.get_client", return_value=None):
        resp = client.get("/api/v1/errors")
    assert resp.status_code == 503


def test_get_logs_returns_500_on_db_exception():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value \
        .eq.return_value.order.return_value \
        .limit.return_value.execute.side_effect = Exception("DB error")
    with patch("app.api.logs.get_client", return_value=mock_client):
        resp = client.get("/api/v1/logs/11111111-1111-1111-1111-111111111111")
    assert resp.status_code == 500
    assert "DB error" in resp.json()["detail"]


def test_get_errors_with_since_parameter():
    since_value = "2026-01-01T00:00:00"
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value \
        .order.return_value.limit.return_value \
        .gte.return_value.execute.return_value.data = []
    with patch("app.api.logs.get_client", return_value=mock_client):
        resp = client.get(f"/api/v1/errors?since={since_value}")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0