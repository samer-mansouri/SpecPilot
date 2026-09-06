import respx
from httpx import Response

from specpilot.safety.policy import OperationRisk, SafetyPolicy
from specpilot.testing.executor import ContractTestExecutor
from specpilot.testing.models import (
    TestExpectation,
    TestRequestData,
    TestScenario,
    TestStatus,
)


@respx.mock
def test_contract_test_executor_successful_get():
    respx.get("https://api.example.com/pets/1").mock(
        return_value=Response(200, json={"id": 1, "name": "Fido"}, headers={"content-type": "application/json"})
    )

    scenario = TestScenario(
        id="get_pet_valid",
        operation_id="get_pet",
        method="GET",
        path="/pets/{id}",
        category="deterministic",
        scenario_type="valid_request",
        description="Get pet by ID",
        request_data=TestRequestData(path_params={"id": 1}),
        expectation=TestExpectation(expected_status_codes=[200], expected_content_type="application/json"),
        risk_level=OperationRisk.READ_ONLY,
    )

    executor = ContractTestExecutor(base_url="https://api.example.com")
    report = executor.execute_suite([scenario])

    assert report.total_scenarios == 1
    assert report.passed_count == 1
    assert report.failed_count == 0
    assert report.results[0].status == TestStatus.PASSED
    assert report.results[0].actual_status_code == 200
    assert report.results[0].actual_body == {"id": 1, "name": "Fido"}


def test_contract_test_executor_read_only_skip_mutating():
    scenario = TestScenario(
        id="delete_pet_test",
        operation_id="delete_pet",
        method="DELETE",
        path="/pets/1",
        category="deterministic",
        scenario_type="valid_request",
        description="Delete pet",
        risk_level=OperationRisk.DESTRUCTIVE,
    )

    safety_policy = SafetyPolicy(read_only_mode=True)
    executor = ContractTestExecutor(base_url="https://api.example.com", safety_policy=safety_policy)
    report = executor.execute_suite([scenario])

    assert report.total_scenarios == 1
    assert report.skipped_count == 1
    assert report.results[0].status == TestStatus.SKIPPED
    assert "blocked by safety policy" in report.results[0].validation_errors[0].lower()
