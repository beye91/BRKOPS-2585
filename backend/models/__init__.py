# =============================================================================
# BRKOPS-2585 Pydantic Models
# Request/Response schemas
# =============================================================================

from models.operations import (
    OperationCreate,
    OperationResponse,
    OperationStatus,
    StageData,
    ApprovalRequest,
)
from models.voice import (
    TranscriptionRequest,
    TranscriptionResponse,
)
from models.mcp import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPToolExecute,
    MCPToolResponse,
)
from models.notifications import (
    NotificationCreate,
    NotificationResponse,
    WebExMessage,
    ServiceNowTicket,
)
from models.admin import (
    ConfigVariableCreate,
    ConfigVariableUpdate,
    ConfigVariableResponse,
    UseCaseCreate,
    UseCaseUpdate,
    UseCaseResponse,
)
from models.common import (
    PaginatedResponse,
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    # Operations
    "OperationCreate",
    "OperationResponse",
    "OperationStatus",
    "StageData",
    "ApprovalRequest",
    # Voice
    "TranscriptionRequest",
    "TranscriptionResponse",
    # MCP
    "MCPServerCreate",
    "MCPServerUpdate",
    "MCPServerResponse",
    "MCPToolExecute",
    "MCPToolResponse",
    # Notifications
    "NotificationCreate",
    "NotificationResponse",
    "WebExMessage",
    "ServiceNowTicket",
    # Admin
    "ConfigVariableCreate",
    "ConfigVariableUpdate",
    "ConfigVariableResponse",
    "UseCaseCreate",
    "UseCaseUpdate",
    "UseCaseResponse",
    # Common
    "PaginatedResponse",
    "ErrorResponse",
    "HealthResponse",
]
