from __future__ import annotations

from collections.abc import Iterable

from app.core.config import get_settings
from app.repositories.supabase_repo import SupabaseWorksheetRepository
from app.templates.loader import load_template_library


LIBRARY = load_template_library()


def unique_rows(rows: Iterable[dict], key_fields: tuple[str, ...]) -> list[dict]:
    seen: set[tuple[object, ...]] = set()
    ordered: list[dict] = []
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(row)
    return ordered


def build_family_rows() -> list[dict]:
    return [
        {
            "family_code": family["family_code"],
            "skill_id": family["skill_id"],
            "name": family["name"],
            "description": family["description"],
            "supports_visual": family.get("supports_visual", False),
            "supports_theme": family.get("supports_theme", False),
            "active": True,
        }
        for family in LIBRARY["families"]
    ]


def build_misconception_rows() -> list[dict]:
    return [
        {
            "code": item["code"],
            "name": item["name"],
            "description": item["description"],
        }
        for item in LIBRARY.get("misconceptions", [])
    ]


def build_skill_misconception_rows(misconception_id_lookup: dict[str, str]) -> list[dict]:
    rows = []
    for skill in LIBRARY["skills"]:
        for code in skill.get("misconception_tags", []):
            misconception_id = misconception_id_lookup.get(code)
            if misconception_id:
                rows.append({"skill_id": skill["skill_id"], "misconception_id": misconception_id})
    return unique_rows(rows, ("skill_id", "misconception_id"))


def build_template_misconception_rows(misconception_id_lookup: dict[str, str]) -> list[dict]:
    rows = []
    for template in LIBRARY["templates"]:
        for code in template.get("misconception_targets", []):
            misconception_id = misconception_id_lookup.get(code)
            if misconception_id:
                rows.append({"template_id": template["template_id"], "misconception_id": misconception_id})
    return unique_rows(rows, ("template_id", "misconception_id"))


def build_prerequisite_rows() -> list[dict]:
    rows = []
    for skill in LIBRARY["skills"]:
        for prerequisite_skill_id in skill.get("prerequisite_skill_ids", []):
            rows.append({"skill_id": skill["skill_id"], "prerequisite_skill_id": prerequisite_skill_id})
    return unique_rows(rows, ("skill_id", "prerequisite_skill_id"))


def main() -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Set MWP_SUPABASE_URL and MWP_SUPABASE_SERVICE_KEY before seeding Supabase.")

    repository = SupabaseWorksheetRepository(settings.supabase_url, settings.supabase_service_key)
    repository.seed_table("skills", LIBRARY["skills"], "skill_id")

    prerequisite_rows = build_prerequisite_rows()
    if prerequisite_rows:
        repository.seed_table("skill_prerequisites", prerequisite_rows, "skill_id,prerequisite_skill_id")

    misconception_rows = build_misconception_rows()
    if misconception_rows:
        repository.seed_table("misconceptions", misconception_rows, "code")

    misconception_id_lookup = {row["code"]: row["id"] for row in repository.fetch_misconceptions()}

    skill_misconception_rows = build_skill_misconception_rows(misconception_id_lookup)
    if skill_misconception_rows:
        repository.seed_table("skill_misconceptions", skill_misconception_rows, "skill_id,misconception_id")

    family_rows = build_family_rows()
    if family_rows:
        repository.seed_table("template_families", family_rows, "family_code")

    repository.seed_table("templates", LIBRARY["templates"], "template_id")

    template_misconception_rows = build_template_misconception_rows(misconception_id_lookup)
    if template_misconception_rows:
        repository.seed_table("template_misconceptions", template_misconception_rows, "template_id,misconception_id")

    blueprint_rows = [
        {
            "id": blueprint["blueprint_id"],
            "blueprint_code": blueprint["blueprint_id"],
            "worksheet_type": blueprint["worksheet_type"],
            "structure_json": blueprint,
            "active": True,
        }
        for blueprint in LIBRARY["blueprints"]
    ]
    repository.seed_table("worksheet_blueprints", blueprint_rows, "id")
    print("Seeded worksheet template library into Supabase.")


if __name__ == "__main__":
    main()
