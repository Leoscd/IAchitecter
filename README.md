# IAchitecter — App de Presupuestos de Obra

API conversacional para arquitectos y constructores (mercado argentino).
Un agente LLM (MiniMax 2.5) orquesta funciones Python para generar presupuestos,
cronogramas y PDFs desde descripciones en lenguaje natural.

## Stack

- **Backend:** FastAPI (Python 3.11) + Pydantic v2
- **IA:** MiniMax 2.5 (tool-use)
- **DB:** Supabase (PostgreSQL + Storage + Auth)
- **Frontend:** Next.js 16 (TypeScript + Tailwind)
- **Deploy:** VPS — systemd + nginx

## Estado actual — 2026-04-21

### ✅ Fases completadas (1-4)

| Fase | Estado |
|---|---|
| Fase 1: Fundaciones | ✅ COMPLETA |
| Fase 2: Integración MiniMax | ✅ COMPLETA |
| Fase 3: Funciones + tests | ✅ COMPLETA |
| Fase 3b: Observabilidad | ✅ COMPLETA |
| Fase 4: Frontend Next.js | ✅ COMPLETA |

**Tests:** 55/55 passing

## Setup local

### 1. Clonar e instalar dependencias

```bash
git clone https://github.com/Leoscd/IAchitecter.git
cd IAchitecter
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Completar `.env` con las credenciales reales:

| Variable | Dónde obtenerla |
|---|---|
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase Dashboard → Project Settings → API → service_role |
| `MINIMAX_API_KEY` | MiniMax Platform → API Keys |
| `MINIMAX_GROUP_ID` | MiniMax Platform → Group ID |
| `SECRET_KEY` | Generar con `python -c "import secrets; print(secrets.token_hex(32))"` |

### 3. Correr los tests

```bash
pytest app/tests/
```

Los tests unitarios **no necesitan credenciales reales** — no hacen llamadas externas.

### 4. Levantar la API

```bash
uvicorn app.main:app --reload
```

### 5. Frontend (opcional)

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible en `http://localhost:3000` (redirige a `/chat`).

## Estructura del proyecto

```
app/
├── functions/       # 6 funciones core
├── agent/           # MiniMax client + tool_dispatcher + system prompt
├── api/             # Endpoints FastAPI
├── core/            # Guardrails + alerts
├── db/              # Supabase client
└── tests/           # Tests unitarios
frontend/           # Next.js 16
```

## Pendiente — Fase 5

- Autenticación / login
- Proxy API (servidor Next.js real)
- Historial persistente
- Email para alertas
- Dark mode
- Deploy a producción

Ver `plan-ejecucion.md` para detalles.