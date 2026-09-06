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
    SpecPilotGraph,
    ToolCall,
)
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
            message=ChatMessage(role="assistant", content="Fallback text")
        )


def _get_sample_registry() -> MCPToolRegistry:
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    spec = OpenAPIParser(SpecLoader().load(json_path)).parse()
    return MCPToolRegistry.from_spec(spec)


@respx.mock
def test_langgraph_single_step_execution() -> None:
    respx.get(url__startswith="https://api.petstore.example.com/v1/pets").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "Fido"}])
    )

    registry = _get_sample_registry()

    step1 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_g1",
                    function=FunctionCall(name="list_pets", arguments='{"limit": 1}'),
                )
            ],
        ),
    )
    step2 = CompletionResponse(
        finish_reason="stop",
        message=ChatMessage(role="assistant", content="Found 1 pet: Fido."),
    )

    provider = MockProvider([step1, step2])
    graph = SpecPilotGraph(registry=registry, provider=provider)

    res = graph.run("Show 1 pet")

    assert res.get("final_content") == "Found 1 pet: Fido."
    assert res.get("steps") == 2
    assert len(res.get("tool_calls_executed", [])) == 1
