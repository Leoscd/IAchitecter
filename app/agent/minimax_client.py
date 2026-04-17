"""
Wrapper del SDK HTTP de MiniMax 2.7.
Maneja autenticación, retry con backoff y timeout de 60s.
"""
import asyncio
import json
import logging
from typing import Any

import httpx

from app.agent.system_prompt import CURRENT_PROMPT
from app.config import settings

logger = logging.getLogger(__name__)

MINIMAX_API_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"
MINIMAX_MODEL = "MiniMax-Text-01"
MAX_RETRIES = 2
TIMEOUT_SECONDS = 60

# JSON schemas de las 6 funciones expuestas como tools a MiniMax
TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "extract_areas",
            "description": "Extrae áreas constructivas del proyecto en m² por tipología (losa, mampostería, revoque, etc.)",
            "parameters": {
                "type": "object",
                "required": ["project_id", "project_description", "project_type"],
                "additionalProperties": False,
                "properties": {
                    "project_id": {"type": "string", "description": "UUID del proyecto"},
                    "project_description": {"type": "string", "description": "Descripción textual del proyecto"},
                    "project_type": {"type": "string", "enum": ["residencial", "comercial", "industrial"]},
                    "total_m2": {"type": "number", "minimum": 1, "description": "Superficie total opcional"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "match_materials",
            "description": "Cruza áreas con materiales del catálogo respetando especificaciones y tier de calidad",
            "parameters": {
                "type": "object",
                "required": ["project_id", "areas"],
                "additionalProperties": False,
                "properties": {
                    "project_id": {"type": "string"},
                    "areas": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["type", "quantity", "unit"],
                            "properties": {
                                "type": {"type": "string"},
                                "quantity": {"type": "number", "minimum": 0.01},
                                "unit": {"type": "string", "enum": ["m²", "ml", "m³", "un"]},
                            },
                        },
                    },
                    "quality_tier": {"type": "string", "enum": ["económico", "standard", "premium"], "default": "standard"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_budget",
            "description": "Genera presupuesto detallado de obra con ítems, cantidades y totales por categoría",
            "parameters": {
                "type": "object",
                "required": ["project_id", "areas", "materials", "reference_date"],
                "additionalProperties": False,
                "properties": {
                    "project_id": {"type": "string"},
                    "areas": {"type": "array", "minItems": 1, "items": {"type": "object"}},
                    "materials": {"type": "array", "minItems": 1, "items": {"type": "object"}},
                    "currency": {"type": "string", "enum": ["ARS", "USD"], "default": "ARS"},
                    "reference_date": {
                        "type": "string",
                        "pattern": "^[0-9]{4}-(0[1-9]|1[0-2])$",
                        "description": "Formato YYYY-MM",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_schedule",
            "description": "Genera cronograma de obra por fases (Gantt simplificado) desde el presupuesto",
            "parameters": {
                "type": "object",
                "required": ["project_id", "budget", "start_date"],
                "additionalProperties": False,
                "properties": {
                    "project_id": {"type": "string"},
                    "budget": {"type": "object"},
                    "start_date": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                    "work_days_per_week": {"type": "integer", "minimum": 1, "maximum": 7, "default": 5},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_budget",
            "description": "Aplica ajustes al presupuesto: inflación, descuentos o cambios de material",
            "parameters": {
                "type": "object",
                "required": ["project_id", "budget", "adjustments"],
                "additionalProperties": False,
                "properties": {
                    "project_id": {"type": "string"},
                    "budget": {"type": "object"},
                    "adjustments": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {"type": "string", "enum": ["inflation", "discount", "replace"]},
                                "value": {"type": "number"},
                                "item_code": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                        },
                    },
                    "reason": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_pdf",
            "description": "Genera PDF profesional con presupuesto y cronograma opcionales para presentar al cliente",
            "parameters": {
                "type": "object",
                "required": ["project_id", "budget"],
                "additionalProperties": False,
                "properties": {
                    "project_id": {"type": "string"},
                    "budget": {"type": "object"},
                    "schedule": {"type": "object"},
                    "project_info": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "client": {"type": "string"},
                            "architect": {"type": "string"},
                            "location": {"type": "string"},
                        },
                    },
                    "template": {"type": "string", "enum": ["default", "minimal", "detailed"], "default": "default"},
                },
            },
        },
    },
]


class MinimaxClient:
    def __init__(self):
        self._headers = {
            "Authorization": f"Bearer {settings.minimax_api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[dict],
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Envía mensajes a MiniMax y devuelve la respuesta completa.
        Reintenta hasta MAX_RETRIES veces en errores 5xx con backoff exponencial.
        """
        payload = {
            "model": MINIMAX_MODEL,
            "messages": [{"role": "system", "content": CURRENT_PROMPT}] + messages,
            "tools": TOOLS,
            "tool_choice": "auto",
        }

        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        MINIMAX_API_URL,
                        headers=self._headers,
                        json=payload,
                    )
                if response.status_code == 200:
                    return response.json()
                if response.status_code >= 500:
                    logger.warning(
                        "MiniMax error %s en intento %d/%d",
                        response.status_code, attempt + 1, MAX_RETRIES + 1,
                    )
                    last_exc = Exception(f"MiniMax HTTP {response.status_code}")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2 ** attempt)
                    continue
                # 4xx — no reintentar
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning("MiniMax timeout en intento %d/%d", attempt + 1, MAX_RETRIES + 1)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)

        raise last_exc or Exception("MiniMax no disponible")

    def parse_tool_calls(self, response: dict) -> list[dict] | None:
        """Extrae tool_calls de la respuesta de MiniMax si existen."""
        try:
            choice = response["choices"][0]["message"]
            return choice.get("tool_calls")
        except (KeyError, IndexError):
            return None

    def parse_text(self, response: dict) -> str:
        """Extrae el texto de la respuesta final de MiniMax."""
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return ""


minimax_client = MinimaxClient()
