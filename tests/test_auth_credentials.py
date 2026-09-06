import os
import pytest
import respx
from httpx import Response

from specpilot.auth.models import APIKeyLocation, AuthConfig, AuthType
from specpilot.auth.manager import AuthManager
from specpilot.mcp.executor import ToolExecutor
from specpilot.mcp.models import MCPTool
from specpilot.safety.redactor import SecretRedactor
from specpilot.testing.executor import ContractTestExecutor
from specpilot.testing.models import (
    ScenarioCategory,
    ScenarioType,
    TestExpectation,
    TestRequestData,
    TestScenario,
    TestStatus,
)


def test_auth_config_bearer_apply():
    config = AuthConfig(auth_type=AuthType.BEARER, bearer_token="secret_token_123")
    headers = {}
    query_params = {}
    config.apply(headers, query_params)

    assert headers.get("Authorization") == "Bearer secret_token_123"
    assert query_params == {}
    assert config.redacted_dict()["bearer_token"] == "[REDACTED]"


def test_auth_config_api_key_header_apply():
    config = AuthConfig(
        auth_type=AuthType.API_KEY,
        api_key="key_abc123",
        api_key_name="X-Custom-Key",
        api_key_in=APIKeyLocation.HEADER,
    )
    headers = {}
    query_params = {}
    config.apply(headers, query_params)

    assert headers.get("X-Custom-Key") == "key_abc123"
    assert query_params == {}
    assert config.redacted_dict()["api_key"] == "[REDACTED]"


def test_auth_config_api_key_query_apply():
    config = AuthConfig(
        auth_type=AuthType.API_KEY,
        api_key="key_abc123",
        api_key_name="api_key",
        api_key_in=APIKeyLocation.QUERY,
    )
    headers = {}
    query_params = {}
    config.apply(headers, query_params)

    assert headers == {}
    assert query_params.get("api_key") == "key_abc123"


def test_auth_config_basic_apply():
    config = AuthConfig(
        auth_type=AuthType.BASIC,
        basic_username="admin",
        basic_password="password123",
    )
    headers = {}
    query_params = {}
    config.apply(headers, query_params)

    assert headers.get("Authorization") == "Basic YWRtaW46cGFzc3dvcmQxMjM="
    assert config.redacted_dict()["basic_password"] == "[REDACTED]"


def test_auth_manager_environment_resolution(monkeypatch):
    monkeypatch.setenv("SPECPILOT_BEARER_TOKEN", "env_bearer_token")
    auth_config = AuthManager.resolve()
    assert auth_config.auth_type == AuthType.BEARER
    assert auth_config.bearer_token == "env_bearer_token"


def test_auth_manager_cli_override(monkeypatch):
    monkeypatch.setenv("SPECPILOT_BEARER_TOKEN", "env_bearer_token")
    auth_config = AuthManager.resolve(cli_api_key="cli_key_value")
    assert auth_config.auth_type == AuthType.API_KEY
    assert auth_config.api_key == "cli_key_value"


def test_secret_redactor_header_and_text():
    raw_headers = {
        "Authorization": "Bearer my_super_secret_token",
        "X-API-Key": "secret_key_999",
        "Content-Type": "application/json",
    }
    redacted_headers = SecretRedactor.redact_headers(raw_headers)
    assert redacted_headers["Authorization"] == "[REDACTED]"
    assert redacted_headers["X-API-Key"] == "[REDACTED]"
    assert redacted_headers["Content-Type"] == "application/json"

    raw_text = '{"token": "secret_val_123", "user": "alice"}'
    redacted_text = SecretRedactor.redact(raw_text)
    assert "secret_val_123" not in redacted_text
    assert "[REDACTED]" in redacted_text


@respx.mock
def test_tool_executor_with_auth():
    route = respx.get("https://api.example.com/secure-data?param=val").mock(
        return_value=Response(200, json={"status": "authenticated"})
    )

    tool = MCPTool(
        name="get_secure_data",
        description="Get secure data",
        method="GET",
        path="/secure-data",
        base_url="https://api.example.com",
    )

    auth = AuthConfig(auth_type=AuthType.BEARER, bearer_token="bearer_xyz")
    executor = ToolExecutor(auth_config=auth)
    result = executor.execute(tool, arguments={"param": "val"})

    assert result.status_code == 200
    assert result.body == {"status": "authenticated"}
    assert route.called
    assert route.calls.last.request.headers["authorization"] == "Bearer bearer_xyz"


@respx.mock
def test_contract_test_executor_with_auth():
    route = respx.get("https://api.example.com/users").mock(
        return_value=Response(200, json=[{"id": 1}])
    )

    auth = AuthConfig(auth_type=AuthType.API_KEY, api_key="test_api_key", api_key_name="X-API-Key")
    executor = ContractTestExecutor(base_url="https://api.example.com", auth_config=auth)

    scenario = TestScenario(
        id="scenario-1",
        operation_id="getUsers",
        title="Get users",
        method="GET",
        path="/users",
        category=ScenarioCategory.DETERMINISTIC,
        scenario_type=ScenarioType.VALID_REQUEST,
        description="Fetch users",
        request_data=TestRequestData(),
        expectation=TestExpectation(expected_status_codes=[200]),
    )

    result = executor.execute_scenario(scenario)
    assert result.status == TestStatus.PASSED
    assert route.called
    assert route.calls.last.request.headers["x-api-key"] == "test_api_key"
