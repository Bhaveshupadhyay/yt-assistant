"""Custom domain exceptions and centralized FastAPI exception handlers."""

import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected internal error occurred."

    def __init__(
        self,
        message: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.default_message
        if status_code is not None:
            self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class OllamaUnavailableException(AppException):
    """Raised when the local Ollama daemon is unreachable or fails to respond."""

    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message: str = (
        "Ollama daemon is unreachable on http://localhost:11434. "
        "Ensure Ollama is running (`ollama serve`) or toggle to a Cloud provider (Claude/OpenAI)."
    )

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        super().__init__(message=message or self.default_message, status_code=self.status_code, details=details)


class TranscriptNotFoundException(AppException):
    """Raised when knowledge base transcripts or chunks cannot be found."""

    status_code: int = status.HTTP_404_NOT_FOUND
    default_message: str = (
        "I could not find specific insights or discussions on this topic within the available Lenny's Podcast transcripts."
    )

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        super().__init__(message=message or self.default_message, status_code=self.status_code, details=details)


class SessionNotFoundException(AppException):
    """Raised when a requested chat session does not exist."""

    status_code: int = status.HTTP_404_NOT_FOUND

    def __init__(self, session_id: Any, details: Any = None) -> None:
        message = f"Chat session '{session_id}' was not found."
        super().__init__(message=message, status_code=self.status_code, details=details)


class MessageNotFoundException(AppException):
    """Raised when a requested message does not exist."""

    status_code: int = status.HTTP_404_NOT_FOUND

    def __init__(self, message_id: Any, details: Any = None) -> None:
        message = f"Message '{message_id}' was not found."
        super().__init__(message=message, status_code=self.status_code, details=details)


class ArtifactNotFoundException(AppException):
    """Raised when a requested artifact does not exist."""

    status_code: int = status.HTTP_404_NOT_FOUND

    def __init__(self, artifact_id: Any, details: Any = None) -> None:
        message = f"Artifact '{artifact_id}' was not found."
        super().__init__(message=message, status_code=self.status_code, details=details)


class ModelProviderException(AppException):
    """Raised when an external model provider (Claude, OpenAI) returns an error."""

    status_code: int = status.HTTP_502_BAD_GATEWAY
    default_message: str = "Model provider encountered an upstream error."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        super().__init__(message=message or self.default_message, status_code=self.status_code, details=details)


class DatabaseException(AppException):
    """Raised when an internal database error occurs."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "Database operation failed."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        super().__init__(message=message or self.default_message, status_code=self.status_code, details=details)


class ValidationException(AppException):
    """Raised for custom input validation errors."""

    status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT
    default_message: str = "Validation failed for the requested operation."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        super().__init__(message=message or self.default_message, status_code=self.status_code, details=details)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles all domain-specific AppExceptions."""
    logger.warning(
        "Application exception handled",
        extra={"extra_data": {"path": request.url.path, "status_code": exc.status_code, "error": exc.message}},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles FastAPI/Pydantic request validation errors."""
    logger.warning(
        "Request validation failed",
        extra={"extra_data": {"path": request.url.path, "errors": exc.errors()}},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Invalid request payload or query parameters.",
                "details": exc.errors(),
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions."""
    logger.exception(
        "Unhandled server exception",
        extra={"extra_data": {"path": request.url.path, "error": str(exc)}},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An internal server error occurred. Please check server logs.",
                "details": None,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers exception handlers onto the FastAPI application instance."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
