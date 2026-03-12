from __future__ import annotations

from copy import deepcopy
from typing import Any

import httpx

from app.repositories.base import WorksheetRepository
from app.schemas.worksheet import RenderableWorksheet, Skill, Template, WorksheetBlueprint
from app.templates.loader import load_template_library


class SupabaseWorksheetRepository(WorksheetRepository):
    def __init__(self, url: str, key: str) -> None:
        self.base_url = url.rstrip("/")
        self.key = key
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    def _rest_url(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    def _get(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        response = httpx.get(self._rest_url(table), headers=self.headers, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def _upsert(self, table: str, payload: list[dict[str, Any]] | dict[str, Any], on_conflict: str) -> None:
        headers = {
            **self.headers,
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        response = httpx.post(
            self._rest_url(table),
            headers=headers,
            params={"on_conflict": on_conflict},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()

    def get_skills(self) -> list[Skill]:
        rows = self._get("skills", {"select": "*", "active": "eq.true"})
        return [Skill.model_validate(row) for row in rows]

    def get_templates(self) -> list[Template]:
        rows = self._get("templates", {"select": "*", "active": "eq.true"})
        return [Template.model_validate(row) for row in rows]

    def get_blueprints(self) -> list[WorksheetBlueprint]:
        rows = self._get("worksheet_blueprints", {"select": "*", "active": "eq.true"})
        return [WorksheetBlueprint.model_validate(row["structure_json"]) for row in rows]

    def get_grade4_family_registry(self) -> list[dict[str, Any]]:
        return deepcopy(load_template_library()["grade4_family_registry"])

    def get_grade4_family_coverage_map(self) -> list[dict[str, Any]]:
        return deepcopy(load_template_library()["grade4_family_coverage_map"])

    def save_generated_worksheet(
        self,
        worksheet: RenderableWorksheet,
        request_payload: dict[str, Any],
        status: str = "generated",
    ) -> None:
        worksheet_payload = {
            "id": worksheet.worksheet_id,
            "request_json": request_payload,
            "output_json": worksheet.model_dump(mode="json"),
            "status": status,
        }
        self._upsert("generated_worksheets", worksheet_payload, "id")

        question_rows = []
        position = 1
        for section in worksheet.sections:
            for item in section.items:
                question_rows.append(
                    {
                        "id": item.question_id,
                        "worksheet_id": worksheet.worksheet_id,
                        "template_id": item.template_id,
                        "skill_id": item.skill_id,
                        "question_position": position,
                        "question_json": item.model_dump(mode="json"),
                        "answer_json": item.answer.model_dump(mode="json"),
                        "metadata_json": item.metadata.model_dump(mode="json"),
                    }
                )
                position += 1
        if question_rows:
            self._upsert("generated_questions", question_rows, "id")

    def get_generated_worksheet(self, worksheet_id: str) -> dict[str, Any] | None:
        rows = self._get(
            "generated_worksheets",
            {"select": "*", "id": f"eq.{worksheet_id}", "limit": 1},
        )
        if not rows:
            return None
        row = rows[0]
        worksheet_json = row["output_json"]
        return {
            "worksheet_id": worksheet_id,
            "status": row["status"],
            "request_json": row["request_json"],
            "worksheet_json": worksheet_json,
            "answer_key_json": worksheet_json.get("answer_key", []),
        }

    def check_connection(self) -> int:
        rows = self._get("skills", {"select": "skill_id", "limit": 1})
        return len(rows)

    def seed_table(self, table: str, payload: list[dict[str, Any]] | dict[str, Any], on_conflict: str) -> None:
        self._upsert(table, payload, on_conflict)

    def fetch_misconceptions(self) -> list[dict[str, Any]]:
        return self._get("misconceptions", {"select": "id,code"})
