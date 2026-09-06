from specpilot.openapi.models import NormalizedSpec, Operation, Parameter, RequestBody, Response
from specpilot.testing.generator import ScenarioGenerator
from specpilot.testing.models import ScenarioCategory, ScenarioType


def test_scenario_generator_basic_operation():
    op = Operation(
        operation_id="get_pet_by_id",
        method="GET",
        path="/pets/{pet_id}",
        tags=["pets"],
        summary="Find pet by ID",
        parameters=[
            Parameter(
                name="pet_id",
                in_location="path",
                required=True,
                schema_def={"type": "integer"},
            ),
            Parameter(
                name="status",
                in_location="query",
                required=False,
                schema_def={"type": "string", "enum": ["available", "pending", "sold"]},
            ),
        ],
        responses=[Response(status_code="200", description="Successful response")],
    )

    spec = NormalizedSpec(
        title="Test API",
        api_version="1.0.0",
        openapi_version="3.0.0",
        source="./test.yaml",
        operations=[op],
    )

    generator = ScenarioGenerator()
    scenarios = generator.generate_scenarios_for_spec(spec)

    assert len(scenarios) >= 3
    valid_scenarios = [s for s in scenarios if s.scenario_type == ScenarioType.VALID_REQUEST]
    missing_param_scenarios = [s for s in scenarios if s.scenario_type == ScenarioType.MISSING_REQUIRED_PARAM]
    invalid_enum_scenarios = [s for s in scenarios if s.scenario_type == ScenarioType.INVALID_ENUM_VALUE]

    assert len(valid_scenarios) == 1
    assert valid_scenarios[0].request_data.path_params["pet_id"] == 1
    assert valid_scenarios[0].expectation.expected_status_codes == [200]

    assert len(missing_param_scenarios) == 1
    assert missing_param_scenarios[0].id == "get_pet_by_id_missing_param_pet_id"

    assert len(invalid_enum_scenarios) == 1
    assert invalid_enum_scenarios[0].id == "get_pet_by_id_invalid_enum_status"


def test_scenario_generator_request_body():
    op = Operation(
        operation_id="add_pet",
        method="POST",
        path="/pets",
        tags=["pets"],
        request_body=RequestBody(
            required=True,
            content_types={
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["name", "category"],
                        "properties": {
                            "name": {"type": "string"},
                            "category": {"type": "string"},
                            "tag": {"type": "string"},
                        },
                    }
                }
            },
        ),
        responses=[Response(status_code="201", description="Created")],
    )

    spec = NormalizedSpec(
        title="Pet API",
        api_version="1.0.0",
        openapi_version="3.0.0",
        source="./pet.yaml",
        operations=[op],
    )

    generator = ScenarioGenerator()
    scenarios = generator.generate_scenarios_for_spec(spec)

    missing_body_field = [s for s in scenarios if s.scenario_type == ScenarioType.MISSING_REQUIRED_BODY_FIELD]
    assert len(missing_body_field) == 2
    field_names = [s.id for s in missing_body_field]
    assert "add_pet_missing_body_field_name" in field_names
    assert "add_pet_missing_body_field_category" in field_names
