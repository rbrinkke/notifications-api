"""
Pydantic models for notification requests and responses.
These match the stored procedure return types.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class NotificationType(str, Enum):
    """Notification type enum"""
    ACTIVITY_INVITE = "activity_invite"
    ACTIVITY_REMINDER = "activity_reminder"
    ACTIVITY_UPDATE = "activity_update"
    COMMUNITY_INVITE = "community_invite"
    NEW_MEMBER = "new_member"
    NEW_POST = "new_post"
    COMMENT = "comment"
    REACTION = "reaction"
    MENTION = "mention"
    PROFILE_VIEW = "profile_view"
    NEW_FAVORITE = "new_favorite"
    SYSTEM = "system"

class NotificationStatus(str, Enum):
    """Notification status enum"""
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"

class ActorInfo(BaseModel):
    """Actor who triggered the notification"""
    user_id: UUID
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    main_photo_url: Optional[str] = None

class NotificationResponse(BaseModel):
    """Single notification response"""
    notification_id: UUID
    user_id: UUID
    actor: Optional[ActorInfo] = None
    notification_type: NotificationType
    target_type: str
    target_id: UUID
    title: str
    message: Optional[str] = None
    status: NotificationStatus
    created_at: datetime
    read_at: Optional[datetime] = None
    payload: Optional[Dict[str, Any]] = None

class PaginationMeta(BaseModel):
    """Pagination metadata"""
    total: int
    limit: int
    offset: int
    has_more: bool

class NotificationListResponse(BaseModel):
    """Paginated notification list"""
    notifications: List[NotificationResponse]
    pagination: PaginationMeta

class UnreadCountResponse(BaseModel):
    """Unread notification counts by type"""
    total_unread: int
    by_type: Dict[str, int]
    note: Optional[str] = None

class MarkReadBulkRequest(BaseModel):
    """Bulk mark-read request"""
    notification_ids: Optional[List[UUID]] = None
    mark_all: Optional[bool] = False
    notification_type: Optional[NotificationType] = None

class MarkReadResponse(BaseModel):
    """Mark-read operation response"""
    updated_count: int
    message: str

class DeleteResponse(BaseModel):
    """Delete/archive operation response"""
    success: bool
    message: str

class CreateNotificationRequest(BaseModel):
    """Create notification request (internal service)"""
    user_id: UUID
    actor_user_id: Optional[UUID] = None
    notification_type: NotificationType
    target_type: str = Field(..., pattern="^(activity|post|comment|user)$")
    target_id: UUID
    title: str = Field(..., max_length=255)
    message: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

class CreateNotificationResponse(BaseModel):
    """Create notification response"""
    notification_id: Optional[UUID]
    created_at: Optional[datetime]
    status: str
    reason: Optional[str] = None
