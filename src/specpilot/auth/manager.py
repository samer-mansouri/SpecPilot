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

        # 2. Check Environment variables and .env file
        env_auth_type = os.getenv("SPECPILOT_AUTH_TYPE")
        env_bearer = os.getenv("SPECPILOT_BEARER_TOKEN") or os.getenv("SPECPILOT_BEARER")
        env_api_key = os.getenv("SPECPILOT_API_KEY")
        env_api_key_name = os.getenv("SPECPILOT_API_KEY_NAME", "X-API-Key")
        env_api_key_in = os.getenv("SPECPILOT_API_KEY_IN", "header")
        env_basic_user = os.getenv("SPECPILOT_BASIC_USER")
        env_basic_pass = os.getenv("SPECPILOT_BASIC_PASS")

        if os.path.exists(".env"):
            try:
                with open(".env", "r", encoding="utf-8") as f:
                    lines = f.readlines()
                token_lines = []
                recording_token = False
                for line in lines:
                    stripped = line.strip()
                    if recording_token:
                        token_lines.append(stripped)
                        if stripped.endswith('"') or stripped.endswith("'"):
                            recording_token = False
                        continue

                    if stripped.startswith("SPECPILOT_LOGIN_TOOL="):
                        val = stripped[len("SPECPILOT_LOGIN_TOOL="):].strip().strip('"').strip("'")
                        if val and "SPECPILOT_LOGIN_TOOL" not in os.environ:
                            os.environ["SPECPILOT_LOGIN_TOOL"] = val
                    elif stripped.startswith("SPECPILOT_LOGIN_ARGS="):
                        val = stripped[len("SPECPILOT_LOGIN_ARGS="):].strip().strip('"').strip("'")
                        if val and "SPECPILOT_LOGIN_ARGS" not in os.environ:
                            os.environ["SPECPILOT_LOGIN_ARGS"] = val

                    if not env_bearer:
                        for prefix in ("SPECPILOT_BEARER_TOKEN=", "SPECPILOT_BEARER=", "BEARER="):
                            if stripped.startswith(prefix):
                                val = stripped[len(prefix):].strip()
                                token_lines.append(val)
                                if (val.count('"') % 2 != 0) or (val.count("'") % 2 != 0):
                                    recording_token = True
                                break

                if token_lines and not env_bearer:
                    env_bearer = "".join(token_lines).strip().strip('"').strip("'")
            except Exception:
                pass

        if env_auth_type == "bearer" or env_bearer:
            if env_bearer and "SPECPILOT_BEARER_TOKEN" not in os.environ:
                os.environ["SPECPILOT_BEARER_TOKEN"] = env_bearer

            from specpilot.auth.lifecycle import TokenLifecycleManager
            lifecycle = TokenLifecycleManager.get_instance()
            lifecycle.active_token = env_bearer
            lifecycle.auth_type = AuthType.BEARER
            if not lifecycle.last_login_tool_name:
                lifecycle.last_login_tool_name = os.getenv("SPECPILOT_LOGIN_TOOL")
            if not lifecycle.last_login_arguments and os.getenv("SPECPILOT_LOGIN_ARGS"):
                try:
                    import json
                    lifecycle.last_login_arguments = json.loads(os.getenv("SPECPILOT_LOGIN_ARGS"))
                except Exception:
                    pass

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

    @classmethod
    def auto_capture_token(
        cls,
        response_body: Any,
        headers: Optional[Dict[str, str]] = None,
        dotenv_path: str = ".env",
        tool_name: Optional[str] = None,
        login_arguments: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Inspect response body and headers for JWT / OAuth tokens and register with TokenLifecycleManager."""
        from specpilot.auth.extractor import TokenExtractor
        from specpilot.auth.lifecycle import TokenLifecycleManager

        extracted = TokenExtractor.extract_from_response(response_body, headers=headers)
        if not extracted:
            return None

        TokenLifecycleManager.get_instance().register_token(
            extracted,
            tool_name=tool_name,
            login_arguments=login_arguments,
            dotenv_path=dotenv_path,
        )

        return extracted.token

    @classmethod
    def update_dotenv_file(cls, filepath: str, key: str, value: str) -> None:
        """Update or insert a key-value pair in a .env file, cleaning up broken line-split tokens."""
        lines = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

        new_lines = []
        skip_multiline = False
        replaced = False
        target_prefixes = (f"{key}=", "SPECPILOT_BEARER=", "BEARER=")

        for line in lines:
            stripped = line.strip()
            # If skipping orphaned broken multi-line token fragments from past copies
            if skip_multiline:
                if stripped.endswith('"') or stripped.endswith("'"):
                    skip_multiline = False
                continue

            if any(stripped.startswith(p) for p in target_prefixes):
                if not replaced:
                    new_lines.append(f'{key}="{value}"\n')
                    replaced = True
                # Check if this old token entry was multi-line (unclosed quote)
                if (stripped.count('"') % 2 != 0) or (stripped.count("'") % 2 != 0):
                    skip_multiline = True
                continue

            new_lines.append(line)

        if not replaced:
            new_lines.append(f'\n{key}="{value}"\n')

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
