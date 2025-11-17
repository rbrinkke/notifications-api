"""
Pydantic models for user notification settings.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class NotificationSettingsResponse(BaseModel):
    """User notification settings response"""
    user_id: UUID
    email_notifications: bool
    push_notifications: bool
    activity_reminders: bool
    community_updates: bool
    friend_requests: bool
    marketing_emails: bool
    ghost_mode: bool
    language: str
    timezone: str
    updated_at: Optional[datetime] = None

class UpdateSettingsRequest(BaseModel):
    """Update notification settings (all fields optional)"""
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    activity_reminders: Optional[bool] = None
    community_updates: Optional[bool] = None
    friend_requests: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    ghost_mode: Optional[bool] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
