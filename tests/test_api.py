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

    pdf = client.get(f"/api/worksheets/{worksheet_id}/pdf")
    assert pdf.status_code in {200, 503}
