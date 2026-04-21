"""
Sistema de alertas: detecta ráfagas de errores y notifica al admin.
Regla: >= 3 errores en la última hora → log de alerta (email en Fase 5).
"""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

ERROR_THRESHOLD = 3
WINDOW_MINUTES = 60


async def check_error_rate(function_name: str) -> None:
    """
    Consulta error_logs y emite alerta si hay >= ERROR_THRESHOLD errores
    del mismo function_name en los últimos WINDOW_MINUTES minutos.
    Falla silenciosamente — nunca propagar excepciones.
    """
    try:
        from app.db.supabase_client import get_client
        client = get_client()
        if client is None:
            return

        since = (datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)).isoformat()
        response = (
            client.table("error_logs")
            .select("id", count="exact")
            .eq("function_name", function_name)
            .gte("created_at", since)
            .execute()
        )
        count = response.count or 0
        if count >= ERROR_THRESHOLD:
            logger.critical(
                "ALERTA: %d errores en %dmin para función '%s'. "
                "Revisar error_logs. [TODO Fase 5: enviar email admin]",
                count, WINDOW_MINUTES, function_name,
            )
    except Exception:
        pass  # Nunca romper el flujo principal por una alerta