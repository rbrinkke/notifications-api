"""
PostgreSQL connection pool management.
Uses asyncpg for async database operations.
"""
import asyncpg
from typing import Optional
import structlog

logger = structlog.get_logger()

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self, database_url: str):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=10,
                max_size=100,
                command_timeout=60
            )
            logger.info("database_connected", pool_size=10)
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise

    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("database_disconnected")

    async def execute_sp(self, procedure_name: str, *args):
        """
        Execute stored procedure and return results.

        Args:
            procedure_name: Full procedure name (e.g., 'activity.sp_get_user_notifications')
            *args: Procedure parameters in order

        Returns:
            List of Record objects from database
        """
        async with self.pool.acquire() as conn:
            # Build parameter placeholders: $1, $2, $3, etc.
            placeholders = ", ".join([f"${i+1}" for i in range(len(args))])
            query = f"SELECT * FROM {procedure_name}({placeholders})"

            logger.debug(
                "executing_stored_procedure",
                procedure=procedure_name,
                param_count=len(args)
            )

            result = await conn.fetch(query, *args)
            return result

# Global database instance
db = Database()
