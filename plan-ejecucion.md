# Plan de ejecución — App conversacional arquitectura con MiniMax + guardrails

---

## Estado actual — 2026-04-21

### ✅ Fase 1 — Fundaciones (COMPLETA)
### ✅ Fase 2 — Integración MiniMax (COMPLETA)
### ✅ Fase 3 — Funciones restantes + tests (COMPLETA)
### ✅ Fase 3b — Observabilidad (COMPLETA)
### ✅ Fase 4 — Chat web Next.js (COMPLETA)

### Avances completado por Alfred (2026-04-21):

**Fase 3b:**
- `app/api/logs.py`: Implementados endpoints GET /logs/{project_id} y GET /errors
- `app/api/upload.py`: Implementado POST /upload a Supabase Storage
- `app/core/alerts.py`: Sistema de alertas (>= 3 errores en 60min)
- `app/core/logger.py`: Integración con check_error_rate
- Tests: 55/55 passing

**Fase 4:**
- `frontend/` creado con Next.js 16 + TypeScript + Tailwind
- Componentes: ChatInput, MessageList, MessageBubble, StatusBar, BudgetCard
- Hook useChat para estado conversacional
- Página /chat con UI conversacional completa
- Build estático: `npm run build` → out/ (5 páginas)
- TypeScript compila sin errores, lint pasa

**Pendiente Fase 5:**
- Proxy API (requiere servidor Next.js real, no static export)
- Autenticación / login
- Historial persistente en Supabase
- Email para alertas

---

## Criterios de aceptación (Fase 3 - VERIFICADOS)
- ✅ `pytest app/tests/` corre sin errores (52/52 passing)
- ✅ Las 3 funciones tienen modelos Pydantic Input + Output con `ConfigDict(strict=True)`
- ✅ Orden de decoradores correcto en las 3 funciones (`@with_logging` → `@with_validation` → `@with_timeout`)
- ✅ `adjust_budget` no muta el dict `budget` recibido (usa copia profunda)
- ✅ `generate_schedule` solo incluye fases con ítems reales en el presupuesto
- ✅ `export_pdf` genera PDF sin hacer llamadas reales a Supabase en tests
- ✅ Ningún `print()` ni `logger.debug()` extra
- ✅ 11 archivos modificados/creados en esta fase

---

## INSTRUCCIONES FASE 3b — Observabilidad + endpoints pendientes

### Contexto
El backend tiene 52 tests pasando. Hay 3 endpoints con stub `501` y falta el sistema de alertas.
Implementar todo en `app/api/` y `app/core/`. No tocar funciones core ni guardrails.

### Tarea 1 — Implementar `app/api/logs.py` completamente

Reemplazar el stub actual con implementación real. El archivo debe quedar así:

```python
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
```

### Tarea 2 — Implementar `app/api/upload.py` completamente

El esqueleto ya valida MIME type y tamaño. Agregar la subida real a Supabase Storage:

```python
# Después de validar content y size_mb, reemplazar el raise 501 con:
try:
    client = get_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Storage no disponible")
    
    # Ruta en el bucket: project-files/{project_id}/{timestamp}_{filename}
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = file.filename.replace(" ", "_") if file.filename else "upload"
    storage_path = f"{project_id}/{timestamp}_{safe_name}"
    
    client.storage.from_("project-files").upload(
        path=storage_path,
        file=content,
        file_options={"content-type": file.content_type},
    )
    public_url = client.storage.from_("project-files").get_public_url(storage_path)
    
    return {
        "storage_path": storage_path,
        "public_url": public_url,
        "size_mb": round(size_mb, 2),
        "content_type": file.content_type,
        "filename": safe_name,
    }
except HTTPException:
    raise
except Exception as exc:
    raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {exc}")
```

Agregar `from datetime import datetime` al inicio del archivo.
El bucket `project-files` debe existir en Supabase (crearlo desde el dashboard si no existe, con acceso público).

### Tarea 3 — Sistema de alertas `app/core/alerts.py`

Crear el archivo `app/core/alerts.py`:

```python
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
```

Llamar a `check_error_rate` desde `app/core/logger.py` al final de `log_error`:

```python
# Al final de log_error, después del insert:
from app.core.alerts import check_error_rate
import asyncio
asyncio.create_task(check_error_rate(function_name))
```

**Importante:** usar `asyncio.create_task` para que la alerta no bloquee el flujo.

### Tarea 4 — Tests de Fase 3b

