import os
import time
import pytest
import respx
from httpx import Response

from specpilot.auth.detector import AuthEndpointDetector
from specpilot.auth.extractor import TokenExtractor, ExtractedToken
from specpilot.auth.lifecycle import TokenLifecycleManager
from specpilot.auth.models import AuthType
from specpilot.mcp.executor import ToolExecutor
from specpilot.mcp.models import MCPTool
from specpilot.openapi.models import NormalizedSpec, Operation, RequestBody


def test_auth_endpoint_detector_login_and_refresh():
    login_op = Operation(
        operation_id="loginUser",
        method="POST",
        path="/api/auth/login",
        tags=["auth"],
    )
    refresh_op = Operation(
        operation_id="refreshToken",
        method="POST",
        path="/api/auth/refresh",
        tags=["auth"],
    )
    get_op = Operation(
        operation_id="getUser",
        method="GET",
        path="/api/users/1",
    )

    spec = NormalizedSpec(
        title="Test API",
        api_version="1.0.0",
        openapi_version="3.0.0",
        source="test",
        operations=[login_op, refresh_op, get_op],
    )

    logins = AuthEndpointDetector.detect_login_operations(spec)
    refreshes = AuthEndpointDetector.detect_refresh_operations(spec)

    assert len(logins) == 1
    assert logins[0].operation_id == "loginUser"
    assert len(refreshes) == 1
    assert refreshes[0].operation_id == "refreshToken"


def test_token_extractor_json_body():
    body = {
        "success": True,
        "data": {
            "accessToken": "eyJhbGciOiJIUzI1NiJ9.test_token.sig",
            "refreshToken": "refresh_xyz_123",
            "expiresIn": 3600,
        },
    }

    extracted = TokenExtractor.extract_from_response(body)
    assert extracted is not None
    assert extracted.token == "eyJhbGciOiJIUzI1NiJ9.test_token.sig"
    assert extracted.refresh_token == "refresh_xyz_123"
    assert extracted.expires_at is not None
    assert extracted.expires_at > time.time() + 3000


def test_token_extractor_headers():
    headers = {
        "Authorization": "Bearer header_token_999",
        "Set-Cookie": "session_id=cookie_val_123; Path=/; HttpOnly",
    }

    extracted = TokenExtractor.extract_from_response(response_body={}, headers=headers)
    assert extracted is not None
    assert extracted.token == "header_token_999"


def test_token_lifecycle_manager_register_and_expiry(tmp_path):
    dotenv_path = str(tmp_path / ".env")
    mgr = TokenLifecycleManager.get_instance()

    extracted = ExtractedToken(
        token="test_jwt_12345",
        token_type=AuthType.BEARER,
        refresh_token="test_refresh_123",
        expires_at=time.time() + 5.0,
    )

    mgr.register_token(
        extracted,
        tool_name="login",
        login_arguments={"username": "admin"},
        dotenv_path=dotenv_path,
    )

    assert mgr.active_token == "test_jwt_12345"
    assert os.getenv("SPECPILOT_BEARER_TOKEN") == "test_jwt_12345"
    assert mgr.can_auto_refresh() is True
    # Should be expired when buffer of 10s is applied
    assert mgr.is_expired(buffer_seconds=10.0) is True


@respx.mock
def test_tool_executor_auto_401_retry():
    # Mock login endpoint for background auto-relogin
    respx.post("https://api.example.com/api/auth/login").mock(
        return_value=Response(200, json={"accessToken": "new_fresh_token_123"})
    )

    # First call returns 401, second call after auth refresh returns 200
    route = respx.get("https://api.example.com/protected").mock(
        side_effect=[
            Response(401, json={"message": "Unauthorized"}),
            Response(200, json={"data": "success"}),
        ]
    )

    tool = MCPTool(
        name="get_protected",
        description="Get protected data",
        method="GET",
        path="/protected",
        base_url="https://api.example.com",
    )

    # Register stored login arguments in TokenLifecycleManager
    mgr = TokenLifecycleManager.get_instance()
    extracted = ExtractedToken(token="old_token", token_type=AuthType.BEARER)
    mgr.register_token(extracted, tool_name="login", login_arguments={"requestBody": {"username": "admin"}})

    executor = ToolExecutor()
    result = executor.execute(tool, arguments={})

    assert result.status_code == 200
    assert result.body == {"data": "success"}
    assert route.call_count == 2
