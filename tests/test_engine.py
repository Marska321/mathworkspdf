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


def test_fraction_simplify_generation_supports_simplest_form_items() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Fractions",
        subskill="Simplify fractions",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.fill_blank, QuestionType.multiple_choice],
        seed="fraction-simplify-seed",
    )
    worksheet = service.generate(request)
    items = [item for section in worksheet.sections for item in section.items]
    question_types = [item.question_type for item in items]
    assert QuestionType.multiple_choice in question_types
    assert any('Simplify:' in item.question_text for item in items)
    assert any('/' in item.answer.value for item in items)
    assert any(item.metadata.misconception_details for item in items)


def test_fraction_compare_generation_supports_symbol_and_choice_items() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Fractions",
        subskill="Compare fractions",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.fill_blank, QuestionType.multiple_choice],
        seed="fraction-compare-seed",
    )
    worksheet = service.generate(request)
    items = [item for section in worksheet.sections for item in section.items]
    question_types = [item.question_type for item in items]
    assert QuestionType.multiple_choice in question_types
    assert any('__' in item.question_text and '/' in item.question_text for item in items)
    assert any(item.answer.value in {'>', '<'} for item in items if item.question_type == QuestionType.fill_blank)
    assert any('/' in item.answer.value for item in items if item.question_type == QuestionType.multiple_choice)


def test_fraction_equivalent_generation_supports_equivalence_items() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Fractions",
        subskill="Equivalent fractions",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.fill_blank, QuestionType.multiple_choice],
        seed="fraction-equivalent-seed",
    )
    worksheet = service.generate(request)
    items = [item for section in worksheet.sections for item in section.items]
    question_types = [item.question_type for item in items]
    assert QuestionType.multiple_choice in question_types
    assert any("=" in item.question_text for item in items)
    assert any("/" in item.answer.value for item in items if item.question_type == QuestionType.multiple_choice)

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


def test_place_value_generation_supports_digit_value_questions() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Place Value",
        subskill="Place Value Identification",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.fluency,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.fill_blank, QuestionType.multiple_choice],
        seed="place-value-seed",
    )
    worksheet = service.generate(request)
    texts = [item.question_text for section in worksheet.sections for item in section.items]
    assert any("value of the digit" in text.lower() for text in texts)
    assert any(item.answer.value in {"ones", "tens", "hundreds"} or item.answer.value.isdigit() for section in worksheet.sections for item in section.items)


def test_rounding_generation_supports_round_to_place_items() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Place Value",
        subskill="Rounding Whole Numbers",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.fill_blank, QuestionType.multiple_choice],
        seed="rounding-seed",
    )
    worksheet = service.generate(request)
    texts = [item.question_text for section in worksheet.sections for item in section.items]
    assert any("nearest" in text.lower() for text in texts)
    assert any(item.question_type == QuestionType.multiple_choice for section in worksheet.sections for item in section.items)
    assert all(int(item.answer.value) % 10 == 0 for section in worksheet.sections for item in section.items)


def test_compare_order_generation_supports_sequence_items() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Whole Numbers",
        subskill="Compare and Order Whole Numbers",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.fill_blank, QuestionType.sequence, QuestionType.multiple_choice],
        seed="compare-order-seed",
    )
    worksheet = service.generate(request)
    question_types = [item.question_type for section in worksheet.sections for item in section.items]
    assert QuestionType.sequence in question_types
    assert any(item.answer.value.count(',') >= 2 for section in worksheet.sections for item in section.items if item.question_type == QuestionType.sequence)


def test_expanded_notation_generation_supports_expanded_text() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Place Value",
        subskill="Expanded Notation",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.fluency,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.fill_blank],
        seed="expanded-seed",
    )
    worksheet = service.generate(request)
    texts = [item.question_text for section in worksheet.sections for item in section.items]
    assert any("expanded notation" in text.lower() or "+" in text for text in texts)
    assert any(" + " in item.answer.value or item.answer.value.isdigit() for section in worksheet.sections for item in section.items)


def test_add_noregroup_generation_supports_word_problem() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Addition",
        subskill="Addition without regrouping",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.fill_blank, QuestionType.word_problem],
        seed="add-noregroup-seed",
    )
    worksheet = service.generate(request)
    question_types = [item.question_type for section in worksheet.sections for item in section.items]
    assert QuestionType.word_problem in question_types
    assert any("more" in item.question_text.lower() for section in worksheet.sections for item in section.items if item.question_type == QuestionType.word_problem)


