"""
Notification endpoints.
All endpoints require JWT authentication.
"""
from fastapi import APIRouter, Depends, Query, Path, Header
from typing import Optional, List
from uuid import UUID
import structlog

from app.core.security import get_current_user, TokenData, verify_service_token
from app.core.exceptions import ValidationException, UnauthorizedException
from app.services.notification_service import NotificationService
from app.schemas.notifications import (
    NotificationListResponse,
    NotificationResponse,
    NotificationStatus,
    NotificationType,
    MarkReadBulkRequest,
    MarkReadResponse,
    DeleteResponse,
    UnreadCountResponse,
    CreateNotificationRequest,
    CreateNotificationResponse,
    PaginationMeta
)

router = APIRouter()
logger = structlog.get_logger()

# Initialize service
notification_service = NotificationService()

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    current_user: TokenData = Depends(get_current_user),
    status: Optional[NotificationStatus] = Query(None),
    type: Optional[NotificationType] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get paginated list of user's notifications.

    Query params:
        - status: Filter by status (unread, read, archived)
        - type: Filter by notification type
        - limit: Page size (1-100, default 20)
        - offset: Pagination offset (default 0)
    """
    # Determine if user is premium
    include_premium = current_user.subscription_level != "free"

    notifications, total_count = await notification_service.get_user_notifications(
        user_id=UUID(current_user.user_id),
        status=status,
        notification_type=type,
        limit=limit,
        offset=offset,
        include_premium_only=include_premium
    )

    return NotificationListResponse(
        notifications=notifications,
        pagination=PaginationMeta(
            total=total_count,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total_count
        )
    )

@router.get("/unread/count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get count of unread notifications by type.
    """
    include_premium = current_user.subscription_level != "free"

    return await notification_service.get_unread_count(
        user_id=UUID(current_user.user_id),
        include_premium_only=include_premium
    )

@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID = Path(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get single notification by ID.
    """
    return await notification_service.get_notification_by_id(
        user_id=UUID(current_user.user_id),
        notification_id=notification_id
    )

@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID = Path(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Mark single notification as read.
    """
    return await notification_service.mark_as_read(
        user_id=UUID(current_user.user_id),
        notification_id=notification_id
    )

@router.post("/mark-read", response_model=MarkReadResponse)
async def mark_notifications_read_bulk(
    request: MarkReadBulkRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Mark multiple notifications as read (bulk operation).

    Options:
        1. Provide notification_ids to mark specific notifications
        2. Set mark_all=true to mark all unread
        3. Combine mark_all + notification_type to mark all of specific type
    """
    # Validation: notification_type requires mark_all
    if request.notification_type and not request.mark_all:
        raise ValidationException("notification_type requires mark_all=true")

    return await notification_service.mark_as_read_bulk(
        user_id=UUID(current_user.user_id),
        notification_ids=[UUID(str(id)) for id in request.notification_ids] if request.notification_ids else None,
        notification_type=request.notification_type
    )

@router.delete("/{notification_id}", response_model=DeleteResponse)
async def delete_notification(
    notification_id: UUID = Path(...),
    permanent: bool = Query(False),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Archive or permanently delete notification.

    Query params:
        - permanent: If true, hard delete. If false (default), archive.
    """
    return await notification_service.delete_notification(
        user_id=UUID(current_user.user_id),
        notification_id=notification_id,
        permanent=permanent
    )

@router.post("", response_model=CreateNotificationResponse, status_code=201)
async def create_notification(
    request: CreateNotificationRequest,
    x_service_token: Optional[str] = Header(None)
):
    """
    Create new notification (internal service-to-service).

    Requires X-Service-Token header.
    """
    # Verify service token
    if not x_service_token or not verify_service_token(x_service_token):
        raise UnauthorizedException("Invalid service token")

    result = await notification_service.create_notification(
        user_id=request.user_id,
        actor_user_id=request.actor_user_id,
        notification_type=request.notification_type,
        target_type=request.target_type,
        target_id=request.target_id,
        title=request.title,
        message=request.message,
        payload=request.payload
    )

    # Return 201 if created, 200 if skipped
    if result.status == "created":
        return result
    else:
        return result
