from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


LIBRARY_ROOT = Path(__file__).resolve().parent / "library"
GRADE4_ROOT = LIBRARY_ROOT / "grade4"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_template_library() -> dict[str, Any]:
    skills = _load_json(LIBRARY_ROOT / "skills.json")
    blueprints = _load_json(LIBRARY_ROOT / "blueprints.json")
    patterns = _load_json(LIBRARY_ROOT / "patterns.json")
    misconceptions = _load_json(LIBRARY_ROOT / "misconceptions.json")
    grade4_family_registry = _load_json(GRADE4_ROOT / "family_registry.json")
    grade4_family_coverage_map = _load_json(GRADE4_ROOT / "family_coverage_map.json")
    families: list[dict[str, Any]] = []
    templates: list[dict[str, Any]] = []

    for family_path in sorted(LIBRARY_ROOT.rglob("*_family.json")):
        family_payload = _load_json(family_path)
        families.append({key: value for key, value in family_payload.items() if key != "templates"})
        templates.extend(family_payload.get("templates", []))

    return {
        "skills": skills,
        "families": families,
        "templates": templates,
        "blueprints": blueprints,
        "patterns": patterns,
        "misconceptions": misconceptions,
        "grade4_family_registry": grade4_family_registry,
        "grade4_family_coverage_map": grade4_family_coverage_map,
    }
