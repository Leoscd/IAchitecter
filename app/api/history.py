"""
GET  /api/v1/history                    — lista conversaciones del usuario
POST /api/v1/history                    — crea nueva conversación
GET  /api/v1/history/{conversation_id}  — mensajes de una conversación
POST /api/v1/history/{conversation_id}/messages — agrega mensaje
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.db.supabase_client import get_client
from app.core.auth import get_current_user

router = APIRouter()


class NewConversation(BaseModel):
    project_id: str
    title: str | None = None


class NewMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[str] | None = None


@router.get("/history")
async def list_conversations(user: dict = Depends(get_current_user)) -> dict:
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    try:
        resp = (client.table("conversations")
                .select("id, project_id, title, created_at, updated_at")
                .eq("user_id", user["user_id"])
                .order("updated_at", desc=True)
                .limit(50)
                .execute())
        return {"conversations": resp.data, "count": len(resp.data)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/history", status_code=201)
async def create_conversation(body: NewConversation, user: dict = Depends(get_current_user)) -> dict:
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    try:
        resp = (client.table("conversations")
                .insert({"user_id": user["user_id"], "project_id": body.project_id, "title": body.title})
                .execute())
        return resp.data[0]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/history/{conversation_id}")
async def get_messages(conversation_id: str, user: dict = Depends(get_current_user)) -> dict:
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    try:
        conv = (client.table("conversations")
                .select("id")
                .eq("id", conversation_id)
                .eq("user_id", user["user_id"])
                .execute())
        if not conv.data:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        msgs = (client.table("messages")
                .select("id, role, content, tool_calls, created_at")
                .eq("conversation_id", conversation_id)
                .order("created_at")
                .execute())
        return {"conversation_id": conversation_id, "messages": msgs.data}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/history/{conversation_id}/messages", status_code=201)
async def add_message(conversation_id: str, body: NewMessage,
                      user: dict = Depends(get_current_user)) -> dict:
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")
    try:
        conv = (client.table("conversations")
                .select("id")
                .eq("id", conversation_id)
                .eq("user_id", user["user_id"])
                .execute())
        if not conv.data:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        resp = (client.table("messages")
                .insert({"conversation_id": conversation_id, "role": body.role,
                         "content": body.content, "tool_calls": body.tool_calls})
                .execute())
        return resp.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
