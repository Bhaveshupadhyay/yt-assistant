"""Application configuration and settings management using Pydantic v2 and Enums."""

from functools import lru_cache
from typing import Any
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.enums import Environment, LogFormat, LogLevel, ModelName


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General App Settings
    APP_NAME: str = "The Lenny Growth Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Runtime environment (development, staging, production, testing)",
    )
    API_V1_PREFIX: str = "/api/v1"

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./lenny_assistant.db",
        description="Async database connection string (PostgreSQL or SQLite)",
    )
    POSTGRES_DB: str | None = Field(
        default=None,
        description="Optional PostgreSQL database URL alias",
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Enable SQLAlchemy query echo for debugging",
    )

    # Vector Database (Qdrant)
    QDRANT_URL: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL",
    )
    QDRANT_ENDPOINT: str | None = Field(
        default=None,
        description="Optional Qdrant endpoint alias",
    )
    QDRANT_API_KEY: str | None = Field(
        default=None,
        description="Optional Qdrant Cloud / Server API Key",
    )
    QDRANT_KEY: str | None = Field(
        default=None,
        description="Optional Qdrant API key alias",
    )
    QDRANT_COLLECTION_NAME: str = Field(
        default="lenny_transcripts",
        description="Qdrant collection name for Lenny transcript chunks",
    )
    QDRANT_STORAGE_PATH: str | None = Field(
        default=None,
        description="Optional path to local embedded Qdrant disk storage",
    )

    # Embedding Models (FastEmbed high-precision local models)
    EMBEDDING_DENSE_MODEL: str = Field(
        default="BAAI/bge-base-en-v1.5",
        description="FastEmbed dense embedding model (~210MB RAM, 768 dimensions, top MTEB benchmark)",
    )
    EMBEDDING_SPARSE_MODEL: str = Field(
        default="prithivida/Splade_PP_en_v1",
        description="FastEmbed neural sparse embedding model (SPLADE++, ~530MB RAM)",
    )
    EMBEDDING_DENSE_DIMENSION: int = Field(
        default=768,
        description="Vector dimension for the dense embedding model",
    )


    # Transcripts Corpus
    TRANSCRIPTS_DIR: str = Field(
        default="../data/transcripts",
        description="Default path to curated transcripts corpus directory",
    )

    # Local LLM (Ollama)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama local daemon URL",
    )
    OLLAMA_MODEL: str = Field(
        default=ModelName.LLAMA_3_2_1B.value,
        description="Default local Ollama model identifier",
    )

    # Cloud LLM Providers
    ANTHROPIC_API_KEY: str | None = Field(
        default=None,
        description="Anthropic Claude API Key",
    )
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API Key",
    )
    GEMINI_API_KEY: str | None = Field(
        default=None,
        description="Google Gemini API Key",
    )

    # CORS Origins
    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "https://bhaveshupadhyay.github.io",
            "https://lennyai.clientmanger.tech",
        ],
        description="Allowed CORS origins for the frontend client",
    )
    CORS_ORIGIN_REGEX: str | None = Field(
        default=r"https?://.*(clientmanger\.tech|github\.io|vercel\.app|onrender\.com)",
        description="Optional regex pattern for allowed CORS origins",
    )

    # Logging Configuration
    LOG_LEVEL: LogLevel = Field(
        default=LogLevel.INFO,
        description="Standard logging level",
    )
    LOG_FORMAT: LogFormat = Field(
        default=LogFormat.JSON,
        description="Log output format: JSON or CONSOLE",
    )

    @model_validator(mode="after")
    def resolve_aliases_and_url_schemes(self) -> "Settings":
        """Resolve aliases for database and Qdrant endpoints and normalize URL schemes."""
        if self.POSTGRES_DB and (self.DATABASE_URL == "sqlite+aiosqlite:///./lenny_assistant.db" or not self.DATABASE_URL):
            self.DATABASE_URL = self.POSTGRES_DB

        if self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

        if self.QDRANT_ENDPOINT and (self.QDRANT_URL == "http://localhost:6333" or not self.QDRANT_URL):
            self.QDRANT_URL = self.QDRANT_ENDPOINT

        if self.QDRANT_KEY and not self.QDRANT_API_KEY:
            self.QDRANT_API_KEY = self.QDRANT_KEY

        return self

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """Support JSON arrays, comma-separated strings, or list of strings."""
        if v is None:
            raise ValueError("CORS_ORIGINS cannot be None")
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("CORS_ORIGINS cannot be empty")
            if stripped.startswith("[") or stripped.endswith("]"):
                if not (stripped.startswith("[") and stripped.endswith("]")):
                    raise ValueError(f"Malformed JSON array for CORS_ORIGINS: {stripped}")
                import json

                try:
                    parsed = json.loads(stripped)
                    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
                        raise ValueError("CORS_ORIGINS JSON array must contain strings")
                    return parsed
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON for CORS_ORIGINS: {exc}") from exc
            return [i.strip() for i in stripped.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            if not all(isinstance(x, str) for x in v):
                raise ValueError("All CORS_ORIGINS elements must be strings")
            return list(v)
        raise ValueError(f"Unsupported CORS_ORIGINS type: {type(v).__name__}")

    @property
    def is_sqlite(self) -> bool:
        """Helper to determine if current database is SQLite."""
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        """Helper to determine if current database is PostgreSQL."""
        return "postgresql" in self.DATABASE_URL or "postgres" in self.DATABASE_URL


@lru_cache
def get_settings() -> Settings:
    """Cached settings dependency."""
    return Settings()
