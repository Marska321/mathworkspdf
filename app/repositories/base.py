from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.worksheet import RenderableWorksheet, Skill, Template, WorksheetBlueprint


class WorksheetRepository(ABC):
    @abstractmethod
    def get_skills(self) -> list[Skill]:
        raise NotImplementedError

    @abstractmethod
    def get_templates(self) -> list[Template]:
        raise NotImplementedError

    @abstractmethod
    def get_blueprints(self) -> list[WorksheetBlueprint]:
        raise NotImplementedError

    @abstractmethod
    def get_grade4_family_registry(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def get_grade4_family_coverage_map(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_generated_worksheet(
        self,
        worksheet: RenderableWorksheet,
        request_payload: dict[str, Any],
        status: str = "generated",
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_generated_worksheet(self, worksheet_id: str) -> dict[str, Any] | None:
        raise NotImplementedError
