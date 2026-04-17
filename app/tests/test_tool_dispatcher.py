"""Tests para tool_dispatcher - validación de whitelist y despacho."""
import json

import pytest

from app.agent.tool_dispatcher import dispatch
from app.core.errors import DispatchError


def _make_tool_call(name: str, args: dict, tool_id: str = "tc_001") -> dict:
    return {
        "id": tool_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(args),
        },
    }


@pytest.mark.asyncio
async def test_dispatch_rejects_function_not_in_whitelist():
    """Función no en whitelist devuelve error response."""
    tool_call = _make_tool_call("delete_database", {"confirm": True})
    
    result = await dispatch(tool_call)
    
    assert result["role"] == "tool"
    content = json.loads(result["content"])
    assert content.get("error") is True


@pytest.mark.asyncio
async def test_dispatch_rejects_invalid_json_arguments():
    tool_call = {
        "id": "tc_002",
        "type": "function",
        "function": {
            "name": "generate_budget",
            "arguments": "{ invalid json (",
        },
    }

    with pytest.raises(DispatchError, match="JSON"):
        await dispatch(tool_call)


@pytest.mark.asyncio
async def test_dispatch_extract_areas_returns_tool_result():
    tool_call = _make_tool_call("extract_areas", {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "project_description": "Casa de 120 m²",
        "project_type": "residencial",
        "total_m2": 120.0,
    })

    result = await dispatch(tool_call)

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "tc_001"
    content = json.loads(result["content"])
    assert "areas" in content


@pytest.mark.asyncio
async def test_dispatch_not_implemented_returns_error_response():
    """forecast_costs no está implementada - debe devolver error response, no exception."""
    tool_call = _make_tool_call("forecast_costs", {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "budget": {},
    })

    result = await dispatch(tool_call)

    assert result["role"] == "tool"
    content = json.loads(result["content"])
    assert content.get("error") is True
