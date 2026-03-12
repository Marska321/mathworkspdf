from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

import httpx


class MasteryTrackerError(RuntimeError):
    pass


class MasteryTracker:
    def __init__(self, url: str, service_key: str) -> None:
        self.base_url = url.rstrip("/")
        self.service_key = service_key
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        }

    def _rest_url(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    def _get_rows(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            response = httpx.get(self._rest_url(table), headers=self.headers, params=params, timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MasteryTrackerError(f"Unable to read mastery data from Supabase: {exc}") from exc

        payload = response.json()
        if not isinstance(payload, list):
            raise MasteryTrackerError("Supabase returned an unexpected mastery response payload.")
        return payload

    def _upsert_row(self, table: str, payload: dict[str, Any], on_conflict: str) -> dict[str, Any] | None:
        headers = {
            **self.headers,
            "Prefer": "resolution=merge-duplicates,return=representation",
        }
        try:
            response = httpx.post(
                self._rest_url(table),
                headers=headers,
                params={"on_conflict": on_conflict},
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MasteryTrackerError(f"Unable to write mastery data to Supabase: {exc}") from exc

        data = response.json()
        if isinstance(data, list):
            return data[0] if data else None
        if isinstance(data, dict):
            return data
        return None

    @staticmethod
    def _status_for_score(score: int) -> Literal["learning", "remediation", "mastered"]:
        if score >= 85:
            return "mastered"
        if score < 60:
            return "remediation"
        return "learning"

    def get_mastery_record(self, student_id: UUID | str, skill_id: str) -> dict[str, Any] | None:
        rows = self._get_rows(
            "student_mastery",
            {
                "select": "*",
                "student_id": f"eq.{student_id}",
                "skill_id": f"eq.{skill_id}",
                "limit": 1,
            },
        )
        return rows[0] if rows else None

    def evaluate_next_step(
        self,
        student_id: UUID | str,
        target_skill_id: str,
    ) -> Literal["advanced", "core", "remediation"]:
        record = self.get_mastery_record(student_id, target_skill_id)
        if not record:
            return "core"

        score = int(record["mastery_score"])
        if score >= 85:
            return "advanced"
        if score < 60:
            return "remediation"
        return "core"

    def update_score(self, student_id: UUID | str, skill_id: str, latest_score: int) -> dict[str, Any]:
        status = self._status_for_score(latest_score)
        assessed_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "student_id": str(student_id),
            "skill_id": skill_id,
            "mastery_score": latest_score,
            "status": status,
            "last_assessed_at": assessed_at,
        }
        record = self._upsert_row("student_mastery", payload, "student_id,skill_id")
        if record is None:
            record = self.get_mastery_record(student_id, skill_id) or payload
        return record
