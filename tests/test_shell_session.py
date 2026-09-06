from pathlib import Path
from specpilot.cli_shell import SessionState, ShellEngine

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_secret_redaction_in_state() -> None:
    state = SessionState()
    state.add_history_entry("/call get_user --json '{\"api_key\": \"super_secret_key_123\"}'")

    assert len(state.history) == 1
    assert "super_secret_key_123" not in state.history[0]
    assert "[REDACTED" in state.history[0]


def test_verbose_toggle() -> None:
    engine = ShellEngine()
    assert engine.state.verbose is False

    engine.execute_command("/verbose on")
    assert engine.state.verbose is True

    engine.execute_command("/verbose off")
    assert engine.state.verbose is False


def test_history_and_clear_commands() -> None:
    engine = ShellEngine()
    engine.execute_command("/api")
    engine.execute_command("/verbose on")

    assert len(engine.state.history) == 2

    # Execute /history
    should_exit = engine.execute_command("/history")
    assert should_exit is False

    # Execute /clear
    should_exit = engine.execute_command("/clear")
    assert should_exit is False
