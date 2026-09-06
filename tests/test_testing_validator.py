from specpilot.testing.models import (
    FailureCategory,
    TestExpectation,
    TestScenario,
    TestStatus,
)
from specpilot.testing.validator import ContractValidator


def test_contract_validator_success():
    expectation = TestExpectation(
        expected_status_codes=[200],
        expected_content_type="application/json",
        expected_schema={
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        },
    )
    scenario = TestScenario(
        id="valid_scenario",
        operation_id="get_item",
        method="GET",
        path="/items/1",
        category="deterministic",
        scenario_type="valid_request",
        description="Valid request",
        expectation=expectation,
    )

    validator = ContractValidator()
    result = validator.validate(
        scenario=scenario,
        status_code=200,
        headers={"content-type": "application/json; charset=utf-8"},
        body={"id": 1, "name": "Item A"},
        duration_ms=25.0,
    )

    assert result.status == TestStatus.PASSED
    assert result.failure_category == FailureCategory.NONE
    assert len(result.validation_errors) == 0


def test_contract_validator_status_and_schema_failures():
    expectation = TestExpectation(
        expected_status_codes=[200],
        expected_content_type="application/json",
        expected_schema={
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        },
    )
    scenario = TestScenario(
        id="invalid_scenario",
        operation_id="get_item",
        method="GET",
        path="/items/1",
        category="deterministic",
        scenario_type="valid_request",
        description="Valid request",
        expectation=expectation,
    )

    validator = ContractValidator()

    # Mismatch status code and schema (id is string instead of int, name missing)
    result = validator.validate(
        scenario=scenario,
        status_code=500,
        headers={"content-type": "application/json"},
        body={"id": "not_an_int"},
        duration_ms=30.0,
    )

    assert result.status == TestStatus.FAILED
    assert result.failure_category == FailureCategory.CONTRACT_MISMATCH
    assert len(result.validation_errors) >= 1
    assert "Status code mismatch" in result.validation_errors[0]
