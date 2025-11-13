"""
Settings business logic service.
Calls stored procedures for notification settings.
"""
from typing import Optional
from uuid import UUID
import structlog

from app.core.database import db
from app.core.exceptions import handle_db_exception
from app.schemas.settings import NotificationSettingsResponse

logger = structlog.get_logger()

class SettingsService:
    """Service for notification settings operations"""

    async def get_settings(self, user_id: UUID) -> NotificationSettingsResponse:
        """
        Get user's notification settings.

        Calls: activity.sp_get_notification_settings
        """
        try:
            result = await db.execute_sp(
                "activity.sp_get_notification_settings",
                user_id
            )

            if not result:
                # Should not happen (SP returns defaults)
                raise Exception("USER_NOT_FOUND")

            row = result[0]

            return NotificationSettingsResponse(
                user_id=row["user_id"],
                email_notifications=row["email_notifications"],
                push_notifications=row["push_notifications"],
                activity_reminders=row["activity_reminders"],
                community_updates=row["community_updates"],
                friend_requests=row["friend_requests"],
                marketing_emails=row["marketing_emails"],
                ghost_mode=row["ghost_mode"],
                language=row["language"],
                timezone=row["timezone"]
            )

        except Exception as e:
            raise handle_db_exception(e)

    async def update_settings(
        self,
        user_id: UUID,
        email_notifications: Optional[bool],
        push_notifications: Optional[bool],
        activity_reminders: Optional[bool],
        community_updates: Optional[bool],
        friend_requests: Optional[bool],
        marketing_emails: Optional[bool],
        ghost_mode: Optional[bool],
        language: Optional[str],
        timezone: Optional[str]
    ) -> NotificationSettingsResponse:
        """
        Update user's notification settings.

        Calls: activity.sp_update_notification_settings
        """
        try:
            result = await db.execute_sp(
                "activity.sp_update_notification_settings",
                user_id,
                email_notifications,
                push_notifications,
                activity_reminders,
                community_updates,
                friend_requests,
                marketing_emails,
                ghost_mode,
                language,
                timezone
            )

            if not result:
                raise Exception("USER_NOT_FOUND")

            row = result[0]

            logger.info(
                "settings_updated",
                user_id=str(user_id),
                ghost_mode=row["ghost_mode"]
            )

            return NotificationSettingsResponse(
                user_id=row["user_id"],
                email_notifications=row["email_notifications"],
                push_notifications=row["push_notifications"],
                activity_reminders=row["activity_reminders"],
                community_updates=row["community_updates"],
                friend_requests=row["friend_requests"],
                marketing_emails=row["marketing_emails"],
                ghost_mode=row["ghost_mode"],
                language=row["language"],
                timezone=row["timezone"],
                updated_at=row["updated_at"]
            )

        except Exception as e:
            raise handle_db_exception(e)
