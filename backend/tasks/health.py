# =============================================================================
# BRKOPS-2585 Health Check Tasks
# Scheduled health checks for MCP servers
# =============================================================================

from datetime import datetime

import structlog
from sqlalchemy import select

from db.database import async_session
from db.models import MCPServer, HealthStatus
from services.cml_client import CMLClient
from services.splunk_client import SplunkClient

logger = structlog.get_logger()


async def check_mcp_health(ctx: dict):
    """Check health of all registered MCP servers."""
    logger.info("Running MCP health checks")

    async with async_session() as db:
        result = await db.execute(select(MCPServer).where(MCPServer.is_active == True))
        servers = result.scalars().all()

        for server in servers:
            try:
                tools = []
                healthy = False

                if server.type.value == "cml":
                    client = CMLClient(server.endpoint, server.auth_config)
                    try:
                        tools = await client.list_tools()
                        healthy = len(tools) > 0
                    except Exception as e:
                        logger.warning("CML list_tools failed", error=str(e))
                        healthy = await client.health_check()

                elif server.type.value == "splunk":
                    client = SplunkClient(server.endpoint, server.auth_config)
                    try:
                        tools = await client.list_tools()
                        healthy = len(tools) > 0
                    except Exception as e:
                        logger.warning(
                            "Splunk MCP connection failed",
                            server=server.name,
                            error=str(e),
                        )
                        # Use fallback tools but mark as unhealthy
                        tools = client.get_fallback_tools()
                        healthy = False

                server.health_status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
                server.last_health_check = datetime.utcnow()
                if tools:
                    server.available_tools = tools

                logger.info(
                    "MCP server health check",
                    server=server.name,
                    healthy=healthy,
                    tool_count=len(tools),
                )

            except Exception as e:
                server.health_status = HealthStatus.UNHEALTHY
                server.last_health_check = datetime.utcnow()
                logger.error(
                    "MCP server health check failed",
                    server=server.name,
                    error=str(e),
                )

        await db.commit()

    logger.info("MCP health checks complete", server_count=len(servers))
