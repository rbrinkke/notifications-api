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
    version=settings.API_VERSION,
    description="""Real-time notification service with multi-channel delivery (push, email, SMS).

Features subscription management, notification preferences, and delivery status tracking.

## Key Features
- Multi-channel notifications (push/email/SMS)
- User preference management
- Delivery status tracking
- Subscription tiers (free/premium)
- Template-based notification rendering

## Architecture
- Database: PostgreSQL with `activity` schema
- Queue: Redis for async delivery
- Auth: JWT Bearer + service tokens""",
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
    contact={"name": "Activity Platform Team", "email": "dev@activityapp.com"},
    license_info={"name": "Proprietary"}
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token from auth-api"
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

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
# Settings router - separate path to avoid conflict with /{notification_id}
app.include_router(
    settings_routes.router,
    prefix=f"{settings.API_V1_PREFIX}/settings",
    tags=["settings"]
)
# Notifications router
app.include_router(
    notifications.router,
    prefix=f"{settings.API_V1_PREFIX}/notifications",
    tags=["notifications"]
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
