import datetime
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    """Structured execution trace event."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    event_type: str  # e.g., "command", "model_call", "mcp_tool_call", "api_request", "approval", "error"
    details: Dict[str, Any] = Field(default_factory=dict)


class TraceSession(BaseModel):
    """Summary of a structured trace session."""

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    end_time: Optional[str] = None
    events: List[TraceEvent] = Field(default_factory=list)
