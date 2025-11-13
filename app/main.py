"""
FastAPI application initialization.
Sets up middleware, routes, and lifecycle events.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.core.logging_config import setup_logging
from app.core.database import db
from app.middleware.correlation import CorrelationMiddleware
from app.routes import health, notifications, settings as settings_routes

# Setup logging
setup_logging(settings.ENVIRONMENT, settings.LOG_LEVEL)
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None
)

# Add CORS middleware
cors_origins = ["*"] if settings.CORS_ORIGINS == "*" else [
    origin.strip() for origin in settings.CORS_ORIGINS.split(",")
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.add_middleware(CorrelationMiddleware)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(
    notifications.router,
    prefix=f"{settings.API_V1_PREFIX}/notifications",
    tags=["notifications"]
)
app.include_router(
    settings_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/notifications/settings",
    tags=["settings"]
)

# Startup event
@app.on_event("startup")
async def startup():
    """Initialize database connection on startup"""
    logger.info(
        "api_starting",
        environment=settings.ENVIRONMENT,
        project=settings.PROJECT_NAME
    )
    await db.connect(settings.database_url)
    logger.info("api_started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown"""
    logger.info("api_shutting_down")
    await db.disconnect()
    logger.info("api_shutdown_complete")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "running"
    }
