from typing import Dict, List, Optional

from specpilot.openapi.models import NormalizedSpec
from specpilot.mcp.converter import ToolConverter
from specpilot.mcp.models import MCPTool
from specpilot.mcp.server import SpecPilotMCPServer


class MCPToolRegistry:
    """Registry managing converted MCP tools generated from OpenAPI specifications."""

    def __init__(self) -> None:
        self._tools: Dict[str, MCPTool] = {}
        self.converter = ToolConverter()

    @classmethod
    def from_spec(cls, spec: NormalizedSpec) -> "MCPToolRegistry":
        """Create and populate an MCPToolRegistry from a NormalizedSpec."""
        registry = cls()
        tools = registry.converter.convert_spec(spec)
        for tool in tools:
            registry.register_tool(tool)
        return registry

    def register_tool(self, tool: MCPTool) -> None:
        """Register an MCP tool into the registry."""
        self._tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Look up a tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[MCPTool]:
        """Return all registered MCP tools."""
        return list(self._tools.values())

    def bind_to_server(self, server: SpecPilotMCPServer) -> None:
        """Bind all tools in this registry to a SpecPilotMCPServer."""
        for tool in self._tools.values():
            server.register_tool(tool)
