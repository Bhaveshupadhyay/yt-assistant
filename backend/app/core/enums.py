"""Application domain enums to prevent hardcoded strings."""

from enum import StrEnum


class ArtifactType(StrEnum):
    """Supported artifact formats."""

    HTML = "html"
    MARKDOWN = "markdown"
    SVG = "svg"


class MessageRole(StrEnum):
    """Supported message sender roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ModelProvider(StrEnum):
    """Supported LLM provider backends."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class ModelName(StrEnum):
    """Supported and common model identifiers."""

    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    LLAMA_3_2 = "llama3.2"
    MISTRAL = "mistral"
    QWEN_2_5 = "qwen2.5"
    DEEPSEEK_R1 = "deepseek-r1"


class Environment(StrEnum):
    """Runtime environment names."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogFormat(StrEnum):
    """Logging format options."""

    JSON = "json"
    CONSOLE = "console"


class LogLevel(StrEnum):
    """Standard log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class HealthStatus(StrEnum):
    """Health check status levels."""

    OK = "ok"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
