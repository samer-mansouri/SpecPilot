from pathlib import Path
from click.testing import CliRunner
import respx
from httpx import Response

from specpilot.cli import cli

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_cli_tools_command() -> None:
    runner = CliRunner()
    sample_json = str(FIXTURES_DIR / "sample_3_0.json")
    result = runner.invoke(cli, ["tools", sample_json])

    assert result.exit_code == 0
    assert "list_pets" in result.output
    assert "create_pet" in result.output
    assert "show_pet_by_id" in result.output


def test_cli_inspect_command() -> None:
    runner = CliRunner()
    sample_json = str(FIXTURES_DIR / "sample_3_0.json")
    result = runner.invoke(cli, ["inspect", "list_pets", sample_json])

    assert result.exit_code == 0
    assert "MCP Tool Inspection: list_pets" in result.output
    assert "Method: GET" in result.output
    assert "Path: /pets" in result.output
    assert "input_schema" in result.output or "Input JSON Schema" in result.output


def test_cli_inspect_nonexistent_tool() -> None:
    runner = CliRunner()
    sample_json = str(FIXTURES_DIR / "sample_3_0.json")
    result = runner.invoke(cli, ["inspect", "nonexistent_tool", sample_json])

    assert result.exit_code == 1
    assert "Error: Tool 'nonexistent_tool' not found" in result.output


@respx.mock
def test_cli_call_command() -> None:
    respx.get("https://api.petstore.example.com/v1/pets?limit=5").mock(
        return_value=Response(200, json=[{"id": 1, "name": "Rover"}], headers={"content-type": "application/json"})
    )

    runner = CliRunner()
    sample_json = str(FIXTURES_DIR / "sample_3_0.json")
    result = runner.invoke(cli, ["call", "list_pets", sample_json, "--json", '{"limit": 5}'])

    assert result.exit_code == 0
    assert "HTTP Status: 200" in result.output
    assert "Rover" in result.output
