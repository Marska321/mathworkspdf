from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.templates.loader import load_template_library


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
LIBRARY_ROOT = WORKSPACE_ROOT / "app" / "templates" / "library"
TESTS_ROOT = WORKSPACE_ROOT / "tests"


def _load_family_files() -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for family_path in sorted(LIBRARY_ROOT.rglob("*_family.json")):
        payload = json.loads(family_path.read_text(encoding="utf-8"))
        families[payload["family_code"]] = {
            "payload": payload,
            "relative_path": family_path.relative_to(WORKSPACE_ROOT).as_posix(),
        }
    return families


def _load_test_text() -> str:
    parts: list[str] = []
    for test_path in sorted(TESTS_ROOT.glob("test_*.py")):
        parts.append(test_path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _actual_test_coverage(family_code: str, skill_id: str, skill_name: str, subtopic: str | None) -> bool:
    test_text = _load_test_text()
    probes = [family_code, skill_id, skill_name]
    if subtopic:
        probes.append(subtopic)
    return any(probe in test_text for probe in probes if probe)


def _family_skill_lookup(library: dict[str, Any]) -> dict[str, dict[str, Any]]:
    skills_by_id = {skill["skill_id"]: skill for skill in library["skills"]}
    lookup: dict[str, dict[str, Any]] = {}
    for family_code, item in _load_family_files().items():
        skill = skills_by_id.get(item["payload"]["skill_id"], {})
        lookup[family_code] = skill
    return lookup


def validate_grade4_registry() -> list[str]:
    library = load_template_library()
    registry = library["grade4_family_registry"]
    coverage_map = library["grade4_family_coverage_map"]
    known_patterns = {item["pattern_code"] for item in library["patterns"]}
    known_misconceptions = {item["code"] for item in library["misconceptions"]}
    registry_by_code = {item["family_code"]: item for item in registry}
    coverage_codes = {item["family_code"] for item in coverage_map}
    family_files = _load_family_files()
    errors: list[str] = []

    if len(registry_by_code) != len(registry):
        errors.append("duplicate_family_code_in_registry")

    for family_code, entry in registry_by_code.items():
        if family_code not in coverage_codes:
            errors.append(f"missing_coverage_map_entry:{family_code}")
        unknown_patterns = sorted(set(entry.get("allowed_patterns", [])) - known_patterns)
        if unknown_patterns:
            errors.append(f"unknown_registry_patterns:{family_code}:{','.join(unknown_patterns)}")
        unknown_misconceptions = sorted(set(entry.get("misconception_targets", [])) - known_misconceptions)
        if unknown_misconceptions:
            errors.append(f"unknown_registry_misconceptions:{family_code}:{','.join(unknown_misconceptions)}")

    for family_code, item in family_files.items():
        if family_code not in registry_by_code:
            errors.append(f"implemented_family_missing_from_registry:{family_code}")
            continue
        entry = registry_by_code[family_code]
        payload = item["payload"]
        actual_patterns = {template["pattern_code"] for template in payload.get("templates", [])}
        unexpected_patterns = sorted(actual_patterns - set(entry.get("allowed_patterns", [])))
        if unexpected_patterns:
            errors.append(f"registry_missing_family_patterns:{family_code}:{','.join(unexpected_patterns)}")
        actual_misconceptions = set(payload.get("misconception_targets", []))
        unexpected_misconceptions = sorted(actual_misconceptions - set(entry.get("misconception_targets", [])))
        if unexpected_misconceptions:
            errors.append(f"registry_missing_family_misconceptions:{family_code}:{','.join(unexpected_misconceptions)}")
        actual_visual_support = any(
            template.get("visual_supported") or (template.get("rendering") or {}).get("visual_type")
            for template in payload.get("templates", [])
        )
        if bool(entry.get("visual_support")) != actual_visual_support:
            errors.append(f"visual_support_mismatch:{family_code}")

    for family_code in coverage_codes - set(registry_by_code):
        errors.append(f"coverage_entry_missing_from_registry:{family_code}")

    return sorted(errors)


def validate_grade4_coverage_map() -> list[str]:
    library = load_template_library()
    coverage_by_code = {item["family_code"]: item for item in library["grade4_family_coverage_map"]}
    family_files = _load_family_files()
    skill_lookup = _family_skill_lookup(library)
    errors: list[str] = []

    if len(coverage_by_code) != len(library["grade4_family_coverage_map"]):
        errors.append("duplicate_family_code_in_coverage_map")

    for family_code, entry in coverage_by_code.items():
        actual = family_files.get(family_code)
        actual_exists = actual is not None
        if bool(entry.get("implemented")) != actual_exists:
            errors.append(f"implemented_flag_mismatch:{family_code}")
            continue

        if not actual_exists:
            if entry.get("family_file") is not None:
                errors.append(f"pending_family_should_not_have_file:{family_code}")
            if int(entry.get("templates_count", 0)) != 0:
                errors.append(f"pending_family_should_have_zero_templates:{family_code}")
            if entry.get("patterns_supported"):
                errors.append(f"pending_family_should_not_list_patterns:{family_code}")
            if bool(entry.get("tests_exist")):
                errors.append(f"pending_family_should_not_mark_tests:{family_code}")
            continue

        payload = actual["payload"]
        actual_path = actual["relative_path"]
        actual_patterns = sorted({template["pattern_code"] for template in payload.get("templates", [])})
        actual_template_count = len(payload.get("templates", []))
        skill = skill_lookup.get(family_code, {})
        actual_tests_exist = _actual_test_coverage(
            family_code=family_code,
            skill_id=payload.get("skill_id", ""),
            skill_name=skill.get("name", ""),
            subtopic=skill.get("subtopic"),
        )

        if entry.get("family_file") != actual_path:
            errors.append(f"family_file_mismatch:{family_code}")
        if int(entry.get("templates_count", 0)) != actual_template_count:
            errors.append(f"templates_count_mismatch:{family_code}")
        if sorted(entry.get("patterns_supported", [])) != actual_patterns:
            errors.append(f"patterns_supported_mismatch:{family_code}")
        if bool(entry.get("tests_exist")) != actual_tests_exist:
            errors.append(f"tests_exist_mismatch:{family_code}")

    for family_code in set(family_files) - set(coverage_by_code):
        errors.append(f"implemented_family_missing_from_coverage_map:{family_code}")

    return sorted(errors)
