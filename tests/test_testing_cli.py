from click.testing import CliRunner
import respx
from httpx import Response

from specpilot.cli import cli


def test_cli_test_command_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["test", "--help"])
    assert result.exit_code == 0
    assert "Run OpenAPI-driven API contract tests" in result.output
    assert "--tag" in result.output
    assert "--read-only" in result.output


@respx.mock
def test_cli_test_command_execution():
    respx.get(url__startswith="https://api.example.com").mock(
        return_value=Response(200, json=[{"id": 1, "name": "Fido"}], headers={"content-type": "application/json"})
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["test", "./tests/fixtures/sample_3_0.yaml", "--base-url", "https://api.example.com", "--read-only"])
    assert result.exit_code == 0
    assert "API Contract Test Report" in result.output
    assert "Test Execution Summary" in result.output
