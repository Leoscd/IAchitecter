from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.logs import router as logs_router
from app.api.upload import router as upload_router
from app.config import settings

app = FastAPI(
    title="IAchitecter API",
    description="API de presupuestos de obra con orquestación MiniMax",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "IAchitecter API", "docs": "/docs"}
