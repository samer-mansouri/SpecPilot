from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import pytest
import respx

from specpilot.agent import (
    ChatMessage,
    CompletionResponse,
    FunctionCall,
    LLMProvider,
    SpecPilotAgent,
    SpecPilotGraph,
    ToolCall,
)
from specpilot.cli_shell import ShellEngine
from specpilot.mcp.registry import MCPToolRegistry
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.parser import OpenAPIParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockProvider(LLMProvider):
    def __init__(self, responses: List[CompletionResponse]) -> None:
        self.responses = responses
        self.call_count = 0

    def complete(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> CompletionResponse:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return CompletionResponse(
            message=ChatMessage(role="assistant", content="Done.")
        )


def _get_sample_registry() -> MCPToolRegistry:
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    spec = OpenAPIParser(SpecLoader().load(json_path)).parse()
    return MCPToolRegistry.from_spec(spec)


@respx.mock
def test_read_only_mode_blocks_mutating_tools() -> None:
    # Ensure network endpoint is NOT hit
    respx.post("https://api.petstore.example.com/v1/pets").mock(
        return_value=httpx.Response(201, json={"id": 101, "name": "Spot"})
    )

    registry = _get_sample_registry()

    step1 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_create",
                    function=FunctionCall(
                        name="create_pet", arguments='{"name": "Spot"}'
                    ),
                )
            ],
        ),
    )
    step2 = CompletionResponse(
        finish_reason="stop",
        message=ChatMessage(
            role="assistant", content="The pet creation was blocked."
        ),
    )

    provider = MockProvider([step1, step2])
    agent = SpecPilotAgent(registry=registry, provider=provider)

    resp = agent.run("Create pet Spot", read_only=True)

    assert resp.is_error is False
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].is_error is True
    assert "Blocked by read-only mode" in resp.tool_calls[0].result_summary


def test_human_approval_approved() -> None:
    registry = _get_sample_registry()

    step1 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_create",
                    function=FunctionCall(
                        name="create_pet", arguments='{"name": "Spot"}'
                    ),
                )
            ],
        ),
    )
    step2 = CompletionResponse(
        finish_reason="stop",
        message=ChatMessage(role="assistant", content="Pet created successfully."),
    )

    provider = MockProvider([step1, step2])

    with respx.mock:
        respx.post("https://api.petstore.example.com/v1/pets").mock(
            return_value=httpx.Response(201, json={"id": 101, "name": "Spot"})
        )

        agent = SpecPilotAgent(registry=registry, provider=provider)
        approved_calls: List[str] = []

        def mock_approval(method: str, path: str, args: Dict[str, Any]) -> bool:
            approved_calls.append(f"{method} {path}")
            return True

        resp = agent.run("Create pet Spot", approval_handler=mock_approval)

        assert resp.is_error is False
        assert len(approved_calls) == 1
        assert approved_calls[0] == "POST /pets"
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].status_code == 201


def test_human_approval_rejected() -> None:
    registry = _get_sample_registry()

    step1 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_create",
                    function=FunctionCall(
                        name="create_pet", arguments='{"name": "Spot"}'
                    ),
                )
            ],
        ),
    )
    step2 = CompletionResponse(
        finish_reason="stop",
        message=ChatMessage(role="assistant", content="Operation was rejected."),
    )

    provider = MockProvider([step1, step2])

    agent = SpecPilotAgent(registry=registry, provider=provider)

    def mock_approval(method: str, path: str, args: Dict[str, Any]) -> bool:
        return False

    resp = agent.run("Create pet Spot", approval_handler=mock_approval)

    assert resp.is_error is False
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].is_error is True
    assert "Rejected by user" in resp.tool_calls[0].result_summary


def test_shell_safety_command_toggle() -> None:
    engine = ShellEngine()
    assert engine.state.read_only is False

    engine.execute_command("/safety read-only")
    assert engine.state.read_only is True

    engine.execute_command("/safety interactive")
    assert engine.state.read_only is False
