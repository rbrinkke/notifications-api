"""
Notification settings endpoints.
All endpoints require JWT authentication.
"""
from fastapi import APIRouter, Depends
import structlog

from app.core.security import get_current_user, TokenData
from app.services.settings_service import SettingsService
from app.schemas.settings import (
    NotificationSettingsResponse,
    UpdateSettingsRequest
)
from uuid import UUID

router = APIRouter()
logger = structlog.get_logger()

# Initialize service
settings_service = SettingsService()

@router.get("", response_model=NotificationSettingsResponse)
async def get_settings(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get user's notification settings.
    Returns defaults if settings don't exist yet.
    """
    return await settings_service.get_settings(
        user_id=UUID(current_user.user_id)
    )

@router.patch("", response_model=NotificationSettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Update user's notification settings.
    All fields are optional - only send fields to update.

    Note: ghost_mode requires Premium subscription.
    """
    return await settings_service.update_settings(
        user_id=UUID(current_user.user_id),
        email_notifications=request.email_notifications,
        push_notifications=request.push_notifications,
        activity_reminders=request.activity_reminders,
        community_updates=request.community_updates,
        friend_requests=request.friend_requests,
        marketing_emails=request.marketing_emails,
        ghost_mode=request.ghost_mode,
        language=request.language,
        timezone=request.timezone
    )
