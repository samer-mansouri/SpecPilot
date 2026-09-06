from pathlib import Path
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.parser import OpenAPIParser
from specpilot.mcp.converter import ToolConverter

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_converter_sample_3_0() -> None:
    loader = SpecLoader()
    loaded = loader.load(str(FIXTURES_DIR / "sample_3_0.json"))
    spec = OpenAPIParser(loaded).parse()

    converter = ToolConverter()
    tools = converter.convert_spec(spec)

    assert len(tools) == 3
    tool_names = [t.name for t in tools]

    assert "list_pets" in tool_names
    assert "create_pet" in tool_names
    assert "show_pet_by_id" in tool_names

    list_pets_tool = next(t for t in tools if t.name == "list_pets")
    assert list_pets_tool.method == "GET"
    assert list_pets_tool.path == "/pets"
    assert "limit" in list_pets_tool.input_schema["properties"]

    create_pet_tool = next(t for t in tools if t.name == "create_pet")
    assert create_pet_tool.method == "POST"
    assert "requestBody" in create_pet_tool.input_schema["properties"]
    assert "requestBody" in create_pet_tool.input_schema.get("required", [])


def test_converter_collision_handling() -> None:
    from specpilot.openapi.models import Operation, NormalizedSpec

    op1 = Operation(operation_id="get_pet", method="GET", path="/pet/1")
    op2 = Operation(operation_id="get_pet", method="GET", path="/pet/2")

    spec = NormalizedSpec(
        title="Duplicate OP API",
        api_version="1.0",
        openapi_version="3.0.0",
        source="test",
        operations=[op1, op2],
    )

    converter = ToolConverter()
    tools = converter.convert_spec(spec)

    assert len(tools) == 2
    assert tools[0].name == "get_pet"
    assert tools[1].name == "get_pet_2"