Crear `app/tests/test_api/` con `__init__.py` y `test_logs_endpoint.py`:

```python
"""Tests para endpoints de logs y errors usando TestClient (sin Supabase real)."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _mock_client_logs(data):
    """Helper: mockea get_client().table().select()...execute() → data."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value \
        .eq.return_value.order.return_value \
        .limit.return_value.execute.return_value.data = data
    return mock_client


def test_get_logs_returns_200_with_mocked_db():
    with patch("app.api.logs.get_client", return_value=_mock_client_logs([
        {"id": "abc", "function_name": "extract_areas", "status": "success",
         "duration_ms": 120, "error_msg": None, "start_time": "2026-04-20T10:00:00"}
    ])):
        resp = client.get("/api/v1/logs/11111111-1111-1111-1111-111111111111")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_get_logs_returns_503_when_no_client():
    with patch("app.api.logs.get_client", return_value=None):
        resp = client.get("/api/v1/logs/11111111-1111-1111-1111-111111111111")
    assert resp.status_code == 503


def test_get_errors_returns_200_with_mocked_db():
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value \
        .order.return_value.limit.return_value.execute.return_value.data = []
    with patch("app.api.logs.get_client", return_value=mock_client):
        resp = client.get("/api/v1/errors")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
```

### Criterios de aceptación Fase 3b
- [x] `pytest app/tests/` sigue pasando (58/58 passing tras correcciones de revisión)
- [x] `GET /api/v1/logs/{project_id}` devuelve 200 con datos mockeados, 503 sin cliente
- [x] `GET /api/v1/errors` acepta parámetros `limit` y `since`
- [x] `POST /api/v1/upload` sube a Supabase Storage y devuelve `storage_path` + `public_url`
- [x] `app/core/alerts.py` creado y llamado desde `log_error`
- [x] Ningún `print()` ni comentarios TODO sin resolver (TODO en alerts.py es parte del log, intencional Fase 5)

---

## INSTRUCCIONES FASE 4 — Frontend Next.js

### Contexto
El backend corre en `http://localhost:8000`. El endpoint principal es `POST /api/v1/chat`.
El frontend es una SPA conversacional: el usuario describe su proyecto en lenguaje natural,
el agente MiniMax llama a las funciones core y responde con presupuesto/cronograma.

### Setup inicial

```bash
cd /ruta/al/proyecto
npx create-next-app@latest frontend --typescript --tailwind --app --eslint --no-src-dir
cd frontend
npm install
```

### Estructura de directorios a crear

```
frontend/
├── app/
│   ├── layout.tsx          # layout raíz con fuentes y metadata
│   ├── page.tsx            # página principal → redirige a /chat
│   └── chat/
│       └── page.tsx        # página de chat (ruta principal)
├── components/
│   ├── ChatInput.tsx       # textarea + botón enviar
│   ├── MessageList.tsx     # lista de mensajes con scroll automático
│   ├── MessageBubble.tsx   # burbuja individual user/assistant
│   ├── BudgetCard.tsx      # muestra presupuesto parseado del reply
│   └── StatusBar.tsx       # muestra "Ejecutando extract_areas..." durante tool calls
├── lib/
│   ├── api.ts              # cliente fetch hacia el backend
│   └── types.ts            # tipos TypeScript que espeja los modelos Pydantic
├── hooks/
│   └── useChat.ts          # hook principal: estado + llamada al API
└── next.config.ts          # proxy /api/* → http://localhost:8000
```

### `lib/types.ts` — copiar exactamente

```typescript
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  project_id: string;
  messages: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  tool_calls_executed: string[];
  rounds: number;
}

export type MessageWithMeta = ChatMessage & {
  id: string;           // nanoid para key React
  timestamp: Date;
  toolCalls?: string[]; // funciones ejecutadas en ese turno
  isLoading?: boolean;
};
```

### `lib/api.ts` — copiar exactamente

```typescript
import { ChatRequest, ChatResponse } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Error del servidor");
  }
  return res.json();
}
```

### `hooks/useChat.ts` — implementar con esta firma

