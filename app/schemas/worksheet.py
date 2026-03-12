from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class DifficultyBand(str, Enum):
    support = "support"
    core = "core"
    stretch = "stretch"


class WorksheetType(str, Enum):
    fluency = "fluency"
    concept = "concept"
    mixed = "mixed"
    intervention = "intervention"
    assessment = "assessment"


class QuestionType(str, Enum):
    direct = "direct"
    fill_blank = "fill_blank"
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    matching = "matching"
    visual = "visual"
    word_problem = "word_problem"
    error_spotting = "error_spotting"
    sequence = "sequence"


class ConstraintRule(BaseModel):
    type: Literal["expression", "derived"]
    rule: str


class VariableDefinition(BaseModel):
    type: str
    required: bool = True
    values: list[Any] = Field(default_factory=list)


class AnswerFormula(BaseModel):
    type: Literal["expression", "fraction"]
    value: str | None = None
    numerator: str | None = None
    denominator: str | None = None


class DistractorRule(BaseModel):
    type: str


class RenderingConfig(BaseModel):
    visual_type: str | None = None
    visual_variable_map: dict[str, str] = Field(default_factory=dict)
    layout_hint: Literal["single_line", "two_column", "full_width"] = "single_line"


class Skill(BaseModel):
    skill_id: str
    curriculum: str = "CAPS"
    grade: int
    term: int
    strand: str
    topic: str
    subtopic: str | None = None
    name: str
    description: str
    caps_code: str
    difficulty_bands_supported: list[DifficultyBand]
    recommended_question_types: list[QuestionType]
    prerequisite_skill_ids: list[str] = Field(default_factory=list)
    misconception_tags: list[str] = Field(default_factory=list)
    active: bool = True


class Template(BaseModel):
    template_id: str
    template_code: str
    skill_id: str
    family_id: str
    pattern_code: str | None = None
    name: str
    question_type: QuestionType
    template_text: str
    instructions_template: str | None = None
    variable_schema: dict[str, VariableDefinition]
    difficulty_profiles: dict[DifficultyBand, dict[str, Any]]
    constraints: list[ConstraintRule] = Field(default_factory=list)
    answer_formula: AnswerFormula
    distractor_rules: list[DistractorRule] = Field(default_factory=list)
    explanation_template: str
    rendering: RenderingConfig = Field(default_factory=RenderingConfig)
    theme_supported: bool = False
    visual_supported: bool = False
    misconception_targets: list[str] = Field(default_factory=list)
    active: bool = True


class GenerationRequest(BaseModel):
    curriculum: str = Field(default="CAPS", examples=["CAPS"])
    grade: int = Field(examples=[4])
    term: int = Field(examples=[1])
    strand: str = Field(examples=["Number, Operations and Relationships"])
    topic: str = Field(examples=["Fractions"])
    subskill: str | None = Field(default=None, examples=["Fractions as part of a whole"])
    difficulty: DifficultyBand = Field(default=DifficultyBand.support, examples=["support"])
    worksheet_type: WorksheetType = Field(default=WorksheetType.concept, examples=["concept"])
    question_count: int = Field(default=20, ge=5, le=60, examples=[5])
    question_types: list[QuestionType] = Field(default_factory=list, examples=[["visual", "multiple_choice"]])
    theme: str | None = Field(default=None, examples=[None])
    include_examples: bool = Field(default=False, examples=[False])
    include_answer_key: bool = Field(default=True, examples=[True])
    include_challenge_section: bool = Field(default=False, examples=[False])
    include_reflection: bool = Field(default=False, examples=[False])
    diagnostic_mode: bool = Field(default=False, examples=[False])
    learner_profile_id: UUID | None = Field(default=None, examples=[None])
    target_misconceptions: list[str] = Field(default_factory=list, examples=[[]])
    language: Literal["en"] = Field(default="en", examples=["en"])
    seed: str | None = Field(default=None, examples=["swagger-demo"])

    model_config = {
        "json_schema_extra": {
            "example": {
                "grade": 4,
                "term": 1,
                "strand": "Number, Operations and Relationships",
                "topic": "Fractions",
                "subskill": "Fractions as part of a whole",
                "difficulty": "support",
                "worksheet_type": "concept",
                "question_count": 5,
                "question_types": ["visual", "multiple_choice"],
                "theme": None,
                "include_examples": False,
                "include_answer_key": True,
                "include_challenge_section": False,
                "include_reflection": False,
                "diagnostic_mode": False,
                "learner_profile_id": None,
                "target_misconceptions": [],
                "language": "en",
                "seed": "swagger-demo"
            }
        }
    }

    @field_validator("curriculum")
    @classmethod
    def check_curriculum(cls, value: str) -> str:
        if value != "CAPS":
            raise ValueError("Only CAPS is supported in the MVP.")
        return value

    @model_validator(mode="after")
    def default_question_types(self) -> "GenerationRequest":
        if not self.question_types:
            defaults = {
                WorksheetType.fluency: [QuestionType.direct, QuestionType.fill_blank, QuestionType.multiple_choice],
                WorksheetType.concept: [QuestionType.visual, QuestionType.fill_blank, QuestionType.multiple_choice, QuestionType.sequence],
                WorksheetType.mixed: [QuestionType.direct, QuestionType.fill_blank, QuestionType.multiple_choice, QuestionType.visual, QuestionType.sequence],
                WorksheetType.intervention: [QuestionType.visual, QuestionType.fill_blank],
                WorksheetType.assessment: [QuestionType.direct, QuestionType.fill_blank, QuestionType.multiple_choice, QuestionType.sequence],
            }
            self.question_types = defaults[self.worksheet_type]
        return self


