import pytest
from unittest.mock import MagicMock

from specpilot.agent.agent import AgentResponse, SpecPilotAgent
from specpilot.agent.provider import ChatMessage, LLMProvider
from specpilot.cli_shell.engine import ShellEngine
from specpilot.cli_shell.state import SessionState
from specpilot.mcp.models import MCPTool
from specpilot.mcp.registry import MCPToolRegistry


class MockLLM:
    def invoke(self, messages):
        return ChatMessage(role="assistant", content="1. Planned Tool: get_pet\n2. Arguments: petId=42\n3. Reasoning: Retrieve pet details")



class MockProvider(LLMProvider):
    def get_llm(self):
        return MockLLM()

    def complete(self, messages, tools=None):
        from specpilot.agent.provider import CompletionResponse
        return CompletionResponse(
            message=ChatMessage(role="assistant", content="1. Planned Tool: get_pet\n2. Arguments: petId=42\n3. Reasoning: Retrieve pet details")
        )



def test_agent_generate_plan():
    registry = MCPToolRegistry()
    registry.register_tool(
        MCPTool(name="get_pet", description="Get pet by ID", method="GET", path="/pet/{petId}")
    )
    provider = MockProvider()
    agent = SpecPilotAgent(registry=registry, provider=provider)

    response = agent.generate_plan("Retrieve pet #42")
    assert isinstance(response, AgentResponse)
    assert not response.is_error
    assert "Planned Tool: get_pet" in response.content


def test_shell_engine_handle_plan_without_spec(capsys):
    state = SessionState()
    engine = ShellEngine(state=state)

    engine.execute_command("/plan Find pet")
    # Should warn that no spec is loaded
    assert state.spec is None
