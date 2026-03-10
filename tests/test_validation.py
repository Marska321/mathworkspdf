from app.core.config import get_settings
from app.repositories.in_memory import InMemoryWorksheetRepository
from app.schemas.worksheet import DifficultyBand, GenerationRequest, QuestionType, WorksheetType
from app.services.worksheet_engine import WorksheetGenerationService


def test_generated_items_stay_within_support_band() -> None:
    service = WorksheetGenerationService(InMemoryWorksheetRepository(), get_settings())
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
        seed="support-band",
    )
    worksheet = service.generate(request)
    scores = [item.metadata.estimated_difficulty_score for section in worksheet.sections for item in section.items]
    assert all(score <= 0.39 for score in scores)


def test_no_duplicate_signatures_in_generated_worksheet() -> None:
    service = WorksheetGenerationService(InMemoryWorksheetRepository(), get_settings())
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Fractions",
        subskill="Fractions as part of a whole",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.concept,
        question_count=6,
        question_types=[QuestionType.visual, QuestionType.multiple_choice],
        seed="signature-check",
    )
    worksheet = service.generate(request)
    signatures = [service.build_variant_signature(item) for section in worksheet.sections for item in section.items]
    assert len(signatures) == len(set(signatures))