```typescript
import { useState, useCallback } from "react";
import { nanoid } from "nanoid";   // npm install nanoid
import { sendMessage } from "@/lib/api";
import { MessageWithMeta, ChatMessage } from "@/lib/types";

const PROJECT_ID = "demo-project-001"; // hardcoded en Fase 4, auth en Fase 5

export function useChat() {
  const [messages, setMessages] = useState<MessageWithMeta[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;
    setError(null);

    const userMsg: MessageWithMeta = {
      id: nanoid(), role: "user", content: text, timestamp: new Date(),
    };
    const loadingMsg: MessageWithMeta = {
      id: nanoid(), role: "assistant", content: "", timestamp: new Date(), isLoading: true,
    };

    setMessages(prev => [...prev, userMsg, loadingMsg]);
    setIsLoading(true);

    // Construir historial para el API (sin mensajes de loading)
    const history: ChatMessage[] = [...messages, userMsg].map(
      ({ role, content }) => ({ role, content })
    );

    try {
      const response = await sendMessage({ project_id: PROJECT_ID, messages: history });
      setMessages(prev => prev.map(m =>
        m.isLoading
          ? { ...m, content: response.reply, isLoading: false, toolCalls: response.tool_calls_executed }
          : m
      ));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error desconocido";
      setError(msg);
      setMessages(prev => prev.filter(m => !m.isLoading));
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading]);

  return { messages, isLoading, error, send };
}
```

### `next.config.ts` — proxy al backend

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

### Componentes — qué debe hacer cada uno

**`ChatInput.tsx`**
- `<textarea>` con placeholder "Describí tu proyecto de obra..."
- Envío con Enter (sin Shift) o botón
- Deshabilitado mientras `isLoading === true`
- Auto-resize vertical (max 5 líneas)

**`MessageBubble.tsx`**
- Props: `message: MessageWithMeta`
- Burbuja user: alineada derecha, fondo azul
- Burbuja assistant: alineada izquierda, fondo gris
- Si `isLoading`: mostrar spinner animado (3 puntos pulsantes con Tailwind `animate-bounce`)
- Si `toolCalls.length > 0`: mostrar badge pequeño con las funciones ejecutadas, ej: `⚙ extract_areas → match_materials`

**`MessageList.tsx`**
- Lista de `MessageBubble`
- `useEffect` con `scrollIntoView` para auto-scroll al último mensaje
- Si no hay mensajes: pantalla de bienvenida con texto "Contame tu proyecto de obra para empezar"

**`BudgetCard.tsx`**
- Recibe el `reply` (string) del asistente
- Si el texto contiene números con formato `$X.XXX.XXX` o menciona "presupuesto total", renderizar
  un bloque destacado con fondo verde claro y el monto resaltado
- Si no, no renderizar nada (el componente es opcional/contextual)

**`StatusBar.tsx`**
- Solo visible mientras `isLoading === true`
- Mostrar qué funciones se están ejecutando: "Analizando proyecto... ⚙"
- Usar `isLoading` del hook

**`app/chat/page.tsx`**
```typescript
"use client";
import { useChat } from "@/hooks/useChat";
import { MessageList } from "@/components/MessageList";
import { ChatInput } from "@/components/ChatInput";
import { StatusBar } from "@/components/StatusBar";

export default function ChatPage() {
  const { messages, isLoading, error, send } = useChat();

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 shadow-sm">
        <h1 className="text-xl font-semibold text-gray-800">IAchitecter</h1>
        <p className="text-sm text-gray-500">Presupuestador de obra con IA</p>
      </header>

      <main className="flex-1 overflow-hidden flex flex-col max-w-3xl mx-auto w-full px-4 py-4 gap-4">
        <MessageList messages={messages} />
        <StatusBar isLoading={isLoading} />
        {error && (
          <div className="text-red-600 text-sm bg-red-50 rounded px-3 py-2">{error}</div>
        )}
        <ChatInput onSend={send} disabled={isLoading} />
      </main>
    </div>
  );
}
```

### Dependencias a instalar

```bash
npm install nanoid
npm install --save-dev @types/node
```

### `.env.local` a crear en `frontend/`

```
NEXT_PUBLIC_API_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
```

### Criterios de aceptación Fase 4
- [x] Scaffolding Next.js 15 + TypeScript + Tailwind v3 correcto (revisado y corregido 2026-04-21)
- [x] `output: "export"` eliminado — rewrites al backend FastAPI funcionan
- [x] `tailwind.config.js` incluye `./components/**` en content
- [x] Componentes ChatInput, MessageList, MessageBubble, StatusBar, BudgetCard implementados
- [x] Hook `useChat.ts` con optimistic UI y manejo de errores
- [x] `AGENTS.md` con instrucciones concretas para subagente frontend
- [ ] `cd frontend && npm install && npm run dev` arranca sin errores en `http://localhost:3000` (verificar manual)
- [ ] `npm run build` compila sin errores TypeScript (verificar tras npm install)
- [ ] La página `/chat` carga y muestra pantalla de bienvenida (verificar manual)
- [ ] Escribir un mensaje llama a `POST /api/v1/chat` (verificar en Network tab)

