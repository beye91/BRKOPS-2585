# =============================================================================
# BRKOPS-2585 Notifications Router
# WebEx, ServiceNow, and other notification endpoints
# =============================================================================

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import Notification
from models.notifications import (
    NotificationCreate,
    NotificationResponse,
    WebExMessage,
    ServiceNowTicket,
)
from services.notification_service import NotificationService

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    channel: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List notification history with optional filtering."""
    query = select(Notification).order_by(Notification.created_at.desc())

    if channel:
        valid_channels = ['webex', 'servicenow', 'email', 'slack']
        if channel.lower() not in valid_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid channel: {channel}. Must be one of: {', '.join(valid_channels)}",
            )
        query = query.where(Notification.channel == channel.lower())

    if status_filter:
        valid_statuses = ['pending', 'sent', 'delivered', 'failed']
        if status_filter.lower() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}. Must be one of: {', '.join(valid_statuses)}",
            )
        query = query.where(Notification.status == status_filter.lower())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        NotificationResponse(
            id=n.id,
            job_id=n.job_id,
            channel=n.channel,
            recipient=n.recipient,
            subject=n.subject,
            message=n.message,
            status=n.status,
            response_data=n.response_data,
            error_message=n.error_message,
            sent_at=n.sent_at,
            created_at=n.created_at,
        )
        for n in notifications
    ]


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific notification."""
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification {notification_id} not found",
        )

    return NotificationResponse(
        id=notification.id,
        job_id=notification.job_id,
        channel=notification.channel,
        recipient=notification.recipient,
        subject=notification.subject,
        message=notification.message,
        status=notification.status,
        response_data=notification.response_data,
        error_message=notification.error_message,
        sent_at=notification.sent_at,
        created_at=notification.created_at,
    )


@router.post("/webex", response_model=NotificationResponse)
async def send_webex_message(
    message: WebExMessage,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to WebEx.

    Supports plain text, markdown, and adaptive cards.
    """
    logger.info("Sending WebEx message")

    notification_service = NotificationService(db=db)

    try:
        # Create notification record
        notification = Notification(
            channel='webex',
            recipient=message.room_id or "default",
            message=message.markdown or message.text or "",
            status='pending',
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Send the message
        result = await notification_service.send_webex(
            room_id=message.room_id,
            text=message.text,
            markdown=message.markdown,
            attachments=message.attachments,
        )

        # Update notification status
        notification.status = 'sent' if result["success"] else 'failed'
        notification.response_data = result.get("response")
        notification.error_message = result.get("error")
        if result["success"]:
            from datetime import datetime, timezone
            notification.sent_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(notification)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send WebEx message: {result.get('error')}",
            )

        return NotificationResponse(
            id=notification.id,
            job_id=notification.job_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            message=notification.message,
            status=notification.status,
            response_data=notification.response_data,
            error_message=notification.error_message,
            sent_at=notification.sent_at,
            created_at=notification.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("WebEx send failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send WebEx message: {str(e)}",
        )


@router.post("/servicenow", response_model=NotificationResponse)
async def create_servicenow_ticket(
    ticket: ServiceNowTicket,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a ServiceNow incident ticket.
    """
    logger.info("Creating ServiceNow ticket", short_description=ticket.short_description)

    notification_service = NotificationService(db=db)

    try:
        # Create notification record
        notification = Notification(
            channel='servicenow',
            recipient="ServiceNow",
            subject=ticket.short_description,
            message=ticket.description,
            status='pending',
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # Create the ticket
        result = await notification_service.create_servicenow_ticket(
            short_description=ticket.short_description,
            description=ticket.description,
            category=ticket.category,
            subcategory=ticket.subcategory,
            priority=ticket.priority,
            assignment_group=ticket.assignment_group,
            caller_id=ticket.caller_id,
            cmdb_ci=ticket.cmdb_ci,
            custom_fields=ticket.custom_fields,
        )

        # Update notification status
        notification.status = 'sent' if result["success"] else 'failed'
        notification.response_data = result.get("response")
        notification.error_message = result.get("error")
        if result["success"]:
            from datetime import datetime, timezone
            notification.sent_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(notification)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create ServiceNow ticket: {result.get('error')}",
            )

        return NotificationResponse(
            id=notification.id,
            job_id=notification.job_id,
            channel=notification.channel,
            recipient=notification.recipient,
            subject=notification.subject,
            message=notification.message,
            status=notification.status,
            response_data=notification.response_data,
            error_message=notification.error_message,
            sent_at=notification.sent_at,
            created_at=notification.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ServiceNow ticket creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ServiceNow ticket: {str(e)}",
        )


@router.post("/test/webex")
async def test_webex_connection(
    db: AsyncSession = Depends(get_db),
):
    """Test WebEx webhook connection."""
    notification_service = NotificationService(db=db)

    try:
        result = await notification_service.test_webex()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/servicenow")
async def test_servicenow_connection(
    db: AsyncSession = Depends(get_db),
):
    """Test ServiceNow API connection."""
    notification_service = NotificationService(db=db)

    try:
        result = await notification_service.test_servicenow()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}
