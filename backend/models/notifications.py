# =============================================================================
# BRKOPS-2585 Notification Models
# WebEx, ServiceNow, and other notification schemas
# =============================================================================

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    """Request to create a notification."""

    channel: str = Field(..., description="Notification channel: webex, servicenow, email")
    recipient: str = Field(..., description="Recipient identifier")
    subject: Optional[str] = Field(None, description="Subject line (for email/ServiceNow)")
    message: str = Field(..., description="Message content")
    job_id: Optional[UUID] = Field(None, description="Associated pipeline job ID")


class NotificationResponse(BaseModel):
    """Notification response."""

    id: int
    job_id: Optional[UUID] = None
    channel: str
    recipient: str
    subject: Optional[str] = None
    message: str
    status: str
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class WebExMessage(BaseModel):
    """WebEx message schema."""

    room_id: Optional[str] = Field(None, description="WebEx room ID (uses default if not provided)")
    text: Optional[str] = Field(None, description="Plain text message")
    markdown: Optional[str] = Field(None, description="Markdown formatted message")
    attachments: Optional[list] = Field(None, description="Adaptive card attachments")

    class Config:
        json_schema_extra = {
            "example": {
                "markdown": "**Alert:** OSPF configuration change detected on Router-1\n\n- Area changed from 0 to 10\n- 2 adjacencies flapped",
            }
        }


class ServiceNowTicket(BaseModel):
    """ServiceNow incident ticket schema."""

    short_description: str = Field(..., description="Incident short description")
    description: str = Field(..., description="Full incident description")
    category: str = Field("Network", description="Incident category")
    subcategory: Optional[str] = Field(None, description="Incident subcategory")
    priority: str = Field("3", description="Priority: 1 (Critical) to 5 (Planning)")
    assignment_group: Optional[str] = Field(None, description="Assignment group")
    caller_id: Optional[str] = Field(None, description="Caller user ID")
    cmdb_ci: Optional[str] = Field(None, description="Configuration item")
    custom_fields: Dict[str, Any] = Field(default={}, description="Additional custom fields")

    class Config:
        json_schema_extra = {
            "example": {
                "short_description": "OSPF Configuration Change - Router-1",
                "description": "Automated configuration change detected.\n\nDetails:\n- Area changed to 10\n- Initiated via voice command",
                "category": "Network",
                "subcategory": "Routing",
                "priority": "3",
            }
        }


class NotificationTemplate(BaseModel):
    """Notification template configuration."""

    channel: str
    template_type: str  # success, warning, critical
    subject_template: Optional[str] = None
    body_template: str
    variables: list[str] = []
