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
    ToolCall,
)
from specpilot.mcp.registry import MCPToolRegistry
from specpilot.openapi.loader import SpecLoader
from specpilot.openapi.parser import OpenAPIParser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockMultiStepProvider(LLMProvider):
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
            message=ChatMessage(role="assistant", content="Workflow completed.")
        )


def _get_sample_registry() -> MCPToolRegistry:
    json_path = str(FIXTURES_DIR / "sample_3_0.json")
    spec = OpenAPIParser(SpecLoader().load(json_path)).parse()
    return MCPToolRegistry.from_spec(spec)


@respx.mock
def test_multi_step_api_workflow() -> None:
    # 1. Mock GET /pets -> returns pets list
    respx.get(url__startswith="https://api.petstore.example.com/v1/pets").mock(
        return_value=httpx.Response(
            200, json=[{"id": 42, "name": "Rover"}, {"id": 99, "name": "Felix"}]
        )
    )
    # 2. Mock GET /pets/42 -> returns pet details
    respx.get("https://api.petstore.example.com/v1/pets/42").mock(
        return_value=httpx.Response(
            200, json={"id": 42, "name": "Rover", "tag": "dog", "status": "available"}
        )
    )

    registry = _get_sample_registry()

    # Step 1 LLM response: Call list_pets
    step1 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_01",
                    function=FunctionCall(name="list_pets", arguments='{"limit": 5}'),
                )
            ],
        ),
    )
    # Step 2 LLM response: Inspect first pet by calling show_pet_by_id with pet_id="42"
    step2 = CompletionResponse(
        finish_reason="tool_calls",
        message=ChatMessage(
            role="assistant",
            tool_calls=[
                ToolCall(
                    id="call_02",
                    function=FunctionCall(
                        name="show_pet_by_id", arguments='{"petId": "42"}'
                    ),
                )
            ],
        ),
    )
    # Step 3 LLM response: Synthesize final answer
    step3 = CompletionResponse(
        finish_reason="stop",
        message=ChatMessage(
            role="assistant",
            content="Pet 42 is Rover, a dog currently available for adoption.",
        ),
    )

    provider = MockMultiStepProvider([step1, step2, step3])
    agent = SpecPilotAgent(registry=registry, provider=provider, max_steps=5)

    resp = agent.run("Find pet 42 and show its status")

    assert resp.is_error is False
    assert resp.steps == 3
    assert len(resp.tool_calls) == 2
    assert resp.tool_calls[0].tool_name == "list_pets"
    assert resp.tool_calls[1].tool_name == "show_pet_by_id"
    assert "Rover" in resp.content
