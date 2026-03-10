from pathlib import Path
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import get_settings
from app.core.dependencies import get_repository
from app.repositories.base import WorksheetRepository
from app.schemas.worksheet import GenerationRequest, WorksheetGenerateResponse
from app.services.html_renderer import WorksheetHtmlRenderer
from app.services.pdf_exporter import WorksheetPdfExporter
from app.services.worksheet_engine import WorksheetGenerationError, WorksheetGenerationService

router = APIRouter(prefix="/worksheets", tags=["worksheets"])
renderer = WorksheetHtmlRenderer()
pdf_exporter = WorksheetPdfExporter(Path(__file__).resolve().parents[2])


def get_service(repository: WorksheetRepository = Depends(get_repository)) -> WorksheetGenerationService:
    return WorksheetGenerationService(repository=repository, settings=get_settings())


@router.post("/generate", response_model=WorksheetGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_worksheet(
    request: GenerationRequest,
    service: WorksheetGenerationService = Depends(get_service),
) -> WorksheetGenerateResponse:
    try:
        worksheet = service.generate(request)
    except WorksheetGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return WorksheetGenerateResponse(
        worksheet_id=worksheet.worksheet_id,
        status="generated",
        worksheet_json=worksheet,
        answer_key_json=worksheet.answer_key,
    )


@router.get("/{worksheet_id}")
def get_generated_worksheet(
    worksheet_id: str,
    service: WorksheetGenerationService = Depends(get_service),
):
    record = service.get_generated(worksheet_id)
    if not record:
        raise HTTPException(status_code=404, detail="Worksheet not found.")
    return record


@router.get("/{worksheet_id}/html", response_class=HTMLResponse)
def get_generated_worksheet_html(
    worksheet_id: str,
    service: WorksheetGenerationService = Depends(get_service),
) -> HTMLResponse:
    record = service.get_generated(worksheet_id)
    if not record:
        raise HTTPException(status_code=404, detail="Worksheet not found.")
    worksheet = record["worksheet_json"]
    return HTMLResponse(content=renderer.render(worksheet))


@router.get("/{worksheet_id}/pdf")
def get_generated_worksheet_pdf(
    worksheet_id: str,
    request: Request,
    service: WorksheetGenerationService = Depends(get_service),
):
    record = service.get_generated(worksheet_id)
    if not record:
        raise HTTPException(status_code=404, detail="Worksheet not found.")

    base_url = str(request.base_url).rstrip("/")
    try:
        pdf_path = pdf_exporter.render(worksheet_id, base_url)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() if exc.stderr else "PDF export failed. Install Playwright Chromium first."
        raise HTTPException(status_code=503, detail=detail) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="npx is not available for PDF export.") from exc

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{worksheet_id}.pdf",
    )
