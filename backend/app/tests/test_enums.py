"""Tests for domain Enums."""

from app.core.enums import (
    ArtifactType,
    Environment,
    HealthStatus,
    LogFormat,
    LogLevel,
    MessageRole,
    ModelName,
    ModelProvider,
)


def test_artifact_type_enum():
    """Verify ArtifactType enum values."""
    assert ArtifactType.HTML == "html"
    assert ArtifactType.MARKDOWN == "markdown"
    assert ArtifactType.SVG == "svg"
    assert set(ArtifactType) == {ArtifactType.HTML, ArtifactType.MARKDOWN, ArtifactType.SVG}


def test_message_role_enum():
    """Verify MessageRole enum values."""
    assert MessageRole.USER == "user"
    assert MessageRole.ASSISTANT == "assistant"
    assert MessageRole.SYSTEM == "system"


def test_model_enums():
    """Verify ModelProvider and ModelName enum values."""
    assert ModelProvider.ANTHROPIC == "anthropic"
    assert ModelProvider.OPENAI == "openai"
    assert ModelProvider.OLLAMA == "ollama"

    assert ModelName.CLAUDE_3_5_SONNET == "claude-3-5-sonnet"
    assert ModelName.LLAMA_3_2 == "llama3.2"
    assert ModelName.GPT_4O == "gpt-4o"


def test_environment_and_logging_enums():
    """Verify Environment, LogFormat, LogLevel, and HealthStatus enums."""
    assert Environment.DEVELOPMENT == "development"
    assert Environment.PRODUCTION == "production"

    assert LogFormat.JSON == "json"
    assert LogFormat.CONSOLE == "console"

    assert LogLevel.INFO == "INFO"
    assert LogLevel.DEBUG == "DEBUG"

    assert HealthStatus.OK == "ok"
    assert HealthStatus.DEGRADED == "degraded"
