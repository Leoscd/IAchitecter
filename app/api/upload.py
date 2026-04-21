"""
POST /api/v1/upload — subida de archivos (planos, planillas, PDFs).
"""
from datetime import datetime
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
    """Valida y sube archivo a Supabase Storage."""
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

    try:
        from app.db.supabase_client import get_client
        client = get_client()
        if client is None:
            raise HTTPException(status_code=503, detail="Storage no disponible")

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