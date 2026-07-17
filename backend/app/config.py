from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./caos.db"
    jwt_secret: str = "local-development-secret-change-me"
    cors_origins: str = "http://localhost:5173"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    debug: bool = False
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    stepik_client_id: str = ""
    stepik_client_secret: str = ""
    stepik_redirect_uri: str = "http://localhost:8000/api/v1/auth/stepik/callback"
    frontend_url: str = "http://localhost:5173"
    stepik_course_ids: str = "288738,288774,285340"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@caos.thinkred.ru"
    audit_retention_days: int = 90

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def validate_production(self) -> None:
        """Fail-fast if default secrets are used in production (non-SQLite DB)."""
        is_prod = not self.database_url.startswith("sqlite")
        if is_prod:
            if self.jwt_secret == "local-development-secret-change-me":
                raise RuntimeError("JWT_SECRET must be set to a non-default value in production")
            if "change-me" in self.database_url:
                raise RuntimeError("POSTGRES_PASSWORD must be set to a non-default value in production")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def stepik_course_id_list(self) -> list[int]:
        return [int(item.strip()) for item in self.stepik_course_ids.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.validate_production()
    return s
