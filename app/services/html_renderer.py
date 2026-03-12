from __future__ import annotations

from html import escape
from typing import Any


class WorksheetHtmlRenderer:
    def render(self, worksheet: dict[str, Any], teacher_mode: bool = False) -> str:
        title = escape(worksheet["title"])
        subtitle = escape(worksheet["subtitle"])
        metadata = worksheet.get("metadata", {})
        sections = worksheet.get("sections", [])
        answer_key = worksheet.get("answer_key", [])
        teacher_notes = worksheet.get("teacher_notes", {})

        question_number = 1
        rendered_sections: list[str] = []
        for index, section in enumerate(sections, start=1):
            section_html, question_number = self._render_section(index, section, question_number, teacher_mode)
            rendered_sections.append(section_html)

        section_html = "".join(rendered_sections)
        answer_key_html = "".join(self._render_answer(answer) for answer in answer_key)
        teacher_notes_html = self._render_teacher_notes(teacher_notes) if teacher_mode else ""
        metadata_html = "".join(
            f"<span><strong>{escape(str(key).replace('_', ' ').title())}:</strong> {escape(str(value))}</span>"
            for key, value in metadata.items()
            if value is not None and key in {"curriculum", "grade", "term", "topic", "subskill", "difficulty"}
        )

        return f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    :root {{
      --paper: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d1d5db;
      --accent: #0f766e;
      --accent-soft: #ccfbf1;
      --math-soft: #eff6ff;
      --math-line: #93c5fd;
    }}
    body {{
      margin: 0;
      font-family: Georgia, 'Times New Roman', serif;
      color: var(--ink);
      background: linear-gradient(180deg, #f8fafc 0%, #eefbf7 100%);
    }}
    .page {{
      max-width: 900px;
      margin: 24px auto;
      background: var(--paper);
      border: 1px solid var(--line);
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
      padding: 32px;
    }}
    h1 {{ margin: 0; font-size: 2rem; }}
    .subtitle {{ color: var(--accent); margin-top: 6px; font-size: 1.05rem; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 10px 18px; margin: 18px 0 28px; color: var(--muted); font-size: 0.95rem; }}
    .learner-header {{
      display: grid;
      grid-template-columns: 1fr 220px;
      gap: 18px;
      margin: 18px 0 10px;
      align-items: end;
    }}
    .learner-line {{
      border-bottom: 2px solid var(--ink);
      min-height: 28px;
      display: flex;
      align-items: end;
      padding-bottom: 4px;
      font-size: 0.95rem;
    }}
    .section {{ margin-top: 24px; padding-top: 18px; border-top: 2px solid var(--accent-soft); }}
    .section h2 {{ margin: 0 0 6px; font-size: 1.25rem; }}
    .instructions {{ color: var(--muted); margin-bottom: 14px; }}
    .teacher-panel {{
      margin: 20px 0 24px;
      padding: 16px 18px;
      border: 1px solid var(--math-line);
      border-radius: 12px;
      background: linear-gradient(180deg, #f0fdf4 0%, #ecfeff 100%);
    }}
    .teacher-panel h2, .teacher-panel h3 {{ margin: 0 0 8px; }}
    .teacher-panel p {{ margin: 0 0 8px; }}
    .teacher-list {{ margin: 8px 0 0; padding-left: 18px; }}
    .question-list {{ list-style: none; padding-left: 0; margin: 0; }}
    li {{ margin: 0 0 20px; }}
    .item-row {{ display: grid; grid-template-columns: 34px 1fr; gap: 12px; align-items: start; }}
    .item-number {{ font-weight: 700; font-size: 1rem; padding-top: 2px; }}
    .question {{ font-size: 1.05rem; margin-bottom: 8px; }}
    .math-card {{ background: var(--math-soft); border: 1px solid var(--math-line); border-radius: 10px; padding: 12px 14px; display: inline-block; min-width: 220px; }}
    .math-expression {{ font-size: 1.35rem; font-weight: 600; letter-spacing: 0.03em; }}
    .answer-line {{ display: inline-block; min-width: 80px; border-bottom: 2px solid var(--ink); transform: translateY(-2px); }}
    .response-block {{ margin-top: 10px; }}
    .response-label {{ font-size: 0.92rem; color: var(--muted); margin-bottom: 4px; }}
    .fraction-response {{
      display: inline-grid;
      grid-template-columns: 56px;
      justify-items: center;
      align-items: center;
      gap: 4px;
    }}
    .fraction-response .fraction-slot {{
      width: 56px;
      border-bottom: 2px solid var(--ink);
      height: 22px;
    }}
    .fraction-response .fraction-divider {{
      width: 60px;
      border-top: 2px solid var(--ink);
    }}
    .long-response {{
      display: inline-block;
      min-width: 180px;
      border-bottom: 2px solid var(--ink);
      height: 22px;
    }}
    .options {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; margin-top: 8px; }}
    .option {{ border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; background: #ffffff; }}
    .visual {{ margin-top: 10px; }}
    .teacher-item-note {{
      margin-top: 10px;
      padding: 10px 12px;
      border-left: 4px solid var(--accent);
      background: #f8fafc;
      color: var(--ink);
      font-size: 0.95rem;
    }}
    .teacher-item-note strong {{ color: var(--accent); }}
    .fraction-bar {{ display: grid; gap: 4px; min-height: 44px; }}
    .fraction-part {{ border: 1px solid var(--accent); min-height: 42px; }}
    .fraction-part.shaded {{ background: repeating-linear-gradient(135deg, var(--accent-soft), var(--accent-soft) 10px, #99f6e4 10px, #99f6e4 20px); }}
    .flow-diagram {
      display: grid;
      grid-template-columns: minmax(90px, 120px) 48px minmax(110px, 140px) 48px minmax(90px, 120px);
      align-items: center;
      gap: 8px;
      margin-top: 10px;
      max-width: 520px;
    }
    .flow-box {
      border: 2px solid var(--math-line);
      border-radius: 12px;
      background: #ffffff;
      padding: 12px 10px;
      text-align: center;
      min-height: 52px;
    }
    .flow-box.rule {
      background: linear-gradient(180deg, var(--accent-soft) 0%, #ffffff 100%);
      border-color: var(--accent);
      font-weight: 700;
      color: var(--accent);
    }
    .flow-arrow {
      text-align: center;
      color: var(--muted);
      font-size: 1.35rem;
      font-weight: 700;
    }
    .flow-label {
      display: block;
      font-size: 0.8rem;
      color: var(--muted);
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .flow-value {
      font-size: 1.2rem;
      font-weight: 700;
    }
    .answer-key-page {{
      max-width: 900px;
      margin: 24px auto;
      background: var(--paper);
      border: 1px solid var(--line);
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
      padding: 32px;
      break-before: page;
      page-break-before: always;
    }}
    .answer-key {{ margin-top: 0; padding-top: 0; }}
    .answer-key h2 {{ margin: 0 0 12px; }}
    .answer-entry {{ margin-bottom: 10px; }}
    @media print {{
      body {{ background: white; }}
      .page, .answer-key-page {{ box-shadow: none; margin: 0; border: none; max-width: none; }}
    }}
  </style>
</head>
<body>
  <main class=\"page\">
    <h1>{title}</h1>
    <div class=\"subtitle\">{subtitle}</div>
    <div class=\"learner-header\">
      <div class=\"learner-line\"><strong>Name:</strong>&nbsp;</div>
      <div class=\"learner-line\"><strong>Date:</strong>&nbsp;</div>
    </div>
    <div class=\"meta\">{metadata_html}</div>
    {teacher_notes_html}
    {section_html}
  </main>
  <section class=\"answer-key-page\">
    <section class=\"answer-key\">
      <h2>Answer Key</h2>
      {answer_key_html}
    </section>
  </section>
</body>
</html>
""".strip()

    def _render_section(
        self,
        index: int,
        section: dict[str, Any],
        start_number: int,
        teacher_mode: bool,
    ) -> tuple[str, int]:
        items_html: list[str] = []
        question_number = start_number
        for item in section.get("items", []):
            items_html.append(self._render_item(item, question_number, teacher_mode))
            question_number += 1
        instructions = escape(section.get("instructions") or "")
        return (
            f"""
<section class=\"section\">
  <h2>{index}. {escape(section['title'])}</h2>
  <div class=\"instructions\">{instructions}</div>
  <ol class=\"question-list\">{''.join(items_html)}</ol>
</section>
""",
            question_number,
        )

    def _render_item(self, item: dict[str, Any], question_number: int, teacher_mode: bool) -> str:
        options_html = ""
        if item.get("options"):
            options_html = "<div class=\"options\">" + "".join(
                f"<div class=\"option\">{escape(str(option))}</div>" for option in item["options"]
            ) + "</div>"
        visual_html = self._render_visual(item.get("visual_payload"))
        question_html = self._render_question(item)
        response_html = self._render_response(item)
        teacher_note_html = self._render_item_teacher_note(item) if teacher_mode else ""
        return f"""
<li>
  <div class=\"item-row\">
    <div class=\"item-number\">{question_number}.</div>
    <div>
      {question_html}
      {visual_html}
      {response_html}
      {options_html}
      {teacher_note_html}
    </div>
  </div>
</li>
"""

    def _render_question(self, item: dict[str, Any]) -> str:
        question_text = escape(item["question_text"])
        if item.get("family_id") == "add_regroup_family":
            expression = question_text.replace("__", "<span class=\"answer-line\"></span>")
            return f"<div class=\"math-card\"><div class=\"math-expression\">{expression}</div></div>"
        return f"<div class=\"question\">{question_text}</div>"

    def _render_response(self, item: dict[str, Any]) -> str:
        if item.get("options"):
            return ""
        if item.get("answer", {}).get("format") == "fraction":
            return """
<div class=\"response-block\">
  <div class=\"response-label\">Answer:</div>
  <div class=\"fraction-response\">
    <div class=\"fraction-slot\"></div>
    <div class=\"fraction-divider\"></div>
    <div class=\"fraction-slot\"></div>
  </div>
</div>
"""
        return """
<div class=\"response-block\">
  <div class=\"response-label\">Answer:</div>
  <span class=\"long-response\"></span>
</div>
"""

    def _render_visual(self, payload: dict[str, Any] | None) -> str:
        if not payload:
            return ""
        visual_type = payload.get("visual_type")
        params = payload.get("params", {})

        if visual_type == "fraction_bar":
            parts_total = int(params.get("parts_total", 1))
            parts_shaded = int(params.get("parts_shaded", 0))
            parts = []
            for index in range(parts_total):
                class_name = "fraction-part shaded" if index < parts_shaded else "fraction-part"
                parts.append(f"<div class=\"{class_name}\"></div>")
            style = f"grid-template-columns: repeat({parts_total}, minmax(0, 1fr));"
            return f"<div class=\"visual\"><div class=\"fraction-bar\" style=\"{style}\">{''.join(parts)}</div></div>"

        if visual_type == "flow_diagram":
            input_value = escape(str(params.get("input_value", "")))
            output_value = escape(str(params.get("output_value", "")))
            rule_label = escape(str(params.get("rule_label", "?")))
            return (
                "<div class=\"visual\"><div class=\"flow-diagram\">"
                f"<div class=\"flow-box\"><span class=\"flow-label\">Input</span><span class=\"flow-value\">{input_value}</span></div>"
                "<div class=\"flow-arrow\">→</div>"
                f"<div class=\"flow-box rule\"><span class=\"flow-label\">Rule</span><span class=\"flow-value\">{rule_label}</span></div>"
                "<div class=\"flow-arrow\">→</div>"
                f"<div class=\"flow-box\"><span class=\"flow-label\">Output</span><span class=\"flow-value\">{output_value}</span></div>"
                "</div></div>"
            )

        return f"<div class=\"visual\">{escape(payload.get('visual_type', 'visual'))}</div>"

    def _render_answer(self, answer: dict[str, Any]) -> str:
        explanation = escape(answer.get("explanation") or "")
        return (
            f"<div class=\"answer-entry\"><strong>{answer['question_number']}.</strong> "
            f"{escape(answer['correct_answer'])}"
            f"<div>{explanation}</div></div>"
        )

    def _render_teacher_notes(self, teacher_notes: dict[str, Any]) -> str:
        skills = teacher_notes.get("skills_tested", [])
        misconceptions = teacher_notes.get("misconceptions_targeted", [])
        details = teacher_notes.get("misconception_details", [])

        skills_html = "".join(f"<li>{escape(str(skill))}</li>" for skill in skills)
        misconceptions_html = "".join(f"<li>{escape(str(code))}</li>" for code in misconceptions)
        detail_html = "".join(
            "<li>"
            f"<strong>{escape(str(detail.get('name') or detail.get('code') or 'Misconception'))}</strong>: "
            f"{escape(str(detail.get('description') or ''))}"
            "</li>"
            for detail in details
        )

        return f"""
<section class=\"teacher-panel\">
  <h2>Teacher Notes</h2>
  <p><strong>Skills tested:</strong></p>
  <ul class=\"teacher-list\">{skills_html or '<li>None recorded</li>'}</ul>
  <p><strong>Misconceptions targeted:</strong></p>
  <ul class=\"teacher-list\">{misconceptions_html or '<li>None recorded</li>'}</ul>
  <p><strong>Misconception details:</strong></p>
  <ul class=\"teacher-list\">{detail_html or '<li>No misconception details available</li>'}</ul>
</section>
"""

    def _render_item_teacher_note(self, item: dict[str, Any]) -> str:
        metadata = item.get("metadata", {})
        details = metadata.get("misconception_details", [])
        if not details:
            return ""

        detail_html = "".join(
            "<div>"
            f"<strong>{escape(str(detail.get('name') or detail.get('code') or 'Misconception'))}:</strong> "
            f"{escape(str(detail.get('description') or ''))}"
            "</div>"
            for detail in details
        )
        return f"<div class=\"teacher-item-note\"><strong>Teacher note:</strong>{detail_html}</div>"

