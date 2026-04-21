"""
Sistema de alertas: detecta ráfagas de errores y notifica al admin.
Regla: >= 3 errores en la última hora → logger.critical + email via Resend.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

import resend

logger = logging.getLogger(__name__)

ERROR_THRESHOLD = 3
WINDOW_MINUTES = 60


async def _send_alert_email(function_name: str, count: int) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    to_email = os.getenv("ALERT_EMAIL_TO")
    if not api_key or not to_email:
        return
    resend.api_key = api_key
    resend.Emails.send({
        "from": "alertas@iachitecter.app",
        "to": to_email,
        "subject": f"[ALERTA] {count} errores en '{function_name}'",
        "text": f"Se detectaron {count} errores en los últimos 60min para la función '{function_name}'.",
    })


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
                "ALERTA: %d errores en %dmin para función '%s'. Revisar error_logs.",
                count, WINDOW_MINUTES, function_name,
            )
            try:
                await _send_alert_email(function_name, count)
            except Exception:
                pass  # Email falla silenciosamente — el log crítico ya quedó registrado
    except Exception:
        pass  # Nunca romper el flujo principal por una alerta