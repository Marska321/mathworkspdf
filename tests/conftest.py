import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_repository
from app.main import app
from app.repositories.in_memory import InMemoryWorksheetRepository


@pytest.fixture
def repository() -> InMemoryWorksheetRepository:
    repo = InMemoryWorksheetRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    return repo


@pytest.fixture
def client(repository: InMemoryWorksheetRepository) -> TestClient:
    return TestClient(app)
