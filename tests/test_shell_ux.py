from pathlib import Path
from specpilot.cli_shell import ShellEngine

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_shell_invalid_command_handling() -> None:
    engine = ShellEngine()
    # Invalid slash command should not crash
    should_exit = engine.execute_command("/invalid_command_xyz")
    assert should_exit is False


def test_shell_empty_input_handling() -> None:
    engine = ShellEngine()
    should_exit = engine.execute_command("")
    assert should_exit is False


def test_shell_missing_args_handling() -> None:
    engine = ShellEngine()

    # /use without path
    engine.execute_command("/use")
    assert engine.state.spec is None

    # Load spec
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    engine.execute_command(f"/use {json_path}")

    # /inspect without tool name
    engine.execute_command("/inspect")

    # /call without args
    engine.execute_command("/call")
