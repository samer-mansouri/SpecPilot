from typing import Any, Callable, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

from specpilot.mcp.models import MCPTool


class SpecPilotMCPServer:
    """Wrapper around MCPServer for hosting dynamic SpecPilot API tools."""

    def __init__(self, name: str = "SpecPilot", instructions: Optional[str] = None) -> None:
        self.name = name
        self.instructions = instructions or "SpecPilot OpenAPI MCP Server"
        self.mcp_server = MCPServer(name=self.name, instructions=self.instructions)
        self._tools: Dict[str, MCPTool] = {}

    def register_tool(self, tool: MCPTool, handler: Optional[Callable[..., Any]] = None) -> None:
        """Register an MCP tool definition with the server."""
        self._tools[tool.name] = tool
        if handler:
            self.mcp_server.add_tool(
                fn=handler,
                name=tool.name,
                description=tool.description,
            )

    def list_tools(self) -> List[MCPTool]:
        """Return registered tools."""
        return list(self._tools.values())