### Lo que NO implementar en Fase 4 (queda para Fase 5)
- Autenticación / login
- Historial persistente de conversaciones en Supabase
- Múltiples proyectos / sidebar
- Dark mode
- PWA / mobile optimization

---

---

## INSTRUCCIONES FASE 5 — Auth + Historial + Email alertas

### Contexto
Backend FastAPI con 58 tests. Frontend Next.js 15 scaffoldeado. Supabase como DB/Auth.
Esta fase cierra las deudas técnicas conocidas: auth en endpoints, historial persistente de chat, y envío real de emails de alerta.

### Tarea 1 — Migración Supabase: tablas `conversations` + `messages`

Crear `supabase/migrations/003_conversations.sql`:

```sql
-- Tabla de conversaciones (una por sesión de chat)
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id  TEXT NOT NULL,
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tabla de mensajes
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    tool_calls      TEXT[],
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);

-- RLS
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_conversations" ON conversations
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "users_own_messages" ON messages
    FOR ALL USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE user_id = auth.uid()
        )
    );

-- Trigger updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

### Tarea 2 — Middleware de auth JWT en FastAPI

Crear `app/core/auth.py`:

```python
"""Validación de JWT de Supabase para endpoints protegidos."""
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
import os

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]


def get_current_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"],
                             audience="authenticated")
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
```

Agregar `python-jose[cryptography]` a requirements.txt.

Proteger los endpoints sensibles con `user: dict = Depends(get_current_user)`:
- `POST /api/v1/chat` — agregar `user` como parámetro
- `POST /api/v1/upload` — ídem
- `GET /api/v1/errors` — ídem (era "admin only")

### Tarea 3 — Endpoints de historial `app/api/history.py`

Crear `app/api/history.py`:

```python
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
```

Registrar el router en `app/main.py`:
```python
from app.api import history
app.include_router(history.router, prefix="/api/v1")
```

### Tarea 4 — Email real en `app/core/alerts.py`

Instalar `resend` (simple, sin dependencias pesadas): `pip install resend`
Agregar `RESEND_API_KEY` y `ALERT_EMAIL_TO` a `.env`.

Reemplazar el `logger.critical` en `alerts.py` con envío real + fallback a log:

```python
import os, resend

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
```

Llamar `await _send_alert_email(function_name, count)` dentro del bloque `if count >= ERROR_THRESHOLD`, envuelto en su propio try/except.

### Tarea 5 — Frontend: auth + historial

**Login page `frontend/app/login/page.tsx`:**
- Usar `@supabase/ssr` para auth en Next.js App Router
- Instalar: `npm install @supabase/supabase-js @supabase/ssr`
- Form email + password → `supabase.auth.signInWithPassword()`
- Redirect a `/chat` si ya hay sesión

**`frontend/lib/supabase.ts`:**
```typescript
import { createBrowserClient } from "@supabase/ssr";
export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

**`frontend/hooks/useChat.ts` — actualizar:**
- Obtener token de `supabase.auth.getSession()` antes de cada fetch
- Pasar `Authorization: Bearer <token>` en headers de `sendMessage`
- Crear conversación al enviar el primer mensaje, guardar mensajes en Supabase

**`.env.local` — agregar:**
```
NEXT_PUBLIC_SUPABASE_URL=<url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
```

### Criterios de aceptación Fase 5
- [ ] `supabase/migrations/003_conversations.sql` corre sin errores
- [ ] `GET /api/v1/history` devuelve 401 sin token, 200 con token válido
- [ ] `POST /api/v1/history` crea conversación asociada al user_id del JWT
- [ ] `GET /api/v1/errors` devuelve 401 sin token
- [ ] Alerta de email se envía cuando errores >= 3 (verificar con RESEND_API_KEY seteado)
- [ ] `python-jose` y `resend` en requirements.txt
- [ ] Frontend: `/login` muestra form, login exitoso redirige a `/chat`
- [ ] Frontend: historial de chat persiste tras recargar la página
- [ ] `pytest app/tests/` sigue pasando (58+ tests, sin regresiones)

*Última actualización: 2026-04-21 por Leo*