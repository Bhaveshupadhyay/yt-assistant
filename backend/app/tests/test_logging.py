"""Tests for JSON structured logging."""

import json
import logging
from app.core.config import Settings
from app.core.logging import JSONFormatter, get_logger, setup_logging


def test_json_formatter_structure():
    """Verify JSONFormatter produces valid JSON with required schema fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test log message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["logger"] == "test_logger"
    assert data["message"] == "Test log message"
    assert data["line"] == 42
    assert "timestamp" in data


def test_json_formatter_with_extra():
    """Verify JSONFormatter includes extra metadata."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=10,
        msg="Warning message",
        args=(),
        exc_info=None,
    )
    record.extra_data = {"session_id": "12345", "user": "tester"}  # type: ignore[attr-defined]
    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["session_id"] == "12345"
    assert data["user"] == "tester"


def test_setup_logging():
    """Verify setup_logging configures root logger without error."""
    settings = Settings(LOG_LEVEL="DEBUG", LOG_FORMAT="json")
    setup_logging(settings)
    logger = get_logger("app_test")
    assert logger is not None
