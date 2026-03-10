from app.core.config import get_settings
from app.repositories.in_memory import InMemoryWorksheetRepository
from app.schemas.worksheet import DifficultyBand, GenerationRequest, QuestionType, WorksheetType
from app.services.html_renderer import WorksheetHtmlRenderer
from app.services.worksheet_engine import WorksheetGenerationService


FAMILY_ID = "add_regroup_family"
SKILL_ID = "add_regroup_g4_01"


def test_add_regroup_family_runs_end_to_end() -> None:
    repository = InMemoryWorksheetRepository()
    service = WorksheetGenerationService(repository, get_settings())
    renderer = WorksheetHtmlRenderer()

    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Addition",
        subskill="Addition with regrouping",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.fluency,
        question_count=6,
        question_types=[QuestionType.direct, QuestionType.fill_blank],
        seed="add-regroup-acceptance",
    )

    worksheet = service.generate(request)
    saved = repository.get_generated_worksheet(worksheet.worksheet_id)
    html = renderer.render(saved["worksheet_json"])

    items = [item for section in worksheet.sections for item in section.items]
    assert items
    assert all(item.family_id == FAMILY_ID for item in items)
    assert all(item.skill_id == SKILL_ID for item in items)
    assert all(item.answer.value for item in items)
    assert all(item.explanation for item in items)
    assert all(item.metadata.estimated_difficulty_score <= 0.39 for item in items)
    assert all(item.question_type in {QuestionType.direct, QuestionType.fill_blank} for item in items)
    assert saved is not None
    assert len(saved["answer_key_json"]) == 6
    assert "Grade 4 Addition Practice" in html
    assert "math-card" in html
    assert "answer-line" in html
    assert "answer-key-page" in html
    assert "Name:" in html
    assert "Date:" in html
