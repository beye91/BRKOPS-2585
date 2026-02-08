# =============================================================================
# BRKOPS-2585 MCP Router
# MCP server management and tool execution endpoints
# =============================================================================

from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import MCPServer
from models.mcp import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPToolExecute,
    MCPToolResponse,
    CMLTopology,
    CMLLabStatus,
    CMLDemoLabStatus,
    CMLLabNode,
    CreateLabRequest,
    LabActionResponse,
)
from services.cml_client import CMLClient
from services.splunk_client import SplunkClient

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# MCP Server Management
# =============================================================================
@router.get("/servers", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    db: AsyncSession = Depends(get_db),
):
    """List all registered MCP servers."""
    result = await db.execute(select(MCPServer).order_by(MCPServer.name))
    servers = result.scalars().all()

    return [
        MCPServerResponse(
            id=server.id,
            name=server.name,
            type=server.type,
            endpoint=server.endpoint,
            is_active=server.is_active,
            health_status=server.health_status,
            last_health_check=server.last_health_check,
            available_tools=server.available_tools or [],
            created_at=server.created_at,
        )
        for server in servers
    ]


@router.post("/servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server_data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new MCP server."""
    valid_types = ['cml', 'splunk', 'custom']
    server_type = server_data.type.lower()

    if server_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid server type: {server_data.type}. Must be: cml, splunk, or custom",
        )

    # Check for duplicate name + type combination
    existing = await db.execute(
        select(MCPServer).where(
            MCPServer.name == server_data.name,
            MCPServer.type == server_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MCP server '{server_data.name}' of type '{server_type}' already exists",
        )

    server = MCPServer(
        name=server_data.name,
        type=server_type,
        endpoint=server_data.endpoint,
        auth_config=server_data.auth_config,
    )

    db.add(server)
    await db.commit()
    await db.refresh(server)

    logger.info("MCP server created", name=server.name, type=server.type)

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        type=server.type,
        endpoint=server.endpoint,
        is_active=server.is_active,
        health_status=server.health_status,
        last_health_check=server.last_health_check,
        available_tools=[],
        created_at=server.created_at,
    )


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        type=server.type,
        endpoint=server.endpoint,
        is_active=server.is_active,
        health_status=server.health_status,
        last_health_check=server.last_health_check,
        available_tools=server.available_tools or [],
        created_at=server.created_at,
    )


