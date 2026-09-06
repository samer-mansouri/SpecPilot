import os
import time
from typing import Any, Dict, Optional
from specpilot.auth.extractor import ExtractedToken
from specpilot.auth.models import AuthConfig, AuthType


class TokenLifecycleManager:
    """Manages token lifecycles, expiration checks, token refresh, and auto-relogin recovery."""

    _instance: Optional["TokenLifecycleManager"] = None

    def __init__(self) -> None:
        self.active_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.auth_type: AuthType = AuthType.BEARER
        self.expires_at: Optional[float] = None
        self.last_login_tool_name: Optional[str] = os.getenv("SPECPILOT_LOGIN_TOOL")
        self.last_login_arguments: Optional[Dict[str, Any]] = None
        self.refresh_tool_name: Optional[str] = None

        env_args = os.getenv("SPECPILOT_LOGIN_ARGS")
        if env_args:
            try:
                import json
                self.last_login_arguments = json.loads(env_args)
            except Exception:
                pass

    @classmethod
    def get_instance(cls) -> "TokenLifecycleManager":
        """Get global singleton instance of TokenLifecycleManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_token(
        self,
        extracted: ExtractedToken,
        tool_name: Optional[str] = None,
        login_arguments: Optional[Dict[str, Any]] = None,
        refresh_tool_name: Optional[str] = None,
        dotenv_path: str = ".env",
    ) -> None:
        """Register a new active token and persist to runtime environment & .env."""
        self.active_token = extracted.token
        if extracted.refresh_token:
            self.refresh_token = extracted.refresh_token
        self.auth_type = extracted.token_type
        if extracted.expires_at:
            self.expires_at = extracted.expires_at

        if tool_name:
            self.last_login_tool_name = tool_name
        if login_arguments:
            self.last_login_arguments = login_arguments
        if refresh_tool_name:
            self.refresh_tool_name = refresh_tool_name

        # 1. Update live runtime environment
        os.environ["SPECPILOT_BEARER_TOKEN"] = extracted.token
        os.environ["SPECPILOT_BEARER"] = extracted.token
        if self.last_login_tool_name:
            os.environ["SPECPILOT_LOGIN_TOOL"] = self.last_login_tool_name
        if self.last_login_arguments:
            import json
            os.environ["SPECPILOT_LOGIN_ARGS"] = json.dumps(self.last_login_arguments)

        # 2. Update .env file cleanly
        from specpilot.auth.manager import AuthManager
        try:
            AuthManager.update_dotenv_file(dotenv_path, "SPECPILOT_BEARER_TOKEN", extracted.token)
            if self.last_login_tool_name:
                AuthManager.update_dotenv_file(dotenv_path, "SPECPILOT_LOGIN_TOOL", self.last_login_tool_name)
            if self.last_login_arguments:
                import json
                AuthManager.update_dotenv_file(dotenv_path, "SPECPILOT_LOGIN_ARGS", json.dumps(self.last_login_arguments))
        except Exception:
            pass

    def is_expired(self, buffer_seconds: float = 30.0) -> bool:
        """Check if active token is expired or within buffer_seconds of expiration."""
        if not self.expires_at:
            return False
        return time.time() + buffer_seconds >= self.expires_at

    def can_auto_refresh(self) -> bool:
        """Check if background refresh or auto-relogin is possible."""
        return bool(self.refresh_token or (self.last_login_tool_name and self.last_login_arguments))

    def clear(self) -> None:
        """Clear active token lifecycle state."""
        self.active_token = None
        self.refresh_token = None
        self.expires_at = None
        self.last_login_tool_name = None
        self.last_login_arguments = None
        self.refresh_tool_name = None
