# Plan de ejecución — App conversacional arquitectura con MiniMax + guardrails

## Contexto

Leo quiere construir una app donde un usuario sube planos/áreas/precios por chat y un agente LLM (MiniMax 2.7, para el que ya tiene tokens) orquesta funciones Python para generar presupuestos, cronogramas y PDFs. La idea central: **el agente no razona lógica de negocio — solo rutea llamadas a funciones whitelistadas con guardrails estrictos**. Esto minimiza alucinaciones, hace todo auditable y permite iterar sin romper la app.

Leo ya tiene:
- VPS HostGator (plan básico — limitado en CPU/RAM, probablemente sin Docker root)
- Cuenta Supabase (free tier — 500MB DB, 1GB Storage, pausa tras 7 días inactivo)
- Tokens de MiniMax 2.7
- Repositorio GitHub vacío (destino del código)
- OpenClaw como sandbox de desarrollo (no UI de usuario final)

Problema que resuelve: unificar en una sola app las tareas que Leo hoy hace con skills separados (presupuesto-constructor, reportes-obra-semanales, arch-prompt-enhancer, etc.), con trazabilidad y control.

---

## Decisiones arquitectónicas clave

### 1. Stack tecnológico confirmado

| Capa | Tecnología | Razón |
|------|------------|-------|
| LLM orquestador | **MiniMax 2.7** (API) | Tokens ya pagos; buena capacidad tool-use |
| Backend | **FastAPI** (Python 3.11) | Async nativo, validación Pydantic, OpenAPI auto |
| Validación | **Pydantic v2** + **jsonschema** | Schemas fuertes en entrada/salida de cada función |
| DB + Storage + Auth | **Supabase** (free tier) | PostgreSQL + buckets + RLS + auth JWT en un solo servicio |
| Logging DB | Tablas Supabase (`execution_logs`, `error_logs`, `audit_trail`) | Auditoría queryable vía SQL |
| Rate limiting | **slowapi** (Redis opcional) | Decorador simple sobre endpoints FastAPI |
| Timeouts | `asyncio.wait_for` | Nativo Python, sin deps externas |
| PDF generation | **ReportLab** o **WeasyPrint** | WeasyPrint si Leo quiere HTML→PDF (más flexible) |
| Excel/CSV | **openpyxl** + **pandas** | Ya usa en skills actuales |
| Process isolation | **subprocess con timeout** (no Docker) | VPS básico probablemente no permite Docker |
| Deploy | **systemd** + **nginx reverse proxy** | Standard para VPS básico sin Docker |
| UI de usuario final | **Chat web en Next.js 14** (App Router + Tailwind + shadcn/ui) | Confirmado por Leo — se construye en Fase 4 sobre la API FastAPI |

### 2. Decisión crítica: OpenClaw es dev, no prod

OpenClaw servirá como entorno donde Claude + Leo escriben y testean las funciones antes de deployarlas al VPS. **No es la UI de usuario final**. Esto implica:

- Fase 1–3: se desarrolla y valida en OpenClaw → se hace `git push` al repo → se deploya al VPS.
- Fase 4: UI pública en Next.js 14 deployada en Vercel.

### 3. Constraints del VPS HostGator básico

- **Sin Docker** asumido → aislamiento vía `subprocess` + `resource.setrlimit` (Linux) en lugar de contenedores.
- **RAM limitada** → evitar cargar modelos localmente; todo LLM vía API.
- **Un solo proceso FastAPI con workers Uvicorn limitados** (probablemente 2 workers).
- **Backups de Supabase a Storage** (no confiar en free tier para persistencia crítica).

---

## Arquitectura del repo

