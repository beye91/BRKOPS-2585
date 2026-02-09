# =============================================================================
# BRKOPS-2585 Operations Models
# Pipeline job request/response schemas
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StageData(BaseModel):
    """Data for a single pipeline stage."""

    status: str = "pending"  # pending, running, completed, failed, skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class OperationCreate(BaseModel):
    """Request to create a new operation."""

    text: Optional[str] = Field(None, description="Voice command transcript or text input")
    audio_url: Optional[str] = Field(None, description="URL to uploaded audio file")
    use_case: Optional[str] = Field(None, description="Specific use case to apply")
    lab_id: Optional[str] = Field(None, description="User-selected lab override")
    demo_mode: bool = Field(True, description="Enable step-by-step advancement")
    force: bool = Field(False, description="Skip use case validation (advanced mode)")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "I want to change OSPF configuration on Router-1 to use area 10",
                "use_case": "ospf_configuration_change",
                "demo_mode": True,
                "force": False,
            }
        }


class OperationStatus(BaseModel):
    """Status of a single pipeline stage."""

    stage: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class OperationResponse(BaseModel):
    """Full operation response."""

    id: UUID
    use_case_name: str
    input_text: str
    input_audio_url: Optional[str] = None
    current_stage: str
    status: str
    stages: Dict[str, StageData] = {}
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OperationSummary(BaseModel):
    """Summarized operation for list views."""

    id: UUID
    use_case_name: str
    input_text: str
    current_stage: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    """Human approval/rejection request."""

    approved: bool = Field(..., description="Whether to approve the operation")
    comment: Optional[str] = Field(None, description="Optional comment for the decision")
    modified_config: Optional[str] = Field(None, description="Modified configuration if rejecting with changes")

    class Config:
        json_schema_extra = {
            "example": {
                "approved": True,
                "comment": "Approved for production deployment",
            }
        }


class IntentResult(BaseModel):
    """Result of intent parsing stage."""

    action: str
    target_devices: List[str]
    parameters: Dict[str, Any]
    confidence: float
    clarification_needed: Optional[str] = None


class ConfigResult(BaseModel):
    """Result of config generation stage."""

    commands: List[str]
    rollback_commands: List[str]
    config_mode: str = "configure terminal"
    warnings: List[str] = []
    explanation: str


class AnalysisResult(BaseModel):
    """Result of AI analysis stage."""

    severity: str  # INFO, WARNING, CRITICAL
    findings: List[Dict[str, Any]]
    root_cause: Optional[str] = None
    recommendation: str
    requires_action: bool
    suggested_remediation: Optional[str] = None


class RollbackRequest(BaseModel):
    """Request to execute rollback on a deployed configuration."""

    confirm: bool = Field(..., description="Must be True to execute rollback")
    reason: Optional[str] = Field(None, description="Optional reason for rollback")

    class Config:
        json_schema_extra = {
            "example": {
                "confirm": True,
                "reason": "Configuration caused network issues",
            }
        }


class RollbackResponse(BaseModel):
    """Response from rollback execution."""

    success: bool
    message: str
    commands_executed: int
    rollback_output: Optional[str] = None
