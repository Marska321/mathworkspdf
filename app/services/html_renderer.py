from __future__ import annotations

import math
from html import escape
from typing import Any


class SVGRenderer:
    """Internal helper to convert supported visual payloads into inline SVG."""

    VISUAL_PARAM_SPECS: dict[str, tuple[str, ...]] = {
        "fraction_bar": ("parts_total", "parts_shaded", "orientation"),
        "fraction_bar_blank": ("parts_total", "orientation"),
        "array_grid": ("rows", "cols"),
        "flow_diagram": ("input_value", "output_value", "rule_label"),
        "measurement_ruler": ("unit", "max_value", "highlight_value", "tick_step"),
        "clock_face": ("hour", "minute", "caption"),
        "bar_graph": ("categories", "values", "y_max", "title"),
        "pictograph": ("categories", "counts", "key_value", "icon_label"),
    }

    @staticmethod
    def render(visual_payload: dict[str, Any] | None) -> str:
        if not visual_payload:
            return ""

        visual_type = str(visual_payload.get("visual_type") or "")
        params = visual_payload.get("params", {})

        if visual_type == "fraction_bar":
            return SVGRenderer._render_fraction_bar(
                parts_total=int(params.get("parts_total", 1)),
                parts_shaded=int(params.get("parts_shaded", 0)),
                orientation=str(params.get("orientation", "horizontal")),
                blank=False,
            )
        if visual_type == "fraction_bar_blank":
            return SVGRenderer._render_fraction_bar(
                parts_total=int(params.get("parts_total", 1)),
                parts_shaded=0,
                orientation=str(params.get("orientation", "horizontal")),
                blank=True,
            )
        if visual_type == "array_grid":
            return SVGRenderer._render_array_grid(
                rows=int(params.get("rows", 1)),
                cols=int(params.get("cols", 1)),
            )
        if visual_type == "flow_diagram":
            return SVGRenderer._render_flow_diagram(
                input_value=params.get("input_value", ""),
                output_value=params.get("output_value", "?"),
                rule_label=params.get("rule_label", "?"),
            )
        if visual_type == "measurement_ruler":
            return SVGRenderer._render_measurement_ruler(
                unit=str(params.get("unit", "cm")),
                max_value=int(params.get("max_value", 10)),
                highlight_value=(
                    None if params.get("highlight_value") is None else float(params.get("highlight_value"))
                ),
                tick_step=int(params.get("tick_step", 1)),
            )
        if visual_type == "clock_face":
            return SVGRenderer._render_clock_face(
                hour=int(params.get("hour", 12)),
                minute=int(params.get("minute", 0)),
                caption=str(params.get("caption", "")),
            )
        if visual_type == "bar_graph":
            return SVGRenderer._render_bar_graph(
                categories=[str(item) for item in params.get("categories", [])],
                values=[int(item) for item in params.get("values", [])],
                y_max=int(params.get("y_max", 10)),
                title=str(params.get("title", "")),
            )
        if visual_type == "pictograph":
            return SVGRenderer._render_pictograph(
                categories=[str(item) for item in params.get("categories", [])],
                counts=[int(item) for item in params.get("counts", [])],
                key_value=int(params.get("key_value", 1)),
                icon_label=str(params.get("icon_label", "Item")),
            )
        return ""

    @staticmethod
    def _render_fraction_bar(
        *,
        parts_total: int,
        parts_shaded: int,
        orientation: str,
        blank: bool,
    ) -> str:
        total = max(parts_total, 1)
        shaded = max(0, min(parts_shaded, total))
        horizontal = orientation != "vertical"
        width = 260 if horizontal else 72
        height = 48 if horizontal else 220
        segment_width = width / total if horizontal else width
        segment_height = height if horizontal else height / total

        svg_parts = [
            f'<svg class="svg-visual fraction-svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Fraction model showing {shaded} of {total} parts">'
        ]
        for index in range(total):
            x = segment_width * index if horizontal else 0
            y = 0 if horizontal else segment_height * index
            if blank:
                class_name = "fraction-segment blank"
                fill = "#ffffff"
            elif index < shaded:
                class_name = "fraction-segment shaded"
                fill = "#0f766e"
            else:
                class_name = "fraction-segment unshaded"
                fill = "#ffffff"
            svg_parts.append(
                f'<rect class="{class_name}" x="{x:.2f}" y="{y:.2f}" width="{segment_width:.2f}" '
                f'height="{segment_height:.2f}" fill="{fill}" stroke="#1f2937" stroke-width="2" />'
            )
        svg_parts.append("</svg>")
        return "".join(svg_parts)

    @staticmethod
    def _render_array_grid(*, rows: int, cols: int) -> str:
        total_rows = max(rows, 1)
        total_cols = max(cols, 1)
        cell_size = 32
        width = total_cols * cell_size
        height = total_rows * cell_size
        svg_parts = [
            f'<svg class="svg-visual array-svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Array with {total_rows} rows and {total_cols} columns">'
        ]
        for row in range(total_rows):
            for col in range(total_cols):
                x = col * cell_size
                y = row * cell_size
                svg_parts.append(
                    f'<rect class="array-cell" x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                    f'fill="#ffffff" stroke="#93c5fd" stroke-width="1.5" />'
                )
        svg_parts.append("</svg>")
        return "".join(svg_parts)

    @staticmethod
    def _render_flow_diagram(*, input_value: Any, output_value: Any, rule_label: Any) -> str:
        width = 360
        height = 100
        center_y = height / 2
        rule_box_width = 108
        rule_box_height = 44
        rule_box_x = (width - rule_box_width) / 2
        output_text = "____" if str(output_value) == "?" else escape(str(output_value))

        return (
            f'<svg class="svg-visual flow-diagram-svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Flow diagram">'
            '<defs><marker id="flow-arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">'
            '<path d="M0,0 L0,6 L9,3 z" fill="#374151" /></marker></defs>'
            f'<text x="42" y="{center_y:.1f}" dominant-baseline="middle" text-anchor="middle" '
            'font-family="Georgia, serif" font-size="17" fill="#111827">Input</text>'
            f'<text x="42" y="{center_y + 22:.1f}" dominant-baseline="middle" text-anchor="middle" '
            'font-family="Georgia, serif" font-size="19" font-weight="700" fill="#111827">'
            f"{escape(str(input_value))}</text>"
            f'<line x1="72" y1="{center_y:.1f}" x2="{rule_box_x - 10:.1f}" y2="{center_y:.1f}" stroke="#374151" '
            'stroke-width="2.5" marker-end="url(#flow-arrow)" />'
            f'<rect x="{rule_box_x:.1f}" y="{center_y - rule_box_height / 2:.1f}" width="{rule_box_width}" '
            f'height="{rule_box_height}" fill="#ecfeff" stroke="#0f766e" stroke-width="2" rx="8" />'
            f'<text x="{width / 2:.1f}" y="{center_y - 12:.1f}" dominant-baseline="middle" text-anchor="middle" '
            'font-family="Georgia, serif" font-size="13" fill="#0f766e">Rule</text>'
            f'<text x="{width / 2:.1f}" y="{center_y + 10:.1f}" dominant-baseline="middle" text-anchor="middle" '
            'font-family="Georgia, serif" font-size="18" font-weight="700" fill="#111827">'
            f"{escape(str(rule_label))}</text>"
            f'<line x1="{rule_box_x + rule_box_width + 10:.1f}" y1="{center_y:.1f}" x2="{width - 72:.1f}" '
            f'y2="{center_y:.1f}" stroke="#374151" stroke-width="2.5" marker-end="url(#flow-arrow)" />'
            f'<text x="{width - 42:.1f}" y="{center_y:.1f}" dominant-baseline="middle" text-anchor="middle" '
            'font-family="Georgia, serif" font-size="17" fill="#111827">Output</text>'
            f'<text x="{width - 42:.1f}" y="{center_y + 22:.1f}" dominant-baseline="middle" text-anchor="middle" '
            'font-family="Georgia, serif" font-size="19" font-weight="700" fill="#111827">'
            f"{output_text}</text>"
            "</svg>"
        )

    @staticmethod
    def _render_measurement_ruler(
        *,
        unit: str,
        max_value: int,
        highlight_value: float | None,
        tick_step: int,
    ) -> str:
        width = 400
        height = 72
        margin_x = 20
        usable_width = width - (margin_x * 2)
        safe_max = max(float(max_value), 1.0)
        safe_tick_step = max(float(tick_step), 1.0)
        normalized_unit = unit.lower()

        if normalized_unit == "cm":
            minor_step = 0.1
            label_step = 1.0
            tick_label = lambda value: f"{value:.1f}".rstrip("0").rstrip(".")
        elif normalized_unit == "mm":
            minor_step = 1.0
            label_step = safe_tick_step
            tick_label = lambda value: str(int(round(value)))
        else:
            minor_step = safe_tick_step
            label_step = safe_tick_step
            tick_label = lambda value: f"{value:g}"

        tick_count = int(round(safe_max / minor_step)) + 1

        svg = [
            f'<svg class="svg-visual measurement-ruler-svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="Measurement ruler in {escape(unit)}">'
        ]
        svg.append(
            f'<rect x="{margin_x}" y="12" width="{usable_width}" height="42" fill="#f8fafc" '
            'stroke="#374151" stroke-width="2" rx="2" />'
        )

        for index in range(tick_count):
            value = round(index * minor_step, 2)
            x = margin_x + (value / safe_max) * usable_width
            is_major = abs((value / label_step) - round(value / label_step)) < 1e-9 or abs(value) < 1e-9 or abs(value - safe_max) < 1e-9
            tick_height = 18 if is_major else 10
            svg.append(
                f'<line x1="{x:.2f}" y1="12" x2="{x:.2f}" y2="{12 + tick_height}" '
                'stroke="#374151" stroke-width="1.4" />'
            )
            if is_major:
                svg.append(
                    f'<text x="{x:.2f}" y="48" dominant-baseline="middle" text-anchor="middle" '
                    'font-family="sans-serif" font-size="12" fill="#374151">'
                    f'{escape(tick_label(value))}</text>'
                )

        svg.append(
            f'<text x="{width - margin_x - 6}" y="48" dominant-baseline="middle" text-anchor="end" '
            'font-family="sans-serif" font-size="12" font-weight="bold" fill="#374151">'
            f'{escape(unit)}</text>'
        )
        if highlight_value is not None and 0 <= float(highlight_value) <= safe_max:
            hx = margin_x + (float(highlight_value) / safe_max) * usable_width
            svg.append(
                f'<polygon class="ruler-highlight" points="{hx-6:.2f},0 {hx+6:.2f},0 {hx:.2f},12" fill="#ef4444" />'
            )

        svg.append("</svg>")
        return "".join(svg)

    @staticmethod
    def _render_clock_face(*, hour: int, minute: int, caption: str) -> str:
        size = 160
        caption_height = 30 if caption else 0
        cx = size / 2
        cy = size / 2
        radius = 60

        svg = [
            f'<svg class="svg-visual clock-face-svg" width="{size}" height="{size + caption_height}" '
            f'viewBox="0 0 {size} {size + caption_height}" xmlns="http://www.w3.org/2000/svg" '
            'role="img" aria-label="Clock face">'
        ]
        svg.append(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="#ffffff" stroke="#374151" stroke-width="3" />'
        )

        for index in range(1, 13):
            angle = math.radians(index * 30 - 90)
            x1 = cx + (radius - 5) * math.cos(angle)
            y1 = cy + (radius - 5) * math.sin(angle)
            x2 = cx + radius * math.cos(angle)
            y2 = cy + radius * math.sin(angle)
            svg.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                'stroke="#374151" stroke-width="2" />'
            )
            nx = cx + (radius - 18) * math.cos(angle)
            ny = cy + (radius - 18) * math.sin(angle)
            svg.append(
                f'<text x="{nx:.2f}" y="{ny + 4:.2f}" text-anchor="middle" font-family="sans-serif" '
                'font-size="14" font-weight="bold" fill="#374151">'
                f"{index}</text>"
            )

        minute_angle = math.radians(minute * 6 - 90)
        minute_x = cx + (radius - 10) * math.cos(minute_angle)
        minute_y = cy + (radius - 10) * math.sin(minute_angle)
        svg.append(
            f'<line class="minute-hand" x1="{cx}" y1="{cy}" x2="{minute_x:.2f}" y2="{minute_y:.2f}" '
            'stroke="#6b7280" stroke-width="3" stroke-linecap="round" />'
        )

        hour_angle = math.radians(((hour % 12) + minute / 60.0) * 30 - 90)
        hour_x = cx + (radius - 30) * math.cos(hour_angle)
        hour_y = cy + (radius - 30) * math.sin(hour_angle)
        svg.append(
            f'<line class="hour-hand" x1="{cx}" y1="{cy}" x2="{hour_x:.2f}" y2="{hour_y:.2f}" '
            'stroke="#111827" stroke-width="4" stroke-linecap="round" />'
        )
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="4" fill="#111827" />')

        if caption:
            svg.append(
                f'<text x="{cx}" y="{size + 20}" text-anchor="middle" font-family="sans-serif" '
                'font-size="14" fill="#374151">'
                f"{escape(caption)}</text>"
            )

        svg.append("</svg>")
        return "".join(svg)

    @staticmethod
    def _render_bar_graph(*, categories: list[str], values: list[int], y_max: int, title: str) -> str:
        width = 350
        height = 200
        pad_left, pad_bottom, pad_top, pad_right = 40, 40, 30, 20
        graph_width = width - pad_left - pad_right
        graph_height = height - pad_top - pad_bottom
        safe_y_max = max(y_max, 1)

        svg = [
            f'<svg class="svg-visual bar-graph-svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            'role="img" aria-label="Bar graph">'
        ]
        if title:
            svg.append(
                f'<text x="{width / 2:.2f}" y="20" text-anchor="middle" font-family="sans-serif" '
                'font-size="14" font-weight="bold" fill="#111827">'
                f"{escape(title)}</text>"
            )

        tick_count = 5
        for index in range(tick_count + 1):
            value = int(safe_y_max * (index / tick_count))
            y = pad_top + graph_height - (graph_height * (value / safe_y_max))
            svg.append(
                f'<line x1="{pad_left}" y1="{y:.2f}" x2="{width - pad_right}" y2="{y:.2f}" '
                'stroke="#e5e7eb" stroke-width="1" />'
            )
            svg.append(
                f'<text x="{pad_left - 10}" y="{y + 4:.2f}" text-anchor="end" font-family="sans-serif" '
                'font-size="12" fill="#6b7280">'
                f"{value}</text>"
            )

        svg.append(
            f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + graph_height}" '
            'stroke="#374151" stroke-width="2" />'
        )
        svg.append(
            f'<line x1="{pad_left}" y1="{pad_top + graph_height}" x2="{width - pad_right}" y2="{pad_top + graph_height}" '
            'stroke="#374151" stroke-width="2" />'
        )

        if categories and values:
            bar_area_width = graph_width / max(len(categories), 1)
            bar_width = min(40, bar_area_width * 0.7)
            for index, (category, value) in enumerate(zip(categories, values)):
                bar_height = graph_height * (min(value, safe_y_max) / safe_y_max)
                bar_x = pad_left + (index * bar_area_width) + (bar_area_width - bar_width) / 2
                bar_y = pad_top + graph_height - bar_height
                svg.append(
                    f'<rect class="bar-graph-bar" x="{bar_x:.2f}" y="{bar_y:.2f}" width="{bar_width:.2f}" '
                    f'height="{bar_height:.2f}" fill="#0ea5e9" opacity="0.8" rx="2" ry="2" />'
                )
                svg.append(
                    f'<text x="{bar_x + bar_width / 2:.2f}" y="{pad_top + graph_height + 20}" '
                    'text-anchor="middle" font-family="sans-serif" font-size="12" fill="#374151">'
                    f"{escape(category)}</text>"
                )

        svg.append("</svg>")
        return "".join(svg)

    @staticmethod
    def _render_pictograph(
        *,
        categories: list[str],
        counts: list[int],
        key_value: int,
        icon_label: str,
    ) -> str:
        width = 350
        row_height = 30
        height = len(categories) * row_height + 60
        category_width = 100
        safe_key_value = max(key_value, 1)

        svg = [
            f'<svg class="svg-visual pictograph-svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            'role="img" aria-label="Pictograph">'
        ]

        for index, (category, count) in enumerate(zip(categories, counts)):
            y = 20 + index * row_height
            svg.append(
                f'<text x="{category_width - 10}" y="{y + row_height / 2 + 4:.2f}" text-anchor="end" '
                'font-family="sans-serif" font-size="14" font-weight="bold" fill="#374151">'
                f'{escape(category)}</text>'
            )
            svg.append(
                f'<line x1="{category_width}" y1="{y}" x2="{category_width}" y2="{y + row_height}" '
                'stroke="#d1d5db" stroke-width="2" />'
            )

            icon_x = category_width + 15
            for _ in range(max(int(count), 0)):
                svg.append(
                    f'<circle class="pictograph-icon" cx="{icon_x}" cy="{y + row_height / 2:.2f}" r="8" fill="#f59e0b" />'
                )
                icon_x += 22

        key_y = height - 20
        svg.append(
            f'<line x1="20" y1="{key_y - 15}" x2="{width - 20}" y2="{key_y - 15}" stroke="#e5e7eb" stroke-width="1" />'
        )
        svg.append(
            f'<text x="{width / 2:.2f}" y="{key_y}" text-anchor="middle" font-family="sans-serif" '
            'font-size="12" fill="#6b7280">'
            f'Key: 1 <tspan fill="#f59e0b">&#9679;</tspan> = {safe_key_value} {escape(icon_label)}</text>'
        )
        svg.append("</svg>")
        return "".join(svg)

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
    .visual-wrapper {{ display: flex; justify-content: center; }}
    .svg-visual {{ max-width: 100%; height: auto; overflow: visible; }}
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
    .flow-diagram {{
      display: grid;
      grid-template-columns: minmax(90px, 120px) 48px minmax(110px, 140px) 48px minmax(90px, 120px);
      align-items: center;
      gap: 8px;
      margin-top: 10px;
      max-width: 520px;
    }}
    .flow-box {{
      border: 2px solid var(--math-line);
      border-radius: 12px;
      background: #ffffff;
      padding: 12px 10px;
      text-align: center;
      min-height: 52px;
    }}
    .flow-box.rule {{
      background: linear-gradient(180deg, var(--accent-soft) 0%, #ffffff 100%);
      border-color: var(--accent);
      font-weight: 700;
      color: var(--accent);
    }}
    .flow-arrow {{
      text-align: center;
      color: var(--muted);
      font-size: 1.35rem;
      font-weight: 700;
    }}
    .flow-label {{
      display: block;
      font-size: 0.8rem;
      color: var(--muted);
      margin-bottom: 4px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .flow-value {{
      font-size: 1.2rem;
      font-weight: 700;
    }}
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

        svg_content = SVGRenderer.render(payload)
        if svg_content:
            return f"<div class=\"visual visual-wrapper\">{svg_content}</div>"

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
                "<div class=\"flow-arrow\">-></div>"
                f"<div class=\"flow-box rule\"><span class=\"flow-label\">Rule</span><span class=\"flow-value\">{rule_label}</span></div>"
                "<div class=\"flow-arrow\">-></div>"
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






