"""
tool_dispatcher — recibe tool_calls de MiniMax, valida y ejecuta funciones core.

Responsabilidades:
1. Verificar que la función está en la whitelist
2. Validar parámetros contra schema JSON
3. Ejecutar con guardrails activos
4. Devolver resultado o error estructurado
"""
import json
import logging
from typing import Any

from app.core.errors import DispatchError, ValidationError
from app.core.validator import validate_input
from app.functions.adjust_budget import adjust_budget
from app.functions.export_pdf import export_pdf
from app.functions.extract_areas import extract_areas
from app.functions.generate_budget import generate_budget
from app.functions.generate_schedule import generate_schedule
from app.functions.match_materials import match_materials

logger = logging.getLogger(__name__)

# Whitelist: nombre → (función, schema_name | None)
# schema_name=None significa que la validación la hace el decorador @with_validation interno
_FUNCTION_REGISTRY: dict[str, tuple] = {
    "extract_areas":     (extract_areas,     None),
    "match_materials":   (match_materials,    None),
    "generate_budget":   (generate_budget,    "budget"),
    "generate_schedule": (generate_schedule,  None),
    "adjust_budget":     (adjust_budget,      None),
    "export_pdf":        (export_pdf,         None),
}


async def dispatch(tool_call: dict) -> dict[str, Any]:
    """
    Procesa un tool_call de MiniMax.

    Args:
        tool_call: dict con keys 'id', 'type', 'function' (name + arguments)

    Returns:
        dict con 'tool_call_id', 'role': 'tool', 'content': resultado JSON

    Raises:
        DispatchError: si la función no está en whitelist
    """
    function_name: str = tool_call["function"]["name"]
    tool_call_id: str = tool_call.get("id", "")

    # 1. Whitelist check
    if function_name not in _FUNCTION_REGISTRY:
        raise DispatchError(
            f"Función '{function_name}' no está en la whitelist. "
            f"Funciones permitidas: {list(_FUNCTION_REGISTRY.keys())}"
        )

    fn, schema_name = _FUNCTION_REGISTRY[function_name]

    # 2. Parsear argumentos
    try:
        raw_args = tool_call["function"].get("arguments", "{}")
        kwargs: dict = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except json.JSONDecodeError as exc:
        raise DispatchError(f"Argumentos JSON inválidos para '{function_name}': {exc}") from exc

    # 3. Validar contra schema JSON si existe
    if schema_name:
        try:
            validate_input(kwargs, schema_name)
        except ValidationError as exc:
            return _error_response(tool_call_id, function_name, str(exc))

    # 4. Ejecutar función con guardrails
    logger.info("Ejecutando %s con args: %s", function_name, list(kwargs.keys()))
    try:
        result = await fn(**kwargs)
        return {
            "tool_call_id": tool_call_id,
            "role": "tool",
            "content": json.dumps(result, ensure_ascii=False, default=str),
        }
    except NotImplementedError as exc:
        return _error_response(tool_call_id, function_name, f"Función no implementada aún: {exc}")
    except Exception as exc:
        logger.error("Error en %s: %s", function_name, exc)
        return _error_response(tool_call_id, function_name, str(exc))


async def dispatch_all(tool_calls: list[dict]) -> list[dict]:
    """Despacha múltiples tool_calls secuencialmente (MiniMax puede enviar varios)."""
    results = []
    for tool_call in tool_calls:
        result = await dispatch(tool_call)
        results.append(result)
    return results


def _error_response(tool_call_id: str, function_name: str, error_msg: str) -> dict:
    return {
        "tool_call_id": tool_call_id,
        "role": "tool",
        "content": json.dumps({
            "error": True,
            "function": function_name,
            "message": error_msg,
        }, ensure_ascii=False),
    }
