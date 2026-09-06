import re
from typing import Any, Dict, List, Optional

from specpilot.openapi.errors import SpecParseError, RefResolutionError
from specpilot.openapi.loader import LoadedSpec
from specpilot.openapi.models import (
    NormalizedSpec,
    Operation,
    Parameter,
    RequestBody,
    Response,
    SecurityScheme,
    Server,
)
from specpilot.openapi.refs import RefResolver

HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}


class OpenAPIParser:
    """Parses raw OpenAPI specifications into typed NormalizedSpec models."""

    def __init__(self, loaded_spec: LoadedSpec) -> None:
        self.raw_data = loaded_spec.data
        self.source = loaded_spec.source
        self.resolver = RefResolver(self.raw_data)

    def parse(self) -> NormalizedSpec:
        """Parse and normalize the OpenAPI document."""
        if not isinstance(self.raw_data, dict):
            raise SpecParseError(f"Root OpenAPI document in '{self.source}' must be a dictionary.")

        openapi_ver = self.raw_data.get("openapi")
        if not openapi_ver or not isinstance(openapi_ver, str):
            raise SpecParseError(f"Missing or invalid 'openapi' version field in '{self.source}'.")

        if not openapi_ver.startswith("3."):
            raise SpecParseError(
                f"Unsupported OpenAPI version '{openapi_ver}' in '{self.source}'. Only OpenAPI 3.x is supported."
            )

        info = self.raw_data.get("info")
        if not isinstance(info, dict):
            raise SpecParseError(f"Missing or invalid 'info' section in '{self.source}'.")

        title = info.get("title")
        if not title or not isinstance(title, str):
            raise SpecParseError(f"Missing or invalid 'info.title' in '{self.source}'.")

        api_version = info.get("version")
        if not api_version or not isinstance(api_version, str):
            raise SpecParseError(f"Missing or invalid 'info.version' in '{self.source}'.")

        description = info.get("description") if isinstance(info.get("description"), str) else None

        # Parse servers
        servers = self._parse_servers(self.raw_data.get("servers"))

        # Parse tags
        tags = self._parse_tags(self.raw_data.get("tags"))

        # Parse paths and operations
        paths_dict = self.raw_data.get("paths")
        if paths_dict is None or not isinstance(paths_dict, dict):
            raise SpecParseError(f"Missing or invalid 'paths' section in '{self.source}'.")

        operations = self._parse_operations(paths_dict)

        # Parse components schemas and security schemes
        components = self.raw_data.get("components", {})
        if not isinstance(components, dict):
            components = {}

        schemas = components.get("schemas", {})
        if not isinstance(schemas, dict):
            schemas = {}

        security_schemes_raw = components.get("securitySchemes", {})
        security_schemes = self._parse_security_schemes(security_schemes_raw)

        return NormalizedSpec(
            title=title,
            api_version=api_version,
            openapi_version=openapi_ver,
            source=self.source,
            description=description,
            servers=servers,
            tags=tags,
            operations=operations,
            components_schemas=schemas,
            security_schemes=security_schemes,
        )

    def _parse_servers(self, raw_servers: Any) -> List[Server]:
        servers: List[Server] = []
        if isinstance(raw_servers, list):
            for item in raw_servers:
                if isinstance(item, dict) and "url" in item and isinstance(item["url"], str):
                    servers.append(
                        Server(
                            url=item["url"],
                            description=item.get("description") if isinstance(item.get("description"), str) else None,
                        )
                    )
        return servers

    def _parse_tags(self, raw_tags: Any) -> List[str]:
        tags: List[str] = []
        if isinstance(raw_tags, list):
            for item in raw_tags:
                if isinstance(item, dict) and "name" in item and isinstance(item["name"], str):
                    tags.append(item["name"])
                elif isinstance(item, str):
                    tags.append(item)
        return tags

    def _parse_operations(self, paths: Dict[str, Any]) -> List[Operation]:
        operations: List[Operation] = []

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            # Path-level parameters
            raw_path_params = path_item.get("parameters", [])
            path_params = self._parse_parameters(raw_path_params)

            for method_name, raw_operation in path_item.items():
                method_lower = method_name.lower()
                if method_lower not in HTTP_METHODS or not isinstance(raw_operation, dict):
                    continue

                op_id = raw_operation.get("operationId")
                if not op_id or not isinstance(op_id, str):
                    op_id = self._generate_operation_id(method_lower, path)

                op_summary = raw_operation.get("summary") if isinstance(raw_operation.get("summary"), str) else None
                op_desc = raw_operation.get("description") if isinstance(raw_operation.get("description"), str) else None

                op_tags = self._parse_tags(raw_operation.get("tags"))

                # Operation-level parameters
                op_params = self._parse_parameters(raw_operation.get("parameters", []))

                # Combine path & operation params (op overrides path by name+in)
                combined_params = self._merge_parameters(path_params, op_params)

                # Request body
                request_body = self._parse_request_body(raw_operation.get("requestBody"))

                # Responses
                responses = self._parse_responses(raw_operation.get("responses"))

                # Security requirements
                security = raw_operation.get("security", self.raw_data.get("security", []))
                if not isinstance(security, list):
                    security = []

                operations.append(
                    Operation(
                        operation_id=op_id,
                        method=method_lower.upper(),
                        path=path,
                        tags=op_tags,
                        summary=op_summary,
                        description=op_desc,
                        parameters=combined_params,
                        request_body=request_body,
                        responses=responses,
                        security=security,
                    )
                )

        return operations

    def _parse_parameters(self, raw_params: Any) -> List[Parameter]:
        params: List[Parameter] = []
        if not isinstance(raw_params, list):
            return params

        for raw_p in raw_params:
            if not isinstance(raw_p, dict):
                continue

            p = raw_p
            if "$ref" in p and isinstance(p["$ref"], str):
                try:
                    p = self.resolver.resolve(p["$ref"])
                except RefResolutionError as err:
                    raise SpecParseError(f"Failed to resolve parameter $ref: {err}") from err

            name = p.get("name")
            in_loc = p.get("in")
            if not name or not in_loc or not isinstance(name, str) or not isinstance(in_loc, str):
                continue

            schema_def = p.get("schema")
            if isinstance(schema_def, dict):
                schema_def = self.resolver.resolve_deep(schema_def)

            params.append(
                Parameter(
                    name=name,
                    in_location=in_loc,
                    required=bool(p.get("required", in_loc == "path")),
                    description=p.get("description") if isinstance(p.get("description"), str) else None,
                    schema_def=schema_def,
                )
            )

        return params

    def _merge_parameters(self, path_params: List[Parameter], op_params: List[Parameter]) -> List[Parameter]:
        param_map: Dict[tuple[str, str], Parameter] = {}
        for p in path_params:
            param_map[(p.name, p.in_location)] = p
        for p in op_params:
            param_map[(p.name, p.in_location)] = p
        return list(param_map.values())

    def _parse_request_body(self, raw_body: Any) -> Optional[RequestBody]:
        if not raw_body:
            return None

        body = raw_body
        if isinstance(body, dict) and "$ref" in body and isinstance(body["$ref"], str):
            try:
                body = self.resolver.resolve(body["$ref"])
            except RefResolutionError as err:
                raise SpecParseError(f"Failed to resolve requestBody $ref: {err}") from err

        if not isinstance(body, dict):
            return None

        content = body.get("content", {})
        content_types: Dict[str, Any] = {}
        if isinstance(content, dict):
            for media_type, media_obj in content.items():
                if isinstance(media_obj, dict):
                    schema = media_obj.get("schema")
                    if isinstance(schema, dict):
                        content_types[media_type] = self.resolver.resolve_deep(schema)
                    else:
                        content_types[media_type] = {}

        return RequestBody(
            description=body.get("description") if isinstance(body.get("description"), str) else None,
            required=bool(body.get("required", False)),
            content_types=content_types,
        )

    def _parse_responses(self, raw_responses: Any) -> List[Response]:
        responses: List[Response] = []
        if not isinstance(raw_responses, dict):
            return responses

        for status_code, raw_resp in raw_responses.items():
            resp = raw_resp
            if isinstance(resp, dict) and "$ref" in resp and isinstance(resp["$ref"], str):
                try:
                    resp = self.resolver.resolve(resp["$ref"])
                except RefResolutionError as err:
                    raise SpecParseError(f"Failed to resolve response $ref: {err}") from err

            if not isinstance(resp, dict):
                continue

            content = resp.get("content", {})
            content_types: Dict[str, Any] = {}
            if isinstance(content, dict):
                for media_type, media_obj in content.items():
                    if isinstance(media_obj, dict):
                        schema = media_obj.get("schema")
                        if isinstance(schema, dict):
                            content_types[media_type] = self.resolver.resolve_deep(schema)
                        else:
                            content_types[media_type] = {}

            responses.append(
                Response(
                    status_code=str(status_code),
                    description=resp.get("description") if isinstance(resp.get("description"), str) else None,
                    content_types=content_types,
                )
            )

        return responses

    def _parse_security_schemes(self, raw_schemes: Any) -> Dict[str, SecurityScheme]:
        schemes: Dict[str, SecurityScheme] = {}
        if not isinstance(raw_schemes, dict):
            return schemes

        for name, item in raw_schemes.items():
            scheme_dict = item
            if isinstance(scheme_dict, dict) and "$ref" in scheme_dict and isinstance(scheme_dict["$ref"], str):
                scheme_dict = self.resolver.resolve(scheme_dict["$ref"])

            if isinstance(scheme_dict, dict) and "type" in scheme_dict:
                schemes[name] = SecurityScheme(
                    type=scheme_dict["type"],
                    description=scheme_dict.get("description") if isinstance(scheme_dict.get("description"), str) else None,
                    name=scheme_dict.get("name") if isinstance(scheme_dict.get("name"), str) else None,
                    in_location=scheme_dict.get("in") if isinstance(scheme_dict.get("in"), str) else None,
                    scheme=scheme_dict.get("scheme") if isinstance(scheme_dict.get("scheme"), str) else None,
                )
        return schemes

    def _generate_operation_id(self, method: str, path: str) -> str:
        clean_path = re.sub(r"[{}]", "", path)
        parts = [p for p in clean_path.split("/") if p]
        if not parts:
            return method.lower()
        return f"{method.lower()}_" + "_".join(parts)
