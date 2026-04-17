"""
POST /api/v1/chat — entrada principal del usuario hacia MiniMax.

Flujo:
  1. Validar request
  2. Enviar mensajes a MiniMax
  3. Si MiniMax devuelve tool_calls → tool_dispatcher → resultado → MiniMax de nuevo
  4. Devolver respuesta final al usuario
"""
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.minimax_client import minimax_client
from app.agent.tool_dispatcher import dispatch_all

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_TOOL_ROUNDS = 5  # Límite de rondas de tool-use para evitar loops


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    project_id: str
    messages: list[ChatMessage] = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    tool_calls_executed: list[str] = []
    rounds: int = 0


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    messages: list[dict] = [m.model_dump() for m in request.messages]
    tool_calls_executed: list[str] = []
    rounds = 0

    while rounds < MAX_TOOL_ROUNDS:
        rounds += 1
        try:
            response = await minimax_client.chat(
                messages=messages,
                project_id=request.project_id,
            )
        except Exception as exc:
            logger.error("Error llamando MiniMax: %s", exc)
            raise HTTPException(status_code=502, detail=f"Error en MiniMax: {exc}")

        tool_calls = minimax_client.parse_tool_calls(response)

        if not tool_calls:
            # Respuesta final de texto — terminar loop
            return ChatResponse(
                reply=minimax_client.parse_text(response),
                tool_calls_executed=tool_calls_executed,
                rounds=rounds,
            )

        # Ejecutar tool_calls y agregar resultados al historial
        tool_results = await dispatch_all(tool_calls)
        tool_calls_executed.extend(tc["function"]["name"] for tc in tool_calls)

        # Agregar al historial: mensaje del asistente con tool_calls + resultados
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        }
        messages.append(assistant_msg)
        messages.extend(tool_results)

    # Si llegamos aquí, se agotaron los rounds
    logger.warning("Se agotaron %d rounds de tool-use para project_id=%s", MAX_TOOL_ROUNDS, request.project_id)
    raise HTTPException(
        status_code=422,
        detail=f"Se agotaron los {MAX_TOOL_ROUNDS} rounds de tool-use sin respuesta final.",
    )
