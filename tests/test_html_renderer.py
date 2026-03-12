from app.services.html_renderer import SVGRenderer, WorksheetHtmlRenderer


EXPECTED_VISUAL_TYPES = {
    "fraction_bar",
    "fraction_bar_blank",
    "array_grid",
    "flow_diagram",
    "measurement_ruler",
    "clock_face",
    "bar_graph",
    "pictograph",
}


def test_svg_renderer_declares_current_and_future_visual_specs() -> None:
    assert EXPECTED_VISUAL_TYPES.issubset(SVGRenderer.VISUAL_PARAM_SPECS)


def test_fraction_bar_visual_renders_svg_with_shaded_count() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "fraction_bar",
            "params": {"parts_total": 5, "parts_shaded": 3, "orientation": "horizontal"},
        }
    )

    assert '<svg class="svg-visual fraction-svg"' in html
    assert html.count('class="fraction-segment shaded"') == 3
    assert html.count('class="fraction-segment unshaded"') == 2


def test_fraction_bar_blank_visual_renders_unshaded_segments() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "fraction_bar_blank",
            "params": {"parts_total": 4, "orientation": "horizontal"},
        }
    )

    assert '<svg class="svg-visual fraction-svg"' in html
    assert html.count('class="fraction-segment blank"') == 4


def test_array_grid_visual_renders_expected_cell_count() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "array_grid",
            "params": {"rows": 3, "cols": 4},
        }
    )

    assert '<svg class="svg-visual array-svg"' in html
    assert html.count('class="array-cell"') == 12


def test_flow_diagram_visual_renders_labels_and_blank_output() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "flow_diagram",
            "params": {"input_value": 12, "output_value": "?", "rule_label": "divide by 3"},
        }
    )

    assert '<svg class="svg-visual flow-diagram-svg"' in html
    assert "Input" in html
    assert "Rule" in html
    assert "Output" in html
    assert "____" in html
    assert "divide by 3" in html
