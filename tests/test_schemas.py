import pytest
from pydantic import ValidationError

from app.schemas.worksheet import GenerationRequest, QuestionType, WorksheetType


def test_request_defaults_question_types() -> None:
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Fractions",
    )
    assert request.curriculum == "CAPS"
    assert request.include_answer_key is True
    assert QuestionType.visual in request.question_types


def test_request_rejects_invalid_question_count() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            grade=4,
            term=1,
            strand="Number, Operations and Relationships",
            topic="Fractions",
            question_count=2,
        )


def test_request_allows_fluency_defaults() -> None:
    request = GenerationRequest(
        grade=4,
        term=1,
        strand="Number, Operations and Relationships",
        topic="Addition",
        worksheet_type=WorksheetType.fluency,
    )
    assert QuestionType.direct in request.question_types
