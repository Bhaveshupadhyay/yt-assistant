"""Tests for domain custom exceptions."""

from fastapi import status
from app.core.exceptions import (
    AppException,
    ArtifactNotFoundException,
    DatabaseException,
    MessageNotFoundException,
    ModelProviderException,
    OllamaUnavailableException,
    SessionNotFoundException,
    TranscriptNotFoundException,
    ValidationException,
)


def test_custom_domain_exceptions_status_codes():
    """Verify each custom domain exception has the appropriate HTTP status code."""
    assert OllamaUnavailableException().status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert TranscriptNotFoundException().status_code == status.HTTP_404_NOT_FOUND
    assert SessionNotFoundException("dummy-id").status_code == status.HTTP_404_NOT_FOUND
    assert MessageNotFoundException("dummy-id").status_code == status.HTTP_404_NOT_FOUND
    assert ArtifactNotFoundException("dummy-id").status_code == status.HTTP_404_NOT_FOUND
    assert ModelProviderException().status_code == status.HTTP_502_BAD_GATEWAY
    assert DatabaseException().status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert ValidationException().status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_ollama_unavailable_exception_message():
    """Verify Ollama exception message contains actionable advice."""
    exc = OllamaUnavailableException()
    assert "http://localhost:11434" in exc.message
    assert "ollama serve" in exc.message


def test_transcript_not_found_exception_message():
    """Verify zero-hallucination fallback message requirement."""
    exc = TranscriptNotFoundException()
    assert "Lenny's Podcast transcripts" in exc.message
