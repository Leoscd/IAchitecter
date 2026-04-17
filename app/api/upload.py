"""
POST /api/v1/upload — subida de archivos (planos, planillas, PDFs).
Implementación completa en Fase 3.
"""
from fastapi import APIRouter, HTTPException, UploadFile

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "image/jpeg",
    "image/png",
}
MAX_FILE_SIZE_MB = 20


@router.post("/upload")
async def upload_file(file: UploadFile, project_id: str) -> dict:
    """
    Valida y sube archivo a Supabase Storage.
    TODO: Implementar almacenamiento en Fase 3.
    """
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de archivo no permitido: {file.content_type}. "
                   f"Permitidos: {sorted(ALLOWED_MIME_TYPES)}",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"Archivo demasiado grande: {size_mb:.1f}MB. Máximo: {MAX_FILE_SIZE_MB}MB",
        )

    # TODO Fase 3: guardar en Supabase Storage y devolver URL
    raise HTTPException(status_code=501, detail="Upload a Storage — implementar en Fase 3")
