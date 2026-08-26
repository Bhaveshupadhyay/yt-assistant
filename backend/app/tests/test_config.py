"""Tests for configuration and environment settings with Enums."""

import pytest
from pydantic import ValidationError
from app.core.config import Settings, get_settings
from app.core.enums import Environment, LogFormat, LogLevel, ModelName


def test_default_settings():
    """Verify default settings values and enum instances in isolation from local env files."""
    settings = Settings(_env_file=None)
    assert settings.APP_NAME == "The Lenny Growth Assistant"
    assert settings.APP_VERSION == "1.0.0"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.ENVIRONMENT == Environment.DEVELOPMENT
    assert settings.LOG_LEVEL == LogLevel.INFO
    assert settings.LOG_FORMAT == LogFormat.JSON
    assert settings.OLLAMA_BASE_URL == "http://localhost:11434"
    assert settings.OLLAMA_MODEL == ModelName.LLAMA_3_2_1B.value
    assert settings.QDRANT_URL == "http://localhost:6333"
    assert settings.QDRANT_COLLECTION_NAME == "lenny_transcripts"
    assert "https://lennyai.clientmanger.tech" in settings.CORS_ORIGINS
    assert settings.CORS_ORIGIN_REGEX is not None


def test_cors_origins_parsing():
    """Verify CORS origins validator parses list and strings."""
    # List format
    s1 = Settings(CORS_ORIGINS=["http://localhost:3000", "http://example.com"])
    assert s1.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]

    # Comma-separated string format
    s2 = Settings(CORS_ORIGINS="http://localhost:3000, http://example.com")
    assert s2.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]

    # JSON array string format
    s3 = Settings(CORS_ORIGINS='["http://localhost:3000", "http://example.com"]')
    assert s3.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]


def test_cors_origin_regex_configuration():
    """Verify CORS origin regex custom configuration."""
    s = Settings(CORS_ORIGIN_REGEX=r"https://custom-domain\.com")
    assert s.CORS_ORIGIN_REGEX == r"https://custom-domain\.com"


def test_cors_origins_invalid_rejections():
    """Verify CORS origins validator strictly rejects invalid inputs."""
    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS=None)

    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS="[invalid-json")

    with pytest.raises(ValidationError):
        Settings(CORS_ORIGINS="")


def test_database_properties():
    """Verify is_sqlite and is_postgres helper properties."""
    sqlite_settings = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db")
    assert sqlite_settings.is_sqlite is True
    assert sqlite_settings.is_postgres is False

    pg_settings = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db")
    assert pg_settings.is_sqlite is False
    assert pg_settings.is_postgres is True


def test_get_settings_cached():
    """Verify get_settings returns singleton cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
