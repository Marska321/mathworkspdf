from pathlib import Path

from app.services.html_renderer import WorksheetHtmlRenderer
from app.services.pdf_exporter import WorksheetPdfExporter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "manual_visual_checks"


def build_mock_worksheet() -> dict:
    return {
        "title": "Mastery Check: Visuals Pilot",
        "subtitle": "Grade 4 Foundation",
        "metadata": {
            "curriculum": "CAPS",
            "grade": 4,
            "term": 1,
            "topic": "Visual Models",
            "subskill": "SVG smoke test",
            "difficulty": "core",
        },
        "sections": [
            {
                "title": "Fractions and Arrays",
                "instructions": "Check that each visual prints cleanly.",
                "items": [
                    {
                        "question_text": "What fraction of the bar is shaded?",
                        "visual_payload": {
                            "visual_type": "fraction_bar",
                            "params": {"parts_total": 5, "parts_shaded": 3, "orientation": "horizontal"},
                        },
                        "options": ["1/5", "2/5", "3/5", "4/5"],
                    },
                    {
                        "question_text": "Write the multiplication fact for this array.",
                        "visual_payload": {
                            "visual_type": "array_grid",
                            "params": {"rows": 3, "cols": 4},
                        },
                        "options": ["3 x 3", "3 x 4", "4 x 4", "12 x 1"],
                    },
                    {
                        "question_text": "Fill in the numerator for the blank fraction bar.",
                        "visual_payload": {
                            "visual_type": "fraction_bar_blank",
                            "params": {"parts_total": 6, "orientation": "horizontal"},
                        },
                        "answer": {"format": "fraction"},
                    },
                ],
            },
            {
                "title": "Algebraic Thinking",
                "instructions": "Confirm the flow diagram aligns inside the page width.",
                "items": [
                    {
                        "question_text": "What is the output of this flow diagram?",
                        "visual_payload": {
                            "visual_type": "flow_diagram",
                            "params": {"input_value": 12, "output_value": "?", "rule_label": "divide by 3"},
                        },
                        "options": ["3", "4", "6", "9"],
                    }
                ],
            },
        ],
        "answer_key": [],
        "teacher_notes": {},
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    worksheet = build_mock_worksheet()
    renderer = WorksheetHtmlRenderer()
    html_content = renderer.render(worksheet)

    html_path = OUTPUT_DIR / "visual_smoke.html"
    html_path.write_text(html_content, encoding="utf-8")

    exporter = WorksheetPdfExporter(PROJECT_ROOT)
    pdf_path = exporter.render_raw_html(html_content, OUTPUT_DIR / "visual_smoke.pdf")

    print(f"HTML preview written to: {html_path}")
    print(f"PDF written to: {pdf_path}")


if __name__ == "__main__":
    main()
