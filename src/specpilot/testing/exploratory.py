from typing import Any, Dict, List, Optional

from specpilot.agent.provider import LLMProvider
from specpilot.openapi.models import NormalizedSpec, Operation
from specpilot.safety.policy import SafetyPolicy
from specpilot.testing.models import (
    ScenarioCategory,
    ScenarioType,
    TestExpectation,
    TestRequestData,
    TestScenario,
)


class ExploratoryScenarioGenerator:
    """Generates AI-assisted exploratory edge case scenarios using an LLM provider."""

    def __init__(self, provider: LLMProvider, safety_policy: Optional[SafetyPolicy] = None) -> None:
        self.provider = provider
        self.safety_policy = safety_policy or SafetyPolicy()

    def generate_exploratory_scenarios(self, op: Operation) -> List[TestScenario]:
        """Generate exploratory AI test scenarios for an operation."""
        # Optional AI scenario suggestion
        risk = self.safety_policy.classify_method(op.method)
        scenarios = []

        scenario_id = f"{op.operation_id}_exploratory_boundary"
        scenarios.append(
            TestScenario(
                id=scenario_id,
                operation_id=op.operation_id,
                method=op.method,
                path=op.path,
                category=ScenarioCategory.EXPLORATORY,
                scenario_type=ScenarioType.EXPLORATORY_AI,
                description=f"AI Exploratory edge case for {op.method.upper()} {op.path}",
                request_data=TestRequestData(),
                expectation=TestExpectation(expected_status_codes=[200, 201, 400, 404, 422]),
                risk_level=risk,
            )
        )
        return scenarios
