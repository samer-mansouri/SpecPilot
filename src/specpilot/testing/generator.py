import uuid
from typing import Any, Dict, List, Optional

from specpilot.openapi.models import NormalizedSpec, Operation, Parameter
from specpilot.safety.policy import SafetyPolicy
from specpilot.testing.models import (
    ScenarioCategory,
    ScenarioType,
    TestExpectation,
    TestRequestData,
    TestScenario,
)


class ScenarioGenerator:
    """Generates deterministic API contract test scenarios from OpenAPI specifications."""

    def __init__(self, safety_policy: Optional[SafetyPolicy] = None) -> None:
        self.safety_policy = safety_policy or SafetyPolicy()

    def generate_scenarios_for_spec(self, spec: NormalizedSpec, tag_filter: Optional[str] = None) -> List[TestScenario]:
        """Generate test scenarios for all (or tag-filtered) operations in a spec."""
        scenarios: List[TestScenario] = []
        for op in spec.operations:
            if tag_filter and tag_filter.lower() not in [t.lower() for t in op.tags]:
                continue
            scenarios.extend(self.generate_scenarios_for_operation(op))
        return scenarios

    def generate_scenarios_for_operation(self, op: Operation) -> List[TestScenario]:
        """Generate deterministic contract test scenarios for a single operation."""
        scenarios: List[TestScenario] = []
        risk_level = self.safety_policy.classify_method(op.method)

        # Extract documented success & error status codes
        success_codes = self._get_success_status_codes(op)
        error_codes = [400, 404, 422]

        # 1. Valid Request Scenario
        valid_request_data = self._build_valid_request_data(op)
        valid_scenario = TestScenario(
            id=f"{op.operation_id}_valid",
            operation_id=op.operation_id,
            method=op.method,
            path=op.path,
            category=ScenarioCategory.DETERMINISTIC,
            scenario_type=ScenarioType.VALID_REQUEST,
            description=f"Valid request for {op.method.upper()} {op.path}",
            request_data=valid_request_data,
            expectation=TestExpectation(
                expected_status_codes=success_codes,
                expected_content_type="application/json",
            ),
            risk_level=risk_level,
        )
        scenarios.append(valid_scenario)

        # 2. Missing Required Parameter Scenarios
        for param in op.parameters:
            if param.required:
                missing_data = self._build_valid_request_data(op)
                loc = param.in_location.lower()
                if loc == "path" and param.name in missing_data.path_params:
                    # Keep path parameter present for routing, but make invalid/empty
                    missing_data.path_params[param.name] = ""
                elif loc == "query":
                    missing_data.query_params.pop(param.name, None)
                elif loc == "header":
                    missing_data.headers.pop(param.name, None)

                scenarios.append(
                    TestScenario(
                        id=f"{op.operation_id}_missing_param_{param.name}",
                        operation_id=op.operation_id,
                        method=op.method,
                        path=op.path,
                        category=ScenarioCategory.DETERMINISTIC,
                        scenario_type=ScenarioType.MISSING_REQUIRED_PARAM,
                        description=f"Missing required parameter '{param.name}' in {loc}",
                        request_data=missing_data,
                        expectation=TestExpectation(expected_status_codes=error_codes),
                        risk_level=risk_level,
                    )
                )

        # 3. Missing Required Body Field Scenarios
        body_schema = self._extract_json_body_schema(op)
        if body_schema and isinstance(body_schema, dict):
            required_fields = body_schema.get("required", [])
            if isinstance(required_fields, list):
                for field_name in required_fields:
                    if isinstance(valid_request_data.body, dict) and field_name in valid_request_data.body:
                        missing_body_data = self._build_valid_request_data(op)
                        if isinstance(missing_body_data.body, dict):
                            missing_body_data.body = dict(missing_body_data.body)
                            missing_body_data.body.pop(field_name, None)

                        scenarios.append(
                            TestScenario(
                                id=f"{op.operation_id}_missing_body_field_{field_name}",
                                operation_id=op.operation_id,
                                method=op.method,
                                path=op.path,
                                category=ScenarioCategory.DETERMINISTIC,
                                scenario_type=ScenarioType.MISSING_REQUIRED_BODY_FIELD,
                                description=f"Missing required JSON body field '{field_name}'",
                                request_data=missing_body_data,
                                expectation=TestExpectation(expected_status_codes=[400, 422]),
                                risk_level=risk_level,
                            )
                        )

        # 4. Invalid Enum Value Scenarios
        for param in op.parameters:
            schema = param.schema_def or {}
            enum_vals = schema.get("enum")
            if enum_vals and isinstance(enum_vals, list):
                invalid_enum_data = self._build_valid_request_data(op)
                invalid_val = "INVALID_ENUM_VAL_X99"
                loc = param.in_location.lower()
                if loc == "path":
                    invalid_enum_data.path_params[param.name] = invalid_val
                elif loc == "query":
                    invalid_enum_data.query_params[param.name] = invalid_val
                elif loc == "header":
                    invalid_enum_data.headers[param.name] = invalid_val

                scenarios.append(
                    TestScenario(
                        id=f"{op.operation_id}_invalid_enum_{param.name}",
                        operation_id=op.operation_id,
                        method=op.method,
                        path=op.path,
                        category=ScenarioCategory.DETERMINISTIC,
                        scenario_type=ScenarioType.INVALID_ENUM_VALUE,
                        description=f"Invalid enum value for parameter '{param.name}'",
                        request_data=invalid_enum_data,
                        expectation=TestExpectation(expected_status_codes=[400, 422]),
                        risk_level=risk_level,
                    )
                )

        # 5. Missing Auth Scenario
        if op.security:
            no_auth_data = self._build_valid_request_data(op)
            no_auth_data.headers = {
                k: v for k, v in no_auth_data.headers.items()
                if k.lower() not in ("authorization", "api-key", "x-api-key")
            }
            scenarios.append(
                TestScenario(
                    id=f"{op.operation_id}_missing_auth",
                    operation_id=op.operation_id,
                    method=op.method,
                    path=op.path,
                    category=ScenarioCategory.DETERMINISTIC,
                    scenario_type=ScenarioType.MISSING_AUTH,
                    description=f"Missing authentication header for protected endpoint",
                    request_data=no_auth_data,
                    expectation=TestExpectation(expected_status_codes=[401, 403]),
                    risk_level=risk_level,
                )
            )

        return scenarios

    def _get_success_status_codes(self, op: Operation) -> List[int]:
        codes = []
        for r in op.responses:
            try:
                code = int(r.status_code)
                if 200 <= code < 300:
                    codes.append(code)
            except ValueError:
                pass
        return codes if codes else [200, 201, 202, 204]

    def _build_valid_request_data(self, op: Operation) -> TestRequestData:
        path_params: Dict[str, Any] = {}
        query_params: Dict[str, Any] = {}
        headers: Dict[str, str] = {}

        for param in op.parameters:
            val = self._generate_sample_value(param.schema_def or {}, param.name)
            loc = param.in_location.lower()
            if loc == "path":
                path_params[param.name] = val
            elif loc == "query":
                query_params[param.name] = val
            elif loc == "header":
                headers[param.name] = str(val)

        body = None
        body_schema = self._extract_json_body_schema(op)
        if body_schema:
            body = self._generate_sample_body_from_schema(body_schema)

        return TestRequestData(
            path_params=path_params,
            query_params=query_params,
            headers=headers,
            body=body,
        )

    def _extract_json_body_schema(self, op: Operation) -> Optional[Dict[str, Any]]:
        if not op.request_body or not op.request_body.content_types:
            return None

        for content_type, media_obj in op.request_body.content_types.items():
            if "json" in content_type.lower() and isinstance(media_obj, dict):
                return media_obj.get("schema")
        return None

    def _generate_sample_value(self, schema_def: Dict[str, Any], name: str = "") -> Any:
        if "default" in schema_def:
            return schema_def["default"]

        enum_vals = schema_def.get("enum")
        if enum_vals and isinstance(enum_vals, list) and len(enum_vals) > 0:
            return enum_vals[0]

        val_type = schema_def.get("type", "string")
        val_format = schema_def.get("format", "")

        if val_type == "integer":
            return 1
        elif val_type == "number":
            return 1.5
        elif val_type == "boolean":
            return True
        elif val_type == "array":
            items_schema = schema_def.get("items", {})
            return [self._generate_sample_value(items_schema, name)]
        elif val_type == "object":
            props = schema_def.get("properties", {})
            return {k: self._generate_sample_value(v, k) for k, v in props.items()}

        # String fallbacks
        if val_format == "uuid":
            return str(uuid.uuid4())
        elif val_format in ("date", "date-time"):
            return "2026-01-01T00:00:00Z"
        elif val_format == "email":
            return "user@example.com"

        if "id" in name.lower():
            return "1"
        return "sample_value"

    def _generate_sample_body_from_schema(self, schema: Dict[str, Any]) -> Any:
        if not isinstance(schema, dict):
            return {}

        schema_type = schema.get("type", "object")
        if schema_type == "object":
            props = schema.get("properties", {})
            obj: Dict[str, Any] = {}
            if isinstance(props, dict):
                for prop_name, prop_schema in props.items():
                    if isinstance(prop_schema, dict):
                        obj[prop_name] = self._generate_sample_value(prop_schema, prop_name)
            return obj
        elif schema_type == "array":
            items_schema = schema.get("items", {})
            if isinstance(items_schema, dict):
                return [self._generate_sample_body_from_schema(items_schema)]
            return []
        return self._generate_sample_value(schema)
