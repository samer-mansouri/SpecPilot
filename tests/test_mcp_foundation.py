from specpilot.mcp import ExecutionResult, MCPTool, SpecPilotMCPServer


def test_mcp_models_initialization() -> None:
    tool = MCPTool(
        name="get_pet",
        description="Retrieve a pet by ID",
        method="GET",
        path="/pets/{id}",
        input_schema={"type": "object", "properties": {"id": {"type": "string"}}},
    )

    assert tool.name == "get_pet"
    assert tool.method == "GET"
    assert tool.path == "/pets/{id}"
    assert "id" in tool.input_schema["properties"]


def test_mcp_server_tool_registration() -> None:
    server = SpecPilotMCPServer(name="TestServer")
    tool = MCPTool(
        name="test_tool",
        description="Test tool",
        method="GET",
        path="/test",
    )

    def dummy_handler() -> str:
        return "ok"

    server.register_tool(tool, handler=dummy_handler)
    tools = server.list_tools()

    assert len(tools) == 1
    assert tools[0].name == "test_tool"


def test_execution_result_defaults() -> None:
    res = ExecutionResult(status_code=200, body={"success": True})
    assert res.status_code == 200
    assert res.is_error is False
    assert res.body == {"success": True}
