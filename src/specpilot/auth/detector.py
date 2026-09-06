from typing import Any, Dict, List, Optional
from specpilot.openapi.models import NormalizedSpec, Operation


class AuthEndpointDetector:
    """Discovers login, authentication, and token refresh operations from OpenAPI specifications."""

    LOGIN_PATH_KEYWORDS = ("login", "auth", "token", "oauth", "signin", "session")
    REFRESH_PATH_KEYWORDS = ("refresh", "renew")
    LOGIN_TAG_KEYWORDS = ("auth", "login", "security", "session", "account")

    @classmethod
    def detect_login_operations(cls, spec: NormalizedSpec) -> List[Operation]:
        """Find operations in specification that serve as authentication / login endpoints."""
        candidates = []
        for op in spec.operations:
            if cls.is_login_operation(op):
                candidates.append(op)
        return candidates

    @classmethod
    def detect_refresh_operations(cls, spec: NormalizedSpec) -> List[Operation]:
        """Find operations in specification that serve as token refresh endpoints."""
        candidates = []
        for op in spec.operations:
            if cls.is_refresh_operation(op):
                candidates.append(op)
        return candidates

    @classmethod
    def is_login_operation(cls, op: Operation) -> bool:
        """Check if an operation appears to be a login / auth endpoint."""
        if op.method.upper() not in ("POST", "PUT"):
            return False

        path_lower = op.path.lower()
        op_id_lower = (op.operation_id or "").lower()
        tags_lower = [t.lower() for t in op.tags]

        # Explicit refresh endpoints are NOT login endpoints
        if any(kw in path_lower or kw in op_id_lower for kw in cls.REFRESH_PATH_KEYWORDS):
            return False

        # 1. Match path or operationId
        if any(kw in path_lower for kw in ("login", "signin", "/auth/token", "/oauth/token", "/session", "/api/auth")):
            return True
        if any(kw in op_id_lower for kw in ("login", "signin", "authenticate", "createauth", "createtoken", "auth")):
            return True

        # 2. Match tags + path/opId keyword
        if any(t in cls.LOGIN_TAG_KEYWORDS for t in tags_lower):
            if any(kw in path_lower or kw in op_id_lower for kw in cls.LOGIN_PATH_KEYWORDS):
                return True

        # 3. Match request body property names (e.g. username/email + password)
        if op.request_body and op.request_body.content_types:
            for _ctype, media in op.request_body.content_types.items():
                schema = media.get("schema", {})
                props = schema.get("properties", {})
                prop_names = [str(p).lower() for p in props.keys()]
                if ("username" in prop_names or "usernameoremail" in prop_names or "email" in prop_names) and "password" in prop_names:
                    return True

        return False

    @classmethod
    def is_refresh_operation(cls, op: Operation) -> bool:
        """Check if an operation appears to be a token refresh endpoint."""
        if op.method.upper() not in ("POST", "PUT"):
            return False

        path_lower = op.path.lower()
        op_id_lower = (op.operation_id or "").lower()

        if "refresh" in path_lower or "refresh" in op_id_lower:
            return True

        return False
