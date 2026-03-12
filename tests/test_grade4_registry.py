from app.repositories.in_memory import InMemoryWorksheetRepository
from app.services.grade4_coverage import validate_grade4_coverage_map, validate_grade4_registry
from app.services.misconception_catalog import validate_misconception_references
from app.templates.loader import load_template_library


def test_loader_exposes_grade4_governance_artifacts() -> None:
    library = load_template_library()
    assert library["grade4_family_registry"]
    assert library["grade4_family_coverage_map"]


def test_repository_exposes_grade4_governance_artifacts() -> None:
    repository = InMemoryWorksheetRepository()
    assert repository.get_grade4_family_registry()
    assert repository.get_grade4_family_coverage_map()


def test_grade4_registry_references_are_valid() -> None:
    assert validate_grade4_registry() == []


def test_grade4_coverage_map_matches_library_and_tests() -> None:
    assert validate_grade4_coverage_map() == []


def test_misconception_catalog_covers_grade4_registry_references() -> None:
    assert validate_misconception_references() == []


def test_every_registry_family_has_coverage_entry() -> None:
    library = load_template_library()
    registry_codes = {item["family_code"] for item in library["grade4_family_registry"]}
    coverage_codes = {item["family_code"] for item in library["grade4_family_coverage_map"]}
    assert registry_codes == coverage_codes


def test_every_priority_one_registry_family_is_tracked() -> None:
    library = load_template_library()
    priority_one = [item for item in library["grade4_family_registry"] if item["priority"] == 1]
    assert priority_one
    assert all("family_code" in item and item["allowed_patterns"] for item in priority_one)
