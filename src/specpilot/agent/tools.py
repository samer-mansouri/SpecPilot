from typing import Any, Dict, List
from specpilot.mcp.models import MCPTool
from specpilot.mcp.registry import MCPToolRegistry


def mcp_tool_to_llm_tool(tool: MCPTool) -> Dict[str, Any]:
    """Convert a single MCPTool into an OpenAI-compatible function tool definition."""
    schema = tool.input_schema if isinstance(tool.input_schema, dict) else {"type": "object", "properties": {}}
    
    # Ensure JSON schema has type object
    if "type" not in schema:
        schema["type"] = "object"

    description = tool.description or f"Execute HTTP operation {tool.method.upper()} {tool.path}"

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": description,
            "parameters": schema,
        },
    }


def convert_registry_to_llm_tools(registry: MCPToolRegistry) -> List[Dict[str, Any]]:
    """Convert all registered MCP tools into OpenAI-compatible tool specifications."""
    tools = registry.list_tools()
    return [mcp_tool_to_llm_tool(t) for t in tools]
