"""
Health check endpoint for monitoring.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import structlog

from app.core.database import db

router = APIRouter()
logger = structlog.get_logger()

@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns 200 if API is healthy, 503 if degraded.
    """
    checks = {
        "api": "ok"
    }

    # Check database connection
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        logger.error("health_check_database_failed", error=str(e))
        checks["database"] = "error"

    # Determine overall status
    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if all_ok else "degraded",
            "checks": checks
        }
    )
