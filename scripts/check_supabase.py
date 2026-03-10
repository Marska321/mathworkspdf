from app.core.config import get_settings
from app.repositories.supabase_repo import SupabaseWorksheetRepository


def main() -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise RuntimeError("Set MWP_SUPABASE_URL and MWP_SUPABASE_PUBLISHABLE_KEY before checking Supabase.")

    repository = SupabaseWorksheetRepository(settings.supabase_url, settings.supabase_publishable_key)
    total = repository.check_connection()
    print(f"Supabase connection OK. Sample query returned {total} row(s).")


if __name__ == "__main__":
    main()