```
/app
├── main.py                    # FastAPI entrypoint
├── config.py                  # Settings (pydantic-settings, vars de .env)
├── core/
│   ├── guardrails.py          # Decoradores: @with_timeout, @with_validation, @with_logging
│   ├── validator.py           # validate_input(data, schema)
│   ├── logger.py              # log_execution, log_error, log_audit
│   ├── sandbox.py             # safe_execute() con resource limits
│   └── errors.py              # Jerarquía de excepciones (ValidationError, TimeoutError, etc.)
├── functions/                 # Las 6 funciones whitelistadas
│   ├── extract_areas.py
│   ├── match_materials.py
│   ├── generate_budget.py
│   ├── generate_schedule.py
│   ├── adjust_budget.py
│   └── export_pdf.py
├── schemas/                   # JSON schemas de entrada/salida por función
│   ├── budget.json
│   ├── schedule.json
│   └── ...
├── agent/
│   ├── minimax_client.py      # Wrapper del SDK MiniMax
│   ├── system_prompt.py       # Prompt con guardrails + whitelist de tools
│   └── tool_dispatcher.py     # Recibe tool_call de MiniMax → valida → ejecuta
├── api/
│   ├── chat.py                # POST /api/chat (entrada usuario → MiniMax → respuesta)
│   ├── upload.py              # POST /api/upload (drag-drop archivos con validación)
│   ├── logs.py                # GET /api/logs/{project_id}
│   ├── health.py              # GET /api/health
│   └── replay.py              # POST /api/replay/{execution_id}
├── db/
│   ├── supabase_client.py
│   └── migrations/            # SQL para crear tablas
├── tests/
│   ├── test_guardrails.py
│   ├── test_functions/
│   └── fixtures/
└── pyproject.toml
```

---

## Esquema de base de datos (Supabase)

```sql
-- Proyectos
create table projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  name text not null,
  created_at timestamptz default now()
);

-- Log de cada ejecución de función
create table execution_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  project_id uuid references projects,
  function_name text not null,
  parameters jsonb,
  result jsonb,
  status text check (status in ('success','error','timeout')) not null,
  error_msg text,
  start_time timestamptz default now(),
  duration_ms int
);

-- Errores con detalle (foreign key a execution_logs)
create table error_logs (
  id uuid primary key default gen_random_uuid(),
  execution_id uuid references execution_logs,
  error_type text check (error_type in ('validation','timeout','logic','system')),
  stack_trace text,
  recovered boolean default false,
  created_at timestamptz default now()
);

-- Auditoría de acciones de usuario
create table audit_trail (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null,
  project_id uuid references projects,
  action text not null, -- 'upload'|'generate'|'adjust'|'export'
  object_type text,
  object_id uuid,
  old_value jsonb,
  new_value jsonb,
  ip_address inet,
  user_agent text,
  created_at timestamptz default now()
);

-- RLS: cada usuario solo ve sus proyectos
alter table projects enable row level security;
create policy "own projects" on projects for all using (auth.uid() = user_id);
-- (repetir para las demás tablas con join a projects)
```

---

## Contrato agente ↔ backend

### System prompt MiniMax (esqueleto)

```
Eres un asistente que orquesta funciones Python para gestión de obras.
SOLO puedes llamar a estas 6 funciones: extract_areas, match_materials,
generate_budget, generate_schedule, adjust_budget, export_pdf.

No razones sobre fórmulas ni precios — la lógica vive en el backend.
Si el usuario pide algo fuera de estas funciones, respondé que no está soportado.
Cada tool_call debe respetar el JSON schema definido.
Si una función falla, explicale al usuario el error tal cual lo recibiste,
sin inventar recuperaciones.
```

### Flujo de una request

1. Usuario envía mensaje + archivos a `POST /api/chat`
2. Backend valida archivos (MIME, tamaño, schema JSON si aplica) → guarda en Supabase Storage
3. Backend envía a MiniMax: mensaje + lista de tools disponibles + `user_id` en contexto
4. MiniMax devuelve `tool_call` → `tool_dispatcher.py`:
   - Valida nombre contra whitelist
   - Valida params contra schema JSON
   - Verifica permisos de `user_id` sobre `project_id`
   - Ejecuta con `@with_timeout(30) @with_logging @with_validation`
5. Resultado vuelve a MiniMax → respuesta final al usuario
6. Cada paso escribe fila en `execution_logs`

---

## Roadmap ajustado (2h/día)

### Fase 1 — Fundaciones (Días 1–3)
- Inicializar repo GitHub + estructura de carpetas
- Setup FastAPI + Supabase client + .env
- Migraciones SQL (3 tablas + RLS)
- Decoradores core: `@with_timeout`, `@with_validation`, `@with_logging`
- Endpoint `/api/health`
- **Primera función end-to-end**: `generate_budget` con schema, tests, logging
- Desplegar MVP al VPS con systemd + nginx

### Fase 2 — Integración MiniMax (Días 4–6)
- Wrapper `minimax_client.py` + system prompt
- `tool_dispatcher.py` con whitelist
- Endpoint `/api/chat` (sin UI, testeable con curl/Postman)
- Rate limiting con slowapi
- Agregar funciones 2 y 3: `extract_areas`, `match_materials`

