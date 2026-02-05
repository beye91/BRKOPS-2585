# =============================================================================
# BRKOPS-2585 Splunk MCP Client
# Client for Splunk MCP Server communication
# =============================================================================

import base64
import json
from typing import Any, Dict, List, Optional

import httpx
import structlog
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from config import settings

logger = structlog.get_logger()


def decode_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT payload without verification (for diagnostic purposes)."""
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None


class SplunkClient:
    """
    Client for communicating with Splunk MCP Server.
    Provides access to SPL query execution and natural language to SPL conversion.
    """

    def __init__(self, endpoint: str, auth_config: Dict[str, Any]):
        """
        Initialize Splunk MCP client.

        Args:
            endpoint: MCP server endpoint URL
            auth_config: Authentication configuration with host, token
        """
        self.endpoint = endpoint.rstrip("/")
        self.auth_config = auth_config
        self.timeout = settings.pipeline_mcp_timeout

        # Build the MCP endpoint URL
        self.mcp_url = f"{self.endpoint}/mcp"

        # Build auth header - JWT tokens use Bearer, HEC uses Splunk prefix
        token = auth_config.get("token", "")
        self.token_info = None

        if token:
            # JWT tokens (start with eyJ) use Bearer, otherwise use Splunk prefix
            if token.startswith("eyJ"):
                self.auth_header = f"Bearer {token}"
                # Decode JWT for diagnostics
                self.token_info = decode_jwt_payload(token)
                if self.token_info:
                    aud = self.token_info.get("aud", "")
                    if aud != "mcp":
                        logger.warning(
                            "JWT token audience is not 'mcp'",
                            audience=aud,
                            expected="mcp",
                            hint="Generate a new token with audience set to 'mcp' in Splunk",
                        )
            else:
                self.auth_header = f"Splunk {token}"
        else:
            self.auth_header = ""

    def _create_transport(self) -> StreamableHttpTransport:
        """Create a StreamableHttpTransport with auth headers."""
        headers = {}
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        return StreamableHttpTransport(
            url=self.mcp_url,
            headers=headers,
        )

    def _get_ssl_disabled_client(self):
        """Create httpx client with SSL verification disabled."""
        return httpx.AsyncClient(verify=False, timeout=self.timeout)

    async def _call_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Any:
        """
        Call a tool on the MCP server using direct HTTP (with SSL disabled for self-signed certs).

        Args:
            tool_name: Name of the MCP tool to call
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        try:
            headers = {"Authorization": self.auth_header} if self.auth_header else {}
            headers["Content-Type"] = "application/json"

            # Use JSON-RPC format for MCP tool calls
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters or {},
                },
                "id": 1,
            }

            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                response = await client.post(
                    self.mcp_url,
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        "MCP tool call HTTP error",
                        tool=tool_name,
                        status=response.status_code,
                        error=error_detail,
                    )
                    raise Exception(f"MCP tool call failed: HTTP {response.status_code}: {error_detail}")

                data = response.json()

                # Handle JSON-RPC error response
                if "error" in data:
                    error_msg = data["error"].get("message", str(data["error"]))
                    logger.error("MCP tool call RPC error", tool=tool_name, error=error_msg)
                    raise Exception(f"MCP tool call failed: {error_msg}")

                result = data.get("result", {})
                logger.debug(
                    "MCP tool call successful",
                    tool=tool_name,
                    result_type=type(result).__name__,
                )
                return result

        except httpx.RequestError as e:
            logger.error(
                "MCP tool call connection error",
                tool=tool_name,
                parameters=parameters,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "MCP tool call failed",
                tool=tool_name,
                parameters=parameters,
                error=str(e),
            )
            raise

    async def _call_tool_http(self, tool_name: str, parameters: Dict[str, Any] = None) -> Any:
        """
        Call a tool using direct HTTP (fallback for non-MCP servers).

        Args:
            tool_name: Name of the tool to call
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.endpoint}/tools/{tool_name}",
                json={
                    "parameters": parameters or {},
                    "auth": self.auth_config,
                },
                headers={"Authorization": self.auth_header} if self.auth_header else {},
            )

            if response.status_code != 200:
                error_detail = response.text
                logger.error(
                    "HTTP tool call failed",
                    tool=tool_name,
                    status=response.status_code,
                    error=error_detail,
                )
                raise Exception(f"HTTP tool call failed: {error_detail}")

            return response.json()

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the MCP server."""
        try:
            # Use httpx directly with SSL verification disabled for self-signed certs
            headers = {
                "Authorization": self.auth_header,
                "Content-Type": "application/json",
                "Accept": "application/json",
            } if self.auth_header else {"Content-Type": "application/json", "Accept": "application/json"}

            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                # MCP servers expose tools via POST to /mcp endpoint
                response = await client.post(
                    self.mcp_url,
                    json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                    headers=headers,
                )

                logger.debug(
                    "MCP list_tools response",
                    status=response.status_code,
                    url=self.mcp_url,
                )

                if response.status_code == 200:
                    data = response.json()

                    # Check for JSON-RPC error in response
                    if "error" in data:
                        error_msg = data["error"].get("message", str(data["error"]))
                        logger.error(
                            "MCP list_tools returned error",
                            error=error_msg,
                            code=data["error"].get("code"),
                        )
                        raise Exception(f"MCP error: {error_msg}")

                    tools = data.get("result", {}).get("tools", [])
                    logger.info(
                        "MCP tools retrieved successfully",
                        tool_count=len(tools),
                    )
                    return [
                        {
                            "name": tool.get("name"),
                            "description": tool.get("description"),
                            "inputSchema": tool.get("inputSchema"),
                        }
                        for tool in tools
                    ]
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"

                    # Check for authentication issues
                    if response.status_code in (401, 403):
                        if self.token_info:
                            aud = self.token_info.get("aud", "unknown")
                            if aud != "mcp":
                                error_msg = (
                                    f"Authentication failed (HTTP {response.status_code}). "
                                    f"JWT token audience is '{aud}' but must be 'mcp'. "
                                    "Generate a new token in Splunk with audience set to 'mcp'."
                                )
                        else:
                            error_msg = (
                                f"Authentication failed (HTTP {response.status_code}). "
                                "Check your JWT token configuration."
                            )

                    logger.error(
                        "MCP list_tools HTTP error",
                        status=response.status_code,
                        body=response.text[:500],
                        token_audience=self.token_info.get("aud") if self.token_info else None,
                    )
                    raise Exception(error_msg)

        except Exception as e:
            logger.error("Failed to list MCP tools", error=str(e), url=self.mcp_url)
            raise  # Re-raise to prevent silent fallback

    def get_fallback_tools(self) -> List[Dict[str, Any]]:
        """Return fallback tools when MCP connection fails."""
        return [
            {"name": "run_query", "description": "Execute SPL query"},
            {"name": "generate_spl", "description": "Generate SPL from natural language"},
            {"name": "get_indexes", "description": "List available indexes"},
            {"name": "get_saved_searches", "description": "List saved searches"},
        ]

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Any:
        """
        Execute a tool on the MCP server.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Returns:
            Tool result
        """
        return await self._call_tool(tool_name, parameters)

    # ==========================================================================
    # Query Execution
    # ==========================================================================
    async def run_query(
        self,
        spl: str,
        earliest: str = "-1h",
        latest: str = "now",
        max_results: int = 1000,
    ) -> Dict[str, Any]:
        """
        Execute a SPL query.

        Args:
            spl: SPL query string
            earliest: Start time (e.g., "-1h", "-24h", "2024-01-01T00:00:00")
            latest: End time (e.g., "now", "-5m")
            max_results: Maximum number of results to return

        Returns:
            Query results
        """
        try:
            result = await self._call_tool("run_splunk_query", {
                "spl": spl,
                "earliest_time": earliest,
                "latest_time": latest,
                "max_results": max_results,
            })

            # Normalize result format
            if isinstance(result, dict):
                results = result.get("results", [])
            elif isinstance(result, list):
                results = result
            else:
                results = []

            logger.info(
                "SPL query executed",
                result_count=len(results),
            )

            return {
                "query": spl,
                "results": results,
                "result_count": len(results),
                "execution_time_ms": result.get("execution_time_ms", 0) if isinstance(result, dict) else 0,
            }

        except Exception as e:
            logger.error("Failed to run SPL query", spl=spl, error=str(e))
            raise

    async def generate_spl(
        self,
        description: str,
        index: str = "network",
        additional_context: Optional[str] = None,
    ) -> str:
        """
        Generate SPL query from natural language description.

        Args:
            description: Natural language description of what to search for
            index: Default index to use
            additional_context: Additional context for the query

        Returns:
            Generated SPL query string
        """
        try:
            params = {
                "description": description,
                "default_index": index,
            }

            if additional_context:
                params["context"] = additional_context

            result = await self._call_tool("generate_spl", params)

            # Handle different return types
            if isinstance(result, str):
                spl = result
            elif isinstance(result, dict):
                spl = result.get("spl", result.get("query", ""))
            else:
                spl = str(result)

            logger.info("SPL generated", description=description, spl=spl)

            return spl

        except Exception as e:
            logger.error("Failed to generate SPL", description=description, error=str(e))
            # Return a basic fallback query
            return f'index={index} | head 100'

    # ==========================================================================
    # Convenience Methods
    # ==========================================================================
    async def search_ospf_events(
        self,
        earliest: str = "-1h",
        device: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for OSPF-related events."""
        spl = 'index=network (OSPF OR "routing" OR "adjacency")'
        if device:
            spl += f' host="{device}"'
        spl += ' | sort -_time | head 100'

        return await self.run_query(spl, earliest=earliest)

    async def search_routing_errors(
        self,
        earliest: str = "-1h",
        device: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for routing errors and warnings."""
        spl = 'index=network (error OR warning OR critical) (routing OR OSPF OR BGP OR EIGRP)'
        if device:
            spl += f' host="{device}"'
        spl += ' | sort -_time | head 100'

        return await self.run_query(spl, earliest=earliest)

    async def search_config_changes(
        self,
        earliest: str = "-1h",
        device: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for configuration change events."""
        spl = 'index=network ("config" OR "configuration") ("change" OR "modified" OR "updated")'
        if device:
            spl += f' host="{device}"'
        spl += ' | sort -_time | head 100'

        return await self.run_query(spl, earliest=earliest)

    async def search_authentication_events(
        self,
        earliest: str = "-1h",
        device: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for authentication-related events."""
        spl = 'index=network (authentication OR login OR "access" OR "denied" OR "failed")'
        if device:
            spl += f' host="{device}"'
        spl += ' | sort -_time | head 100'

        return await self.run_query(spl, earliest=earliest)

    async def get_device_logs(
        self,
        device: str,
        earliest: str = "-1h",
        max_results: int = 500,
    ) -> Dict[str, Any]:
        """Get all logs from a specific device."""
        spl = f'index=network host="{device}" | sort -_time'
        return await self.run_query(spl, earliest=earliest, max_results=max_results)

    # ==========================================================================
    # Index Management
    # ==========================================================================
    async def get_indexes(self) -> List[str]:
        """Get list of available indexes."""
        try:
            result = await self._call_tool("get_indexes")
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return result.get("indexes", [])
            return []
        except Exception as e:
            logger.error("Failed to get indexes", error=str(e))
            return ["network", "main", "security"]

    async def get_saved_searches(self) -> List[Dict[str, Any]]:
        """Get list of saved searches."""
        try:
            result = await self._call_tool("get_saved_searches")
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return result.get("searches", [])
            return []
        except Exception as e:
            logger.error("Failed to get saved searches", error=str(e))
            return []

    # ==========================================================================
    # Health Check
    # ==========================================================================
    async def health_check(self) -> bool:
        """Check if the MCP server is healthy."""
        try:
            tools = await self.list_tools()
            return len(tools) > 0
        except Exception:
            return False

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Splunk via MCP server."""
        try:
            indexes = await self.get_indexes()
            return {
                "status": "connected",
                "indexes": indexes,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
