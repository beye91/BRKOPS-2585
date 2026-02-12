# =============================================================================
# BRKOPS-2585 Notification Service
# WebEx and ServiceNow integration
# =============================================================================

from typing import Any, Dict, List, Optional

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from services.config_service import ConfigService

logger = structlog.get_logger()


class NotificationService:
    """
    Notification service for WebEx and ServiceNow integrations.
    """

    def __init__(self, db: Optional[AsyncSession] = None, http_timeout: int = 30):
        """Initialize notification service."""
        self.db = db
        self.http_timeout = http_timeout
        self.webex_webhook_url = settings.webex_webhook_url
        self.webex_bot_token = settings.webex_bot_token
        self.webex_room_id = settings.webex_room_id
        # ServiceNow credentials will be loaded from DB when needed
        self.servicenow_instance = None
        self.servicenow_username = None
        self.servicenow_password = None
        self._credentials_loaded = False

    async def _load_servicenow_credentials(self):
        """Load ServiceNow credentials from database, falling back to env vars."""
        if self._credentials_loaded:
            return

        if self.db:
            # Try to load from database first
            self.servicenow_instance = await ConfigService.get_config(
                self.db, "servicenow_instance", settings.servicenow_instance
            )
            self.servicenow_username = await ConfigService.get_config(
                self.db, "servicenow_username", settings.servicenow_username
            )
            self.servicenow_password = await ConfigService.get_config(
                self.db, "servicenow_password", settings.servicenow_password
            )
            logger.info(
                "ServiceNow credentials loaded from database",
                instance=self.servicenow_instance,
                username_configured=bool(self.servicenow_username),
            )
        else:
            # Fall back to environment variables
            self.servicenow_instance = settings.servicenow_instance
            self.servicenow_username = settings.servicenow_username
            self.servicenow_password = settings.servicenow_password
            logger.info(
                "ServiceNow credentials loaded from environment",
                instance=self.servicenow_instance,
                username_configured=bool(self.servicenow_username),
            )

        self._credentials_loaded = True

    # ==========================================================================
    # WebEx
    # ==========================================================================
    async def send_webex(
        self,
        room_id: Optional[str] = None,
        text: Optional[str] = None,
        markdown: Optional[str] = None,
        attachments: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to WebEx.

        Args:
            room_id: WebEx room ID (uses webhook if not provided)
            text: Plain text message
            markdown: Markdown formatted message
            attachments: Adaptive card attachments

        Returns:
            Result dictionary with success status
        """
        if not text and not markdown:
            return {"success": False, "error": "Either text or markdown required"}

        # Use webhook if available (simpler, no room_id needed)
        if self.webex_webhook_url and not room_id:
            return await self._send_webex_webhook(text or markdown)

        # Use bot token for direct API calls (fall back to default room)
        if self.webex_bot_token:
            target_room = room_id or self.webex_room_id
            return await self._send_webex_api(target_room, text, markdown, attachments)

        return {"success": False, "error": "No WebEx credentials configured"}

    async def _send_webex_webhook(self, message: str) -> Dict[str, Any]:
        """Send message via WebEx incoming webhook."""
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(
                    self.webex_webhook_url,
                    json={"markdown": message},
                )

                if response.status_code in [200, 204]:
                    logger.info("WebEx webhook message sent")
                    return {"success": True, "response": {"status": response.status_code}}

                logger.error(
                    "WebEx webhook failed",
                    status=response.status_code,
                    error=response.text,
                )
                return {
                    "success": False,
                    "error": f"Webhook returned {response.status_code}: {response.text}",
                }

        except Exception as e:
            logger.error("WebEx webhook error", error=str(e))
            return {"success": False, "error": str(e)}

    async def _send_webex_api(
        self,
        room_id: Optional[str],
        text: Optional[str],
        markdown: Optional[str],
        attachments: Optional[List[Dict]],
    ) -> Dict[str, Any]:
        """Send message via WebEx API."""
        if not room_id:
            return {"success": False, "error": "room_id required for API calls"}

        try:
            payload = {"roomId": room_id}

            if text:
                payload["text"] = text
            if markdown:
                payload["markdown"] = markdown
            if attachments:
                payload["attachments"] = attachments

            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(
                    "https://webexapis.com/v1/messages",
                    headers={
                        "Authorization": f"Bearer {self.webex_bot_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code == 200:
                    logger.info("WebEx API message sent", room_id=room_id)
                    return {"success": True, "response": response.json()}

                logger.error(
                    "WebEx API failed",
                    status=response.status_code,
                    error=response.text,
                )
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}: {response.text}",
                }

        except Exception as e:
            logger.error("WebEx API error", error=str(e))
            return {"success": False, "error": str(e)}

    async def test_webex(self) -> Dict[str, Any]:
        """Test WebEx connection."""
        test_message = "BRKOPS-2585 Demo Platform - Connection Test"

        if self.webex_webhook_url:
            result = await self._send_webex_webhook(test_message)
            return {
                "success": result["success"],
                "method": "webhook",
                "message": "Connection test sent" if result["success"] else result.get("error"),
            }

        if self.webex_bot_token:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    # Verify the token is valid
                    response = await client.get(
                        "https://webexapis.com/v1/people/me",
                        headers={"Authorization": f"Bearer {self.webex_bot_token}"},
                    )
                    if response.status_code != 200:
                        return {"success": False, "method": "api", "error": "Invalid bot token"}

                    bot_name = response.json().get("displayName", "Bot")

                    # Send a test message if room is configured
                    if self.webex_room_id:
                        result = await self._send_webex_api(
                            self.webex_room_id, None, f"**{bot_name}** - Connection test from BRKOPS-2585", None
                        )
                        if result["success"]:
                            return {"success": True, "method": "api", "message": f"Test message sent to room via {bot_name}"}
                        return {"success": False, "method": "api", "error": f"Token valid but failed to send: {result.get('error')}"}

                    return {"success": True, "method": "api", "message": f"Bot token valid ({bot_name}), no default room configured"}
            except Exception as e:
                return {"success": False, "method": "api", "error": str(e)}

        return {"success": False, "error": "No WebEx credentials configured"}

    # ==========================================================================
    # ServiceNow
    # ==========================================================================
    async def create_servicenow_ticket(
        self,
        short_description: str,
        description: str,
        category: str = "Network",
        subcategory: Optional[str] = None,
        priority: str = "3",
        impact: str = "2",
        urgency: str = "2",
        assignment_group: Optional[str] = None,
        caller_id: Optional[str] = None,
        cmdb_ci: Optional[str] = None,
        custom_fields: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Create a ServiceNow incident ticket.

        Args:
            short_description: Incident short description
            description: Full description
            category: Incident category
            subcategory: Incident subcategory
            priority: Priority level (1-5)
            impact: Impact level (1-3, default "2" Medium)
            urgency: Urgency level (1-3, default "2" Medium)
            assignment_group: Assignment group name
            caller_id: Caller user ID
            cmdb_ci: Configuration item
            custom_fields: Additional custom fields

        Returns:
            Result dictionary with success status and ticket info
        """
        # Load credentials from database if not already loaded
        await self._load_servicenow_credentials()

        if not all([self.servicenow_instance, self.servicenow_username, self.servicenow_password]):
            return {"success": False, "error": "ServiceNow credentials not configured"}

        try:
            # Build incident payload
            payload = {
                "short_description": short_description,
                "description": description,
                "category": category,
                "priority": priority,
                "impact": impact,
                "urgency": urgency,
            }

            if subcategory:
                payload["subcategory"] = subcategory
            if assignment_group:
                payload["assignment_group"] = assignment_group
            if caller_id:
                payload["caller_id"] = caller_id
            if cmdb_ci:
                payload["cmdb_ci"] = cmdb_ci
            if custom_fields:
                payload.update(custom_fields)

            # ServiceNow REST API URL
            url = f"https://{self.servicenow_instance}/api/now/table/incident"

            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(
                    url,
                    auth=(self.servicenow_username, self.servicenow_password),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json=payload,
                )

                if response.status_code == 201:
                    result = response.json()
                    ticket = result.get("result", {})

                    logger.info(
                        "ServiceNow ticket created",
                        number=ticket.get("number"),
                        sys_id=ticket.get("sys_id"),
                    )

                    return {
                        "success": True,
                        "response": {
                            "number": ticket.get("number"),
                            "sys_id": ticket.get("sys_id"),
                            "link": f"https://{self.servicenow_instance}/incident.do?sys_id={ticket.get('sys_id')}",
                        },
                    }

                logger.error(
                    "ServiceNow ticket creation failed",
                    status=response.status_code,
                    error=response.text,
                )
                return {
                    "success": False,
                    "error": f"ServiceNow returned {response.status_code}: {response.text}",
                }

        except Exception as e:
            logger.error("ServiceNow error", error=str(e))
            return {"success": False, "error": str(e)}

    async def test_servicenow(self) -> Dict[str, Any]:
        """Test ServiceNow connection."""
        # Load credentials from database if not already loaded
        await self._load_servicenow_credentials()

        if not all([self.servicenow_instance, self.servicenow_username, self.servicenow_password]):
            return {"success": False, "error": "ServiceNow credentials not configured"}

        try:
            # Test API connection by getting user info
            url = f"https://{self.servicenow_instance}/api/now/table/sys_user?sysparm_limit=1"

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    url,
                    auth=(self.servicenow_username, self.servicenow_password),
                    headers={"Accept": "application/json"},
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "ServiceNow connection successful",
                        "instance": self.servicenow_instance,
                    }

                return {
                    "success": False,
                    "error": f"ServiceNow returned {response.status_code}",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================================================
    # Utility Methods
    # ==========================================================================
    async def send_operation_notification(
        self,
        channel: str,
        severity: str,
        template: Dict[str, str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send operation notification using templates.

        Args:
            channel: Notification channel (webex, servicenow)
            severity: Severity level (success, warning, critical)
            template: Template dictionary with message templates
            context: Context for variable substitution

        Returns:
            Result dictionary
        """
        # Get appropriate template
        message_template = template.get(severity, template.get("success", ""))

        # Substitute variables
        message = message_template
        for key, value in context.items():
            placeholder = "{{" + key + "}}"
            message = message.replace(placeholder, str(value))

        if channel == "webex":
            return await self.send_webex(markdown=message)
        elif channel == "servicenow":
            return await self.create_servicenow_ticket(
                short_description=context.get("short_description", "Network Operation"),
                description=message,
                category=context.get("category", "Network"),
                priority=context.get("priority", "3"),
            )

        return {"success": False, "error": f"Unknown channel: {channel}"}
