import json
from pathlib import Path
from specpilot.tracing import ExecutionTracer, TraceEvent, TraceSession, get_tracer


def test_execution_tracer_local_file(tmp_path: Path):
    tracer = ExecutionTracer(session_id="test_session_123", trace_dir=tmp_path)

    event = tracer.trace("model_call", {
        "model": "gpt-4o-mini",
        "api_key": "secret_key_12345",
        "prompt_tokens": 150,
    })

    assert event.event_type == "model_call"
    assert event.details["api_key"] == "[REDACTED]"
    assert event.details["model"] == "gpt-4o-mini"

    # Check local JSON trace file
    trace_file = tmp_path / "trace_test_session_123.json"
    assert trace_file.exists()

    with open(trace_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["session_id"] == "test_session_123"
    assert len(data["events"]) == 1
    assert data["events"][0]["event_type"] == "model_call"
    assert data["events"][0]["details"]["api_key"] == "[REDACTED]"


def test_get_tracer_singleton():
    tracer1 = get_tracer(session_id="session_a")
    tracer2 = get_tracer(session_id="session_a")
    assert tracer1 is tracer2

    tracer3 = get_tracer(session_id="session_b")
    assert tracer3 is not tracer1
    assert tracer3.session_id == "session_b"
