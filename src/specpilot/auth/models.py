import base64
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class APIKeyLocation(str, Enum):
    HEADER = "header"
    QUERY = "query"


class AuthConfig(BaseModel):
    """Authentication configuration for target API calls."""

    auth_type: AuthType = AuthType.NONE
    bearer_token: Optional[str] = None
    api_key: Optional[str] = None
    api_key_name: str = "X-API-Key"
    api_key_in: APIKeyLocation = APIKeyLocation.HEADER
    basic_username: Optional[str] = None
    basic_password: Optional[str] = None

    def apply(self, headers: Dict[str, str], query_params: Dict[str, Any]) -> None:
        """Apply authentication credentials to headers or query parameters."""
        if self.auth_type == AuthType.BEARER:
            if self.bearer_token:
                clean_token = "".join(self.bearer_token.split()).strip('"').strip("'")
                if clean_token:
                    headers["Authorization"] = f"Bearer {clean_token}"
        elif self.auth_type == AuthType.API_KEY:
            if self.api_key:
                clean_key = "".join(self.api_key.split()).strip('"').strip("'")
                if clean_key:
                    if self.api_key_in == APIKeyLocation.HEADER:
                        headers[self.api_key_name] = clean_key
                    elif self.api_key_in == APIKeyLocation.QUERY:
                        query_params[self.api_key_name] = clean_key
        elif self.auth_type == AuthType.BASIC:
            user = (self.basic_username or "").strip()
            pwd = (self.basic_password or "").strip()
            cred_bytes = f"{user}:{pwd}".encode("utf-8")
            encoded = base64.b64encode(cred_bytes).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"

    def redacted_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation with sensitive values redacted."""
        res: Dict[str, Any] = {"auth_type": self.auth_type.value}
        if self.auth_type == AuthType.BEARER:
            res["bearer_token"] = "[REDACTED]" if self.bearer_token else None
        elif self.auth_type == AuthType.API_KEY:
            res["api_key"] = "[REDACTED]" if self.api_key else None
            res["api_key_name"] = self.api_key_name
            res["api_key_in"] = self.api_key_in.value
        elif self.auth_type == AuthType.BASIC:
            res["basic_username"] = self.basic_username
            res["basic_password"] = "[REDACTED]" if self.basic_password else None
        return res
