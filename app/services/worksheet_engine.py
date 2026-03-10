from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.repositories.base import WorksheetRepository
from app.schemas.worksheet import (
    AnswerKeyEntry,
    AnswerValue,
    BlueprintSection,
    DifficultyBand,
    GeneratedQuestionVariant,
    GenerationRequest,
    QuestionMetadata,
    QuestionType,
    RenderableWorksheet,
    SectionOutput,
    Skill,
    TeacherNotes,
    Template,
    ValidationResult,
    VisualPayload,
    WorksheetBlueprint,
)


class WorksheetGenerationError(RuntimeError):
    pass


@dataclass
class EngineContext:
    request: GenerationRequest
    rng: random.Random
    target_skills: list[Skill]
    templates: list[Template]
    blueprint: WorksheetBlueprint


class WorksheetGenerationService:
    def __init__(self, repository: WorksheetRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    def generate(self, request: GenerationRequest) -> RenderableWorksheet:
        normalized = self.normalize_request(request)
        context = EngineContext(
            request=normalized,
            rng=random.Random(normalized.seed),
            target_skills=self.resolve_target_skills(normalized),
            templates=self.repository.get_templates(),
            blueprint=self.build_blueprint(normalized),
        )
        worksheet = self.assemble_worksheet(context)
        self.repository.save_generated_worksheet(worksheet, normalized.model_dump(mode="json"))
        return worksheet

    def get_generated(self, worksheet_id: str) -> dict[str, Any] | None:
        return self.repository.get_generated_worksheet(worksheet_id)

    def normalize_request(self, request: GenerationRequest) -> GenerationRequest:
        payload = request.model_copy(deep=True)
        if not payload.seed:
            seed_basis = (
                f"{payload.grade}|{payload.term}|{payload.strand}|{payload.topic}|"
                f"{payload.subskill}|{payload.difficulty.value}|{payload.question_count}"
            )
            payload.seed = uuid.uuid5(uuid.NAMESPACE_DNS, seed_basis).hex[:12]
        return payload

    def resolve_target_skills(self, request: GenerationRequest) -> list[Skill]:
        skills = [
            skill
            for skill in self.repository.get_skills()
            if skill.grade == request.grade
            and skill.term == request.term
            and skill.strand.lower() == request.strand.lower()
            and skill.topic.lower() == request.topic.lower()
        ]
        if request.subskill:
            by_subskill = [
                skill for skill in skills if (skill.subtopic or "").lower() == request.subskill.lower()
            ]
            skills = by_subskill or skills
        if not skills:
            raise WorksheetGenerationError("No matching skills were found for the request.")
        return skills

    def build_blueprint(self, request: GenerationRequest) -> WorksheetBlueprint:
        blueprint = next(
            (item for item in self.repository.get_blueprints() if item.worksheet_type == request.worksheet_type),
            None,
        )
        if blueprint is None:
            raise WorksheetGenerationError(f"No blueprint configured for {request.worksheet_type.value}.")

        if request.include_challenge_section:
            active_sections = blueprint.sections
        else:
            active_sections = [section for section in blueprint.sections if section.section_id != "challenge"]

        total_weight = sum(section.target_count for section in active_sections)
        allocated = 0
        sections: list[BlueprintSection] = []
        for index, section in enumerate(active_sections):
            if index == len(active_sections) - 1:
                target_count = request.question_count - allocated
            else:
                proportion = section.target_count / total_weight
                target_count = max(1, round(request.question_count * proportion))
                allocated += target_count
            sections.append(section.model_copy(update={"target_count": target_count, "difficulty_bias": request.difficulty}))

        return blueprint.model_copy(update={"question_count": request.question_count, "sections": sections})

    def assemble_worksheet(self, context: EngineContext) -> RenderableWorksheet:
        used_template_codes: list[str] = []
        used_family_ids: list[str] = []
        used_answer_values: list[str] = []
        used_signatures: set[str] = set()
        sections: list[SectionOutput] = []

        for section in context.blueprint.sections:
            items: list[GeneratedQuestionVariant] = []
            while len(items) < section.target_count:
                template = self.choose_template(context, section, used_template_codes, used_family_ids)
                variant = self.generate_valid_variant(
                    context=context,
                    template=template,
                    section=section,
                    used_template_codes=used_template_codes,
                    used_family_ids=used_family_ids,
                    used_answer_values=used_answer_values,
                    used_signatures=used_signatures,
                    current_item_count=sum(len(sec.items) for sec in sections) + len(items),
                )
                items.append(variant)
                used_template_codes.append(template.template_id)
                used_family_ids.append(template.family_id)
                used_answer_values.append(variant.answer.value)
                used_signatures.add(self.build_variant_signature(variant))

            sections.append(
                SectionOutput(
                    section_id=section.section_id,
                    title=section.title,
                    instructions=section.instructions,
                    items=self.sequence_section_items(items),
                )
            )

        answer_key = self.build_answer_key(sections)
        skills_tested = sorted({item.skill_id for section in sections for item in section.items})
        misconceptions = sorted(
            {tag for section in sections for item in section.items for tag in item.metadata.misconception_targets}
        )
        worksheet_id = f"ws_{uuid.uuid4().hex[:12]}"
        return RenderableWorksheet(
            worksheet_id=worksheet_id,
            title=f"Grade {context.request.grade} {context.request.topic} Practice",
            subtitle=context.request.subskill or context.request.topic,
            metadata={
                "curriculum": context.request.curriculum,
                "grade": context.request.grade,
                "term": context.request.term,
                "topic": context.request.topic,
                "subskill": context.request.subskill,
                "difficulty": context.request.difficulty.value,
                "theme": context.request.theme,
                "worksheet_type": context.request.worksheet_type.value,
                "seed": context.request.seed,
            },
            sections=sections,
            answer_key=answer_key if context.request.include_answer_key else [],
            teacher_notes=TeacherNotes(
                skills_tested=skills_tested,
                misconceptions_targeted=misconceptions,
            ),
        )

    def choose_template(
        self,
        context: EngineContext,
        section: BlueprintSection,
        used_template_codes: list[str],
        used_family_ids: list[str],
    ) -> Template:
        target_skill_ids = {skill.skill_id for skill in context.target_skills}
        candidates = [
            template
            for template in context.templates
            if template.active
            and template.skill_id in target_skill_ids
            and template.question_type in section.question_types
            and template.question_type in context.request.question_types
            and (not section.template_family_bias or template.family_id in section.template_family_bias)
        ]
        if not candidates:
            raise WorksheetGenerationError(f"No templates available for section {section.section_id}.")

        def template_rank(candidate: Template) -> tuple[int, int]:
            consecutive_penalty = 1 if len(used_family_ids) >= 2 and used_family_ids[-2:] == [candidate.family_id, candidate.family_id] else 0
            prior_usage = used_template_codes.count(candidate.template_id)
            return (consecutive_penalty, prior_usage)

        best_rank = min(template_rank(candidate) for candidate in candidates)
        best_candidates = [candidate for candidate in candidates if template_rank(candidate) == best_rank]
        return context.rng.choice(best_candidates)

    def generate_valid_variant(
        self,
        context: EngineContext,
        template: Template,
        section: BlueprintSection,
        used_template_codes: list[str],
        used_family_ids: list[str],
        used_answer_values: list[str],
        used_signatures: set[str],
        current_item_count: int,
    ) -> GeneratedQuestionVariant:
        for _ in range(self.settings.generation_max_attempts):
            variables = self.sample_variables(template, section.difficulty_bias, context.rng)
            if not self.constraints_hold(template, variables):
                continue
            answer = self.compute_answer(template, variables)
            distractors = self.generate_distractors(template, variables, answer)
            options = self.build_options(template.question_type, answer, distractors, context.rng)
            difficulty_score = self.score_difficulty(template, variables, section.difficulty_bias)
            skill = next(skill for skill in context.target_skills if skill.skill_id == template.skill_id)
            variant = GeneratedQuestionVariant(
                question_id=f"q_{uuid.uuid4().hex[:10]}",
                template_id=template.template_id,
                skill_id=template.skill_id,
                family_id=template.family_id,
                difficulty=section.difficulty_bias,
                question_type=template.question_type,
                variables=variables,
                question_text=template.template_text.format(**variables),
                answer=answer,
                distractors=distractors,
                explanation=template.explanation_template,
                metadata=QuestionMetadata(
                    representation_type="visual" if template.question_type == QuestionType.visual else "symbolic",
                    misconception_targets=template.misconception_targets,
                    prerequisite_skill_ids=skill.prerequisite_skill_ids,
                    estimated_difficulty_score=difficulty_score,
                ),
                options=options,
                visual_payload=self.build_visual_payload(template, variables),
            )
            validation = self.validate_variant(
                variant=variant,
                request=context.request,
                used_template_codes=used_template_codes,
                used_family_ids=used_family_ids,
                used_answer_values=used_answer_values,
                used_signatures=used_signatures,
                current_item_count=current_item_count,
            )
            if validation.valid:
                return variant
        raise WorksheetGenerationError(f"Unable to generate a valid item for {template.template_code}.")

    def sample_variables(
        self,
        template: Template,
        difficulty: DifficultyBand,
        rng: random.Random,
    ) -> dict[str, Any]:
        profile = template.difficulty_profiles[difficulty]
        for _ in range(self.settings.generation_max_attempts):
            if template.template_code in {"add_regroup_direct_01", "add_regroup_mcq_01"}:
                variables = {"a": rng.randint(*profile["a_range"]), "b": rng.randint(*profile["b_range"])}
            elif template.template_code == "add_regroup_missing_01":
                a = rng.randint(*profile["a_range"])
                b = rng.randint(*profile["b_range"])
                variables = {"a": a, "b": b, "total": a + b}
            elif template.template_code in {"fraction_partwhole_visual_01", "fraction_partwhole_mcq_01"}:
                parts_total = rng.choice(profile["parts_total_values"])
                parts_shaded = rng.randint(1, parts_total - 1)
                variables = {"parts_total": parts_total, "parts_shaded": parts_shaded}
            else:
                raise WorksheetGenerationError(f"No variable sampler registered for {template.template_code}.")

            if self.constraints_hold(template, variables):
                return variables

        raise WorksheetGenerationError(f"Unable to sample valid variables for {template.template_code}.")

    def constraints_hold(self, template: Template, variables: dict[str, Any]) -> bool:
        for constraint in template.constraints:
            if not bool(eval(constraint.rule, {"__builtins__": {}}, variables)):
                return False
        return True

    def compute_answer(self, template: Template, variables: dict[str, Any]) -> AnswerValue:
        formula = template.answer_formula
        if formula.type == "expression":
            value = eval(formula.value or "", {"__builtins__": {}}, variables)
            return AnswerValue(value=str(value), format="integer" if isinstance(value, int) else "text")
        numerator = eval(formula.numerator or "", {"__builtins__": {}}, variables)
        denominator = eval(formula.denominator or "", {"__builtins__": {}}, variables)
        return AnswerValue(value=f"{numerator}/{denominator}", format="fraction")

    def generate_distractors(self, template: Template, variables: dict[str, Any], answer: AnswerValue) -> list[str]:
        distractors: list[str] = []
        for rule in template.distractor_rules:
            candidate = self.apply_distractor_rule(rule.type, template.template_code, variables, answer)
            if candidate and candidate != answer.value and candidate not in distractors:
                distractors.append(candidate)
        while len(distractors) < 3:
            fallback = self.fallback_distractor(template.template_code, variables, answer, len(distractors) + 1)
            if fallback != answer.value and fallback not in distractors:
                distractors.append(fallback)
        return distractors[:3]

    def apply_distractor_rule(
        self,
        rule_type: str,
        template_code: str,
        variables: dict[str, Any],
        answer: AnswerValue,
    ) -> str | None:
        if template_code.startswith("add_regroup"):
            a = variables["a"]
            b = variables["b"]
            total = int(answer.value)
            if rule_type == "ignore_carry":
                return str(((a // 10) + (b // 10)) * 10 + ((a % 10) + (b % 10)) % 10)
            if rule_type == "off_by_ten":
                return str(total + 10)
            if rule_type == "digit_reversal":
                return str(int(str(total)[::-1])) if total >= 10 else str(total)
            if rule_type == "off_by_one":
                return str(total - 1 if total > 1 else total + 1)

        if template_code.startswith("fraction_partwhole"):
            total = variables["parts_total"]
            shaded = variables["parts_shaded"]
            if rule_type == "swap_num_den":
                return f"{total}/{shaded}"
            if rule_type == "use_unshaded_as_numerator":
                return f"{total - shaded}/{total}"
            if rule_type == "off_by_one_shaded":
                adjusted = shaded + 1 if shaded + 1 < total else shaded - 1
                return f"{adjusted}/{total}"
            if rule_type == "simplified_wrong":
                gcd_value = math.gcd(shaded, total)
                if gcd_value > 1:
                    return f"{max(1, shaded // gcd_value)}/{max(2, (total // gcd_value) + 1)}"
                return f"{shaded}/{max(2, total + 1)}"
        return None

    def fallback_distractor(
        self,
        template_code: str,
        variables: dict[str, Any],
        answer: AnswerValue,
        offset: int,
    ) -> str:
        if template_code.startswith("add_regroup"):
            return str(int(answer.value) + offset * 2)
        numerator, denominator = answer.value.split("/")
        return f"{max(1, int(numerator) + offset)}/{denominator}"

    def score_difficulty(
        self,
        template: Template,
        variables: dict[str, Any],
        requested_band: DifficultyBand,
    ) -> float:
        if template.template_code.startswith("add_regroup"):
            max_number = max(variables["a"], variables.get("b", 0), variables.get("total", 0))
            number_complexity = min(max_number / 160, 1.0)
            structure_complexity = 0.38 if template.question_type in {QuestionType.direct, QuestionType.multiple_choice} else 0.5
            representation_complexity = 0.1
            linguistic_load = 0.05
            distractor_similarity = 0.45
        else:
            denominator = variables["parts_total"]
            number_complexity = min(denominator / 12, 1.0)
            structure_complexity = 0.35
            representation_complexity = 0.65 if template.question_type == QuestionType.visual else 0.4
            linguistic_load = 0.08
            distractor_similarity = 0.5

        score = (
            0.30 * number_complexity
            + 0.25 * structure_complexity
            + 0.20 * representation_complexity
            + 0.10 * linguistic_load
            + 0.15 * distractor_similarity
        )
        adjustment = {
            DifficultyBand.support: -0.30,
            DifficultyBand.core: 0.02,
            DifficultyBand.stretch: 0.18,
        }[requested_band]
        return round(min(max(score + adjustment, 0.0), 1.0), 2)

    def build_visual_payload(self, template: Template, variables: dict[str, Any]) -> VisualPayload | None:
        if template.rendering.visual_type == "fraction_bar":
            return VisualPayload(
                visual_type="fraction_bar",
                params={
                    "parts_total": variables["parts_total"],
                    "parts_shaded": variables["parts_shaded"],
                    "orientation": "horizontal",
                },
            )
        return None

    def build_options(
        self,
        question_type: QuestionType,
        answer: AnswerValue,
        distractors: list[str],
        rng: random.Random,
    ) -> list[str]:
        if question_type != QuestionType.multiple_choice:
            return []
        options = [answer.value, *distractors]
        rng.shuffle(options)
        return options

    def validate_variant(
        self,
        variant: GeneratedQuestionVariant,
        request: GenerationRequest,
        used_template_codes: list[str],
        used_family_ids: list[str],
        used_answer_values: list[str],
        used_signatures: set[str],
        current_item_count: int,
    ) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not variant.answer.value:
            errors.append("answer_not_null")
        if len(set(variant.distractors)) != len(variant.distractors):
            errors.append("no_duplicate_distractors")
        if variant.answer.value in variant.distractors:
            errors.append("correct_not_in_distractors")
        if variant.question_type == QuestionType.multiple_choice and len(set(variant.options)) != 4:
            errors.append("mcq_options_invalid")
        if "/" in variant.answer.value:
            _, denominator = variant.answer.value.split("/")
            if int(denominator) == 0:
                errors.append("no_division_by_zero")

        score = variant.metadata.estimated_difficulty_score
        if variant.difficulty == DifficultyBand.support and score > 0.39:
            errors.append("difficulty_in_band")
        elif variant.difficulty == DifficultyBand.core and not (0.40 <= score <= 0.69):
            errors.append("difficulty_in_band")
        elif variant.difficulty == DifficultyBand.stretch and score < 0.70:
            errors.append("difficulty_in_band")

        signature = self.build_variant_signature(variant)
        if signature in used_signatures:
            errors.append("duplicate_signature")
        if len(set(used_family_ids + [variant.family_id])) > 1 and len(used_family_ids) >= 2 and used_family_ids[-2:] == [variant.family_id, variant.family_id]:
            errors.append("family_consecutive_limit")
        if len(set(used_template_codes + [variant.template_id])) > 3 and (used_template_codes.count(variant.template_id) + 1) / max(current_item_count + 1, 1) > 0.30:
            errors.append("template_ratio_limit")
        if used_answer_values.count(variant.answer.value) >= 3:
            errors.append("repeated_answer_limit")
        if len(variant.question_text) > 160:
            errors.append("text_length_under_limit")
        if variant.question_type == QuestionType.visual and variant.visual_payload is None:
            errors.append("renderable_layout")
        if request.question_types and variant.question_type not in request.question_types:
            errors.append("question_type_disallowed")
        if score >= 0.35 and variant.difficulty == DifficultyBand.support:
            warnings.append("Difficulty close to upper support threshold")
        return ValidationResult(valid=not errors, errors=errors, warnings=warnings)

    def build_variant_signature(self, variant: GeneratedQuestionVariant) -> str:
        variable_signature = "|".join(f"{key}={value}" for key, value in sorted(variant.variables.items()))
        return f"{variant.template_id}|{variable_signature}"

    def sequence_section_items(self, items: list[GeneratedQuestionVariant]) -> list[GeneratedQuestionVariant]:
        return sorted(items, key=lambda item: item.metadata.estimated_difficulty_score)

    def build_answer_key(self, sections: list[SectionOutput]) -> list[AnswerKeyEntry]:
        answer_key: list[AnswerKeyEntry] = []
        number = 1
        for section in sections:
            for item in section.items:
                answer_key.append(
                    AnswerKeyEntry(
                        question_number=number,
                        question_id=item.question_id,
                        correct_answer=item.answer.value,
                        explanation=item.explanation,
                        skill_id=item.skill_id,
                        misconception_note=item.metadata.misconception_targets[0] if item.metadata.misconception_targets else None,
                    )
                )
                number += 1
        return answer_key







