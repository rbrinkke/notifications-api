"""
Structured logging configuration with correlation IDs.
Uses structlog for JSON logging in production.
"""
import structlog
import logging

def setup_logging(environment: str, log_level: str):
    """
    Configure structured logging.

    Args:
        environment: "development" or "production"
        log_level: "DEBUG", "INFO", "WARNING", "ERROR"
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set root logger level
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper())
    )
