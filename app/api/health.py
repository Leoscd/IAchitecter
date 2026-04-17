from fastapi import APIRouter
from pydantic import BaseModel

from app.db.supabase_client import get_client

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    db: str
    functions: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    db_status = "ok"
    try:
        client = get_client()
        client.table("execution_logs").select("id").limit(1).execute()
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="ok",
        db=db_status,
        functions={
            "generate_budget": "ok",
            "extract_areas": "pending",
            "match_materials": "pending",
            "generate_schedule": "pending",
            "adjust_budget": "pending",
            "export_pdf": "pending",
        },
    )
