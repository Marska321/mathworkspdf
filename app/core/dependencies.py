from functools import lru_cache

from app.core.config import get_settings
from app.repositories.base import WorksheetRepository
from app.repositories.in_memory import InMemoryWorksheetRepository


@lru_cache
def get_repository() -> WorksheetRepository:
    settings = get_settings()
    if not settings.use_inmemory_repository and settings.supabase_url:
        from app.repositories.supabase_repo import SupabaseWorksheetRepository

        server_key = settings.supabase_service_key or settings.supabase_publishable_key
        if server_key:
            return SupabaseWorksheetRepository(settings.supabase_url, server_key)
    return InMemoryWorksheetRepository()
