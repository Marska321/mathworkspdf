from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CAPS Worksheet Engine"
    api_prefix: str = "/api"
    default_curriculum: str = "CAPS"
    default_language: str = "en"
    generation_max_attempts: int = 60
    use_inmemory_repository: bool = True
    supabase_url: str | None = None
    supabase_key: str | None = None
    supabase_publishable_key: str | None = None
    supabase_service_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MWP_",
        extra="ignore",
    )

    @field_validator("supabase_url", "supabase_key", "supabase_publishable_key", "supabase_service_key")
    @classmethod
    def normalize_empty_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def fill_legacy_key_fields(self) -> "Settings":
        if self.supabase_publishable_key is None and self.supabase_key is not None:
            self.supabase_publishable_key = self.supabase_key
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
