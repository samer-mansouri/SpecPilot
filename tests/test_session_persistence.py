import os
from pathlib import Path
import pytest
from langchain_core.messages import HumanMessage, AIMessage

from specpilot.cli_shell.state import SessionState


def test_session_save_and_load(tmp_path, monkeypatch):
    # Override SESSIONS_DIR to temporary path
    monkeypatch.setattr(SessionState, "SESSIONS_DIR", tmp_path / "sessions")

    state = SessionState()
    state.location = "./examples/petstore_sample.yaml"
    state.verbose = True
    state.read_only = True
    state.add_history_entry("/tools")
    state.messages = [
        HumanMessage(content="Find available pets"),
        AIMessage(content="Found 3 pets."),
    ]

    session_file = state.save_session("test_session")
    assert session_file.exists()
    assert "test_session.json" in str(session_file)

    # Restore in new state
    new_state = SessionState()
    restored_path = new_state.load_session("test_session")
    assert restored_path == session_file
    assert new_state.verbose is True
    assert new_state.read_only is True
    assert "/tools" in new_state.history
    assert len(new_state.messages) == 2
    assert new_state.messages[0].content == "Find available pets"


def test_session_list_saved(tmp_path, monkeypatch):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setattr(SessionState, "SESSIONS_DIR", sessions_dir)

    state = SessionState()
    state.save_session("session_alpha")
    state.save_session("session_beta")

    saved_list = SessionState.list_saved_sessions()
    assert "session_alpha" in saved_list
    assert "session_beta" in saved_list
