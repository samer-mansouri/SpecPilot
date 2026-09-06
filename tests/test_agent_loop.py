from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import pytest
import respx

from specpilot.agent import (
    ChatMessage,
    CompletionResponse,
    FunctionCall,
    LLMConfig,
    LLMProvider,
    SpecPilotAgent,
    ToolCall,
)
from specpilot.mcp.models import ExecutionResult
from specpilot.mcp.executor import ToolExecutor
from specpilot.mcp.registry import MCPToolRegistry
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.parser import OpenAPIParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockProvider(LLMProvider):
    """Mock LLM Provider that returns pre-configured sequential responses."""

    def __init__(self, responses: List[CompletionResponse]) -> None:
        self.responses = responses
        self.call_count = 0
        self.history: List[List[ChatMessage]] = []

    def complete(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> CompletionResponse:
        self.history.append(messages)
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return CompletionResponse(
            message=ChatMessage(role="assistant", content="Fallback response")
        )


def _get_sample_registry() -> MCPToolRegistry:
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    spec = OpenAPIParser(SpecLoader().load(json_path)).parse()
    return MCPToolRegistry.from_spec(spec)


@respx.mock
def test_agent_successful_tool_call_loop() -> None:
    # Mock HTTP endpoint for list_pets tool
    respx.get(url__startswith="https://api.petstore.example.com/v1/pets").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1, "name": "Fido"}, {"id": 2, "name": "Rover"}]
        )
    )

    registry = _get_sample_registry()

    # Provider step 1: Request tool call `list_pets` with arguments `{"limit": 2}`
    step1 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_001",
                    function=FunctionCall(name="list_pets", arguments='{"limit": 2}'),
                )
            ],
        ),
    )
    # Provider step 2: Return final synthesized text
    step2 = CompletionResponse(
        finish_reason="stop",
        message=ChatMessage(
            role="assistant", content="Found 2 pets: Fido and Rover."
        ),
    )

    provider = MockProvider([step1, step2])
    agent = SpecPilotAgent(registry=registry, provider=provider)

    resp = agent.run("Show me 2 pets")

    assert resp.is_error is False
    assert resp.steps == 2
    assert resp.content == "Found 2 pets: Fido and Rover."
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].tool_name == "list_pets"
    assert resp.tool_calls[0].arguments == {"limit": 2}
    assert resp.tool_calls[0].status_code == 200


def test_agent_max_steps_exceeded() -> None:
    registry = _get_sample_registry()

    # Provider constantly requests tool calls in an infinite loop
    loop_step = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_loop",
                    function=FunctionCall(name="list_pets", arguments="{}"),
                )
            ],
        ),
    )

    provider = MockProvider([loop_step] * 10)
    agent = SpecPilotAgent(registry=registry, provider=provider, max_steps=3)

    resp = agent.run("Loop forever")

    assert resp.is_error is True
    assert resp.steps == 3
    assert "maximum execution step limit" in resp.content
    assert resp.error_message == "Max steps exceeded"


def test_agent_unknown_tool_handling() -> None:
    registry = _get_sample_registry()

    step1 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_invalid",
                    function=FunctionCall(name="non_existent_tool", arguments="{}"),
                )
            ],
        ),
    )
    step2 = CompletionResponse(
        finish_reason="stop",
        message=ChatMessage(
            role="assistant", content="Sorry, I could not find that tool."
        ),
    )

    provider = MockProvider([step1, step2])
    agent = SpecPilotAgent(registry=registry, provider=provider)

    resp = agent.run("Run invalid tool")

    assert resp.is_error is False
    assert resp.steps == 2
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].is_error is True
    assert "not found" in resp.tool_calls[0].result_summary