class BlueprintSection(BaseModel):
    section_id: str
    title: str
    target_count: int
    difficulty_bias: DifficultyBand
    question_types: list[QuestionType]
    template_family_bias: list[str] = Field(default_factory=list)
    instructions: str | None = None


class WorksheetBlueprint(BaseModel):
    blueprint_id: str
    worksheet_type: WorksheetType
    question_count: int
    sections: list[BlueprintSection]


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnswerValue(BaseModel):
    value: str
    format: Literal["integer", "fraction", "text"] = "integer"


class VisualPayload(BaseModel):
    visual_type: str
    params: dict[str, Any]




class MisconceptionDetail(BaseModel):
    code: str
    name: str
    description: str
    distractor_strategy: str | None = None

class QuestionMetadata(BaseModel):
    representation_type: str
    misconception_targets: list[str] = Field(default_factory=list)
    misconception_details: list[MisconceptionDetail] = Field(default_factory=list)
    prerequisite_skill_ids: list[str] = Field(default_factory=list)
    estimated_difficulty_score: float


class GeneratedQuestionVariant(BaseModel):
    question_id: str
    template_id: str
    skill_id: str
    family_id: str
    difficulty: DifficultyBand
    question_type: QuestionType
    variables: dict[str, Any]
    question_text: str
    answer: AnswerValue
    distractors: list[str] = Field(default_factory=list)
    explanation: str
    metadata: QuestionMetadata
    options: list[str] = Field(default_factory=list)
    visual_payload: VisualPayload | None = None


class SectionOutput(BaseModel):
    section_id: str
    title: str
    instructions: str | None = None
    items: list[GeneratedQuestionVariant]


class AnswerKeyEntry(BaseModel):
    question_number: int
    question_id: str
    correct_answer: str
    alternate_answers: list[str] = Field(default_factory=list)
    explanation: str
    skill_id: str
    misconception_note: str | None = None


class TeacherNotes(BaseModel):
    skills_tested: list[str]
    misconceptions_targeted: list[str]
    misconception_details: list[MisconceptionDetail] = Field(default_factory=list)


class RenderableWorksheet(BaseModel):
    worksheet_id: str
    title: str
    subtitle: str
    metadata: dict[str, Any]
    sections: list[SectionOutput]
    answer_key: list[AnswerKeyEntry] = Field(default_factory=list)
    teacher_notes: TeacherNotes


class WorksheetGenerateResponse(BaseModel):
    worksheet_id: str
    status: Literal["generated"]
    worksheet_json: RenderableWorksheet
    answer_key_json: list[AnswerKeyEntry]



