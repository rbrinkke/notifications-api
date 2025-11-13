"""
Notification business logic service.
Calls stored procedures and formats results.
"""
from typing import List, Optional
from uuid import UUID
import structlog

from app.core.database import db
from app.core.exceptions import handle_db_exception
from app.schemas.notifications import (
    NotificationResponse,
    ActorInfo,
    NotificationType,
    NotificationStatus,
    UnreadCountResponse,
    MarkReadResponse,
    DeleteResponse,
    CreateNotificationResponse
)

logger = structlog.get_logger()

class NotificationService:
    """Service for notification operations"""

    async def get_user_notifications(
        self,
        user_id: UUID,
        status: Optional[NotificationStatus],
        notification_type: Optional[NotificationType],
        limit: int,
        offset: int,
        include_premium_only: bool
    ) -> tuple[List[NotificationResponse], int]:
        """
        Get paginated notifications for user.

        Calls: activity.sp_get_user_notifications

        Returns:
            (notifications_list, total_count)
        """
        try:
            # Convert enums to strings (or None)
            status_str = status.value if status else None
            type_str = notification_type.value if notification_type else None

            result = await db.execute_sp(
                "activity.sp_get_user_notifications",
                user_id,
                status_str,
                type_str,
                limit,
                offset,
                include_premium_only
            )

            if not result:
                return [], 0

            # Get total count from first row (window function)
            total_count = result[0]["total_count"] if result else 0

            # Format notifications
            notifications = []
            for row in result:
                # Build actor info if present
                actor = None
                if row["actor_user_id"]:
                    actor = ActorInfo(
                        user_id=row["actor_user_id"],
                        username=row["actor_username"],
                        first_name=row["actor_first_name"],
                        main_photo_url=row["actor_main_photo_url"]
                    )

                notification = NotificationResponse(
                    notification_id=row["notification_id"],
                    user_id=row["user_id"],
                    actor=actor,
                    notification_type=row["notification_type"],
                    target_type=row["target_type"],
                    target_id=row["target_id"],
                    title=row["title"],
                    message=row["message"],
                    status=row["status"],
                    created_at=row["created_at"],
                    read_at=row["read_at"],
                    payload=row["payload"]
                )
                notifications.append(notification)

            logger.info(
                "notifications_retrieved",
                user_id=str(user_id),
                count=len(notifications),
                total=total_count
            )

            return notifications, total_count

        except Exception as e:
            raise handle_db_exception(e)

    async def get_notification_by_id(
        self,
        user_id: UUID,
        notification_id: UUID
    ) -> NotificationResponse:
        """
        Get single notification by ID.

        Calls: activity.sp_get_notification_by_id
        """
        try:
            result = await db.execute_sp(
                "activity.sp_get_notification_by_id",
                user_id,
                notification_id
            )

            if not result:
                raise Exception("NOTIFICATION_NOT_FOUND")

            row = result[0]

            # Build actor info if present
            actor = None
            if row["actor_user_id"]:
                actor = ActorInfo(
                    user_id=row["actor_user_id"],
                    username=row["actor_username"],
                    first_name=row["actor_first_name"],
                    last_name=row["actor_last_name"],
                    main_photo_url=row["actor_main_photo_url"]
                )

            return NotificationResponse(
                notification_id=row["notification_id"],
                user_id=row["user_id"],
                actor=actor,
                notification_type=row["notification_type"],
                target_type=row["target_type"],
                target_id=row["target_id"],
                title=row["title"],
                message=row["message"],
                status=row["status"],
                created_at=row["created_at"],
                read_at=row["read_at"],
                payload=row["payload"]
            )

        except Exception as e:
            raise handle_db_exception(e)

    async def mark_as_read(
        self,
        user_id: UUID,
        notification_id: UUID
    ) -> dict:
        """
        Mark single notification as read.

        Calls: activity.sp_mark_notification_as_read
        """
        try:
            result = await db.execute_sp(
                "activity.sp_mark_notification_as_read",
                user_id,
                notification_id
            )

            if not result:
                raise Exception("NOTIFICATION_NOT_FOUND")

            row = result[0]

            logger.info(
                "notification_marked_read",
                notification_id=str(notification_id),
                user_id=str(user_id)
            )

            return {
                "notification_id": row["notification_id"],
                "status": row["status"],
                "read_at": row["read_at"]
            }

        except Exception as e:
            raise handle_db_exception(e)

    async def mark_as_read_bulk(
        self,
        user_id: UUID,
        notification_ids: Optional[List[UUID]],
        notification_type: Optional[NotificationType]
    ) -> MarkReadResponse:
        """
        Mark multiple notifications as read.

        Calls: activity.sp_mark_notifications_as_read_bulk
        """
        try:
            # Convert to appropriate types
            ids_array = notification_ids if notification_ids else None
            type_str = notification_type.value if notification_type else None

            result = await db.execute_sp(
                "activity.sp_mark_notifications_as_read_bulk",
                user_id,
                ids_array,
                type_str
            )

            updated_count = result[0]["updated_count"] if result else 0

            logger.info(
                "notifications_marked_read_bulk",
                user_id=str(user_id),
                count=updated_count
            )

            return MarkReadResponse(
                updated_count=updated_count,
                message=f"{updated_count} notifications marked as read"
            )

        except Exception as e:
            raise handle_db_exception(e)

    async def delete_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
        permanent: bool
    ) -> DeleteResponse:
        """
        Delete or archive notification.

        Calls: activity.sp_delete_notification
        """
        try:
            result = await db.execute_sp(
                "activity.sp_delete_notification",
                user_id,
                notification_id,
                permanent
            )

            if not result:
                raise Exception("NOTIFICATION_NOT_FOUND")

            row = result[0]

            logger.info(
                "notification_deleted",
                notification_id=str(notification_id),
                permanent=permanent
            )

            return DeleteResponse(
                success=row["success"],
                message=row["message"]
            )

        except Exception as e:
            raise handle_db_exception(e)

    async def get_unread_count(
        self,
        user_id: UUID,
        include_premium_only: bool
    ) -> UnreadCountResponse:
        """
        Get unread notification counts by type.

        Calls: activity.sp_get_unread_count
        """
        try:
            result = await db.execute_sp(
                "activity.sp_get_unread_count",
                user_id,
                include_premium_only
            )

            if not result:
                return UnreadCountResponse(total_unread=0, by_type={})

            row = result[0]

            by_type = {
                "activity_invite": row["activity_invite_count"],
                "activity_reminder": row["activity_reminder_count"],
                "activity_update": row["activity_update_count"],
                "community_invite": row["community_invite_count"],
                "new_member": row["new_member_count"],
                "new_post": row["new_post_count"],
                "comment": row["comment_count"],
                "reaction": row["reaction_count"],
                "mention": row["mention_count"],
                "profile_view": row["profile_view_count"],
                "new_favorite": row["new_favorite_count"],
                "system": row["system_count"]
            }

            note = None
            if not include_premium_only:
                note = "Premium-exclusive notification types (profile_view, new_favorite) are not included"

            return UnreadCountResponse(
                total_unread=row["total_unread"],
                by_type=by_type,
                note=note
            )

        except Exception as e:
            raise handle_db_exception(e)

    async def create_notification(
        self,
        user_id: UUID,
        actor_user_id: Optional[UUID],
        notification_type: NotificationType,
        target_type: str,
        target_id: UUID,
        title: str,
        message: Optional[str],
        payload: Optional[dict]
    ) -> CreateNotificationResponse:
        """
        Create new notification (internal service).

        Calls: activity.sp_create_notification
        """
        try:
            result = await db.execute_sp(
                "activity.sp_create_notification",
                user_id,
                actor_user_id,
                notification_type.value,
                target_type,
                target_id,
                title,
                message,
                payload
            )

            if not result:
                return CreateNotificationResponse(
                    notification_id=None,
                    created_at=None,
                    status="skipped",
                    reason="User has disabled this notification type"
                )

            row = result[0]

            if row["notification_id"]:
                logger.info(
                    "notification_created",
                    notification_id=str(row["notification_id"]),
                    user_id=str(user_id),
                    type=notification_type.value
                )
                return CreateNotificationResponse(
                    notification_id=row["notification_id"],
                    created_at=row["created_at"],
                    status="created"
                )
            else:
                logger.info(
                    "notification_skipped",
                    user_id=str(user_id),
                    type=notification_type.value
                )
                return CreateNotificationResponse(
                    notification_id=None,
                    created_at=None,
                    status="skipped",
                    reason="User has disabled this notification type"
                )

        except Exception as e:
            raise handle_db_exception(e)
