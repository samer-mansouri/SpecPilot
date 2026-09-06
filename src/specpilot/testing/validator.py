from typing import Any, Dict, List, Optional
import jsonschema

from specpilot.testing.models import (
    FailureCategory,
    TestExpectation,
    TestResult,
    TestScenario,
    TestStatus,
)


class ContractValidator:
    """Validates actual HTTP responses against documented OpenAPI contract expectations."""

    def validate(
        self,
        scenario: TestScenario,
        status_code: int,
        headers: Dict[str, str],
        body: Optional[Any],
        duration_ms: float = 0.0,
    ) -> TestResult:
        """Validate response status code, content type, and schema compatibility."""
        errors: List[str] = []
        expectation: TestExpectation = scenario.expectation

        # 1. Status Code Validation
        if expectation.expected_status_codes and status_code not in expectation.expected_status_codes:
            expected_str = ", ".join(str(c) for c in expectation.expected_status_codes)
            errors.append(f"Status code mismatch: expected [{expected_str}], got {status_code}")

        # 2. Content Type Validation (if expected_content_type specified and response status is 2xx)
        if 200 <= status_code < 300 and expectation.expected_content_type:
            content_type_header = ""
            for k, v in headers.items():
                if k.lower() == "content-type":
                    content_type_header = v
                    break

            if expectation.expected_content_type.lower() not in content_type_header.lower():
                errors.append(
                    f"Content-Type mismatch: expected '{expectation.expected_content_type}', got '{content_type_header}'"
                )

        # 3. JSON Schema Validation
        if 200 <= status_code < 300 and expectation.expected_schema and body is not None:
            try:
                jsonschema.validate(instance=body, schema=expectation.expected_schema)
            except jsonschema.ValidationError as err:
                errors.append(f"Response schema validation failed: {err.message}")
            except jsonschema.SchemaError as err:
                errors.append(f"Invalid OpenAPI JSON Schema definition: {err.message}")

        status = TestStatus.PASSED if not errors else TestStatus.FAILED
        failure_cat = FailureCategory.NONE if not errors else FailureCategory.CONTRACT_MISMATCH

        return TestResult(
            scenario=scenario,
            status=status,
            actual_status_code=status_code,
            actual_headers=headers,
            actual_body=body,
            duration_ms=duration_ms,
            failure_category=failure_cat,
            validation_errors=errors,
        )
