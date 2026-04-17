# IAchitecter — App de Presupuestos de Obra

API conversacional para arquitectos y constructores (mercado argentino).
Un agente LLM (MiniMax 2.7) orquesta funciones Python para generar presupuestos,
cronogramas y PDFs desde descripciones en lenguaje natural.

## Stack

- **Backend:** FastAPI (Python 3.11) + Pydantic v2
- **IA:** MiniMax 2.7 (tool-use)
- **DB:** Supabase (PostgreSQL + Storage + Auth)
- **Deploy:** VPS HostGator — systemd + nginx

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
Solo `export_pdf` necesita mockear el cliente Supabase (ver instrucciones en `plan-ejecucion.md`).

### 4. Levantar la API localmente

```bash
uvicorn app.main:app --reload
```

Health check: `curl http://localhost:8000/api/health`

## Estructura del proyecto

```
app/
├── functions/       # 6 funciones core (extract_areas, match_materials, generate_budget,
│                    #   generate_schedule, adjust_budget, export_pdf)
├── agent/           # MiniMax client + tool_dispatcher + system prompt
├── api/             # Endpoints FastAPI (/chat, /upload, /logs, /health)
├── core/            # Guardrails (@with_logging, @with_validation, @with_timeout)
├── db/              # Supabase client + migraciones SQL
└── tests/           # Tests unitarios con pytest-asyncio
```

## Tarea actual — Fase 3

Ver `plan-ejecucion.md` para instrucciones detalladas.

**Resumen:** implementar las 3 funciones stub y sus tests:
- `app/functions/generate_schedule.py`
- `app/functions/adjust_budget.py`
- `app/functions/export_pdf.py`

Referencia de implementación: `app/functions/generate_budget.py`

**Criterio de done:** `pytest app/tests/` pasa en verde completo.
