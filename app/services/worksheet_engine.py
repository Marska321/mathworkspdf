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
    MisconceptionDetail,
    QuestionMetadata,
    QuestionType,
    RenderableWorksheet,
    SectionOutput,
    Skill,
    TeacherNotes,
    Template,
    ValidationResult,
    VariableDefinition,
    VisualPayload,
    WorksheetBlueprint,
)
from app.services.misconception_catalog import get_misconception
from app.services.template_helpers import (
    HELPER_REGISTRY,
    adjacent_place_value,
    distractor_ignore_carry,
    expand_number_as_text,
    round_down_to_place,
    round_to_place_value,
    round_up_to_place,
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
        used_pattern_codes: list[str] = []
        used_answer_values: list[str] = []
        used_signatures: set[str] = set()
        sections: list[SectionOutput] = []

        for section in context.blueprint.sections:
            items: list[GeneratedQuestionVariant] = []
            while len(items) < section.target_count:
                template = self.choose_template(
                    context,
                    section,
                    used_template_codes,
                    used_family_ids,
                    used_pattern_codes,
                )
                variant = self.generate_valid_variant(
                    context=context,
                    template=template,
                    section=section,
                    used_template_codes=used_template_codes,
                    used_family_ids=used_family_ids,
                    used_answer_values=used_answer_values,
                    used_pattern_codes=used_pattern_codes,
                    used_signatures=used_signatures,
                    current_item_count=sum(len(sec.items) for sec in sections) + len(items),
                )
                items.append(variant)
                used_template_codes.append(template.template_id)
                used_family_ids.append(template.family_id)
                used_answer_values.append(variant.answer.value)
                used_pattern_codes.append(template.pattern_code or template.question_type.value)
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
        misconception_details = self.build_misconception_details(misconceptions)
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
                misconception_details=misconception_details,
            ),
        )

    def choose_template(
        self,
        context: EngineContext,
        section: BlueprintSection,
        used_template_codes: list[str],
        used_family_ids: list[str],
        used_pattern_codes: list[str],
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

        def template_rank(candidate: Template) -> tuple[int, int, int]:
            candidate_pattern = candidate.pattern_code or candidate.question_type.value
            family_penalty = 1 if len(used_family_ids) >= 2 and used_family_ids[-2:] == [candidate.family_id, candidate.family_id] else 0
            pattern_penalty = 1 if used_pattern_codes and used_pattern_codes[-1] == candidate_pattern else 0
            prior_usage = used_template_codes.count(candidate.template_id)
            return (family_penalty, pattern_penalty, prior_usage)

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
        used_pattern_codes: list[str],
        used_signatures: set[str],
        current_item_count: int,
    ) -> GeneratedQuestionVariant:
        for _ in range(self.settings.generation_max_attempts):
            variables = self.sample_variables(template, section.difficulty_bias, context.rng)
            variables = self.apply_derived_rules(template, variables)
            if not self.constraints_hold(template, variables):
                continue
            answer = self.compute_answer(template, variables)
            distractors = self.generate_distractors(template, variables, answer)
            options = self.build_options(template.question_type, answer, distractors, context.rng)
            difficulty_score = self.score_difficulty(template, variables, section.difficulty_bias)
            skill = next(skill for skill in context.target_skills if skill.skill_id == template.skill_id)
            misconception_details = self.build_misconception_details(template.misconception_targets)
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
                    misconception_details=misconception_details,
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
                used_pattern_codes=used_pattern_codes,
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
            variables: dict[str, Any] = {}
            stalled_rounds = 0
            while len(variables) < len(template.variable_schema) and stalled_rounds < 3:
                previous_count = len(variables)
                for name, definition in template.variable_schema.items():
                    if name in variables:
                        continue
                    sampled = self.sample_variable_value(name, definition, profile, variables, rng)
                    if sampled is not None:
                        variables[name] = sampled
                variables = self.apply_derived_rules(template, variables)
                stalled_rounds = stalled_rounds + 1 if len(variables) == previous_count else 0

            variables = self.apply_derived_rules(template, variables)
            if set(template.variable_schema).issubset(variables) and self.constraints_hold(template, variables):
                return variables

        raise WorksheetGenerationError(f"Unable to sample valid variables for {template.template_code}.")

    def sample_variable_value(
        self,
        name: str,
        definition: VariableDefinition,
        profile: dict[str, Any],
        variables: dict[str, Any],
        rng: random.Random,
    ) -> Any | None:
        values_key = f"{name}_values"
        range_key = f"{name}_range"
        allowed_key = f"allowed_{name}s"

        if values_key in profile:
            return rng.choice(profile[values_key])
        if range_key in profile:
            low, high = profile[range_key]
            if definition.type == "float":
                return round(rng.uniform(low, high), 2)
            return rng.randint(low, high)
        if definition.values:
            values = [value for value in definition.values if value in profile.get(allowed_key, definition.values)]
            return rng.choice(values or definition.values)
        if definition.type == "enum" and allowed_key in profile:
            return rng.choice(profile[allowed_key])
        if name in {"place", "answer_place"} and "allowed_places" in profile:
            return rng.choice(profile["allowed_places"])
        if name == "parts_shaded" and "parts_total" in variables:
            return rng.randint(1, variables["parts_total"] - 1)
        if name == "numerator" and "denominator" in variables:
            return rng.randint(1, variables["denominator"] - 1)
        if name == "remainder" and "b" in variables:
            return rng.randint(1, variables["b"] - 1)
        if definition.type == "string" and name.endswith("_csv"):
            source_name = name.removesuffix("_csv")
            if source_name in variables and isinstance(variables[source_name], list):
                return ", ".join(str(value) for value in variables[source_name])
        return None

    def apply_derived_rules(self, template: Template, variables: dict[str, Any]) -> dict[str, Any]:
        resolved = dict(variables)
        for constraint in template.constraints:
            if constraint.type != "derived":
                continue
            target, expression = [part.strip() for part in constraint.rule.split("=", maxsplit=1)]
            try:
                resolved[target] = self.evaluate_expression(expression, resolved)
            except NameError:
                continue
        return resolved

    def constraints_hold(self, template: Template, variables: dict[str, Any]) -> bool:
        resolved = self.apply_derived_rules(template, variables)
        for constraint in template.constraints:
            if constraint.type != "expression":
                continue
            if not bool(self.evaluate_expression(constraint.rule, resolved)):
                return False
        return True

    def evaluate_expression(self, expression: str, variables: dict[str, Any]) -> Any:
        return eval(expression, {"__builtins__": {}}, {**HELPER_REGISTRY, **variables})

    def compute_answer(self, template: Template, variables: dict[str, Any]) -> AnswerValue:
        formula = template.answer_formula
        resolved = self.apply_derived_rules(template, variables)
        if formula.type == "expression":
            value = self.evaluate_expression(formula.value or "", resolved)
            if isinstance(value, bool):
                return AnswerValue(value="True" if value else "False", format="text")
            if isinstance(value, (list, tuple)):
                return AnswerValue(value=", ".join(str(item) for item in value), format="text")
            return AnswerValue(value=str(value), format="integer" if isinstance(value, int) else "text")
        numerator = self.evaluate_expression(formula.numerator or "", resolved)
        denominator = self.evaluate_expression(formula.denominator or "", resolved)
        return AnswerValue(value=f"{numerator}/{denominator}", format="fraction")

    def generate_distractors(self, template: Template, variables: dict[str, Any], answer: AnswerValue) -> list[str]:
        if template.question_type != QuestionType.multiple_choice and not template.distractor_rules:
            return []
        distractors: list[str] = []
        for rule in template.distractor_rules:
            candidate = self.apply_distractor_rule(rule.type, variables, answer)
            if candidate and candidate != answer.value and candidate not in distractors:
                distractors.append(candidate)
        fallback_attempts = 0
        while len(distractors) < 3 and fallback_attempts < 8:
            fallback_attempts += 1
            fallback = self.fallback_distractor(template.template_code, variables, answer, fallback_attempts)
            if fallback != answer.value and fallback not in distractors:
                distractors.append(fallback)
        return distractors[:3]

    def apply_distractor_rule(
        self,
        rule_type: str,
        variables: dict[str, Any],
        answer: AnswerValue,
    ) -> str | None:
        if {"a", "b"}.issubset(variables):
            a = variables["a"]
            b = variables["b"]
            total = int(answer.value) if answer.value.lstrip('-').isdigit() else a + b
            if rule_type == "ignore_carry":
                return str(distractor_ignore_carry(a, b))
            if rule_type == "off_by_ten":
                return str(total + 10)
            if rule_type == "digit_reversal":
                return str(int(str(total)[::-1])) if total >= 10 else str(total)
            if rule_type == "off_by_one":
                return str(total - 1 if total > 1 else total + 1)
            if rule_type == "digit_concat_error":
                return f"{a // 10 + b // 10}{(a % 10) + (b % 10)}"
            if rule_type == "place_mix_error":
                return str((a // 10 + b % 10) * 10 + (a % 10 + b // 10))
            if rule_type == "subtract_reversed_digits":
                return str(abs((a % 10) - (b % 10)) + abs((a // 10) - (b // 10)) * 10)
            if rule_type == "place_mix_error_sub":
                return str(abs((a // 10) - (b % 10)) * 10 + abs((a % 10) - (b // 10)))
            if rule_type == "borrow_not_applied":
                return str((a // 10 - b // 10) * 10 + abs((a % 10) - (b % 10)))
            if rule_type == "forget_reduce_tens":
                return str(((a // 10) - (b // 10)) * 10 + (10 + (a % 10) - (b % 10)))
            if rule_type == "near_additive_error":
                return str(a + b)
            if rule_type == "factor_plus_factor":
                return str(a + b)
            if rule_type == "multiply_instead":
                return str(a * b)
            if rule_type == "subtract_instead":
                return str(max(0, a - b))


        if {"numerator", "denominator", "scale_factor"}.issubset(variables):
            numerator = variables["numerator"]
            denominator = variables["denominator"]
            scale_factor = variables["scale_factor"]
            if rule_type == "scale_denominator_only":
                return f"{numerator}/{denominator * scale_factor}"
            if rule_type == "add_to_both_fraction_terms":
                return f"{numerator + scale_factor}/{denominator + scale_factor}"
            if rule_type == "copy_fraction_terms":
                return f"{numerator}/{denominator}"
        if {"parts_total", "parts_shaded"}.issubset(variables):
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

        if "correct_value" in variables:
            correct_value = int(variables["correct_value"])
            if rule_type == "digit_only":
                return str(variables.get("digit", correct_value))
            if rule_type == "neighbor_place_value":
                return str(adjacent_place_value(correct_value))
            if rule_type == "zero_append_error":
                return str(correct_value * 10) if correct_value < 1000 else str(max(1, correct_value // 10))

        if "digit" in variables and "answer_place" in variables:
            place_names = ["ones", "tens", "hundreds", "thousands"]
            current = variables["answer_place"]
            if rule_type == "neighbor_place_name" and current in place_names:
                index = place_names.index(current)
                return place_names[max(0, index - 1)] if index == len(place_names) - 1 else place_names[index + 1]


        if {"number", "round_to_place"}.issubset(variables):
            number = variables["number"]
            round_to_place = variables["round_to_place"]
            if rule_type == "round_down_place":
                return str(round_down_to_place(number, round_to_place))
            if rule_type == "round_up_place":
                return str(round_up_to_place(number, round_to_place))
            if rule_type == "wrong_place_rounding":
                adjacent_place = {"tens": "hundreds", "hundreds": "tens", "thousands": "hundreds"}.get(round_to_place, "tens")
                return str(round_to_place_value(number, adjacent_place))

        if {"a", "b", "total"}.issubset(variables):
            a = variables["a"]
            b = variables["b"]
            total = variables["total"]
            if rule_type == "use_product_as_factor":
                return str(total)
            if rule_type == "additive_factor_error":
                additive_guess = total - a
                if additive_guess != b and additive_guess > 0:
                    return str(additive_guess)
                return str(a + b)
            if rule_type == "off_by_one_factor":
                return str(b + 1 if b < 12 else max(1, b - 1))

        if {"a", "b", "quotient", "remainder"}.issubset(variables):
            quotient = variables["quotient"]
            remainder = variables["remainder"]
            divisor = variables["b"]
            if rule_type == "ignore_remainder_value":
                return str(quotient)
            if rule_type == "use_divisor_as_remainder_value":
                return f"{quotient} remainder {divisor}"
            if rule_type == "round_up_quotient_remainder_value":
                return f"{quotient + 1} remainder 0"
        if rule_type == "other_fraction_in_pair" and {"numerator", "left_denominator", "right_denominator"}.issubset(variables):
            left_fraction = f"{variables['numerator']}/{variables['left_denominator']}"
            right_fraction = f"{variables['numerator']}/{variables['right_denominator']}"
            return right_fraction if answer.value == left_fraction else left_fraction

        if rule_type == "simplify_numerator_only" and {"base_numerator", "denominator"}.issubset(variables):
            return f"{variables['base_numerator']}/{variables['denominator']}"

        if rule_type == "simplify_denominator_only" and {"numerator", "base_denominator"}.issubset(variables):
            return f"{variables['numerator']}/{variables['base_denominator']}"

        if rule_type == "keep_unsimplified_fraction" and {"numerator", "denominator"}.issubset(variables):
            return f"{variables['numerator']}/{variables['denominator']}"

        if rule_type == "one_part_only" and {"unit_size"}.issubset(variables):
            return str(variables['unit_size'])

        if rule_type == "use_denominator_value" and {"denominator"}.issubset(variables):
            return str(variables['denominator'])

        if rule_type == "use_whole_set_value" and {"total_objects"}.issubset(variables):
            return str(variables['total_objects'])

        if rule_type == "unit_fraction_same_denominator" and "/" in answer.value:
            numerator, denominator = [int(part) for part in answer.value.split("/")]
            unit_numerator = 2 if numerator == 1 and denominator > 2 else 1
            return f"{unit_numerator}/{denominator}"

        if rule_type == "neighbor_numerator_same_denominator" and "/" in answer.value:
            numerator, denominator = [int(part) for part in answer.value.split("/")]
            if numerator + 1 < denominator:
                return f"{numerator + 1}/{denominator}"
            return f"{max(1, numerator - 1)}/{denominator}"

        if {"a", "b"}.issubset(variables) and rule_type == "flip_compare_symbol":
            compare_map = {">": "<", "<": ">", "=": "="}
            return compare_map.get(answer.value)

        if {"left_numerator", "right_numerator", "denominator"}.issubset(variables) and rule_type == "flip_compare_symbol":
            compare_map = {">": "<", "<": ">", "=": "="}
            return compare_map.get(answer.value)

        if {"a", "b", "c"}.issubset(variables) and rule_type == "reverse_order_csv":
            return ", ".join(str(value) for value in sorted([variables["a"], variables["b"], variables["c"]], reverse=True))

        if {"a", "b", "c", "d"}.issubset(variables) and rule_type == "other_values":
            other_values = [variables["a"], variables["b"], variables["c"], variables["d"]]
            for value in sorted(other_values, reverse=True):
                if str(value) != answer.value:
                    return str(value)
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
        if template_code.startswith("add_noregroup"):
            return str(int(answer.value) + offset)
        if template_code.startswith("sub_regroup"):
            return str(max(0, int(answer.value) + offset))
        if template_code.startswith("sub_noregroup"):
            return str(max(0, int(answer.value) + offset))
        if template_code.startswith("mult_facts"):
            return str(int(answer.value) + offset)
        if template_code.startswith("div_facts"):
            return str(max(1, int(float(answer.value)) + offset))
        if template_code.startswith("div_remainder") and answer.value.isdigit():
            return str(max(1, int(answer.value) + offset))
        if template_code.startswith("mult_missing_factor") and answer.value.isdigit():
            return str(max(1, int(answer.value) + offset))
        if template_code.startswith("rounding") and answer.value.isdigit():
            return str(int(answer.value) + offset * 10)
        if template_code.startswith("fraction_compare") and "/" in answer.value:
            numerator, denominator = answer.value.split("/")
            return f"{numerator}/{max(int(numerator) + 1, int(denominator) + offset)}"
        if template_code.startswith("fraction_equivalent") and answer.format == "fraction":
            numerator, denominator = answer.value.split("/")
            return f"{max(1, int(numerator) + offset)}/{max(2, int(denominator) + offset)}"
        if template_code.startswith("expanded_") and answer.value.isdigit():
            return str(int(answer.value) + offset)
        if answer.format == "fraction":
            numerator, denominator = answer.value.split("/")
            return f"{max(1, int(numerator) + offset)}/{denominator}"
        if answer.format == "integer" and answer.value.lstrip('-').isdigit():
            return str(int(answer.value) + offset)
        text_fallbacks = {
            ">": "<",
            "<": ">",
            "=": ">",
            "ones": "tens",
            "tens": "hundreds",
            "hundreds": "thousands",
            "thousands": "hundreds",
            "True": "False",
            "False": "True",
        }
        return text_fallbacks.get(answer.value, f"{answer.value} (check)")

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
        elif template.template_code.startswith("fraction_compare"):
            denominator = max(variables.get("denominator", 0), variables.get("left_denominator", 0), variables.get("right_denominator", 0))
            number_complexity = min(denominator / 12, 1.0)
            structure_complexity = 0.36 if template.question_type == QuestionType.multiple_choice else 0.4
            representation_complexity = 0.24
            linguistic_load = 0.08
            distractor_similarity = 0.42
        elif template.template_code.startswith("fraction_simplify"):
            denominator = variables["denominator"]
            number_complexity = min(denominator / 16, 1.0)
            structure_complexity = 0.36 if template.question_type == QuestionType.multiple_choice else 0.4
            representation_complexity = 0.26
            linguistic_load = 0.08
            distractor_similarity = 0.44
        elif template.template_code.startswith("fraction_of_set"):
            total_objects = variables["total_objects"]
            number_complexity = min(total_objects / 40, 1.0)
            structure_complexity = 0.34 if template.question_type == QuestionType.multiple_choice else 0.4
            representation_complexity = 0.22
            linguistic_load = 0.08
            distractor_similarity = 0.4
        elif template.template_code.startswith("fraction_equivalent"):
            denominator = variables["denominator"]
            number_complexity = min(denominator / 12, 1.0)
            structure_complexity = 0.38 if template.question_type == QuestionType.multiple_choice else 0.42
            representation_complexity = 0.28
            linguistic_load = 0.08
            distractor_similarity = 0.45
        elif template.template_code.startswith("fraction_partwhole"):
            denominator = variables["parts_total"]
            number_complexity = min(denominator / 12, 1.0)
            structure_complexity = 0.35
            representation_complexity = 0.65 if template.question_type == QuestionType.visual else 0.4
            linguistic_load = 0.08
            distractor_similarity = 0.5
        elif template.template_code.startswith("pv_identify"):
            number_complexity = min(len(str(variables["number"])) / 4, 1.0)
            structure_complexity = 0.25 if template.question_type == QuestionType.direct else 0.35
            representation_complexity = 0.2
            linguistic_load = 0.08
            distractor_similarity = 0.4
        elif template.template_code.startswith("expanded_"):
            number_complexity = min(len(str(variables["number"])) / 4, 1.0)
            structure_complexity = 0.3
            representation_complexity = 0.3
            linguistic_load = 0.1
            distractor_similarity = 0.2
        elif template.template_code.startswith("add_noregroup"):
            max_number = max(variables["a"], variables.get("b", 0), variables.get("sum", 0))
            number_complexity = min(max_number / 500, 1.0)
            structure_complexity = 0.3 if template.question_type == QuestionType.direct else 0.4
            representation_complexity = 0.15 if template.question_type != QuestionType.word_problem else 0.25
            linguistic_load = 0.06 if template.question_type != QuestionType.word_problem else 0.16
            distractor_similarity = 0.3
        elif template.template_code.startswith("sub_noregroup"):
            max_number = max(variables["a"], variables.get("b", 0), variables.get("difference", 0))
            number_complexity = min(max_number / 500, 1.0)
            structure_complexity = 0.32 if template.question_type == QuestionType.direct else 0.42
            representation_complexity = 0.15 if template.question_type != QuestionType.word_problem else 0.25
            linguistic_load = 0.06 if template.question_type != QuestionType.word_problem else 0.16
            distractor_similarity = 0.3
        elif template.template_code.startswith("sub_regroup"):
            max_number = max(variables["a"], variables.get("b", 0), variables.get("wrong_answer", 0))
            number_complexity = min(max_number / 500, 1.0)
            structure_complexity = 0.42 if template.question_type in {QuestionType.direct, QuestionType.fill_blank} else 0.5
            representation_complexity = 0.18 if template.question_type != QuestionType.word_problem else 0.28
            linguistic_load = 0.08 if template.question_type != QuestionType.word_problem else 0.18
            distractor_similarity = 0.42
        elif template.template_code.startswith("div_remainder"):
            max_number = max(variables.get("a", 0), variables.get("b", 0), variables.get("quotient", 0))
            number_complexity = min(max_number / 120, 1.0)
            structure_complexity = 0.42 if template.question_type == QuestionType.multiple_choice else 0.48
            representation_complexity = 0.22
            linguistic_load = 0.07
            distractor_similarity = 0.45
        elif template.template_code.startswith("mult_missing_factor"):
            max_number = max(variables.get("a", 0), variables.get("b", 0), variables.get("total", 0))
            number_complexity = min(max_number / 120, 1.0)
            structure_complexity = 0.4 if template.question_type == QuestionType.multiple_choice else 0.46
            representation_complexity = 0.2
            linguistic_load = 0.06
            distractor_similarity = 0.42
        elif template.template_code.startswith("mult_facts"):
            max_number = max(variables.get("a", 0), variables.get("b", 0), variables.get("rows", 0), variables.get("cols", 0))
            number_complexity = min(max_number / 12, 1.0)
            structure_complexity = 0.28 if template.question_type == QuestionType.direct else 0.38
            representation_complexity = 0.2 if template.question_type == QuestionType.direct else 0.55
            linguistic_load = 0.05
            distractor_similarity = 0.28
        elif template.template_code.startswith("div_facts"):
            max_number = max(variables.get("a", 0), variables.get("b", 0), variables.get("sampled_quotient", 0))
            number_complexity = min(max_number / 120, 1.0)
            structure_complexity = 0.32 if template.question_type == QuestionType.direct else 0.4
            representation_complexity = 0.18 if template.question_type == QuestionType.direct else 0.28
            linguistic_load = 0.06 if template.question_type == QuestionType.direct else 0.16
            distractor_similarity = 0.3
        elif template.template_code.startswith("compare_order"):
            max_number = max(value for key, value in variables.items() if key in {"a", "b", "c", "d"})
            number_complexity = min(max_number / 9999, 1.0)
            structure_complexity = 0.45 if template.question_type == QuestionType.sequence else 0.3
            representation_complexity = 0.2
            linguistic_load = 0.08
            distractor_similarity = 0.35
        elif template.template_code.startswith("rounding"):
            max_number = variables.get("number", 0)
            number_complexity = min(max_number / 9999, 1.0)
            structure_complexity = 0.42 if template.question_type == QuestionType.multiple_choice else 0.5
            representation_complexity = 0.18
            linguistic_load = 0.08
            distractor_similarity = 0.45
        else:
            number_complexity = 0.3
            structure_complexity = 0.3
            representation_complexity = 0.2
            linguistic_load = 0.08
            distractor_similarity = 0.3

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
        if template.rendering.visual_type == "fraction_bar_blank":
            return VisualPayload(
                visual_type="fraction_bar_blank",
                params={
                    "parts_total": variables["denominator"],
                    "orientation": "horizontal",
                },
            )
        if template.rendering.visual_type == "array_grid":
            return VisualPayload(
                visual_type="array_grid",
                params={
                    "rows": variables["rows"],
                    "cols": variables["cols"],
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
        used_pattern_codes: list[str],
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

    def build_misconception_details(self, codes: list[str]) -> list[MisconceptionDetail]:
        details: list[MisconceptionDetail] = []
        for code in codes:
            payload = get_misconception(code)
            if not payload:
                continue
            details.append(
                MisconceptionDetail(
                    code=payload['code'],
                    name=payload['name'],
                    description=payload['description'],
                    distractor_strategy=payload.get('distractor_strategy'),
                )
            )
        return details

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





