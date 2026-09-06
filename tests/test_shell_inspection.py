from pathlib import Path
from prompt_toolkit.document import Document
from specpilot.cli_shell import SessionState, ShellEngine
from specpilot.cli_shell.completion import SpecPilotCompleter

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_shell_api_and_tools_inspection() -> None:
    engine = ShellEngine()
    json_path = str(FIXTURES_DIR / "sample_3_0.json")

    # Load specification
    engine.execute_command(f"/use {json_path}")

    # Test /api command
    should_exit = engine.execute_command("/api")
    assert should_exit is False

    # Test /tools command
    should_exit = engine.execute_command("/tools")
    assert should_exit is False

    # Test /tools with tag filter
    should_exit = engine.execute_command("/tools pets")
    assert should_exit is False

    # Test /inspect tool command
    should_exit = engine.execute_command("/inspect list_pets")
    assert should_exit is False


def test_shell_completer_commands() -> None:
    state = SessionState()
    completer = SpecPilotCompleter(state)

    # Complete slash command prefix
    doc = Document("/in")
    completions = [c.text for c in completer.get_completions(doc)]
    assert "/inspect" in completions


def test_shell_completer_tool_names() -> None:
    state = SessionState()
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    state.load_specification(json_path)

    completer = SpecPilotCompleter(state)

    # Complete tool name after /inspect
    doc = Document("/inspect list")
    completions = [c.text for c in completer.get_completions(doc)]
    assert "list_pets" in completions
