from __future__ import annotations

from collections.abc import Iterable

from app.core.config import get_settings
from app.repositories.supabase_repo import SupabaseWorksheetRepository
from app.templates.seed_data.pilot_content import PILOT_CONTENT


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
    skill_lookup = {skill["skill_id"]: skill for skill in PILOT_CONTENT["skills"]}
    family_rows = []
    for template in PILOT_CONTENT["templates"]:
        skill = skill_lookup[template["skill_id"]]
        family_rows.append(
            {
                "family_code": template["family_id"],
                "skill_id": template["skill_id"],
                "name": template["family_id"].replace("_", " ").title(),
                "description": f"Pilot family for {skill['name']}.",
                "supports_visual": template.get("visual_supported", False),
                "supports_theme": template.get("theme_supported", False),
                "active": True,
            }
        )
    return unique_rows(family_rows, ("family_code",))


def build_misconception_rows() -> list[dict]:
    misconception_codes = set()
    for skill in PILOT_CONTENT["skills"]:
        misconception_codes.update(skill.get("misconception_tags", []))
    for template in PILOT_CONTENT["templates"]:
        misconception_codes.update(template.get("misconception_targets", []))

    rows = []
    for code in sorted(misconception_codes):
        name = code.replace("_", " ").title()
        rows.append(
            {
                "code": code,
                "name": name,
                "description": f"Auto-seeded misconception tag for {name}.",
            }
        )
    return rows


def build_skill_misconception_rows(misconception_id_lookup: dict[str, str]) -> list[dict]:
    rows = []
    for skill in PILOT_CONTENT["skills"]:
        for code in skill.get("misconception_tags", []):
            misconception_id = misconception_id_lookup.get(code)
            if misconception_id:
                rows.append({"skill_id": skill["skill_id"], "misconception_id": misconception_id})
    return unique_rows(rows, ("skill_id", "misconception_id"))


def build_template_misconception_rows(misconception_id_lookup: dict[str, str]) -> list[dict]:
    rows = []
    for template in PILOT_CONTENT["templates"]:
        for code in template.get("misconception_targets", []):
            misconception_id = misconception_id_lookup.get(code)
            if misconception_id:
                rows.append({"template_id": template["template_id"], "misconception_id": misconception_id})
    return unique_rows(rows, ("template_id", "misconception_id"))


def build_prerequisite_rows() -> list[dict]:
    rows = []
    for skill in PILOT_CONTENT["skills"]:
        for prerequisite_skill_id in skill.get("prerequisite_skill_ids", []):
            rows.append({"skill_id": skill["skill_id"], "prerequisite_skill_id": prerequisite_skill_id})
    return unique_rows(rows, ("skill_id", "prerequisite_skill_id"))


def main() -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("Set MWP_SUPABASE_URL and MWP_SUPABASE_SERVICE_KEY before seeding Supabase.")

    repository = SupabaseWorksheetRepository(settings.supabase_url, settings.supabase_service_key)
    repository.seed_table("skills", PILOT_CONTENT["skills"], "skill_id")

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

    repository.seed_table("templates", PILOT_CONTENT["templates"], "template_id")

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
        for blueprint in PILOT_CONTENT["blueprints"]
    ]
    repository.seed_table("worksheet_blueprints", blueprint_rows, "id")
    print("Seeded pilot worksheet content into Supabase.")


if __name__ == "__main__":
    main()
