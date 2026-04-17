"""
export_pdf — genera PDF profesional con presupuesto y cronograma.

Genera un PDF con:
- Header: nombre proyecto, cliente, arquitecto, fecha
- Tabla de ítems con códigos, descripción, unidades, cantidades, precios
- Subtotales por categoría
- Total general
- Si incluye schedule: tabla de fases
"""
import copy
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from weasyprint import HTML

from app.core.guardrails import with_logging, with_timeout


class ProjectInfo(BaseModel):
    model_config = ConfigDict(strict=True)
    
    name: str
    client: str = ""
    architect: str = ""
    address: str = ""


class ExportInput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    budget: dict
    schedule: dict | None = None
    project_info: dict | None = None
    template: str = "default"


class ExportOutput(BaseModel):
    model_config = ConfigDict(strict=True)

    project_id: str
    file_url: str
    storage_path: str
    pages: int


def _build_html(budget: dict, schedule: dict | None, project_info: dict | None) -> str:
    """Construye el HTML del PDF."""
    
    # Project info
    proj_name = project_info.get("name", "Presupuesto de Obra") if project_info else "Presupuesto de Obra"
    client = project_info.get("client", "") if project_info else ""
    architect = project_info.get("architect", "") if project_info else ""
    address = project_info.get("address", "") if project_info else ""
    
    # Header
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
            .info {{ margin-bottom: 20px; color: #666; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f5f5f5; }}
            .total {{ font-weight: bold; font-size: 18px; }}
            .category-header {{ background-color: #e0e0e0; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>{proj_name}</h1>
        <div class="info">
    """
    
    if client:
        html += f"<p><strong>Cliente:</strong> {client}</p>"
    if architect:
        html += f"<p><strong>Arquitecto:</strong> {architect}</p>"
    if address:
        html += f"<p><strong>Dirección:</strong> {address}</p>"
    
    html += f"""
            <p><strong>Fecha:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
            <p><strong>Versión:</strong> {budget.get('version', 1)}</p>
        </div>
        
        <h2>Presupuesto</h2>
        <table>
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Descripción</th>
                    <th>Unidad</th>
                    <th>Cantidad</th>
                    <th>Precio Unit.</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
    """
    
    # Items grouped by category
    items = budget.get("items", [])
    subtotals = budget.get("subtotals", {})
    
    current_category = None
    for item in items:
        category = item.get("category", "general")
        
        # Category header
        if category != current_category:
            if current_category is not None:
                html += f"""
                    <tr class="category-header">
                        <td colspan="5">Subtotal {current_category.title()}</td>
                        <td>${subtotals.get(current_category, 0):,.2f}</td>
                    </tr>
                """
            current_category = category
            html += f"""
                <tr style="background-color: #f0f0f0;">
                    <td colspan="6"><strong>{category.title()}</strong></td>
                </tr>
            """
        
        html += f"""
            <tr>
                <td>{item.get('code', '')}</td>
                <td>{item.get('description', '')}</td>
                <td>{item.get('unit', '')}</td>
                <td>{item.get('quantity', 0):.2f}</td>
                <td>${item.get('unit_price', 0):,.2f}</td>
                <td>${item.get('total', 0):,.2f}</td>
            </tr>
        """
    
    # Close category
    if current_category:
        html += f"""
            <tr class="category-header">
                <td colspan="5">Subtotal {current_category.title()}</td>
                <td>${subtotals.get(current_category, 0):,.2f}</td>
            </tr>
        """
    
    # Total
    html += f"""
            <tr style="font-weight: bold; font-size: 16px;">
                <td colspan="5">TOTAL</td>
                <td>${budget.get('total', 0):,.2f}</td>
            </tr>
        </tbody>
        </table>
    """
    
    # Schedule if provided
    if schedule and schedule.get("phases"):
        html += """
        <h2>Cronograma de Obra</h2>
        <table>
            <thead>
                <tr>
                    <th>Fase</th>
                    <th>Inicio</th>
                    <th>Fin</th>
                    <th>Semanas</th>
                    <th> costo</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for phase in schedule.get("phases", []):
            html += f"""
            <tr>
                <td>{phase.get('name', '')}</td>
                <td>{phase.get('start_date', '')}</td>
                <td>{phase.get('end_date', '')}</td>
                <td>{phase.get('weeks', 0)}</td>
                <td>${phase.get('cost', 0):,.2f}</td>
            </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
    
    html += """
    </body>
    </html>
    """
    
    return html


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
    Genera PDF profesional y devuelve URL.
    
    Por ahora retorna un placeholder - requiere Supabase real paraStorage.
    """
    # Build HTML
    html_content = _build_html(budget, schedule, project_info)
    
    # Generate PDF
    pdf_bytes = HTML(string=html_content).write_pdf()
    
    # Calculate pages (approximation)
    items_count = len(budget.get("items", []))
    pages = max(1, items_count // 30 + 1)
    
    # Storage path
    version = budget.get("version", 1)
    storage_path = f"exports/{project_id}/{project_id}_v{version}.pdf"
    
    # TODO: Upload to Supabase Storage when credentials available
    # Placeholder URL for now
    file_url = f"https://placeholder.supabase.co/{storage_path}"
    
    return {
        "project_id": project_id,
        "file_url": file_url,
        "storage_path": storage_path,
        "pages": pages,
    }