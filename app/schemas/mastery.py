from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.worksheet import DifficultyBand, QuestionType, RenderableWorksheet, WorksheetType

AssignedDifficulty = Literal["advanced", "core", "remediation"]
MasteryStatus = Literal["learning", "remediation", "mastered"]
LanguageCode = Literal["en"]


class AdaptiveGenerationOptions(BaseModel):
    worksheet_type: WorksheetType = Field(default=WorksheetType.concept)
    question_count: int = Field(default=20, ge=5, le=60)
    question_types: list[QuestionType] = Field(default_factory=list)
    theme: str | None = None
    include_examples: bool = False
    include_answer_key: bool = True
    include_challenge_section: bool = False
    include_reflection: bool = False
    diagnostic_mode: bool = False
    target_misconceptions: list[str] = Field(default_factory=list)
    language: LanguageCode = "en"
    seed: str | None = None


class AdaptiveGenerateRequest(BaseModel):
    student_id: UUID
    target_skill_id: str
    generation: AdaptiveGenerationOptions = Field(default_factory=AdaptiveGenerationOptions)


class AdaptiveGenerateMetadata(BaseModel):
    assigned_difficulty: AssignedDifficulty
    generation_difficulty: DifficultyBand
    status: MasteryStatus
    message: str


class AdaptiveGenerateLinks(BaseModel):
    pdf_download: str
    html_preview: str


class AdaptiveGenerateResponse(BaseModel):
    worksheet_id: str
    metadata: AdaptiveGenerateMetadata
    worksheet: RenderableWorksheet
    links: AdaptiveGenerateLinks


class MasteryGradeRequest(BaseModel):
    student_id: UUID
    skill_id: str
    latest_score: int = Field(ge=0, le=100)


class MasteryGradeResponse(BaseModel):
    student_id: UUID
    skill_id: str
    mastery_score: int = Field(ge=0, le=100)
    status: MasteryStatus
    last_assessed_at: datetime
