"""
Custom exception handling with structured error responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Optional, Any
import structlog

logger = structlog.get_logger()


class OmniCodeException(Exception):
    """Base exception for OmniCode application."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(OmniCodeException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_FAILED",
            details=details,
        )


class AuthorizationError(OmniCodeException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_FAILED",
            details=details,
        )


class ResourceNotFoundError(OmniCodeException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "id": resource_id},
        )


class ValidationError(OmniCodeException):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class RateLimitError(OmniCodeException):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            message="Rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after} if retry_after else {},
        )


class ExternalServiceError(OmniCodeException):
    """Raised when an external service (GitHub, OpenAI, etc.) fails."""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
        )


class DatabaseError(OmniCodeException):
    """Raised when database operations fail."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
        )


class CacheError(OmniCodeException):
    """Raised when cache operations fail."""

    def __init__(self, message: str = "Cache operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CACHE_ERROR",
        )


def create_error_response(
    request: Request,
    exc: OmniCodeException,
    correlation_id: Optional[str] = None,
) -> dict:
    """Create a structured error response."""
    response = {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
        "meta": {
            "request_id": correlation_id or request.headers.get("x-correlation-id", "unknown"),
        },
    }
    return response


async def omni_exception_handler(request: Request, exc: OmniCodeException) -> JSONResponse:
    """Handle OmniCode exceptions and return structured JSON responses."""
    correlation_id = request.headers.get("x-correlation-id")

    logger.error(
        "request_error",
        error_code=exc.error_code,
        error_message=exc.message,
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        details=exc.details,
    )

    content = create_error_response(request, exc, correlation_id)

    headers = {}
    if isinstance(exc, RateLimitError) and exc.details.get("retry_after"):
        headers["Retry-After"] = str(exc.details["retry_after"])

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=headers,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with safe error responses."""
    correlation_id = request.headers.get("x-correlation-id")

    logger.exception(
        "unexpected_error",
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        error_type=type(exc).__name__,
    )

    content = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        },
        "meta": {
            "request_id": correlation_id or "unknown",
        },
    }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
    )