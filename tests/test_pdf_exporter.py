from pathlib import Path

from app.services.pdf_exporter import WorksheetPdfExporter


def test_pdf_exporter_builds_output_path() -> None:
    exporter = WorksheetPdfExporter(Path(r"C:\Users\User\Downloads\mathworkspdf"))
    path = exporter.build_output_path("ws_test")
    assert path.name == "ws_test.pdf"
    assert "output" in str(path)
    assert "pdf" in str(path)
