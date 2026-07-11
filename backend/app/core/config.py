"""
AI-CRE WIMLOGIC V1

Application configuration.
"""

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings"""

    # ---------------------------------------------------------
    # Pydantic Settings
    # ---------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------------------------------------------------------
    # Application
    # ---------------------------------------------------------

    APP_NAME: str = "AI-CRE WIMLOGIC V1"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI-CRE WIMLOGIC V1"

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "ai_cre_wimlogic"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # ---------------------------------------------------------
    # Debug
    # ---------------------------------------------------------

    DEBUG: bool = True

    # ---------------------------------------------------------
    # Storage (Phase 3A -- Enterprise Image Upload & Workflow Integration)
    # ---------------------------------------------------------

    # Root directory for all filesystem-stored business assets. Relative
    # paths are stored in the database; this is the base they are resolved
    # against at runtime. Works on Windows and Linux because pathlib.Path
    # handles separators natively.
    UPLOAD_ROOT: str = "uploads"

    # Sub-directory (under UPLOAD_ROOT) containing one folder per property.
    PROPERTIES_SUBDIR: str = "properties"

    # Maximum accepted upload size per file, in megabytes.
    MAX_UPLOAD_SIZE_MB: int = 25

    # Accepted image file extensions for upload/import (lowercase, no dot).
    ALLOWED_IMAGE_EXTENSIONS: str = "jpg,jpeg,png,webp"

    # Longest edge (in pixels) for generated thumbnails.
    THUMBNAIL_MAX_DIMENSION: int = 400

    # Timeout (seconds) for outbound URL image imports.
    URL_IMPORT_TIMEOUT_SECONDS: int = 15

    # ---------------------------------------------------------
    # Phase 4 -- DEV-TOOLS Integration (Enterprise Payload Builder)
    # ---------------------------------------------------------

    # Publicly reachable base URL of this AI-CRE backend (no trailing slash),
    # e.g. "http://127.0.0.1:8000" in dev or "https://ai-cre.example.com" in
    # production. Required so outbound payloads sent to the external
    # DEV-TOOLS orchestrator contain fetchable absolute image URLs rather
    # than the relative paths stored in the database. Mirrors the existing
    # "/uploads" static mount already registered in main.py.
    APP_BASE_URL: str = "http://127.0.0.1:8000"

    # ---------------------------------------------------------
    # Phase 1A-BE -- WACP Client SDK Integration
    # ---------------------------------------------------------
    #
    # AI-CRE speaks WACP exclusively through the official WACP Client SDK
    # (wacp.client.WacpClient) - see services/wacp_adapter.py, which is
    # the one and only module that constructs a WacpClient. No other module
    # may import wacp.client directly (Backend Generation Standard:
    # business logic stays in services; this is a service-layer integration
    # concern).
    #
    # Named WACP_* rather than DEVTOOLS_* deliberately: AI-CRE integrates
    # with the WACP protocol, not with any particular server implementation.
    # DEV-TOOLS WIMLOGIC is the WACP-compliant server this deployment happens
    # to point at today; a future WACP-compliant server would need only
    # these same settings repointed, not a naming/adapter rewrite.
    #
    # These replace the previous DEVTOOLS_API_BASE_URL /
    # DEVTOOLS_API_KEY-as-Bearer-token scheme, which targeted the legacy,
    # now-retired Enterprise Payload Protocol endpoints and does not work
    # against a WACP 1.0 server.

    # Root origin of the WACP server, no trailing slash and no path suffix,
    # e.g. "https://devtools.wimlogic.internal". The WACP Client SDK owns
    # the "/wacp/v1/..." path templates internally - do not include any
    # path segment here.
    #
    # NOTE: wacp.client.ClientConfig requires an "https://" URL (enforces
    # 10_WACP_PROTOCOL.md §16.3's TLS 1.2+ transport requirement) and will
    # raise ValueError on construction otherwise. A plain-HTTP WACP server
    # dev instance will need TLS in front of it (e.g. a local reverse
    # proxy) before AI-CRE can reach it - this is a deliberate SDK-enforced
    # constraint, not a bug in this adapter.
    WACP_BASE_URL: str = ""

    # Identifies AI-CRE as the submitting Business Application. Must equal
    # the application_id AI-CRE was registered under with the WACP server,
    # and is sent as both the X-WACP-Application-Id header and
    # wacp.application_id in every envelope (10_WACP_PROTOCOL.md §7.2, §8).
    WACP_APPLICATION_ID: str = ""

    # AI-CRE's WACP API key, sent as the X-WACP-Api-Key header (§8, §16.1).
    WACP_API_KEY: str = ""

    # AI-CRE's WACP API secret, sent as the X-WACP-Api-Secret header and
    # used to verify inbound callback signatures if callback_url is ever
    # registered (§8, §16.1, §17.3).
    WACP_API_SECRET: str = ""

    # Timeout (seconds) for outbound WACP calls. Passed through to
    # wacp.client.ClientConfig.timeout_seconds.
    WACP_TIMEOUT_SECONDS: int = 30

    # When false, check_workflow_status() behaves exactly like the
    # pre-Phase-4 implementation (local status only, no outbound call).
    # When true, it actively polls the WACP server and, on a terminal
    # status, fetches and synchronizes results via the same result_sync
    # implementation the webhook callback uses.
    ENABLE_WACP_POLLING: bool = True

    # WACP company_id sent on every job envelope (10_WACP_PROTOCOL.md §7.2
    # requires company_id on every envelope). This is pure WACP transport
    # metadata, not an AI-CRE business concept: AI-CRE is a single-workspace,
    # open-source application - one dedicated VPS and one dedicated database
    # per customer deployment - and deliberately has no Company or Tenant
    # entity of its own. This value is read from configuration and passed
    # straight through to the WACP envelope; it is never persisted in any
    # AI-CRE business table, and no Company/Tenant model should ever be
    # introduced to back it.
    WACP_COMPANY_ID: str = "AI-CRE-DEFAULT"

    # ---------------------------------------------------------
    # SQLAlchemy URL
    # ---------------------------------------------------------

    @property
    def DATABASE_URL(self) -> str:
        password = quote_plus(self.DB_PASSWORD)

        return (
            f"mysql+pymysql://"
            f"{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )


settings = Settings()


# ---------------------------------------------------------
# Startup Debug
# Remove after backend is fully validated
# ---------------------------------------------------------

print("=" * 70)
print("AI-CRE CONFIG LOADED")
print("=" * 70)
print(f"DB_HOST     : {settings.DB_HOST}")
print(f"DB_PORT     : {settings.DB_PORT}")
print(f"DB_NAME     : {settings.DB_NAME}")
print(f"DB_USER     : {settings.DB_USER}")
print(f"PASSWORD LEN: {len(settings.DB_PASSWORD)}")
print(
    f"DATABASE_URL: mysql+pymysql://{settings.DB_USER}:********@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)
print("=" * 70)
