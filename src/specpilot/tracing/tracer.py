import json
import os
from pathlib import Path
import uuid
from typing import Any, Dict, Optional

from specpilot.safety.redactor import SecretRedactor
from specpilot.tracing.models import TraceEvent, TraceSession


class ExecutionTracer:
    """Handles local structured JSON execution tracing and optional Langfuse exporter."""

    def __init__(self, session_id: Optional[str] = None, trace_dir: Optional[Path] = None) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.trace_dir = trace_dir or (Path.home() / ".specpilot" / "traces")
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.trace_dir / f"trace_{self.session_id}.json"
        self.session = TraceSession(session_id=self.session_id)

        # Check for optional Langfuse integration
        self.langfuse_enabled = bool(
            os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
        )
        self._langfuse_client = None
        if self.langfuse_enabled:
            try:
                from langfuse import Langfuse

                host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
                self._langfuse_client = Langfuse(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=host,
                )
            except Exception:
                # Degrade gracefully if langfuse is not installed or fails initialization
                self.langfuse_enabled = False
                self._langfuse_client = None

    def trace(self, event_type: str, details: Dict[str, Any]) -> TraceEvent:
        """Record a structured execution event, redacting sensitive information."""
        safe_details = SecretRedactor.redact_dict(details)
        event = TraceEvent(
            session_id=self.session_id,
            event_type=event_type,
            details=safe_details,
        )
        self.session.events.append(event)
        self._flush_local()

        if self.langfuse_enabled and self._langfuse_client:
            try:
                self._langfuse_client.trace(
                    name=f"specpilot:{event_type}",
                    session_id=self.session_id,
                    metadata=safe_details,
                )
            except Exception:
                # Silently ignore Langfuse export failures
                pass

        return event

    def _flush_local(self) -> None:
        """Persist structured trace session to local JSON file."""
        try:
            with open(self.trace_file, "w", encoding="utf-8") as f:
                json.dump(self.session.model_dump(), f, indent=2)
        except Exception:
            pass


_global_tracer: Optional[ExecutionTracer] = None


def get_tracer(session_id: Optional[str] = None) -> ExecutionTracer:
    """Retrieve or initialize singleton execution tracer."""
    global _global_tracer
    if _global_tracer is None or (session_id and _global_tracer.session_id != session_id):
        _global_tracer = ExecutionTracer(session_id=session_id)
    return _global_tracer
