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

    # API key (for service-to-service auth from marketplace)
    coa_api_key: str = ""

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173,https://harvex.app"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Image processing
    max_image_dimension: int = 1568  # Max px on longest side for Claude Vision

    # Microsoft / SharePoint
    ms_tenant_id: str = ""
    ms_client_id: str = ""
    ms_client_secret: str = ""

    # SharePoint default upload destination (for automated uploads)
    sp_default_site_id: str = ""
    sp_default_drive_id: str = ""
    sp_default_folder_id: str = ""

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
    imap_use_oauth2: bool = False  # Use OAuth2 (XOAUTH2) instead of password auth

    # Email ingestion security
    email_sender_allowlist: str = ""            # Comma-separated trusted sender domains/addresses, empty = accept all
    max_pdf_file_size_mb: int = 50              # Max attachment size in MB
    max_pdf_page_count: int = 100               # Max pages per PDF
    pdf_conversion_timeout_seconds: int = 120   # Timeout for pdf2image conversion

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
    def sender_allowlist(self) -> list[str]:
        if not self.email_sender_allowlist:
            return []
        return [s.strip().lower() for s in self.email_sender_allowlist.split(",") if s.strip()]

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
