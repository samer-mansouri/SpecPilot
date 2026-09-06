from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from specpilot.safety.policy import OperationRisk


class ScenarioCategory(str, Enum):
    """Broad category for API test scenarios."""

    DETERMINISTIC = "deterministic"
    EXPLORATORY = "exploratory"


class ScenarioType(str, Enum):
    """Specific scenario classification."""

    VALID_REQUEST = "valid_request"
    MISSING_REQUIRED_PARAM = "missing_required_param"
    MISSING_REQUIRED_BODY_FIELD = "missing_required_body_field"
    INVALID_TYPE = "invalid_type"
    INVALID_ENUM_VALUE = "invalid_enum_value"
    MISSING_AUTH = "missing_auth"
    EXPLORATORY_AI = "exploratory_ai"


class TestStatus(str, Enum):
    """Status of an executed test scenario."""

    __test__ = False
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class FailureCategory(str, Enum):
    """Categorization of failure cause."""

    NONE = "none"
    CONTRACT_MISMATCH = "contract_mismatch"
    EXPLORATORY_WARNING = "exploratory_warning"
    TRANSPORT_FAILURE = "transport_failure"
    SETUP_FAILURE = "setup_failure"


class TestExpectation(BaseModel):
    """Expected response behavior for an API contract scenario."""

    __test__ = False
    expected_status_codes: List[int] = Field(default_factory=list)
    expected_content_type: Optional[str] = None
    expected_schema: Optional[Dict[str, Any]] = None


class TestRequestData(BaseModel):
    """Request data parameters for executing a test scenario."""

    __test__ = False
    path_params: Dict[str, Any] = Field(default_factory=dict)
    query_params: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = None


class TestScenario(BaseModel):
    """Definition of a single API test scenario."""

    __test__ = False
    id: str
    operation_id: str
    method: str
    path: str
    category: ScenarioCategory
    scenario_type: ScenarioType
    description: str
    request_data: TestRequestData = Field(default_factory=TestRequestData)
    expectation: TestExpectation = Field(default_factory=TestExpectation)
    risk_level: OperationRisk = OperationRisk.READ_ONLY


class TestResult(BaseModel):
    """Execution result and validation output for a test scenario."""

    __test__ = False
    scenario: TestScenario
    status: TestStatus
    actual_status_code: Optional[int] = None
    actual_headers: Dict[str, str] = Field(default_factory=dict)
    actual_body: Optional[Any] = None
    duration_ms: float = 0.0
    failure_category: FailureCategory = FailureCategory.NONE
    validation_errors: List[str] = Field(default_factory=list)


class TestRunReport(BaseModel):
    """Aggregate report for a complete contract test run."""

    __test__ = False
    api_title: str
    api_version: str
    target_base_url: str
    timestamp: str
    total_scenarios: int = 0
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    duration_ms: float = 0.0
    results: List[TestResult] = Field(default_factory=list)
