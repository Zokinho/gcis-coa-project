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

    # Microsoft / SharePoint
    ms_tenant_id: str = ""
    ms_client_id: str = ""
    ms_client_secret: str = ""

    # Zoho CRM
    zoho_client_id: str = ""
    zoho_client_secret: str = ""
    zoho_refresh_token: str = ""
    zoho_data_center: str = "CA"  # US, CA, or EU

    # Admin auth
    admin_user: str = "admin"
    admin_password: str = "changeme"
    admin_secret_key: str = "change-this-to-a-random-secret"
    admin_token_expire_hours: int = 24

    # IMAP email ingestion
    imap_host: str = ""
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""
    imap_use_ssl: bool = True
    imap_poll_interval_seconds: int = 120
    imap_folder: str = "INBOX"
    email_ingestion_enabled: bool = False

    # Evernote
    evernote_developer_token: str = ""
    evernote_sandbox: bool = False
    evernote_is_business: bool = True
    evernote_notebook_guid: str = ""

    # SMTP email notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_email: str = ""
    smtp_from_name: str = "GCIS CoA Automation"
    notification_admin_email: str = ""
    notifications_enabled: bool = False

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

    @property
    def email_attachments_path(self) -> Path:
        p = self.storage_path / "email_attachments"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def photos_path(self) -> Path:
        p = self.storage_path / "photos"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def evernote_imports_path(self) -> Path:
        p = self.storage_path / "evernote_imports"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
