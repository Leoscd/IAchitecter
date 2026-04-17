"""Tests para decoradores de guardrails: @with_timeout, @with_validation, @with_logging."""
import asyncio

import pytest

from app.core.errors import TimeoutError, ValidationError
from app.core.guardrails import with_logging, with_timeout, with_validation


# ── @with_timeout ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_with_timeout_raises_on_slow_function():
    @with_timeout(seconds=1)
    async def slow_fn():
        await asyncio.sleep(5)

    with pytest.raises(TimeoutError):
        await slow_fn()


@pytest.mark.asyncio
async def test_with_timeout_passes_on_fast_function():
    @with_timeout(seconds=5)
    async def fast_fn():
        return {"ok": True}

    result = await fast_fn()
    assert result == {"ok": True}


# ── @with_validation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_with_validation_passes_with_valid_input():
    from pydantic import BaseModel

    class InputModel(BaseModel):
        value: int

    @with_validation(input_model=InputModel)
    async def fn(value: int):
        return {"result": value * 2}

    result = await fn(value=5)
    assert result["result"] == 10


@pytest.mark.asyncio
async def test_with_validation_rejects_invalid_input():
    from pydantic import BaseModel

    class InputModel(BaseModel):
        value: int

    @with_validation(input_model=InputModel)
    async def fn(value: int):
        return {"result": value}

    with pytest.raises(ValidationError):
        await fn(value="no_es_entero")  # type: ignore


# ── @with_logging ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_with_logging_does_not_suppress_exceptions(monkeypatch):
    # Mockear log_execution y log_error para no depender de Supabase
    monkeypatch.setattr("app.core.guardrails.log_execution", lambda **kw: None)
    monkeypatch.setattr("app.core.guardrails.log_error", lambda **kw: None)

    @with_logging
    async def failing_fn():
        raise ValueError("error esperado")

    with pytest.raises(ValueError, match="error esperado"):
        await failing_fn()


@pytest.mark.asyncio
async def test_with_logging_returns_result_on_success(monkeypatch):
    monkeypatch.setattr("app.core.guardrails.log_execution", lambda **kw: None)
    monkeypatch.setattr("app.core.guardrails.log_error", lambda **kw: None)

    @with_logging
    async def ok_fn():
        return {"status": "ok"}

    result = await ok_fn()
    assert result == {"status": "ok"}
