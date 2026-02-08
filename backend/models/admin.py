# =============================================================================
# BRKOPS-2585 Admin Models
# Configuration and use case management schemas
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Configuration Variables
# =============================================================================
class ConfigVariableCreate(BaseModel):
    """Request to create a configuration variable."""

    key: str = Field(..., description="Unique configuration key")
    value: Any = Field(..., description="Configuration value (JSON)")
    description: Optional[str] = Field(None, description="Human-readable description")
    category: str = Field(..., description="Category for grouping")
    is_secret: bool = Field(False, description="Whether value should be masked")


class ConfigVariableUpdate(BaseModel):
    """Request to update a configuration variable."""

    value: Optional[Any] = None
    description: Optional[str] = None
    is_secret: Optional[bool] = None


class ConfigVariableResponse(BaseModel):
    """Configuration variable response."""

    id: int
    key: str
    value: Any
    description: Optional[str] = None
    category: str
    is_secret: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConfigCategory(BaseModel):
    """Configuration category with variables."""

    category: str
    variables: List[ConfigVariableResponse]


# =============================================================================
# Use Cases
# =============================================================================
class UseCaseCreate(BaseModel):
    """Request to create a use case."""

    name: str = Field(..., description="Unique use case identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Use case description")
    trigger_keywords: List[str] = Field(default=[], description="Keywords that trigger this use case")
    intent_prompt: str = Field(..., description="LLM prompt for intent parsing")
    config_prompt: str = Field(..., description="LLM prompt for config generation")
    analysis_prompt: str = Field(..., description="LLM prompt for analysis")
    notification_template: Dict[str, Any] = Field(default={}, description="Notification templates")
    cml_target_lab: Optional[str] = Field(None, description="Target CML lab ID")
    splunk_index: str = Field("netops", description="Splunk index to query")
    convergence_wait_seconds: int = Field(45, description="Wait time after config push")
    servicenow_enabled: bool = Field(False, description="Enable ServiceNow ticket creation")
    allowed_actions: List[str] = Field(default=[], description="Allowed action types for scope validation")
    scope_validation_enabled: bool = Field(True, description="Enable scope validation")
    llm_provider: Optional[str] = Field(None, description="LLM provider override (openai, anthropic, or null for global default)")
    llm_model: Optional[str] = Field(None, description="LLM model override (e.g., gpt-4-turbo-preview, claude-3-sonnet-20240229)")
    explanation_template: Optional[str] = Field(None, description="Template for config explanation. Use {{device_count}}, {{new_area}}, etc.")
    impact_description: Optional[str] = Field(None, description="Human-readable estimated impact")
    splunk_query_config: Optional[Dict[str, Any]] = Field(None, description="Splunk query routing config, e.g. {\"query_type\": \"ospf_events\"}")
    pre_checks: Optional[List[str]] = Field(None, description="Pre-deployment checks")
    post_checks: Optional[List[str]] = Field(None, description="Post-deployment checks")
    risk_profile: Optional[Dict[str, Any]] = Field(None, description="Risk factors, mitigation steps, and affected services")
    is_active: bool = Field(True, description="Whether use case is active")
    sort_order: int = Field(0, description="Display sort order")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "ospf_change",
                "display_name": "OSPF Configuration Change",
                "description": "Modify OSPF routing configuration",
                "trigger_keywords": ["ospf", "routing", "area"],
                "intent_prompt": "Parse the following voice command...",
                "config_prompt": "Generate Cisco IOS commands...",
                "analysis_prompt": "Analyze Splunk results...",
                "convergence_wait_seconds": 45,
                "explanation_template": "Change OSPF area to {{new_area}} on {{device_count}} device(s)",
                "impact_description": "Brief OSPF neighbor flap during area transition",
                "pre_checks": ["Verify OSPF neighbor state"],
                "post_checks": ["Check routing table convergence"],
            }
        }


class UseCaseUpdate(BaseModel):
    """Request to update a use case."""

    display_name: Optional[str] = None
    description: Optional[str] = None
    trigger_keywords: Optional[List[str]] = None
    intent_prompt: Optional[str] = None
    config_prompt: Optional[str] = None
    analysis_prompt: Optional[str] = None
    notification_template: Optional[Dict[str, Any]] = None
    cml_target_lab: Optional[str] = None
    splunk_index: Optional[str] = None
    convergence_wait_seconds: Optional[int] = None
    servicenow_enabled: Optional[bool] = None
    allowed_actions: Optional[List[str]] = None
    scope_validation_enabled: Optional[bool] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    explanation_template: Optional[str] = None
    impact_description: Optional[str] = None
    splunk_query_config: Optional[Dict[str, Any]] = None
    pre_checks: Optional[List[str]] = None
    post_checks: Optional[List[str]] = None
    risk_profile: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class UseCaseResponse(BaseModel):
    """Use case response."""

    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    trigger_keywords: List[str] = []
    intent_prompt: str
    config_prompt: str
    analysis_prompt: str
    notification_template: Dict[str, Any] = {}
    cml_target_lab: Optional[str] = None
    splunk_index: str
    convergence_wait_seconds: int
    servicenow_enabled: bool = False
    allowed_actions: List[str] = []
    scope_validation_enabled: bool = True
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    explanation_template: Optional[str] = None
    impact_description: Optional[str] = None
    splunk_query_config: Optional[Dict[str, Any]] = None
    pre_checks: Optional[List[str]] = None
    post_checks: Optional[List[str]] = None
    risk_profile: Optional[Dict[str, Any]] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Users
# =============================================================================
class UserCreate(BaseModel):
    """Request to create a user."""

    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    """Request to update a user."""

    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response (without password)."""

    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
