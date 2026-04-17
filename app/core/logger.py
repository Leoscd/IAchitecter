from typing import Any

from app.db.supabase_client import get_client


async def log_execution(
    function_name: str,
    status: str,
    duration_ms: int,
    error_msg: str | None = None,
    project_id: str | None = None,
) -> None:
    try:
        client = get_client()
        client.table("execution_logs").insert({
            "function_name": function_name,
            "status": status,
            "duration_ms": duration_ms,
            "error_msg": error_msg,
            "project_id": project_id,
        }).execute()
    except Exception:
        # No propagar errores de logging — nunca romper la función por un log fallido
        pass


async def log_error(
    function_name: str,
    error_type: str,
    error_message: str,
    stack_trace: str | None = None,
) -> None:
    try:
        client = get_client()
        client.table("error_logs").insert({
            "function_name": function_name,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
        }).execute()
    except Exception:
        pass


async def log_audit(
    user_id: str,
    action: str,
    project_id: str | None = None,
    object_type: str | None = None,
    old_value: Any = None,
    new_value: Any = None,
) -> None:
    try:
        client = get_client()
        client.table("audit_trail").insert({
            "user_id": user_id,
            "action": action,
            "project_id": project_id,
            "object_type": object_type,
            "old_value": old_value,
            "new_value": new_value,
        }).execute()
    except Exception:
        pass