### Fase 3 — Funciones restantes + auditoría (Días 7–9)
- `generate_schedule`, `adjust_budget`, `export_pdf`
- Endpoints `/api/logs`, `/api/replay`, `/api/errors`
- Alertas: si una función falla 3× en 1h → email admin
- Tests de integración end-to-end

### Fase 4 — Chat web en Next.js (Días 10–14)
- Next.js 14 (App Router) + Tailwind + shadcn/ui
- Auth vía Supabase Auth (magic link o email/password)
- Componentes: `ChatWindow`, `MessageList`, `FileDropZone`, `BudgetTable`, `GanttViewer`
- Streaming de respuestas del backend (SSE desde FastAPI)
- Drag-drop con validación cliente (tipos, tamaños) antes de subir
- Deploy frontend: **Vercel free tier** (separado del VPS)
- El VPS queda solo para FastAPI + jobs nocturnos

### Fase 5 — Features avanzadas (después)
- Multi-RAG sobre proyectos históricos (pgvector en Supabase)
- Workflow de aprobaciones (>$100k requiere admin)
- Export batch (múltiples proyectos a la vez)

---

## Funciones reutilizables de tus skills actuales

Varios skills que ya usás tienen lógica directamente aprovechable — **no reescribir, importar**:

- `anthropic-skills:presupuesto-constructor` → base para `generate_budget` y `match_materials`
- `anthropic-skills:reportes-obra-semanales` → base para `export_pdf` (HTML→PDF)
- `anthropic-skills:presupuesto-sanitario` → scraping de precios reutilizable en `match_materials`
- `anthropic-skills:xlsx` → helpers para leer CSV/XLSX en `extract_areas`
- `anthropic-skills:pdf` → parsing PDF para `extract_areas`

**Acción concreta Fase 1**: revisar cada skill, extraer las funciones puras a módulos en `/app/functions/` y envolver con decoradores de guardrails.

---

## Verificación end-to-end

Al terminar Fase 3, debe pasar este test manual:

```bash
# 1. Health check
curl https://tuvps.com/api/health
# → {"status":"ok","db":"ok","functions":{"generate_budget":"ok",...}}

# 2. Upload archivo
curl -X POST https://tuvps.com/api/upload \
  -H "Authorization: Bearer $JWT" \
  -F "file=@plano.pdf" -F "project_id=..."

# 3. Chat con MiniMax
curl -X POST https://tuvps.com/api/chat \
  -H "Authorization: Bearer $JWT" \
  -d '{"message":"armá presupuesto del proyecto X","project_id":"..."}'
# → respuesta estructurada con tool_calls ejecutados

# 4. Auditoría
# En Supabase SQL editor:
select function_name, status, duration_ms
from execution_logs
where project_id = '...'
order by start_time desc;
# → lista cronológica de todas las funciones ejecutadas
```

Tests automatizados a correr en CI (GitHub Actions):
- `pytest tests/test_guardrails.py` → valida timeouts, rechazos por schema
- `pytest tests/test_functions/` → cada función con fixtures de entrada válida/inválida
- Test de integración con mock de MiniMax → valida flujo completo sin gastar tokens

---

## Puntos abiertos para confirmar antes de empezar

1. **Plan de backup Supabase**: free tier pausa tras 7 días sin actividad — agendar cron de keep-alive + export semanal de tablas a Storage.
2. **Dominio + SSL para API**: ¿HostGator te da subdominio con SSL gratis o hay que configurar Let's Encrypt manual con certbot?
3. **Monto tokens MiniMax**: ¿cuántos tokens mensuales tenés? Define si agregamos cache agresivo de respuestas en Fase 2.
4. **CORS**: el frontend Next.js en Vercel deberá estar en la whitelist CORS del FastAPI en VPS — configurar en Fase 2.

---

## Archivos críticos a crear (Fase 1)

- `app/main.py` — FastAPI app
- `app/config.py` — settings con Pydantic
- `app/core/guardrails.py` — los 3 decoradores base
- `app/core/logger.py` — interfaz a `execution_logs` y `error_logs`
- `app/db/migrations/001_init.sql` — las 4 tablas + RLS
- `app/functions/generate_budget.py` — primera función completa
- `app/schemas/budget.json` — JSON schema de entrada/salida
- `app/tests/test_generate_budget.py` — fixtures + casos edge
- `pyproject.toml` + `.env.example`
- `deploy/systemd.service` + `deploy/nginx.conf`
