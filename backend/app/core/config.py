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
