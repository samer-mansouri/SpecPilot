from pathlib import Path
from specpilot.cli_shell import SessionState, ShellEngine

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_session_state_load_spec() -> None:
    state = SessionState()
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    spec = state.load_specification(json_path)

    assert spec.title == "Petstore API"
    assert state.spec is not None
    assert state.registry is not None
    assert state.location == json_path
    assert len(state.registry.list_tools()) == 3


def test_shell_engine_dispatch_help() -> None:
    engine = ShellEngine()
    should_exit = engine.execute_command("/help")
    assert should_exit is False


def test_shell_engine_dispatch_exit() -> None:
    engine = ShellEngine()
    should_exit = engine.execute_command("/exit")
    assert should_exit is True


def test_shell_engine_use_command() -> None:
    engine = ShellEngine()
    yaml_path = str(FIXTURES_DIR / "sample_3_0.yaml")
    engine.execute_command(f"/use {yaml_path}")

    assert engine.state.spec is not None
    assert engine.state.spec.title == "Petstore YAML API"
    assert engine.state.location == yaml_path
