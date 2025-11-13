"""
Correlation ID middleware for request tracing.
Adds X-Trace-ID header to all requests and responses.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog
import uuid

class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Trace-ID"] = correlation_id

        # Clear context
        structlog.contextvars.clear_contextvars()

        return response