@router.put("/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: int,
    server_data: MCPServerUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an MCP server configuration."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    if server_data.name is not None:
        server.name = server_data.name
    if server_data.endpoint is not None:
        server.endpoint = server_data.endpoint
    if server_data.auth_config is not None:
        server.auth_config = server_data.auth_config
    if server_data.is_active is not None:
        server.is_active = server_data.is_active

    await db.commit()
    await db.refresh(server)

    logger.info("MCP server updated", id=server_id)

    return MCPServerResponse(
        id=server.id,
        name=server.name,
        type=server.type,
        endpoint=server.endpoint,
        is_active=server.is_active,
        health_status=server.health_status,
        last_health_check=server.last_health_check,
        available_tools=server.available_tools or [],
        created_at=server.created_at,
    )


@router.delete("/servers/{server_id}", status_code=status.HTTP_200_OK)
async def delete_mcp_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an MCP server from the registry."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    server_name = server.name
    await db.delete(server)
    await db.commit()

    logger.info("MCP server deleted", id=server_id, name=server_name)

    return {"success": True, "message": f"MCP server '{server_name}' deleted"}


@router.post("/servers/{server_id}/test")
async def test_mcp_server(
    server_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Test connection to an MCP server."""
    from datetime import datetime

    result = await db.execute(select(MCPServer).where(MCPServer.id == server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {server_id} not found",
        )

    logger.info("Testing MCP server connection", name=server.name)

    try:
        if server.type == "cml":
            client = CMLClient(server.endpoint, server.auth_config)
            tools = await client.list_tools()
        elif server.type == "splunk":
            client = SplunkClient(server.endpoint, server.auth_config)
            tools = await client.list_tools()
        else:
            tools = []

        server.health_status = 'healthy'
        server.last_health_check = datetime.utcnow()
        server.available_tools = tools
        await db.commit()

        return {
            "success": True,
            "message": "Connection successful",
            "tools_count": len(tools),
            "tools": tools,
        }

    except Exception as e:
        logger.error("MCP server test failed", error=str(e))

        server.health_status = 'unhealthy'
        server.last_health_check = datetime.utcnow()
        await db.commit()

        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "tools_count": 0,
            "tools": [],
        }


# =============================================================================
# Tool Execution
# =============================================================================
@router.get("/tools")
async def list_all_tools(
    db: AsyncSession = Depends(get_db),
):
    """List all available tools from all active MCP servers."""
    result = await db.execute(
        select(MCPServer).where(MCPServer.is_active == True)
    )
    servers = result.scalars().all()

    all_tools = []
    for server in servers:
        for tool in server.available_tools or []:
            all_tools.append({
                "server_id": server.id,
                "server_name": server.name,
                "server_type": server.type,
                **tool,
            })

    return {"tools": all_tools, "count": len(all_tools)}


@router.post("/execute", response_model=MCPToolResponse)
async def execute_mcp_tool(
    request: MCPToolExecute,
    db: AsyncSession = Depends(get_db),
):
    """Execute a tool on an MCP server."""
    import time

    result = await db.execute(select(MCPServer).where(MCPServer.id == request.server_id))
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server {request.server_id} not found",
        )

    if not server.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MCP server is not active",
        )

    logger.info(
        "Executing MCP tool",
        server=server.name,
        tool=request.tool_name,
        params=request.parameters,
    )

    start_time = time.time()

    try:
        if server.type == "cml":
            client = CMLClient(server.endpoint, server.auth_config)
            result_data = await client.execute_tool(request.tool_name, request.parameters)
        elif server.type == "splunk":
            client = SplunkClient(server.endpoint, server.auth_config)
            result_data = await client.execute_tool(request.tool_name, request.parameters)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown server type: {server.type}",
            )

        execution_time = int((time.time() - start_time) * 1000)

        return MCPToolResponse(
            success=True,
            tool_name=request.tool_name,
            result=result_data,
            execution_time_ms=execution_time,
        )

    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        logger.error("MCP tool execution failed", error=str(e))

        return MCPToolResponse(
            success=False,
            tool_name=request.tool_name,
            result=None,
            execution_time_ms=execution_time,
            error=str(e),
        )


# =============================================================================
# CML-Specific Endpoints
# =============================================================================
@router.get("/cml/labs")
async def get_cml_labs(
    db: AsyncSession = Depends(get_db),
):
    """Get all labs from the active CML server."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        labs = await client.get_labs()
        return {"labs": labs}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get labs: {str(e)}",
        )


@router.get("/cml/labs/{lab_id}/topology", response_model=CMLTopology)
async def get_cml_topology(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get topology graph data for a CML lab."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        topology = await client.get_topology(lab_id)
        return topology
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get topology: {str(e)}",
        )


@router.get("/cml/labs/{lab_id}/status", response_model=CMLLabStatus)
async def get_cml_lab_status(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed status of a CML lab including node states."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        lab = await client.get_lab_by_id(lab_id)
        nodes = await client.get_nodes(lab_id)

        node_list = [
            CMLLabNode(
                id=node.get("id", ""),
                label=node.get("label", ""),
                node_definition=node.get("node_definition", ""),
                state=node.get("state", "UNKNOWN"),
                x=node.get("x"),
                y=node.get("y"),
            )
            for node in nodes
        ]

        return CMLLabStatus(
            lab_id=lab.get("id"),
            title=lab.get("title", "Untitled"),
            state=lab.get("state", "UNKNOWN"),
            node_count=len(nodes),
            nodes=node_list,
            exists=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lab status: {str(e)}",
        )


@router.get("/cml/labs/demo-status", response_model=CMLDemoLabStatus)
async def get_demo_lab_status(
    db: AsyncSession = Depends(get_db),
):
    """Check if the BRKOPS-2585 demo lab exists and get its status."""
    from db.models import MCPServerType

    DEMO_LAB_TITLE = "BRKOPS-2585-OSPF-Demo"

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        return CMLDemoLabStatus(
            exists=False,
            state="NO_CML_SERVER",
            title=DEMO_LAB_TITLE,
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        labs = await client.get_labs()

        # Find demo lab by title (API returns lab_title)
        demo_lab = None
        for lab in labs:
            if lab.get("lab_title") == DEMO_LAB_TITLE:
                demo_lab = lab
                break

        if not demo_lab:
            return CMLDemoLabStatus(
                exists=False,
                state="NOT_FOUND",
                title=DEMO_LAB_TITLE,
            )

        lab_id = demo_lab.get("id")
        nodes = await client.get_nodes(lab_id)

        node_list = [
            CMLLabNode(
                id=node.get("id", ""),
                label=node.get("label", ""),
                node_definition=node.get("node_definition", ""),
                state=node.get("state", "UNKNOWN"),
                x=node.get("x"),
                y=node.get("y"),
            )
            for node in nodes
        ]

        # Build management IP mapping
        mgmt_ips = {
            "Router-1": "198.18.1.201",
            "Router-2": "198.18.1.202",
            "Router-3": "198.18.1.203",
            "Router-4": "198.18.1.204",
        }

        return CMLDemoLabStatus(
            exists=True,
            lab_id=lab_id,
            title=DEMO_LAB_TITLE,
            state=demo_lab.get("state", "UNKNOWN"),
            node_count=len(nodes),
            nodes=node_list,
            management_ips=mgmt_ips,
        )

    except Exception as e:
        logger.error("Failed to check demo lab status", error=str(e))
        return CMLDemoLabStatus(
            exists=False,
            state="ERROR",
            title=DEMO_LAB_TITLE,
        )


@router.post("/cml/labs/create", response_model=LabActionResponse)
async def create_cml_lab(
    request: CreateLabRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new CML lab from YAML topology."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        result_data = await client.create_lab_from_yaml(request.yaml, request.title)

        lab_id = result_data.get("id") if isinstance(result_data, dict) else str(result_data)

        return LabActionResponse(
            success=True,
            lab_id=lab_id,
            action="create",
            message="Lab created successfully",
        )
    except Exception as e:
        logger.error("Failed to create lab", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create lab: {str(e)}",
        )


@router.post("/cml/labs/build-demo", response_model=LabActionResponse)
async def build_demo_lab(
    db: AsyncSession = Depends(get_db),
):
    """Build the BRKOPS-2585 demo lab using predefined topology."""
    import os
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    # Load the demo lab YAML from file
    # __file__ is /app/routers/mcp.py, so .. takes us to /app where cml-lab is
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "cml-lab", "brkops-ospf-demo.yaml")
    yaml_path = os.path.abspath(yaml_path)

    if not os.path.exists(yaml_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo lab topology file not found",
        )

    with open(yaml_path, "r") as f:
        yaml_content = f.read()

    try:
        client = CMLClient(server.endpoint, server.auth_config)

        # Check if lab already exists (API returns lab_title)
        labs = await client.get_labs()
        for lab in labs:
            if lab.get("lab_title") == "BRKOPS-2585-OSPF-Demo":
                return LabActionResponse(
                    success=True,
                    lab_id=lab.get("id"),
                    action="exists",
                    message="Demo lab already exists",
                )

        result_data = await client.create_lab_from_yaml(yaml_content)
        lab_id = result_data.get("id") if isinstance(result_data, dict) else str(result_data)

        return LabActionResponse(
            success=True,
            lab_id=lab_id,
            action="create",
            message="Demo lab created successfully",
        )
    except Exception as e:
        logger.error("Failed to build demo lab", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build demo lab: {str(e)}",
        )


@router.post("/cml/labs/{lab_id}/start", response_model=LabActionResponse)
async def start_cml_lab(
    lab_id: str,
    wait_for_convergence: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Start a CML lab."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        await client.start_lab(lab_id, wait_for_convergence)

        return LabActionResponse(
            success=True,
            lab_id=lab_id,
            action="start",
            message="Lab started successfully",
        )
    except Exception as e:
        logger.error("Failed to start lab", lab_id=lab_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start lab: {str(e)}",
        )


@router.post("/cml/labs/{lab_id}/stop", response_model=LabActionResponse)
async def stop_cml_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Stop a CML lab."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        await client.stop_lab(lab_id)

        return LabActionResponse(
            success=True,
            lab_id=lab_id,
            action="stop",
            message="Lab stopped successfully",
        )
    except Exception as e:
        logger.error("Failed to stop lab", lab_id=lab_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop lab: {str(e)}",
        )


@router.post("/cml/labs/{lab_id}/reset", response_model=LabActionResponse)
async def reset_cml_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reset all router configurations to their default demo state."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        reset_results = await client.reset_lab_configs(lab_id)

        # Check if any router failed
        failed_routers = [
            r for r, status in reset_results.get("reset_results", {}).items()
            if status != "success"
        ]

        if failed_routers:
            return LabActionResponse(
                success=False,
                lab_id=lab_id,
                action="reset",
                message=f"Reset completed with errors on: {', '.join(failed_routers)}",
            )

        return LabActionResponse(
            success=True,
            lab_id=lab_id,
            action="reset",
            message="Lab configurations reset to default successfully",
        )
    except Exception as e:
        logger.error("Failed to reset lab", lab_id=lab_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset lab: {str(e)}",
        )


@router.delete("/cml/labs/{lab_id}", response_model=LabActionResponse)
async def delete_cml_lab(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a CML lab."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.CML,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active CML server found",
        )

    try:
        client = CMLClient(server.endpoint, server.auth_config)
        await client.delete_lab(lab_id)

        return LabActionResponse(
            success=True,
            lab_id=lab_id,
            action="delete",
            message="Lab deleted successfully",
        )
    except Exception as e:
        logger.error("Failed to delete lab", lab_id=lab_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lab: {str(e)}",
        )


# =============================================================================
# Splunk-Specific Endpoints
# =============================================================================
@router.post("/splunk/query")
async def run_splunk_query(
    spl: str,
    earliest: str = "-1h",
    latest: str = "now",
    db: AsyncSession = Depends(get_db),
):
    """Execute a SPL query on the active Splunk server."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.SPLUNK,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Splunk server found",
        )

    try:
        client = SplunkClient(server.endpoint, server.auth_config)
        results = await client.run_query(spl, earliest, latest)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run query: {str(e)}",
        )


@router.post("/splunk/generate-spl")
async def generate_spl(
    description: str,
    index: str = "netops",
    db: AsyncSession = Depends(get_db),
):
    """Generate SPL query from natural language description."""
    from db.models import MCPServerType

    result = await db.execute(
        select(MCPServer).where(
            MCPServer.type == MCPServerType.SPLUNK,
            MCPServer.is_active == True,
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active Splunk server found",
        )

    try:
        client = SplunkClient(server.endpoint, server.auth_config)
        spl = await client.generate_spl(description, index)
        return {"spl": spl, "description": description}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate SPL: {str(e)}",
        )
