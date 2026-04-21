"""
GET /api/v1/logs/{project_id}  — últimos N execution_logs del proyecto
GET /api/v1/errors             — últimos N error_logs globales (admin)
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.db.supabase_client import get_client

router = APIRouter()


@router.get("/logs/{project_id}")
async def get_logs(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Devuelve execution_logs del proyecto, ordenados por start_time desc."""
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    try:
        response = (
            client.table("execution_logs")
            .select("id, function_name, status, duration_ms, error_msg, start_time")
            .eq("project_id", project_id)
            .order("start_time", desc=True)
            .limit(limit)
            .execute()
        )
        return {"project_id": project_id, "logs": response.data, "count": len(response.data)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/errors")
async def get_errors(
    limit: int = Query(default=50, ge=1, le=200),
    since: str | None = Query(default=None, description="ISO datetime, ej: 2026-04-01T00:00:00"),
) -> dict:
    """Devuelve error_logs recientes. Parámetro `since` filtra por fecha."""
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    try:
        query = (
            client.table("error_logs")
            .select("id, function_name, error_type, error_message, created_at")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if since:
            query = query.gte("created_at", since)
        response = query.execute()
        return {"errors": response.data, "count": len(response.data)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))