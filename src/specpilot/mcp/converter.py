import re
from typing import Any, Dict, List, Optional, Set

from specpilot.openapi.models import NormalizedSpec, Operation, Parameter, RequestBody
from specpilot.mcp.models import MCPTool


class ToolConverter:
    """Converts OpenAPI operations into callable MCP tools with input schemas."""

    def __init__(self) -> None:
        pass

    def convert_spec(self, spec: NormalizedSpec) -> List[MCPTool]:
        """Convert all operations in a NormalizedSpec into MCP tools."""
        tools: List[MCPTool] = []
        used_names: Set[str] = set()
        base_url = spec.servers[0].url if spec.servers else None

        for op in spec.operations:
            tool_name = self.derive_tool_name(op, used_names)
            used_names.add(tool_name)

            description = self._build_tool_description(op)
            input_schema = self.generate_input_schema(op)

            tool = MCPTool(
                name=tool_name,
                description=description,
                method=op.method,
                path=op.path,
                input_schema=input_schema,
                original_operation=op,
                base_url=base_url,
            )
            tools.append(tool)

        return tools

    def derive_tool_name(self, op: Operation, used_names: Set[str]) -> str:
        """Derive a clean, deterministic, collision-free tool name for an operation."""
        base_name = ""
        if op.operation_id and isinstance(op.operation_id, str):
            base_name = self._to_snake_case(op.operation_id)
        
        if not base_name:
            clean_path = re.sub(r"[{}]", "", op.path)
            path_parts = [p for p in clean_path.split("/") if p]
            base_name = f"{op.method.lower()}_" + "_".join(path_parts) if path_parts else op.method.lower()

        base_name = self._sanitize_identifier(base_name)
        candidate = base_name

        counter = 2
        while candidate in used_names:
            candidate = f"{base_name}_{counter}"
            counter += 1

        return candidate

    def generate_input_schema(self, op: Operation) -> Dict[str, Any]:
        """Generate a JSON Schema object for tool input parameters and request body."""
        properties: Dict[str, Any] = {}
        required: List[str] = []

        # Convert parameters (path, query, header, cookie)
        for param in op.parameters:
            param_schema = self._convert_schema(param.schema_def)
            if param.description:
                param_schema["description"] = param.description

            properties[param.name] = param_schema
            if param.required:
                required.append(param.name)

        # Convert request body
        if op.request_body:
            body_schema = self._extract_body_schema(op.request_body)
            if body_schema:
                properties["requestBody"] = body_schema
                if op.request_body.required:
                    required.append("requestBody")

        schema: Dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required

        return schema

    def _convert_schema(self, raw_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not raw_schema or not isinstance(raw_schema, dict):
            return {"type": "string"}

        converted: Dict[str, Any] = {}
        target_type = raw_schema.get("type")
        if isinstance(target_type, str):
            converted["type"] = target_type
        elif isinstance(target_type, list):
            converted["type"] = [t for t in target_type if isinstance(t, str)]
        else:
            converted["type"] = "string"

        if "description" in raw_schema and isinstance(raw_schema["description"], str):
            converted["description"] = raw_schema["description"]

        if "enum" in raw_schema and isinstance(raw_schema["enum"], list):
            converted["enum"] = raw_schema["enum"]

        if "items" in raw_schema and isinstance(raw_schema["items"], dict):
            converted["items"] = self._convert_schema(raw_schema["items"])

        if "properties" in raw_schema and isinstance(raw_schema["properties"], dict):
            converted["properties"] = {
                k: self._convert_schema(v) for k, v in raw_schema["properties"].items() if isinstance(v, dict)
            }
            if "required" in raw_schema and isinstance(raw_schema["required"], list):
                converted["required"] = [r for r in raw_schema["required"] if isinstance(r, str)]

        return converted

    def _extract_body_schema(self, request_body: RequestBody) -> Optional[Dict[str, Any]]:
        if not request_body.content_types:
            return None

        # Prefer application/json, fall back to first media type
        json_content = request_body.content_types.get("application/json")
        if json_content is None and request_body.content_types:
            json_content = next(iter(request_body.content_types.values()))

        if isinstance(json_content, dict):
            schema = self._convert_schema(json_content)
            if request_body.description:
                schema["description"] = request_body.description
            return schema

        return None

    def _build_tool_description(self, op: Operation) -> str:
        parts: List[str] = []
        if op.summary:
            parts.append(op.summary)
        if op.description and op.description != op.summary:
            parts.append(op.description)
        if not parts:
            parts.append(f"{op.method} {op.path}")
        return " - ".join(parts)

    def _to_snake_case(self, name: str) -> str:
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _sanitize_identifier(self, name: str) -> str:
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        sanitized = re.sub(r"_+", "_", sanitized).strip("_")
        if not sanitized:
            return "tool"
        if sanitized[0].isdigit():
            return f"tool_{sanitized}"
        return sanitized
