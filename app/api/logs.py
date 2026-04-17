"""
GET /api/v1/logs/{project_id} — consulta de execution_logs y error_logs.
Implementación completa en Fase 3.
"""
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/logs/{project_id}")
async def get_logs(project_id: str, limit: int = 50) -> dict:
    """
    Devuelve los últimos `limit` registros de execution_logs para el proyecto.
    TODO: Implementar en Fase 3.
    """
    raise HTTPException(status_code=501, detail="Logs endpoint — implementar en Fase 3")
