from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import pytest

from app.services.mastery_tracker import MasteryTracker


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://example.test")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("request failed", request=self.request, response=httpx.Response(self.status_code, request=self.request))

    def json(self) -> Any:
        return self._payload


def test_evaluate_next_step_defaults_to_core_without_history(monkeypatch: pytest.MonkeyPatch) -> None:
    tracker = MasteryTracker("https://example.supabase.co", "service-key")

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse([])

    monkeypatch.setattr("app.services.mastery_tracker.httpx.get", fake_get)

    assert tracker.evaluate_next_step(uuid4(), "fraction_partwhole_g4_01") == "core"


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (59, "remediation"),
        (60, "core"),
        (84, "core"),
        (85, "advanced"),
    ],
)
def test_evaluate_next_step_uses_thresholds(
    monkeypatch: pytest.MonkeyPatch,
    score: int,
    expected: str,
) -> None:
    tracker = MasteryTracker("https://example.supabase.co", "service-key")

    def fake_get(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse([
            {
                "student_id": str(uuid4()),
                "skill_id": "fraction_partwhole_g4_01",
                "mastery_score": score,
                "status": "learning",
                "last_assessed_at": "2026-03-13T10:00:00+00:00",
            }
        ])

    monkeypatch.setattr("app.services.mastery_tracker.httpx.get", fake_get)

    assert tracker.evaluate_next_step(uuid4(), "fraction_partwhole_g4_01") == expected


@pytest.mark.parametrize(
    ("latest_score", "expected_status"),
    [
        (40, "remediation"),
        (72, "learning"),
        (95, "mastered"),
    ],
)
def test_update_score_upserts_latest_mastery(
    monkeypatch: pytest.MonkeyPatch,
    latest_score: int,
    expected_status: str,
) -> None:
    tracker = MasteryTracker("https://example.supabase.co", "service-key")
    student_id = uuid4()
    captured: dict[str, Any] = {}

    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        captured["params"] = kwargs["params"]
        captured["json"] = kwargs["json"]
        payload = dict(kwargs["json"])
        payload["id"] = str(uuid4())
        return FakeResponse([payload])

    monkeypatch.setattr("app.services.mastery_tracker.httpx.post", fake_post)

    record = tracker.update_score(student_id, "fraction_partwhole_g4_01", latest_score)

    assert captured["params"]["on_conflict"] == "student_id,skill_id"
    assert captured["json"]["student_id"] == str(student_id)
    assert captured["json"]["skill_id"] == "fraction_partwhole_g4_01"
    assert captured["json"]["mastery_score"] == latest_score
    assert captured["json"]["status"] == expected_status
    assert record["status"] == expected_status
