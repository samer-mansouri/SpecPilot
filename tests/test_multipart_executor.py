import pytest
import respx
from httpx import Response

from specpilot.mcp.executor import ToolExecutor
from specpilot.mcp.models import MCPTool


@respx.mock
def test_multipart_file_upload_execution(tmp_path):
    # Create temporary dummy upload file
    dummy_file = tmp_path / "document.txt"
    dummy_file.write_text("Test file payload content", encoding="utf-8")

    tool = MCPTool(
        name="upload_doc",
        description="Upload document",
        method="POST",
        path="/upload",
        base_url="http://localhost:8080",
    )

    respx.post("http://localhost:8080/upload").mock(
        return_value=Response(200, json={"status": "uploaded", "filename": "document.txt"})
    )

    executor = ToolExecutor()
    result = executor.execute(tool, arguments={"requestBody": {"file_path": str(dummy_file), "category": "specs"}})

    assert not result.is_error
    assert result.status_code == 200
    assert result.body == {"status": "uploaded", "filename": "document.txt"}
