from pathlib import Path

from app.services.pdf_exporter import WorksheetPdfExporter


def test_pdf_exporter_builds_output_path() -> None:
    exporter = WorksheetPdfExporter(Path(r"C:\Users\User\Downloads\mathworkspdf"))
    path = exporter.build_output_path("ws_test")
    assert path.name == "ws_test.pdf"
    assert "output" in str(path)
    assert "pdf" in str(path)


def test_pdf_exporter_builds_teacher_mode_html_url() -> None:
    exporter = WorksheetPdfExporter(Path(r"C:\Users\User\Downloads\mathworkspdf"))
    url = exporter.build_html_url("ws_test", "http://localhost:8000", teacher_mode=True)
    assert url == "http://localhost:8000/api/worksheets/ws_test/html?teacher_mode=true"
