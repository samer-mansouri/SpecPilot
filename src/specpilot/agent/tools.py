import re
from typing import Any, Dict, List, Optional
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


def convert_registry_to_llm_tools(
    registry: MCPToolRegistry,
    user_prompt: Optional[str] = None,
    max_tools: int = 128,
) -> List[Dict[str, Any]]:
    """Convert registered MCP tools into OpenAI-compatible tool specifications, capping at max_tools (default 128)."""
    tools = registry.list_tools()

    if max_tools > 0 and len(tools) > max_tools:
        if user_prompt:
            prompt_words = set(re.findall(r"\w+", user_prompt.lower()))

            def _score_tool(t: MCPTool) -> int:
                score = 0
                text = f"{t.name} {t.path} {t.description or ''}".lower()
                for word in prompt_words:
                    if len(word) > 2 and word in text:
                        score += 1
                return score

            tools = sorted(tools, key=_score_tool, reverse=True)[:max_tools]
        else:
            tools = tools[:max_tools]

    return [mcp_tool_to_llm_tool(t) for t in tools]

