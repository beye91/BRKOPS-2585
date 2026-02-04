# =============================================================================
# BRKOPS-2585 MCP Models
# MCP server and tool schemas
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str
    description: str
    parameters: Dict[str, Any] = {}


class MCPServerCreate(BaseModel):
    """Request to create MCP server registration."""

    name: str = Field(..., description="Server display name")
    type: str = Field(..., description="Server type: cml, splunk, or custom")
    endpoint: str = Field(..., description="MCP server endpoint URL")
    auth_config: Dict[str, Any] = Field(default={}, description="Authentication configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "CML Primary",
                "type": "cml",
                "endpoint": "http://cml-mcp-server:8080",
                "auth_config": {
                    "host": "https://cml.example.com",
                    "username": "admin",
                    "password": "***",
                },
            }
        }


class MCPServerUpdate(BaseModel):
    """Request to update MCP server."""

    name: Optional[str] = None
    endpoint: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class MCPServerResponse(BaseModel):
    """MCP server response."""

    id: int
    name: str
    type: str
    endpoint: str
    is_active: bool
    health_status: str
    last_health_check: Optional[datetime] = None
    available_tools: List[MCPTool] = []
    created_at: datetime

    class Config:
        from_attributes = True


class MCPToolExecute(BaseModel):
    """Request to execute an MCP tool."""

    server_id: int = Field(..., description="MCP server ID")
    tool_name: str = Field(..., description="Tool name to execute")
    parameters: Dict[str, Any] = Field(default={}, description="Tool parameters")

    class Config:
        json_schema_extra = {
            "example": {
                "server_id": 1,
                "tool_name": "get_labs",
                "parameters": {},
            }
        }


class MCPToolResponse(BaseModel):
    """Response from MCP tool execution."""

    success: bool
    tool_name: str
    result: Any
    execution_time_ms: int
    error: Optional[str] = None


class CMLTopology(BaseModel):
    """CML lab topology for visualization."""

    lab_id: str
    lab_title: str
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]


class SplunkQueryResult(BaseModel):
    """Splunk query result."""

    query: str
    results: List[Dict[str, Any]]
    result_count: int
    execution_time_ms: int


# =============================================================================
# CML Lab Management Models
# =============================================================================
class CMLLabNode(BaseModel):
    """CML lab node information."""

    id: str
    label: str
    node_definition: str
    state: str
    x: Optional[int] = None
    y: Optional[int] = None


class CMLLabStatus(BaseModel):
    """CML lab status response."""

    lab_id: Optional[str] = None
    title: str
    state: str
    node_count: int
    nodes: List[CMLLabNode] = []
    created: Optional[datetime] = None
    started: Optional[datetime] = None
    exists: bool = True


class CMLDemoLabStatus(BaseModel):
    """Demo lab status for the BRKOPS-2585 OSPF demo."""

    exists: bool
    lab_id: Optional[str] = None
    title: str = "BRKOPS-2585-OSPF-Demo"
    state: str = "NOT_FOUND"
    node_count: int = 0
    nodes: List[CMLLabNode] = []
    management_ips: Dict[str, str] = {}


class CreateLabRequest(BaseModel):
    """Request to create a CML lab from YAML topology."""

    yaml: str = Field(..., description="CML topology YAML content")
    title: Optional[str] = Field(None, description="Optional title override")


class LabActionResponse(BaseModel):
    """Response for lab start/stop/delete actions."""

    success: bool
    lab_id: str
    action: str
    message: str
