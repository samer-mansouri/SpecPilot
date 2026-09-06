from pathlib import Path
from specpilot.agent.tools import convert_registry_to_llm_tools, mcp_tool_to_llm_tool
from specpilot.mcp.registry import MCPToolRegistry
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.parser import OpenAPIParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_mcp_tool_to_llm_tool_conversion() -> None:
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    loader = SpecLoader()
    raw = loader.load(json_path)
    spec = OpenAPIParser(raw).parse()

    registry = MCPToolRegistry.from_spec(spec)
    tool = registry.get_tool("list_pets")
    assert tool is not None

    llm_tool = mcp_tool_to_llm_tool(tool)
    assert llm_tool["type"] == "function"
    assert llm_tool["function"]["name"] == "list_pets"
    assert "List all pets" in llm_tool["function"]["description"]
    assert "properties" in llm_tool["function"]["parameters"]
    assert "limit" in llm_tool["function"]["parameters"]["properties"]


def test_convert_registry_to_llm_tools() -> None:
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    loader = SpecLoader()
    raw = loader.load(json_path)
    spec = OpenAPIParser(raw).parse()

    registry = MCPToolRegistry.from_spec(spec)
    llm_tools = convert_registry_to_llm_tools(registry)

    assert len(llm_tools) == 3
    tool_names = [t["function"]["name"] for t in llm_tools]
    assert "list_pets" in tool_names
    assert "create_pet" in tool_names
    assert "show_pet_by_id" in tool_names
