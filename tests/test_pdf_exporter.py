from pathlib import Path

from app.services.pdf_exporter import WorksheetPdfExporter


PROJECT_ROOT = Path(r"C:\Users\User\Downloads\mathworkspdf")


def test_pdf_exporter_builds_output_path() -> None:
    exporter = WorksheetPdfExporter(PROJECT_ROOT)
    path = exporter.build_output_path("ws_test")
    assert path.name == "ws_test.pdf"
    assert "output" in str(path)
    assert "pdf" in str(path)


def test_pdf_exporter_builds_teacher_mode_html_url() -> None:
    exporter = WorksheetPdfExporter(PROJECT_ROOT)
    url = exporter.build_html_url("ws_test", "http://localhost:8000", teacher_mode=True)
    assert url == "http://localhost:8000/api/worksheets/ws_test/html?teacher_mode=true"


def test_pdf_exporter_can_render_raw_html(monkeypatch, tmp_path: Path) -> None:
    exporter = WorksheetPdfExporter(PROJECT_ROOT)
    output_path = tmp_path / "visual_smoke.pdf"
    recorded: dict[str, object] = {}

    def fake_run_render_command(source_url: str, resolved_output: Path) -> None:
        recorded["source_url"] = source_url
        recorded["output_path"] = resolved_output
        resolved_output.write_text("pdf", encoding="utf-8")

    monkeypatch.setattr(exporter, "_run_render_command", fake_run_render_command)

    result = exporter.render_raw_html("<html><body>pilot</body></html>", output_path)

    assert result == output_path
    assert output_path.read_text(encoding="utf-8") == "pdf"
    assert str(recorded["source_url"]).startswith("file:///")
    assert recorded["output_path"] == output_path
    assert not list(tmp_path.glob("*.html"))
