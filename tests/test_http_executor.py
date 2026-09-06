import pytest
import respx
from httpx import Response, TimeoutException

from specpilot.mcp import MCPTool, ToolExecutionError, ToolExecutor
from specpilot.openapi.models import Operation, Parameter


@respx.mock
def test_execute_get_with_path_and_query() -> None:
    op = Operation(
        operation_id="showPetById",
        method="GET",
        path="/pets/{petId}",
        parameters=[
            Parameter(name="petId", in_location="path", required=True),
            Parameter(name="verbose", in_location="query", required=False),
        ],
    )
    tool = MCPTool(
        name="show_pet_by_id",
        description="Show pet info",
        method="GET",
        path="/pets/{petId}",
        base_url="https://api.petstore.com/v1",
        original_operation=op,
    )

    respx.get("https://api.petstore.com/v1/pets/42?verbose=true").mock(
        return_value=Response(
            200,
            json={"id": 42, "name": "Fido"},
            headers={"Content-Type": "application/json", "Authorization": "Bearer secret_token"},
        )
    )

    executor = ToolExecutor()
    result = executor.execute(tool, {"petId": "42", "verbose": "true"})

    assert result.status_code == 200
    assert result.is_error is False
    assert result.body == {"id": 42, "name": "Fido"}
    assert result.headers.get("authorization") == "[REDACTED]"


@respx.mock
def test_execute_post_with_body() -> None:
    tool = MCPTool(
        name="create_pet",
        description="Create pet",
        method="POST",
        path="/pets",
        base_url="https://api.petstore.com/v1",
    )

    respx.post("https://api.petstore.com/v1/pets").mock(
        return_value=Response(201, json={"id": 100, "status": "created"})
    )

    executor = ToolExecutor()
    result = executor.execute(tool, {"requestBody": {"name": "Buddy"}})

    assert result.status_code == 201
    assert result.is_error is False
    assert result.body["id"] == 100


@respx.mock
def test_execute_http_error_500() -> None:
    tool = MCPTool(
        name="get_error",
        description="Error endpoint",
        method="GET",
        path="/fail",
        base_url="https://api.example.com",
    )

    respx.get("https://api.example.com/fail").mock(
        return_value=Response(500, json={"error": "Internal Server Error"})
    )

    executor = ToolExecutor()
    result = executor.execute(tool, {})

    assert result.status_code == 500
    assert result.is_error is True
    assert "HTTP 500" in (result.error_message or "")


@respx.mock
def test_execute_timeout() -> None:
    tool = MCPTool(
        name="timeout_tool",
        description="Slow endpoint",
        method="GET",
        path="/slow",
        base_url="https://api.example.com",
    )

    respx.get("https://api.example.com/slow").side_effect = TimeoutException("Timed out")

    executor = ToolExecutor()
    result = executor.execute(tool, {}, timeout=1.0)

    assert result.status_code == 408
    assert result.is_error is True
    assert "timed out" in (result.error_message or "")


def test_execute_missing_base_url() -> None:
    tool = MCPTool(
        name="no_url_tool",
        description="Missing URL",
        method="GET",
        path="/pets",
    )

    executor = ToolExecutor()
    with pytest.raises(ToolExecutionError, match="No base URL specified"):
        executor.execute(tool, {})
