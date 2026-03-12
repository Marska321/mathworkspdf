from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.templates.loader import load_template_library


@lru_cache(maxsize=1)
def load_misconception_catalog() -> dict[str, dict[str, Any]]:
    misconceptions = load_template_library().get("misconceptions", [])
    return {item["code"]: item for item in misconceptions}


def get_misconception(code: str) -> dict[str, Any] | None:
    return load_misconception_catalog().get(code)


def validate_misconception_references() -> list[str]:
    library = load_template_library()
    known_codes = set(load_misconception_catalog())
    referenced_codes: set[str] = set()
    for skill in library["skills"]:
        referenced_codes.update(skill.get("misconception_tags", []))
    for family in library["families"]:
        referenced_codes.update(family.get("misconception_targets", []))
    for template in library["templates"]:
        referenced_codes.update(template.get("misconception_targets", []))
    for family in library.get("grade4_family_registry", []):
        referenced_codes.update(family.get("misconception_targets", []))
    return sorted(referenced_codes - known_codes)
