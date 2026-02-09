# =============================================================================
# BRKOPS-2585 CML MCP Client
# Client for CML MCP Server communication using FastMCP
# =============================================================================

import base64
import re
from typing import Any, Dict, List, Optional

import httpx
import structlog
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from config import settings

logger = structlog.get_logger()


class CMLClient:
    """
    Client for communicating with CML MCP Server.
    Provides access to CML lab management, device configuration, and CLI execution.
    Uses FastMCP client for MCP protocol communication.
    """

    def __init__(self, endpoint: str, auth_config: Dict[str, Any]):
        """
        Initialize CML MCP client.

        Args:
            endpoint: MCP server endpoint URL (e.g., http://192.168.1.213:9001)
            auth_config: Authentication configuration with username and password
        """
        self.endpoint = endpoint.rstrip("/")
        self.auth_config = auth_config
        self.timeout = settings.pipeline_mcp_timeout

        # Build the MCP endpoint URL
        self.mcp_url = f"{self.endpoint}/mcp"

        # Build auth header for HTTP transport
        # CML MCP expects X-Authorization header with base64 encoded credentials
        username = auth_config.get("username", "admin")
        password = auth_config.get("password", "")
        credentials = f"{username}:{password}"
        encoded_creds = base64.b64encode(credentials.encode()).decode()
        self.auth_header = f"Basic {encoded_creds}"

    def _create_transport(self) -> StreamableHttpTransport:
        """Create a StreamableHttpTransport with auth headers."""
        return StreamableHttpTransport(
            url=self.mcp_url,
            headers={"X-Authorization": self.auth_header},
        )

    def _parse_mcp_result(self, result: Any) -> Any:
        """Parse MCP tool result to extract actual data."""
        import json

        # If it's a basic scalar type, return it
        if isinstance(result, (str, int, float, bool, type(None))):
            return result

        # If it's a dict, return it directly
        if isinstance(result, dict):
            return result

        # If it's a list, check if items need parsing (might be TextContent objects)
        if isinstance(result, list):
            if result and hasattr(result[0], 'text'):
                # List of TextContent - extract and parse
                texts = [item.text for item in result if hasattr(item, 'text')]
                if texts:
                    combined = texts[0] if len(texts) == 1 else '\n'.join(texts)
                    try:
                        return json.loads(combined)
                    except json.JSONDecodeError:
                        return combined
            return result

        # Handle CallToolResult from fastmcp
        if hasattr(result, 'content') and result.content:
            # Content is a list of TextContent, ImageContent, etc.
            texts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    texts.append(content.text)

            # If we have text content, try to parse as JSON
            if texts:
                combined = texts[0] if len(texts) == 1 else '\n'.join(texts)
                try:
                    return json.loads(combined)
                except json.JSONDecodeError:
                    return combined

        # Fallback: try to convert to string
        return str(result)

    async def _call_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the MCP tool to call
            parameters: Tool parameters

        Returns:
            Tool execution result
        """
        transport = self._create_transport()
        async with Client(transport) as client:
            try:
                result = await client.call_tool(tool_name, parameters or {})
                logger.debug(
                    "MCP tool call successful",
                    tool=tool_name,
                    result_type=type(result).__name__,
                )

                # Parse and return the result
                return self._parse_mcp_result(result)
            except Exception as e:
                logger.error(
                    "MCP tool call failed",
                    tool=tool_name,
                    parameters=parameters,
                    error=str(e),
                )
                raise

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools from the MCP server."""
        try:
            transport = self._create_transport()
            async with Client(transport) as client:
                tools = await client.list_tools()
                # Convert to list of dicts for API response
                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema if hasattr(tool, "inputSchema") else None,
                    }
                    for tool in tools
                ]
        except Exception as e:
            logger.error("Failed to list MCP tools", error=str(e))
            # Return common CML tools as fallback
            return [
                {"name": "get_cml_labs", "description": "Get all labs"},
                {"name": "get_nodes_for_cml_lab", "description": "Get nodes in a lab"},
                {"name": "configure_cml_node", "description": "Set node startup config"},
                {"name": "send_cli_command", "description": "Send CLI command to node"},
                {"name": "start_cml_lab", "description": "Start a lab"},
                {"name": "stop_cml_lab", "description": "Stop a lab"},
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
    # Lab Management
    # ==========================================================================
    async def get_labs(self, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all labs from CML."""
        try:
            params = {}
            if user:
                params["user"] = user
            result = await self._call_tool("get_cml_labs", params if params else None)
            # Result is the list of labs directly
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error("Failed to get labs", error=str(e))
            raise

    async def get_lab(self, lab_id: str) -> Dict[str, Any]:
        """Get details of a specific lab by title."""
        try:
            result = await self._call_tool("get_cml_lab_by_title", {"title": lab_id})
            return result
        except Exception as e:
            logger.error("Failed to get lab", lab_id=lab_id, error=str(e))
            raise

    async def get_lab_by_id(self, lab_id: str) -> Dict[str, Any]:
        """Get lab by UUID."""
        try:
            # Use get_cml_labs and filter by ID
            labs = await self.get_labs()
            for lab in labs:
                if lab.get("id") == lab_id:
                    return lab
            raise Exception(f"Lab with ID {lab_id} not found")
        except Exception as e:
            logger.error("Failed to get lab by ID", lab_id=lab_id, error=str(e))
            raise

    # ==========================================================================
    # Node Management
    # ==========================================================================
    async def get_nodes(self, lab_id: str) -> List[Dict[str, Any]]:
        """Get all nodes in a lab."""
        try:
            # MCP tool expects 'lid' parameter
            result = await self._call_tool("get_nodes_for_cml_lab", {"lid": lab_id})
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error("Failed to get nodes", lab_id=lab_id, error=str(e))
            raise

    async def get_node(self, lab_id: str, node_id: str) -> Dict[str, Any]:
        """Get details of a specific node."""
        try:
            nodes = await self.get_nodes(lab_id)
            for node in nodes:
                if node.get("id") == node_id:
                    return node
            raise Exception(f"Node with ID {node_id} not found in lab {lab_id}")
        except Exception as e:
            logger.error("Failed to get node", lab_id=lab_id, node_id=node_id, error=str(e))
            raise

    async def find_node_by_label(self, lab_id: str, label: str) -> Optional[Dict[str, Any]]:
        """Find a node by its label/name."""
        nodes = await self.get_nodes(lab_id)
        for node in nodes:
            if node.get("label", "").lower() == label.lower():
                return node
        return None

    # ==========================================================================
    # Configuration Management
    # ==========================================================================
    async def get_node_config(self, lab_id: str, node_id: str) -> str:
        """Get the current configuration of a node via console log."""
        try:
            # MCP tool expects 'lid' and 'nid' parameters
            result = await self._call_tool("get_console_log", {
                "lid": lab_id,
                "nid": node_id,
            })
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.error("Failed to get node config", lab_id=lab_id, node_id=node_id, error=str(e))
            raise

    async def configure_node(
        self,
        lab_id: str,
        node_id: str,
        config: str,
    ) -> Dict[str, Any]:
        """
        Set node startup configuration.

        Args:
            lab_id: Lab UUID
            node_id: Node UUID
            config: Configuration to set

        Returns:
            Result of configuration
        """
        try:
            # MCP tool expects 'lid' and 'nid' parameters
            result = await self._call_tool("configure_cml_node", {
                "lid": lab_id,
                "nid": node_id,
                "config": config,
            })

            logger.info(
                "Configuration set",
                lab_id=lab_id,
                node_id=node_id,
            )

            return result if isinstance(result, dict) else {"status": "success", "result": result}

        except Exception as e:
            logger.error(
                "Failed to configure node",
                lab_id=lab_id,
                node_id=node_id,
                error=str(e),
            )
            raise

    async def apply_config(
        self,
        lab_id: str,
        node_id: str,
        config: str,
        save: bool = True,
    ) -> Dict[str, Any]:
        """
        Apply configuration to a running node via CLI.

        Args:
            lab_id: Lab ID
            node_id: Node ID
            config: Configuration commands to apply
            save: Whether to save config after applying

        Returns:
            Result of configuration application
        """
        try:
            # Get node label for CLI command
            node = await self.get_node(lab_id, node_id)
            node_label = node.get("label", node_id)

            # Add 'end' and optionally 'write memory' to config
            full_config = config.strip()
            if save:
                full_config += "\nend\nwrite memory"
            else:
                full_config += "\nend"

            # Send all config commands as a block with config_command flag
            # This ensures commands are sent in config mode (not exec mode)
            result = await self._call_tool("send_cli_command", {
                "lid": lab_id,
                "label": node_label,
                "commands": full_config,
                "config_command": True,
            })

            logger.info(
                "Configuration applied via CLI",
                lab_id=lab_id,
                node_id=node_id,
                node_label=node_label,
            )

            return {
                "success": True,
                "output": result if isinstance(result, str) else str(result),
            }

        except Exception as e:
            error_str = str(e)
            # Workaround for pyATS/unicon bug where state check fails even when
            # the expected and actual states are identical (false negative)
            if "Expected device to reach" in error_str and "but landed on" in error_str:
                # Extract states from error message
                match = re.search(r"reach '(\w+)' state.*landed on '(\w+)' state", error_str)
                if match and match.group(1).lower() == match.group(2).lower():
                    logger.warning(
                        "Ignoring pyATS false-negative state check error",
                        lab_id=lab_id,
                        node_id=node_id,
                        expected_state=match.group(1),
                        actual_state=match.group(2),
                    )
                    return {
                        "success": True,
                        "output": "Configuration applied (pyATS state check bypassed)",
                    }

            logger.error(
                "Failed to apply config",
                lab_id=lab_id,
                node_id=node_id,
                error=error_str,
            )
            raise

    # ==========================================================================
    # CLI Execution
    # ==========================================================================
    async def run_command(
        self,
        lab_id: str,
        node_label: str,
        command: str,
    ) -> str:
        """
        Run a CLI command on a node.

        Args:
            lab_id: Lab UUID
            node_label: Node label/name (not UUID)
            command: CLI command to execute

        Returns:
            Command output
        """
        try:
            # MCP tool expects 'lid', 'label', and 'commands' (as a string) parameters
            result = await self._call_tool("send_cli_command", {
                "lid": lab_id,
                "label": node_label,
                "commands": command,  # Single command as string
            })
            return result if isinstance(result, str) else str(result)
        except Exception as e:
            logger.error(
                "Failed to run command",
                lab_id=lab_id,
                node_label=node_label,
                command=command,
                error=str(e),
            )
            raise

    async def run_commands(
        self,
        lab_id: str,
        node_label: str,
        commands: List[str],
    ) -> List[str]:
        """
        Run multiple CLI commands on a node.

        Args:
            lab_id: Lab UUID
            node_label: Node label
            commands: List of CLI commands

        Returns:
            List of command outputs
        """
        outputs = []
        for command in commands:
            output = await self.run_command(lab_id, node_label, command)
            outputs.append(output)
        return outputs

    # ==========================================================================
    # Lab Operations
    # ==========================================================================
    async def start_lab(self, lab_id: str, wait_for_convergence: bool = True) -> Dict[str, Any]:
        """Start a lab."""
        try:
            # MCP tool expects 'lid' parameter
            result = await self._call_tool("start_cml_lab", {
                "lid": lab_id,
                "wait_for_convergence": wait_for_convergence,
            })
            logger.info("Lab started", lab_id=lab_id)
            return result if isinstance(result, dict) else {"status": "started"}
        except Exception as e:
            logger.error("Failed to start lab", lab_id=lab_id, error=str(e))
            raise

    async def stop_lab(self, lab_id: str) -> Dict[str, Any]:
        """Stop a lab."""
        try:
            # MCP tool expects 'lid' parameter
            result = await self._call_tool("stop_cml_lab", {"lid": lab_id})
            logger.info("Lab stopped", lab_id=lab_id)
            return result if isinstance(result, dict) else {"status": "stopped"}
        except Exception as e:
            logger.error("Failed to stop lab", lab_id=lab_id, error=str(e))
            raise

    # ==========================================================================
    # Topology
    # ==========================================================================
    def _extract_node_from_link(self, link: Dict, side: str) -> Optional[str]:
        """
        Extract node ID from link object with multiple fallback patterns.

        Args:
            link: Link object from CML MCP
            side: Either 'a' or 'b' for node_a/node_b

        Returns:
            Node ID or None if not found
        """
        # Try direct fields first
        patterns = [
            f"node_{side}",           # node_a, node_b
            f"node_{side}_id",        # node_a_id, node_b_id
        ]

        for pattern in patterns:
            if value := link.get(pattern):
                return value

        # Try nested interface structure
        interface_key = f"interface_{side}"
        if interface := link.get(interface_key):
            if isinstance(interface, dict):
                # Try various node reference fields
                for field in ["node", "node_id", "id"]:
                    if value := interface.get(field):
                        return value

        return None

    async def get_topology(self, lab_id: str) -> Dict[str, Any]:
        """
        Get topology graph data for visualization.

        Args:
            lab_id: Lab UUID

        Returns:
            Topology data with nodes and links
        """
        try:
            # Get lab details
            lab = await self.get_lab_by_id(lab_id)

            # Get nodes
            nodes = await self.get_nodes(lab_id)

            # Get links - MCP tool expects 'lid' parameter
            links_result = await self._call_tool("get_all_links_for_lab", {"lid": lab_id})
            links = links_result if isinstance(links_result, list) else []

            # DEBUG: Log raw link structure
            logger.info("CML topology links retrieved",
                        lab_id=lab_id,
                        link_count=len(links),
                        sample_link=links[0] if links else None)

            # Transform for frontend visualization
            graph_nodes = []
            for node in nodes:
                graph_nodes.append({
                    "id": node.get("id"),
                    "label": node.get("label"),
                    "type": node.get("node_definition"),
                    "state": node.get("state"),
                    "x": node.get("x", 0),
                    "y": node.get("y", 0),
                })

            graph_links = []
            node_ids = {node.get("id") for node in nodes}  # Set of valid node IDs
            filtered_links = []

            for link in links:
                # DEBUG: Log each link before transformation
                logger.debug("Processing link",
                             link_id=link.get("id"),
                             raw_fields=list(link.keys()))

                source = self._extract_node_from_link(link, "a")
                target = self._extract_node_from_link(link, "b")

                # Validate node IDs exist
                if not source or not target:
                    logger.warning("Link missing endpoints",
                                   link_id=link.get("id"),
                                   source=source,
                                   target=target,
                                   raw_link=link)
                    filtered_links.append(link.get("id"))
                    continue

                if source not in node_ids or target not in node_ids:
                    logger.warning("Link references unknown nodes",
                                   link_id=link.get("id"),
                                   source=source,
                                   target=target,
                                   valid_nodes=list(node_ids))
                    filtered_links.append(link.get("id"))
                    continue

                # Valid link - add to graph
                graph_links.append({
                    "id": link.get("id"),
                    "source": source,
                    "target": target,
                    "interface_a": link.get("interface_a"),
                    "interface_b": link.get("interface_b"),
                })

            logger.info("Topology links processed",
                        total_links=len(links),
                        valid_links=len(graph_links),
                        filtered_links=len(filtered_links))

            return {
                "lab_id": lab_id,
                "lab_title": lab.get("title", "Untitled Lab"),
                "nodes": graph_nodes,
                "links": graph_links,
            }

        except Exception as e:
            logger.error("Failed to get topology", lab_id=lab_id, error=str(e))
            raise

    # ==========================================================================
    # System Information
    # ==========================================================================
    async def get_system_info(self) -> Dict[str, Any]:
        """Get CML server information."""
        try:
            result = await self._call_tool("get_cml_information")
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error("Failed to get system info", error=str(e))
            raise

    async def get_statistics(self) -> Dict[str, Any]:
        """Get CML resource statistics."""
        try:
            result = await self._call_tool("get_cml_statistics")
            return result if isinstance(result, dict) else {}
        except Exception as e:
            logger.error("Failed to get statistics", error=str(e))
            raise

    # ==========================================================================
    # Health Check
    # ==========================================================================
    async def health_check(self) -> bool:
        """Check if the MCP server is healthy by listing tools."""
        try:
            tools = await self.list_tools()
            return len(tools) > 0
        except Exception:
            return False

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to CML via MCP server."""
        try:
            # Try to get system info as a connectivity test
            info = await self.get_system_info()
            return {
                "status": "connected",
                "server_version": info.get("version", "unknown"),
                "hostname": info.get("hostname", "unknown"),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    # ==========================================================================
    # Lab Creation and Deletion
    # ==========================================================================
    async def create_lab_from_yaml(self, yaml_content: str, title: str = None) -> Dict[str, Any]:
        """
        Create a lab from YAML topology definition.

        Args:
            yaml_content: CML topology YAML content
            title: Optional title override

        Returns:
            Created lab information including ID
        """
        import yaml as yaml_lib

        try:
            # Parse YAML string to dict
            topology_dict = yaml_lib.safe_load(yaml_content)

            params = {"topology": topology_dict}
            if title:
                params["title"] = title

            result = await self._call_tool("create_full_lab_topology", params)
            logger.info("Lab created from YAML", title=title)
            return result if isinstance(result, dict) else {"id": str(result)}
        except Exception as e:
            logger.error("Failed to create lab from YAML", error=str(e))
            raise

    async def check_lab_exists(self, title: str) -> bool:
        """
        Check if a lab with given title exists.

        Args:
            title: Lab title to check

        Returns:
            True if lab exists, False otherwise
        """
        try:
            result = await self._call_tool("get_cml_lab_by_title", {"title": title})
            return result is not None
        except Exception:
            return False

    async def delete_lab(self, lab_id: str) -> Dict[str, Any]:
        """
        Delete a lab by ID.

        Args:
            lab_id: Lab UUID to delete

        Returns:
            Deletion result
        """
        try:
            # Stop the lab first if it's running
            try:
                await self.stop_lab(lab_id)
            except Exception:
                pass  # Lab might already be stopped

            # MCP tool expects 'lid' parameter
            result = await self._call_tool("delete_cml_lab", {"lid": lab_id})
            logger.info("Lab deleted", lab_id=lab_id)
            return result if isinstance(result, dict) else {"status": "deleted"}
        except Exception as e:
            logger.error("Failed to delete lab", lab_id=lab_id, error=str(e))
            raise

    async def get_lab_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get a lab by its title.

        Args:
            title: Lab title to find

        Returns:
            Lab information or None if not found
        """
        try:
            result = await self._call_tool("get_cml_lab_by_title", {"title": title})
            return result
        except Exception as e:
            logger.error("Failed to get lab by title", title=title, error=str(e))
            return None

    # ==========================================================================
    # Lab Reset
    # ==========================================================================
    def _get_router1_baseline(self) -> str:
        """Get baseline interface configuration commands for Router-1."""
        return """hostname Router-1
!
default interface GigabitEthernet2
default interface GigabitEthernet3
default interface GigabitEthernet4
!
interface GigabitEthernet2
 description Link-to-Router-2
 ip address 10.1.12.1 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet3
 description Link-to-Router-3
 ip address 10.1.13.1 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet4
 description Link-to-Router-4
 ip address 10.1.14.1 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
router ospf 1
 network 10.1.12.0 0.0.0.3 area 0
 network 10.1.13.0 0.0.0.3 area 0
 network 10.1.14.0 0.0.0.3 area 0
 network 10.255.255.1 0.0.0.0 area 0
end"""

    def _get_router2_baseline(self) -> str:
        """Get baseline interface configuration commands for Router-2."""
        return """hostname Router-2
!
default interface GigabitEthernet2
default interface GigabitEthernet3
default interface GigabitEthernet4
!
interface GigabitEthernet2
 description Link-to-Router-1
 ip address 10.1.12.2 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet3
 description Link-to-Router-3
 ip address 10.1.23.1 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet4
 description Link-to-Router-4
 ip address 10.1.24.1 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
router ospf 1
 network 10.1.12.0 0.0.0.3 area 0
 network 10.1.23.0 0.0.0.3 area 0
 network 10.1.24.0 0.0.0.3 area 0
 network 10.255.255.2 0.0.0.0 area 0
end"""

    def _get_router3_baseline(self) -> str:
        """Get baseline interface configuration commands for Router-3."""
        return """hostname Router-3
!
default interface GigabitEthernet2
default interface GigabitEthernet3
default interface GigabitEthernet4
!
interface GigabitEthernet2
 description Link-to-Router-1
 ip address 10.1.13.2 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet3
 description Link-to-Router-2
 ip address 10.1.23.2 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet4
 description Link-to-Router-4
 ip address 10.1.34.1 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
router ospf 1
 network 10.1.13.0 0.0.0.3 area 0
 network 10.1.23.0 0.0.0.3 area 0
 network 10.1.34.0 0.0.0.3 area 0
 network 10.255.255.3 0.0.0.0 area 0
end"""

    def _get_router4_baseline(self) -> str:
        """Get baseline interface configuration commands for Router-4."""
        return """hostname Router-4
!
default interface GigabitEthernet2
default interface GigabitEthernet3
default interface GigabitEthernet4
!
interface GigabitEthernet2
 description Link-to-Router-1
 ip address 10.1.14.2 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet3
 description Link-to-Router-2
 ip address 10.1.24.2 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
interface GigabitEthernet4
 description Link-to-Router-3
 ip address 10.1.34.2 255.255.255.252
 ip ospf network point-to-point
 no shutdown
!
router ospf 1
 network 10.1.14.0 0.0.0.3 area 0
 network 10.1.24.0 0.0.0.3 area 0
 network 10.1.34.0 0.0.0.3 area 0
 network 10.255.255.4 0.0.0.0 area 0
end"""

    async def reset_lab_configs(self, lab_id: str) -> Dict[str, Any]:
        """
        Reset all router configurations to baseline demo state.

        This applies the original startup interface configurations to each router
        via CLI commands without needing to stop/wipe/restart the lab.

        Args:
            lab_id: Lab UUID

        Returns:
            Dictionary with reset results per router
        """
        baseline_configs = {
            "Router-1": self._get_router1_baseline(),
            "Router-2": self._get_router2_baseline(),
            "Router-3": self._get_router3_baseline(),
            "Router-4": self._get_router4_baseline(),
        }

        results = {}
        for label, config in baseline_configs.items():
            try:
                # Apply config via CLI using commands parameter (as string)
                await self._call_tool("send_cli_command", {
                    "lid": lab_id,
                    "label": label,
                    "commands": config,
                    "config_command": True,
                })
                results[label] = "success"
                logger.info("Router config reset", lab_id=lab_id, router=label)
            except Exception as e:
                results[label] = f"error: {str(e)}"
                logger.error(
                    "Failed to reset router config",
                    lab_id=lab_id,
                    router=label,
                    error=str(e),
                )

        return {"reset_results": results}
