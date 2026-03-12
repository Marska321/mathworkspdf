from pathlib import Path


def test_generate_and_fetch_worksheet(client) -> None:
    payload = {
        "grade": 4,
        "term": 1,
        "strand": "Number, Operations and Relationships",
        "topic": "Fractions",
        "subskill": "Fractions as part of a whole",
        "worksheet_type": "concept",
        "question_count": 5,
        "difficulty": "support",
        "include_challenge_section": False,
        "seed": "api-seed",
    }
    response = client.post("/api/worksheets/generate", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "generated"
    assert len(body["worksheet_json"]["sections"]) >= 1
    assert len(body["answer_key_json"]) == 5

    worksheet_id = body["worksheet_id"]
    fetch = client.get(f"/api/worksheets/{worksheet_id}")
    assert fetch.status_code == 200
    saved = fetch.json()
    assert saved["worksheet_id"] == worksheet_id
    assert saved["worksheet_json"]["worksheet_id"] == worksheet_id

    html = client.get(f"/api/worksheets/{worksheet_id}/html")
    assert html.status_code == 200
    assert "text/html" in html.headers["content-type"]
    assert "Grade 4 Fractions Practice" in html.text
    assert "fraction-bar" in html.text
    assert "Name:" in html.text
    assert "Date:" in html.text
    assert "answer-key-page" in html.text
    assert "Teacher Notes" not in html.text
    assert "Teacher note:" not in html.text

    teacher_html = client.get(f"/api/worksheets/{worksheet_id}/html?teacher_mode=true")
    assert teacher_html.status_code == 200
    assert "Teacher Notes" in teacher_html.text
    assert "Teacher note:" in teacher_html.text
    assert "Misconceptions targeted:" in teacher_html.text

    pdf = client.get(f"/api/worksheets/{worksheet_id}/pdf")
    assert pdf.status_code in {200, 503}


def test_pdf_endpoint_propagates_teacher_mode(client, monkeypatch, tmp_path) -> None:
    payload = {
        "grade": 4,
        "term": 1,
        "strand": "Number, Operations and Relationships",
        "topic": "Fractions",
        "subskill": "Fractions as part of a whole",
        "worksheet_type": "concept",
        "question_count": 5,
        "difficulty": "support",
        "include_challenge_section": False,
        "seed": "pdf-teacher-mode-seed",
    }
    response = client.post("/api/worksheets/generate", json=payload)
    assert response.status_code == 201
    worksheet_id = response.json()["worksheet_id"]

    pdf_path = tmp_path / "teacher-mode.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%stub\n")
    calls: list[dict[str, object]] = []

    def fake_render(worksheet_id: str, base_url: str, teacher_mode: bool = False) -> Path:
        calls.append(
            {
                "worksheet_id": worksheet_id,
                "base_url": base_url,
                "teacher_mode": teacher_mode,
            }
        )
        return pdf_path

    monkeypatch.setattr("app.api.worksheets.pdf_exporter.render", fake_render)

    pdf = client.get(f"/api/worksheets/{worksheet_id}/pdf?teacher_mode=true")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert calls == [
        {
            "worksheet_id": worksheet_id,
            "base_url": "http://testserver",
            "teacher_mode": True,
        }
    ]

from uuid import uuid4

from fastapi import HTTPException

from app.core.config import Settings
from app.core.dependencies import get_mastery_tracker
from app.main import app


class StubMasteryTracker:
    def __init__(self, assigned_difficulty: str, has_history: bool = True) -> None:
        self.assigned_difficulty = assigned_difficulty
        self.has_history = has_history

    def get_mastery_record(self, student_id, skill_id):
        if not self.has_history:
            return None
        return {
            "student_id": str(student_id),
            "skill_id": skill_id,
            "mastery_score": 92 if self.assigned_difficulty == "advanced" else 72,
            "status": "mastered" if self.assigned_difficulty == "advanced" else "learning",
            "last_assessed_at": "2026-03-13T10:00:00+00:00",
        }

    def evaluate_next_step(self, student_id, target_skill_id):
        return self.assigned_difficulty

    def update_score(self, student_id, skill_id, latest_score):
        return {
            "student_id": str(student_id),
            "skill_id": skill_id,
            "mastery_score": latest_score,
            "status": "mastered" if latest_score >= 85 else ("remediation" if latest_score < 60 else "learning"),
            "last_assessed_at": "2026-03-13T10:00:00+00:00",
        }