def test_sub_noregroup_generation_supports_word_problem() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Subtraction",
        subskill="Subtraction without regrouping",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.fill_blank, QuestionType.word_problem],
        seed="sub-noregroup-seed",
    )
    worksheet = service.generate(request)
    question_types = [item.question_type for section in worksheet.sections for item in section.items]
    assert QuestionType.word_problem in question_types
    assert any("left" in item.question_text.lower() for section in worksheet.sections for item in section.items if item.question_type == QuestionType.word_problem)


def test_sub_regroup_generation_supports_error_spotting() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Subtraction",
        subskill="Subtraction with regrouping",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.error_spotting, QuestionType.word_problem],
        seed="sub-regroup-seed",
    )
    worksheet = service.generate(request)
    question_types = [item.question_type for section in worksheet.sections for item in section.items]
    assert QuestionType.error_spotting in question_types
    assert any(item.answer.value == "No" for section in worksheet.sections for item in section.items if item.question_type == QuestionType.error_spotting)


def test_mult_missing_factor_generation_supports_inverse_reasoning() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Multiplication",
        subskill="Missing factor facts",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.fill_blank, QuestionType.multiple_choice],
        seed="mult-missing-factor-seed",
    )
    worksheet = service.generate(request)
    items = [item for section in worksheet.sections for item in section.items]
    question_types = [item.question_type for item in items]
    assert QuestionType.multiple_choice in question_types
    assert any("__" in item.question_text for item in items)
    assert all(item.answer.value.isdigit() for item in items)

def test_mult_facts_generation_supports_array_visual() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Multiplication",
        subskill="Multiplication facts",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.visual],
        seed="mult-facts-seed",
    )
    worksheet = service.generate(request)
    visuals = [item.visual_payload for section in worksheet.sections for item in section.items if item.question_type == QuestionType.visual]
    assert visuals
    assert all(payload and payload.visual_type == "array_grid" for payload in visuals)


def test_div_remainder_generation_supports_quotient_and_remainder() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Division",
        subskill="Division with remainders",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.multiple_choice],
        seed="div-remainder-seed",
    )
    worksheet = service.generate(request)
    items = [item for section in worksheet.sections for item in section.items]
    question_types = [item.question_type for item in items]
    assert QuestionType.multiple_choice in question_types
    assert any("remainder" in item.question_text.lower() for item in items)
    assert any("remainder" in item.answer.value.lower() for item in items)

def test_div_facts_generation_supports_sharing_story() -> None:
    service = build_service()
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Division",
        subskill="Division facts",
        difficulty=DifficultyBand.support,
        worksheet_type=WorksheetType.mixed,
        question_count=5,
        question_types=[QuestionType.direct, QuestionType.word_problem],
        seed="div-facts-seed",
    )
    worksheet = service.generate(request)
    question_types = [item.question_type for section in worksheet.sections for item in section.items]
    assert QuestionType.word_problem in question_types
    assert any("equally" in item.question_text.lower() for section in worksheet.sections for item in section.items if item.question_type == QuestionType.word_problem)


from app.services.misconception_catalog import load_misconception_catalog, validate_misconception_references


def test_misconception_registry_covers_all_references() -> None:
    missing = validate_misconception_references()
    assert missing == []
    catalog = load_misconception_catalog()
    assert 'ignore_carry' in catalog
    assert catalog['ignore_carry']['distractor_strategy'] == 'ignore_carry'


def test_generated_metadata_includes_misconception_details() -> None:
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
        question_types=[QuestionType.visual, QuestionType.multiple_choice],
        seed="misconception-details-seed",
    )
    worksheet = service.generate(request)
    items = [item for section in worksheet.sections for item in section.items]
    assert any(item.metadata.misconception_details for item in items)
    first_with_details = next(item for item in items if item.metadata.misconception_details)
    assert first_with_details.metadata.misconception_details[0].code in first_with_details.metadata.misconception_targets
    assert worksheet.teacher_notes.misconception_details
    assert worksheet.teacher_notes.misconception_details[0].description



