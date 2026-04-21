"""Validación de JWT de Supabase para endpoints protegidos."""
import os

from fastapi import HTTPException, Header
from jose import jwt, JWTError


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    secret = os.getenv("SUPABASE_JWT_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Auth no configurado")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"],
                             audience="authenticated")
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
