from specpilot.safety.policy import OperationRisk
from specpilot.testing.models import (
    FailureCategory,
    ScenarioCategory,
    ScenarioType,
    TestExpectation,
    TestRequestData,
    TestResult,
    TestRunReport,
    TestScenario,
    TestStatus,
)


def test_test_scenario_instantiation():
    expectation = TestExpectation(expected_status_codes=[200, 201])
    request_data = TestRequestData(query_params={"limit": 10})
    scenario = TestScenario(
        id="pet_list_valid",
        operation_id="list_pets",
        method="GET",
        path="/pets",
        category=ScenarioCategory.DETERMINISTIC,
        scenario_type=ScenarioType.VALID_REQUEST,
        description="Valid list_pets request",
        request_data=request_data,
        expectation=expectation,
        risk_level=OperationRisk.READ_ONLY,
    )

    assert scenario.id == "pet_list_valid"
    assert scenario.method == "GET"
    assert scenario.category == ScenarioCategory.DETERMINISTIC
    assert scenario.expectation.expected_status_codes == [200, 201]


def test_test_result_and_report_aggregation():
    scenario = TestScenario(
        id="pet_list_valid",
        operation_id="list_pets",
        method="GET",
        path="/pets",
        category=ScenarioCategory.DETERMINISTIC,
        scenario_type=ScenarioType.VALID_REQUEST,
        description="Valid request",
    )
    result = TestResult(
        scenario=scenario,
        status=TestStatus.PASSED,
        actual_status_code=200,
        duration_ms=45.2,
    )
    report = TestRunReport(
        api_title="Petstore",
        api_version="1.0.0",
        target_base_url="https://api.petstore.com",
        timestamp="2026-09-06T18:00:00Z",
        total_scenarios=1,
        passed_count=1,
        failed_count=0,
        skipped_count=0,
        duration_ms=45.2,
        results=[result],
    )

    assert report.total_scenarios == 1
    assert report.passed_count == 1
    assert report.results[0].status == TestStatus.PASSED
    assert report.results[0].failure_category == FailureCategory.NONE
