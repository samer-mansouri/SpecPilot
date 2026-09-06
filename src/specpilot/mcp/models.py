from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from specpilot.openapi.models import Operation


class MCPTool(BaseModel):
    """Represents a dynamically converted MCP tool derived from an OpenAPI operation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    method: str
    path: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    original_operation: Optional[Operation] = None
    base_url: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of executing an MCP tool request against a target API."""

    status_code: int
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Any = None
    is_error: bool = False
    error_message: Optional[str] = None
    duration_ms: float = 0.0
