import os
from typing import Optional
from specpilot.auth.models import APIKeyLocation, AuthConfig, AuthType
from specpilot.config.models import Profile


class AuthManager:
    """Resolves and manages authentication configurations from CLI, environment, or profiles."""

    @classmethod
    def resolve(
        cls,
        cli_bearer_token: Optional[str] = None,
        cli_api_key: Optional[str] = None,
        cli_api_key_name: Optional[str] = None,
        cli_api_key_in: Optional[str] = None,
        cli_basic_user: Optional[str] = None,
        cli_basic_pass: Optional[str] = None,
        profile: Optional[Profile] = None,
    ) -> AuthConfig:
        """Resolve AuthConfig prioritizing CLI flags -> Environment variables -> Profile settings."""
        # 1. Check CLI flags
        if cli_bearer_token:
            return AuthConfig(
                auth_type=AuthType.BEARER,
                bearer_token=cli_bearer_token,
            )
        if cli_api_key:
            loc = APIKeyLocation.HEADER
            if cli_api_key_in and cli_api_key_in.lower() == "query":
                loc = APIKeyLocation.QUERY
            return AuthConfig(
                auth_type=AuthType.API_KEY,
                api_key=cli_api_key,
                api_key_name=cli_api_key_name or "X-API-Key",
                api_key_in=loc,
            )
        if cli_basic_user or cli_basic_pass:
            return AuthConfig(
                auth_type=AuthType.BASIC,
                basic_username=cli_basic_user,
                basic_password=cli_basic_pass,
            )

        # 2. Check Environment variables
        env_auth_type = os.getenv("SPECPILOT_AUTH_TYPE")
        env_bearer = os.getenv("SPECPILOT_BEARER_TOKEN")
        env_api_key = os.getenv("SPECPILOT_API_KEY")
        env_api_key_name = os.getenv("SPECPILOT_API_KEY_NAME", "X-API-Key")
        env_api_key_in = os.getenv("SPECPILOT_API_KEY_IN", "header")
        env_basic_user = os.getenv("SPECPILOT_BASIC_USER")
        env_basic_pass = os.getenv("SPECPILOT_BASIC_PASS")

        if env_auth_type == "bearer" or env_bearer:
            return AuthConfig(
                auth_type=AuthType.BEARER,
                bearer_token=env_bearer,
            )
        if env_auth_type == "api_key" or env_api_key:
            loc = APIKeyLocation.QUERY if env_api_key_in.lower() == "query" else APIKeyLocation.HEADER
            return AuthConfig(
                auth_type=AuthType.API_KEY,
                api_key=env_api_key,
                api_key_name=env_api_key_name,
                api_key_in=loc,
            )
        if env_auth_type == "basic" or (env_basic_user and env_basic_pass):
            return AuthConfig(
                auth_type=AuthType.BASIC,
                basic_username=env_basic_user,
                basic_password=env_basic_pass,
            )

        # 3. Check Profile settings if provided
        if profile and hasattr(profile, "auth") and profile.auth:
            return profile.auth

        return AuthConfig(auth_type=AuthType.NONE)
