"""
Custom exception classes and database error mapping.
Maps PostgreSQL exceptions to HTTP status codes.
"""
from fastapi import HTTPException
import structlog

logger = structlog.get_logger()

# Exception name -> HTTP status code mapping
EXCEPTION_MAPPING = {
    "NOTIFICATION_NOT_FOUND": 404,
    "USER_NOT_FOUND": 404,
    "USER_NOT_FOUND_OR_INACTIVE": 404,
    "UNAUTHORIZED_ACCESS": 403,
    "PREMIUM_FEATURE_REQUIRED": 403,
}

def handle_db_exception(e: Exception) -> HTTPException:
    """
    Map PostgreSQL exception to HTTPException.

    Args:
        e: Exception from database

    Returns:
        HTTPException with appropriate status code and message
    """
    error_message = str(e)

    # Check if error matches known exception patterns
    for exception_name, status_code in EXCEPTION_MAPPING.items():
        if exception_name in error_message:
            # Clean error message
            clean_message = error_message.split(": ", 1)[-1] if ": " in error_message else error_message
            logger.warning(
                "database_exception",
                exception_type=exception_name,
                status_code=status_code
            )
            return HTTPException(status_code=status_code, detail=clean_message)

    # Unknown error - log and return 500
    logger.error("unexpected_database_error", error=error_message)
    return HTTPException(status_code=500, detail="Internal server error")

class AppException(HTTPException):
    """Base exception for application errors"""
    pass

class ValidationException(AppException):
    """Validation error (422)"""
    def __init__(self, message: str):
        super().__init__(status_code=422, detail=message)

class NotFoundException(AppException):
    """Resource not found (404)"""
    def __init__(self, resource: str):
        super().__init__(status_code=404, detail=f"{resource} not found")

class UnauthorizedException(AppException):
    """Unauthorized access (401)"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(status_code=401, detail=message)

class ForbiddenException(AppException):
    """Forbidden access (403)"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(status_code=403, detail=message)
