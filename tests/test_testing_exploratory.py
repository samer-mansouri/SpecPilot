from specpilot.agent.provider import ChatMessage, CompletionResponse
from specpilot.openapi.models import Operation
from specpilot.testing.exploratory import ExploratoryScenarioGenerator
from specpilot.testing.models import ScenarioCategory, ScenarioType


class MockLLMProvider:
    def complete(self, messages, tools=None):
        return CompletionResponse(message=ChatMessage(role="assistant", content="Suggested exploratory scenario"))


def test_exploratory_scenario_generator():
    provider = MockLLMProvider()
    generator = ExploratoryScenarioGenerator(provider=provider)
    op = Operation(
        operation_id="get_pet",
        method="GET",
        path="/pets/{id}",
    )

    scenarios = generator.generate_scenarios_for_spec(op) if hasattr(generator, 'generate_scenarios_for_spec') else generator.generate_exploratory_scenarios(op)
    assert len(scenarios) == 1
    assert scenarios[0].category == ScenarioCategory.EXPLORATORY
    assert scenarios[0].scenario_type == ScenarioType.EXPLORATORY_AI
