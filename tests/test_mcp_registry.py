from pathlib import Path
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.parser import OpenAPIParser
from specpilot.mcp.registry import MCPToolRegistry
from specpilot.mcp.server import SpecPilotMCPServer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_registry_from_spec() -> None:
    loader = SpecLoader()
    loaded = loader.load(str(FIXTURES_DIR / "sample_3_0.json"))
    spec = OpenAPIParser(loaded).parse()

    registry = MCPToolRegistry.from_spec(spec)
    tools = registry.list_tools()

    assert len(tools) == 3
    assert registry.get_tool("list_pets") is not None
    assert registry.get_tool("nonexistent") is None


def test_registry_bind_to_server() -> None:
    loader = SpecLoader()
    loaded = loader.load(str(FIXTURES_DIR / "sample_3_0.json"))
    spec = OpenAPIParser(loaded).parse()

    registry = MCPToolRegistry.from_spec(spec)
    server = SpecPilotMCPServer(name="RegistryServer")
    registry.bind_to_server(server)

    server_tools = server.list_tools()
    assert len(server_tools) == 3
