import time
from typing import Any, Dict, Optional, Union
import urllib.parse

import httpx

from specpilot.auth.models import AuthConfig
from specpilot.mcp.models import ExecutionResult, MCPTool
from specpilot.openapi.errors import SpecPilotError
from specpilot.tracing import get_tracer


class ToolExecutionError(SpecPilotError):
    """Raised when executing an HTTP tool request fails."""
    pass


class ToolExecutor:
    """Executes HTTP requests for generated MCP tools against target APIs."""

    SENSITIVE_HEADERS = {"authorization", "api-key", "x-api-key", "bearer", "token", "secret"}

    def __init__(
        self,
        default_timeout: float = 10.0,
        auth_config: Optional[AuthConfig] = None,
    ) -> None:
        self.default_timeout = default_timeout
        self.auth_config = auth_config

    def execute(
        self,
        tool: MCPTool,
        arguments: Dict[str, Any],
        base_url_override: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        auth_config: Optional[AuthConfig] = None,
    ) -> ExecutionResult:
        """Execute a tool with provided arguments."""
        base_url = base_url_override or tool.base_url
        if not base_url:
            raise ToolExecutionError(
                f"Cannot execute tool '{tool.name}': No base URL specified in tool definition or override."
            )

        # 1. Substitute path parameters
        url_path = tool.path
        query_params: Dict[str, Any] = {}
        headers: Dict[str, str] = {}
        if extra_headers:
            headers.update(extra_headers)

        # Apply authentication if configured
        eff_auth = auth_config or self.auth_config
        if eff_auth:
            eff_auth.apply(headers, query_params)

        body_data: Any = None

        if tool.original_operation:
            param_locations = {p.name: p.in_location for p in tool.original_operation.parameters}
        else:
            param_locations = {}

        for key, val in arguments.items():
            if key == "requestBody":
                body_data = val
                continue

            loc = param_locations.get(key)
            if loc == "path" or (loc is None and f"{{{key}}}" in url_path):
                url_path = url_path.replace(f"{{{key}}}", urllib.parse.quote(str(val), safe=""))
            elif loc == "header":
                headers[key] = str(val)
            else:
                # Default query parameter
                query_params[key] = val

        target_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", url_path.lstrip("/"))
        req_timeout = timeout if timeout is not None else self.default_timeout

        start_time = time.perf_counter()
        try:
            client = httpx.Client(timeout=req_timeout, follow_redirects=True)
            response = client.request(
                method=tool.method.upper(),
                url=target_url,
                params=query_params if query_params else None,
                headers=headers if headers else None,
                json=body_data if body_data is not None else None,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Redact sensitive response headers
            clean_headers = self._redact_headers(dict(response.headers))

            # Parse JSON body if available
            parsed_body: Any = response.text
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    parsed_body = response.json()
                except Exception:
                    parsed_body = response.text

            is_error = response.is_error
            error_msg = f"HTTP {response.status_code}: {response.reason_phrase}" if is_error else None

            res = ExecutionResult(
                status_code=response.status_code,
                headers=clean_headers,
                body=parsed_body,
                is_error=is_error,
                error_message=error_msg,
                duration_ms=round(duration_ms, 2),
            )
            get_tracer().trace("mcp_tool_call", {
                "tool_name": tool.name,
                "method": tool.method,
                "target_url": target_url,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "is_error": is_error,
            })
            return res


        except httpx.TimeoutException as err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                status_code=408,
                is_error=True,
                error_message=f"HTTP request to '{target_url}' timed out after {req_timeout}s.",
                duration_ms=round(duration_ms, 2),
            )
        except httpx.RequestError as err:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                status_code=500,
                is_error=True,
                error_message=f"HTTP request error: {err}",
                duration_ms=round(duration_ms, 2),
            )

    def _redact_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        redacted: Dict[str, str] = {}
        for k, v in headers.items():
            if k.lower() in self.SENSITIVE_HEADERS:
                redacted[k] = "[REDACTED]"
            else:
                redacted[k] = v
        return redacted
