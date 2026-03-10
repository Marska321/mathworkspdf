import random

from app.core.config import get_settings
from app.repositories.in_memory import InMemoryWorksheetRepository
from app.schemas.worksheet import DifficultyBand, GenerationRequest, QuestionType, WorksheetType
from app.services.worksheet_engine import WorksheetGenerationService


def build_service() -> WorksheetGenerationService:
    return WorksheetGenerationService(InMemoryWorksheetRepository(), get_settings())


def test_addition_generation_is_deterministic() -> None:
    service = build_service()
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
        seed="fixed-seed",
    )
    worksheet_a = service.generate(request)
    worksheet_b = service.generate(request)
    texts_a = [item.question_text for section in worksheet_a.sections for item in section.items]
    texts_b = [item.question_text for section in worksheet_b.sections for item in section.items]
    assert texts_a == texts_b


def test_template_can_generate_many_valid_items() -> None:
    repository = InMemoryWorksheetRepository()
    service = WorksheetGenerationService(repository, get_settings())
    template = next(item for item in repository.get_templates() if item.template_code == "add_regroup_direct_01")
    for index in range(120):
        variables = service.sample_variables(template, DifficultyBand.core, random.Random(f"seed-{index}"))
        assert service.constraints_hold(template, variables)
        answer = service.compute_answer(template, variables)
        distractors = service.generate_distractors(template, variables, answer)
        assert answer.value not in distractors
        assert len(set(distractors)) == 3


def test_fraction_visual_generates_payload() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Fractions",
        subskill="Fractions as part of a whole",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.concept,
        question_count=5,
        seed="fractions-seed",
    )
    worksheet = service.generate(request)
    visuals = [
        item.visual_payload
        for section in worksheet.sections
        for item in section.items
        if item.question_type == QuestionType.visual
    ]
    assert visuals
    assert all(payload and payload.visual_type == "fraction_bar" for payload in visuals)
