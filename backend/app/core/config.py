
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CampusPulse"
    app_version: str = "0.1.0"
    app_environment: str = "development"
    api_prefix: str = "/api"

    # --- Authentication configuration ---
    # Secret used to sign access tokens. REQUIRED in production; when unset in
    # development an ephemeral per-process secret is generated with a warning.
    auth_jwt_secret: str = ""
    auth_jwt_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 480

    # Comma-separated roles that public self-registration may create.
    # Privileged roles must be provisioned by a trusted process (for example
    # the development/demo seeding path) instead of open registration.
    self_registration_roles: str = "student,mentor"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
