from functools import lru_cache

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.repositories.base import WorksheetRepository
from app.repositories.in_memory import InMemoryWorksheetRepository
from app.services.mastery_tracker import MasteryTracker


@lru_cache
def get_repository() -> WorksheetRepository:
    settings = get_settings()
    if not settings.use_inmemory_repository and settings.supabase_url:
        from app.repositories.supabase_repo import SupabaseWorksheetRepository

        server_key = settings.supabase_service_key or settings.supabase_publishable_key
        if server_key:
            return SupabaseWorksheetRepository(settings.supabase_url, server_key)
    return InMemoryWorksheetRepository()


def get_mastery_tracker() -> MasteryTracker:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mastery tracking requires MWP_SUPABASE_URL and MWP_SUPABASE_SERVICE_KEY.",
        )
    return MasteryTracker(settings.supabase_url, settings.supabase_service_key)
