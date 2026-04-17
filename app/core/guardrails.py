import asyncio
import functools
import time
from typing import Any, Callable

from app.core.errors import TimeoutError, ValidationError
from app.core.logger import log_error, log_execution


def with_logging(func: Callable) -> Callable:
    """Registra cada ejecución en execution_logs. Aplicar como decorador externo."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start = time.monotonic()
        status = "success"
        error_msg = None
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as exc:
            status = "error"
            error_msg = str(exc)
            await log_error(
                function_name=func.__name__,
                error_type=type(exc).__name__,
                error_message=error_msg,
            )
            raise
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            await log_execution(
                function_name=func.__name__,
                status=status,
                duration_ms=duration_ms,
                error_msg=error_msg,
            )
    return wrapper


def with_validation(input_model=None, output_model=None):
    """Valida input y output con modelos Pydantic v2."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if input_model and kwargs:
                try:
                    input_model.model_validate(kwargs)
                except Exception as exc:
                    raise ValidationError(f"Input inválido en {func.__name__}: {exc}") from exc
            result = await func(*args, **kwargs)
            if output_model:
                try:
                    output_model.model_validate(
                        result if isinstance(result, dict) else result.model_dump()
                    )
                except Exception as exc:
                    raise ValidationError(f"Output inválido en {func.__name__}: {exc}") from exc
            return result
        return wrapper
    return decorator


def with_timeout(seconds: int = 30):
    """Cancela la función si supera `seconds` segundos."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"{func.__name__} superó el límite de {seconds}s"
                )
        return wrapper
    return decorator
