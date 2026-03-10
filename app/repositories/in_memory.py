from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.repositories.base import WorksheetRepository
from app.schemas.worksheet import RenderableWorksheet, Skill, Template, WorksheetBlueprint
from app.templates.loader import load_template_library


class InMemoryWorksheetRepository(WorksheetRepository):
    def __init__(self) -> None:
        library = load_template_library()
        self._skills = [Skill.model_validate(item) for item in library["skills"]]
        self._templates = [Template.model_validate(item) for item in library["templates"]]
        self._blueprints = [WorksheetBlueprint.model_validate(item) for item in library["blueprints"]]
        self._generated: dict[str, dict[str, Any]] = {}

    def get_skills(self) -> list[Skill]:
        return deepcopy(self._skills)

    def get_templates(self) -> list[Template]:
        return deepcopy(self._templates)

    def get_blueprints(self) -> list[WorksheetBlueprint]:
        return deepcopy(self._blueprints)

    def save_generated_worksheet(
        self,
        worksheet: RenderableWorksheet,
        request_payload: dict[str, Any],
        status: str = "generated",
    ) -> None:
        self._generated[worksheet.worksheet_id] = {
            "worksheet_id": worksheet.worksheet_id,
            "status": status,
            "request_json": deepcopy(request_payload),
            "worksheet_json": worksheet.model_dump(mode="json"),
            "answer_key_json": [entry.model_dump(mode="json") for entry in worksheet.answer_key],
        }

    def get_generated_worksheet(self, worksheet_id: str) -> dict[str, Any] | None:
        record = self._generated.get(worksheet_id)
        return deepcopy(record) if record else None
