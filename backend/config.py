"""Application configuration using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = ""
    vision_model: str = "claude-sonnet-4-5-20250929"
    vision_max_tokens: int = 4000

    # Database
    database_url: str = "sqlite:///./gcis_coa.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    storage_path: Path = Path("./storage")

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Image processing
    max_image_dimension: int = 1568  # Max px on longest side for Claude Vision

    # Admin auth
    admin_user: str = "admin"
    admin_password: str = "changeme"
    admin_secret_key: str = "change-this-to-a-random-secret"
    admin_token_expire_hours: int = 24

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def uploads_path(self) -> Path:
        p = self.storage_path / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def working_path(self) -> Path:
        p = self.storage_path / "working"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def redacted_path(self) -> Path:
        p = self.storage_path / "redacted"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def published_path(self) -> Path:
        p = self.storage_path / "published"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