def test_adaptive_generate_uses_target_skill_and_mastery_decision(client, monkeypatch) -> None:
    tracker = StubMasteryTracker("advanced", has_history=True)
    monkeypatch.setitem(app.dependency_overrides, get_mastery_tracker, lambda: tracker)

    payload = {
        "student_id": str(uuid4()),
        "target_skill_id": "fraction_partwhole_g4_01",
        "generation": {
            "worksheet_type": "concept",
            "question_count": 5,
            "question_types": ["visual", "multiple_choice"],
            "seed": "adaptive-api-seed"
        },
    }

    response = client.post("/api/worksheets/generate/adaptive", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["metadata"]["assigned_difficulty"] == "advanced"
    assert body["metadata"]["generation_difficulty"] == "stretch"
    assert body["metadata"]["status"] == "mastered"
    assert body["worksheet_id"] == body["worksheet"]["worksheet_id"]
    assert body["worksheet"]["metadata"]["topic"] == "Fractions"
    assert body["worksheet"]["metadata"]["subskill"] == "Fractions as part of a whole"
    assert body["worksheet"]["metadata"]["difficulty"] == "stretch"
    assert body["links"]["pdf_download"] == f"/api/worksheets/{body['worksheet_id']}/pdf"
    assert body["links"]["html_preview"] == f"/api/worksheets/{body['worksheet_id']}/html"


def test_adaptive_generate_returns_404_for_unknown_skill(client, monkeypatch) -> None:
    monkeypatch.setitem(app.dependency_overrides, get_mastery_tracker, lambda: StubMasteryTracker("core"))

    payload = {
        "student_id": str(uuid4()),
        "target_skill_id": "missing_skill",
        "generation": {
            "worksheet_type": "concept",
            "question_count": 5,
            "seed": "adaptive-missing-skill"
        },
    }

    response = client.post("/api/worksheets/generate/adaptive", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Target skill not found."


def test_grade_mastery_returns_updated_snapshot(client, monkeypatch) -> None:
    monkeypatch.setitem(app.dependency_overrides, get_mastery_tracker, lambda: StubMasteryTracker("core"))

    payload = {
        "student_id": str(uuid4()),
        "skill_id": "fraction_partwhole_g4_01",
        "latest_score": 91,
    }

    response = client.post("/api/mastery/grade", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["skill_id"] == payload["skill_id"]
    assert body["mastery_score"] == 91
    assert body["status"] == "mastered"
    assert body["last_assessed_at"].startswith("2026-03-13T10:00:00")


def test_grade_mastery_validates_score_bounds(client, monkeypatch) -> None:
    monkeypatch.setitem(app.dependency_overrides, get_mastery_tracker, lambda: StubMasteryTracker("core"))

    payload = {
        "student_id": str(uuid4()),
        "skill_id": "fraction_partwhole_g4_01",
        "latest_score": 101,
    }

    response = client.post("/api/mastery/grade", json=payload)

    assert response.status_code == 422


def test_adaptive_generate_returns_503_when_mastery_tracking_is_unconfigured(client, monkeypatch) -> None:
    monkeypatch.delitem(app.dependency_overrides, get_mastery_tracker, raising=False)
    monkeypatch.setattr(
        "app.core.dependencies.get_settings",
        lambda: Settings(supabase_url=None, supabase_service_key=None, supabase_publishable_key=None),
    )

    payload = {
        "student_id": str(uuid4()),
        "target_skill_id": "fraction_partwhole_g4_01",
        "generation": {
            "worksheet_type": "concept",
            "question_count": 5,
            "seed": "adaptive-no-config"
        },
    }

    response = client.post("/api/worksheets/generate/adaptive", json=payload)

    assert response.status_code == 503
    assert "Mastery tracking requires" in response.json()["detail"]
