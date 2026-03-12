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
