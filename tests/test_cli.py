from pathlib import Path
from click.testing import CliRunner

from specpilot.cli import cli

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "specpilot, version" in result.output


def test_cli_import_success() -> None:
    runner = CliRunner()
    sample_json = str(FIXTURES_DIR / "sample_3_0.json")
    result = runner.invoke(cli, ["import", sample_json])

    assert result.exit_code == 0
    assert "Title: Petstore API" in result.output
    assert "API Version: 1.0.0" in result.output
    assert "OpenAPI Version: 3.0.3" in result.output
    assert "Operations Discovered: 3" in result.output


def test_cli_import_nonexistent_file() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["import", "non_existent.json"])

    assert result.exit_code == 1
    assert "Error: Local file does not exist" in result.output


def test_cli_endpoints_success() -> None:
    runner = CliRunner()
    sample_json = str(FIXTURES_DIR / "sample_3_0.json")
    result = runner.invoke(cli, ["endpoints", sample_json])

    assert result.exit_code == 0
    assert "GET" in result.output
    assert "/pets" in result.output
    assert "listPets" in result.output
    assert "showPetById" in result.output


def test_cli_endpoints_yaml() -> None:
    runner = CliRunner()
    sample_yaml = str(FIXTURES_DIR / "sample_3_0.yaml")
    result = runner.invoke(cli, ["endpoints", sample_yaml])

    assert result.exit_code == 0
    assert "GET" in result.output
    assert "/pets" in result.output
    assert "listPets" in result.output
