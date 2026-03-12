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


def test_measurement_ruler_visual_renders_ticks_and_highlight() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "measurement_ruler",
            "params": {"unit": "cm", "max_value": 10, "highlight_value": 6.4, "tick_step": 1},
        }
    )

    assert '<svg class="svg-visual measurement-ruler-svg"' in html
    assert 'class="ruler-highlight"' in html
    assert ">cm</text>" in html



def test_clock_face_visual_renders_hands_and_caption() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "clock_face",
            "params": {"hour": 3, "minute": 30, "caption": "Half past three"},
        }
    )

    assert '<svg class="svg-visual clock-face-svg"' in html
    assert 'class="minute-hand"' in html
    assert 'class="hour-hand"' in html
    assert "Half past three" in html



def test_bar_graph_visual_renders_bars_and_labels() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "bar_graph",
            "params": {
                "categories": ["Red", "Blue", "Green"],
                "values": [2, 5, 3],
                "y_max": 6,
                "title": "Favourite Colours",
            },
        }
    )

    assert '<svg class="svg-visual bar-graph-svg"' in html
    assert html.count('class="bar-graph-bar"') == 3
    assert "Favourite Colours" in html
    assert "Red" in html



def test_pictograph_visual_renders_icons_and_key() -> None:
    renderer = WorksheetHtmlRenderer()
    html = renderer._render_visual(
        {
            "visual_type": "pictograph",
            "params": {
                "categories": ["Cats", "Dogs"],
                "counts": [4, 3],
                "key_value": 2,
                "icon_label": "pets",
            },
        }
    )

    assert '<svg class="svg-visual pictograph-svg"' in html
    assert html.count('class="pictograph-icon"') == 7
    assert 'class="pictograph-partial-icon"' not in html
    assert "Key:" in html
    assert "pets" in html


