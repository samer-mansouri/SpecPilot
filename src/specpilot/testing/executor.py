import datetime
import time
from typing import Any, Callable, Dict, List, Optional
import httpx

from specpilot.auth.models import AuthConfig
from specpilot.safety.policy import OperationRisk, SafetyPolicy
from specpilot.safety.redactor import SecretRedactor
from specpilot.testing.models import (
    FailureCategory,
    TestResult,
    TestRunReport,
    TestScenario,
    TestStatus,
)
from specpilot.testing.validator import ContractValidator


ApprovalHandler = Callable[[str, str, Dict[str, Any]], bool]


class ContractTestExecutor:
    """Executes API contract test scenarios against a target server."""

    def __init__(
        self,
        base_url: str,
        safety_policy: Optional[SafetyPolicy] = None,
        redactor: Optional[SecretRedactor] = None,
        validator: Optional[ContractValidator] = None,
        approval_handler: Optional[ApprovalHandler] = None,
        allow_mutating: bool = False,
        auth_config: Optional[AuthConfig] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.safety_policy = safety_policy or SafetyPolicy()
        self.redactor = redactor or SecretRedactor()
        self.validator = validator or ContractValidator()
        self.approval_handler = approval_handler
        self.allow_mutating = allow_mutating
        self.auth_config = auth_config


    def execute_suite(
        self,
        scenarios: List[TestScenario],
        api_title: str = "API Test Suite",
        api_version: str = "1.0.0",
    ) -> TestRunReport:
        """Execute a full suite of API contract scenarios and aggregate report."""
        start_time = time.perf_counter()
        results: List[TestResult] = []

        passed_count = 0
        failed_count = 0
        skipped_count = 0

        for scenario in scenarios:
            result = self.execute_scenario(scenario)
            results.append(result)

            if result.status == TestStatus.PASSED:
                passed_count += 1
            elif result.status == TestStatus.SKIPPED:
                skipped_count += 1
            else:
                failed_count += 1

        total_duration_ms = (time.perf_counter() - start_time) * 1000.0

        return TestRunReport(
            api_title=api_title,
            api_version=api_version,
            target_base_url=self.base_url,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            total_scenarios=len(scenarios),
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            duration_ms=round(total_duration_ms, 2),
            results=results,
        )

    def execute_scenario(self, scenario: TestScenario) -> TestResult:
        """Execute a single scenario with safety checks and response validation."""
        # 1. Check Safety Policy
        if not self.safety_policy.is_allowed(scenario.method):
            return TestResult(
                scenario=scenario,
                status=TestStatus.SKIPPED,
                failure_category=FailureCategory.NONE,
                validation_errors=["Skipped: Operation blocked by safety policy (read-only mode active)"],
            )

        # 2. Check Mutating Approval Requirements
        if self.safety_policy.requires_approval(scenario.method):
            if self.approval_handler is not None:
                # Request interactive approval
                combined_args = {
                    **scenario.request_data.path_params,
                    **scenario.request_data.query_params,
                }
                if scenario.request_data.body is not None:
                    combined_args["body"] = scenario.request_data.body

                approved = self.approval_handler(scenario.method, scenario.path, combined_args)
                if not approved:
                    return TestResult(
                        scenario=scenario,
                        status=TestStatus.SKIPPED,
                        failure_category=FailureCategory.NONE,
                        validation_errors=["Skipped: Operation approval denied by user"],
                    )
            elif not self.allow_mutating:
                return TestResult(
                    scenario=scenario,
                    status=TestStatus.SKIPPED,
                    failure_category=FailureCategory.NONE,
                    validation_errors=[
                        f"Skipped: Mutating/destructive operation ({scenario.method.upper()}) requires explicit confirmation or --allow-mutating flag"
                    ],
                )

        # 3. Build URL and Execute Request
        path_filled = scenario.path
        for k, v in scenario.request_data.path_params.items():
            path_filled = path_filled.replace(f"{{{k}}}", str(v))

        url = f"{self.base_url}{path_filled}"
        req_headers = dict(scenario.request_data.headers or {})
        req_query = dict(scenario.request_data.query_params or {})
        if self.auth_config:
            self.auth_config.apply(req_headers, req_query)

        step_start = time.perf_counter()
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.request(
                    method=scenario.method.upper(),
                    url=url,
                    params=req_query or None,
                    headers=req_headers or None,
                    json=scenario.request_data.body if scenario.request_data.body is not None else None,
                )
                duration_ms = round((time.perf_counter() - step_start) * 1000.0, 2)


                resp_body = None
                if response.content:
                    try:
                        resp_body = response.json()
                    except Exception:
                        resp_body = response.text

                raw_headers = dict(response.headers)
                safe_resp_headers = self.redactor.redact_headers(raw_headers)

                return self.validator.validate(
                    scenario=scenario,
                    status_code=response.status_code,
                    headers=safe_resp_headers,
                    body=resp_body,
                    duration_ms=duration_ms,
                )

        except (httpx.RequestError, httpx.TimeoutException) as err:
            duration_ms = round((time.perf_counter() - step_start) * 1000.0, 2)
            return TestResult(
                scenario=scenario,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                failure_category=FailureCategory.TRANSPORT_FAILURE,
                validation_errors=[f"Transport failure: {type(err).__name__} - {str(err)}"],
            )
        except Exception as err:
            duration_ms = round((time.perf_counter() - step_start) * 1000.0, 2)
            return TestResult(
                scenario=scenario,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                failure_category=FailureCategory.SETUP_FAILURE,
                validation_errors=[f"Execution setup failure: {type(err).__name__} - {str(err)}"],
            )
