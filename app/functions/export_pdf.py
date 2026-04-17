"""
export_pdf — genera PDF profesional con presupuesto y cronograma.

Produce un archivo PDF descargable con formato de presentación
para el cliente final (arquitecto → comitente).
Implementación completa en Fase 3.
"""
from typing import Any

from app.core.guardrails import with_logging, with_timeout


@with_logging
@with_timeout(seconds=60)
async def export_pdf(
    project_id: str,
    budget: dict,
    schedule: dict | None = None,
    project_info: dict | None = None,
    template: str = "default",
) -> dict[str, Any]:
    """
    Genera PDF profesional con presupuesto y cronograma opcionales.

    Args:
        project_id: UUID del proyecto
        budget: Output de generate_budget
        schedule: Output de generate_schedule (opcional)
        project_info: Datos del proyecto para portada (nombre, cliente, arquitecto)
        template: Nombre del template de diseño

    Returns:
        {'project_id': str, 'file_url': str, 'storage_path': str, 'pages': int}

    TODO: Implementar en Fase 3
    """
    raise NotImplementedError("export_pdf aún no implementada — Fase 3")
