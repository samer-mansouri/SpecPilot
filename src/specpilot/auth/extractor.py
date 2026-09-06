import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from specpilot.auth.models import APIKeyLocation, AuthType


class ExtractedToken(BaseModel):
    """Container for tokens and metadata extracted from authentication responses."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    token: str
    token_type: AuthType = AuthType.BEARER
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None
    api_key_name: Optional[str] = None
    api_key_location: Optional[APIKeyLocation] = None


class TokenExtractor:
    """Universal token extractor for response bodies and headers across all auth schemes."""

    ACCESS_TOKEN_KEYS = (
        "accessToken",
        "access_token",
        "token",
        "bearerToken",
        "bearer_token",
        "jwt",
        "id_token",
        "idToken",
        "session_token",
        "sessionToken",
        "sessionId",
        "session_id",
        "apiKey",
        "api_key",
    )

    REFRESH_TOKEN_KEYS = (
        "refreshToken",
        "refresh_token",
        "renew_token",
        "renewToken",
    )

    EXPIRES_IN_KEYS = (
        "expires_in",
        "expiresIn",
        "expires_at",
        "expiresAt",
        "ttl",
    )

    @classmethod
    def extract_from_response(
        cls,
        response_body: Any,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[ExtractedToken]:
        """Extract access token, refresh token, and expiry details from response body and headers."""
        token_str: Optional[str] = None
        refresh_str: Optional[str] = None
        expires_at: Optional[float] = None
        auth_type: AuthType = AuthType.BEARER

        # 1. Search response body
        if isinstance(response_body, dict):
            containers = [response_body]
            for sub in ("data", "result", "payload", "response", "auth", "tokens"):
                val = response_body.get(sub)
                if isinstance(val, dict):
                    containers.append(val)

            for container in containers:
                if not token_str:
                    for key in cls.ACCESS_TOKEN_KEYS:
                        val = container.get(key)
                        if isinstance(val, str) and len(val.strip()) > 5:
                            token_str = val.strip()
                            break

                if not refresh_str:
                    for key in cls.REFRESH_TOKEN_KEYS:
                        val = container.get(key)
                        if isinstance(val, str) and len(val.strip()) > 5:
                            refresh_str = val.strip()
                            break

                if expires_at is None:
                    for key in cls.EXPIRES_IN_KEYS:
                        val = container.get(key)
                        if isinstance(val, (int, float)) and val > 0:
                            if val > 1_000_000_000:
                                expires_at = float(val)
                            else:
                                expires_at = time.time() + float(val)
                            break

        # 2. Search headers (Authorization, X-Auth-Token, Set-Cookie)
        if headers:
            for k, v in headers.items():
                k_lower = k.lower()
                if k_lower in ("authorization", "x-auth-token", "x-access-token"):
                    if v.lower().startswith("bearer "):
                        token_str = v[7:].strip()
                    elif len(v.strip()) > 5:
                        token_str = v.strip()
                elif k_lower == "set-cookie":
                    for item in v.split(";"):
                        if "=" in item:
                            cookie_k, cookie_v = item.split("=", 1)
                            if cookie_k.strip().lower() in ("token", "session", "sessionid", "jwt", "access_token"):
                                if len(cookie_v.strip()) > 5 and not token_str:
                                    token_str = cookie_v.strip()

        if not token_str:
            return None

        clean_token = "".join(token_str.split()).strip('"').strip("'")

        return ExtractedToken(
            token=clean_token,
            token_type=auth_type,
            refresh_token=refresh_str,
            expires_at=expires_at,
        )
