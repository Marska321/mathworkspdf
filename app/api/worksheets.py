from pathlib import Path
import subprocess

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import get_settings
from app.core.dependencies import get_mastery_tracker, get_repository
from app.repositories.base import WorksheetRepository
from app.schemas.mastery import (
    AdaptiveGenerateLinks,
    AdaptiveGenerateMetadata,
    AdaptiveGenerateRequest,
    AdaptiveGenerateResponse,
)
from app.schemas.worksheet import DifficultyBand, GenerationRequest, WorksheetGenerateResponse
from app.services.html_renderer import WorksheetHtmlRenderer
from app.services.mastery_tracker import MasteryTracker, MasteryTrackerError
from app.services.pdf_exporter import WorksheetPdfExporter
from app.services.worksheet_engine import WorksheetGenerationError, WorksheetGenerationService

router = APIRouter(prefix="/worksheets", tags=["worksheets"])
renderer = WorksheetHtmlRenderer()
pdf_exporter = WorksheetPdfExporter(Path(__file__).resolve().parents[2])


def get_service(repository: WorksheetRepository = Depends(get_repository)) -> WorksheetGenerationService:
    return WorksheetGenerationService(repository=repository, settings=get_settings())


def _generation_difficulty_for_step(step: str) -> DifficultyBand:
    mapping = {
        "remediation": DifficultyBand.support,
        "core": DifficultyBand.core,
        "advanced": DifficultyBand.stretch,
    }
    return mapping[step]


def _mastery_status_for_step(step: str) -> str:
    mapping = {
        "remediation": "remediation",
        "core": "learning",
        "advanced": "mastered",
    }
    return mapping[step]


def _mastery_message(step: str, has_history: bool) -> str:
    if not has_history:
        return "No mastery history. Using core difficulty."
    if step == "remediation":
        return "Student scored below 60% previously. Lowering difficulty."
    if step == "advanced":
        return "Student scored at least 85% previously. Raising difficulty."
    return "Student is in the learning band. Keeping core difficulty."


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


@router.post("/generate/adaptive", response_model=AdaptiveGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_adaptive_worksheet(
    request: AdaptiveGenerateRequest,
    service: WorksheetGenerationService = Depends(get_service),
    repository: WorksheetRepository = Depends(get_repository),
    mastery_tracker: MasteryTracker = Depends(get_mastery_tracker),
) -> AdaptiveGenerateResponse:
    target_skill = next((skill for skill in repository.get_skills() if skill.skill_id == request.target_skill_id), None)
    if target_skill is None:
        raise HTTPException(status_code=404, detail="Target skill not found.")

    try:
        has_history = mastery_tracker.get_mastery_record(request.student_id, request.target_skill_id) is not None
        assigned_difficulty = mastery_tracker.evaluate_next_step(request.student_id, request.target_skill_id)
    except MasteryTrackerError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    generation_difficulty = _generation_difficulty_for_step(assigned_difficulty)
    generation_request = GenerationRequest(
        curriculum=target_skill.curriculum,
        grade=target_skill.grade,
        term=target_skill.term,
        strand=target_skill.strand,
        topic=target_skill.topic,
        subskill=target_skill.subtopic,
        difficulty=generation_difficulty,
        worksheet_type=request.generation.worksheet_type,
        question_count=request.generation.question_count,
        question_types=request.generation.question_types,
        theme=request.generation.theme,
        include_examples=request.generation.include_examples,
        include_answer_key=request.generation.include_answer_key,
        include_challenge_section=request.generation.include_challenge_section,
        include_reflection=request.generation.include_reflection,
        diagnostic_mode=request.generation.diagnostic_mode,
        learner_profile_id=request.student_id,
        target_misconceptions=request.generation.target_misconceptions,
        language=request.generation.language,
        seed=request.generation.seed,
    )

    try:
        worksheet = service.generate(generation_request)
    except WorksheetGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AdaptiveGenerateResponse(
        worksheet_id=worksheet.worksheet_id,
        metadata=AdaptiveGenerateMetadata(
            assigned_difficulty=assigned_difficulty,
            generation_difficulty=generation_difficulty,
            status=_mastery_status_for_step(assigned_difficulty),
            message=_mastery_message(assigned_difficulty, has_history),
        ),
        worksheet=worksheet,
        links=AdaptiveGenerateLinks(
            pdf_download=f"/api/worksheets/{worksheet.worksheet_id}/pdf",
            html_preview=f"/api/worksheets/{worksheet.worksheet_id}/html",
        ),
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
    teacher_mode: bool = Query(default=False),
    service: WorksheetGenerationService = Depends(get_service),
) -> HTMLResponse:
    record = service.get_generated(worksheet_id)
    if not record:
        raise HTTPException(status_code=404, detail="Worksheet not found.")
    worksheet = record["worksheet_json"]
    return HTMLResponse(content=renderer.render(worksheet, teacher_mode=teacher_mode))


@router.get("/{worksheet_id}/pdf")
def get_generated_worksheet_pdf(
    worksheet_id: str,
    request: Request,
    teacher_mode: bool = Query(default=False),
    service: WorksheetGenerationService = Depends(get_service),
):
    record = service.get_generated(worksheet_id)
    if not record:
        raise HTTPException(status_code=404, detail="Worksheet not found.")

    base_url = str(request.base_url).rstrip("/")
    try:
        pdf_path = pdf_exporter.render(worksheet_id, base_url, teacher_mode=teacher_mode)
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
