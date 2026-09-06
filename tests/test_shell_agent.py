from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import pytest
import respx

from specpilot.agent import ChatMessage, CompletionResponse, FunctionCall, LLMConfig, ToolCall
from specpilot.cli_shell import ShellEngine

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_shell_unconfigured_llm_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPECPILOT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    engine = ShellEngine()
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    engine.execute_command(f"/use {json_path}")

    # Enter natural language prompt
    should_exit = engine.execute_command("Show me all pets")
    assert should_exit is False


@respx.mock
def test_shell_natural_language_agent_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPECPILOT_LLM_API_KEY", "test_key_123")

    # Mock LLM provider completion endpoint
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "There are 5 pets registered in the store.",
                        },
                    }
                ]
            },
        )
    )

    engine = ShellEngine()
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    engine.execute_command(f"/use {json_path}")
    engine.execute_command("/verbose on")

    should_exit = engine.execute_command("How many pets are there?")
    assert should_exit is False
