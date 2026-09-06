import re
from typing import Any, Dict, List, Union


class SecretRedactor:
    """Reusable utility for redacting credentials, tokens, and secret parameters."""

    PATTERNS = [
        # JSON string key-value pairs
        re.compile(
            r'(\"(?:api[_-]?key|bearer|token|secret|password|auth|authorization|access[_-]?token|refresh[_-]?token)\"\s*:\s*\")([^\"]+)(\")',
            re.IGNORECASE,
        ),
        # Authorization header with or without Bearer prefix
        re.compile(
            r'((?:authorization|api[_-]?key)\s*:\s*(?:bearer\s+)?)(\S+)',
            re.IGNORECASE,
        ),
        # Key=value assignment in parameters or query strings
        re.compile(
            r'((?:api[_-]?key|bearer|token|secret|password|access[_-]?token)\s*=\s*)([^\s&,{}"]+)',
            re.IGNORECASE,
        ),
    ]

    SENSITIVE_KEYS = {
        "api_key",
        "apikey",
        "api-key",
        "x-api-key",
        "x-api-token",
        "x-auth-token",
        "authorization",
        "auth",
        "bearer",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "password",
        "passwd",
    }


    @classmethod
    def redact(cls, text: str) -> str:
        """Redact sensitive patterns from text strings."""
        if not text:
            return text

        redacted = text
        for pattern in cls.PATTERNS:
            def _replacer(match: re.Match) -> str:
                groups = match.groups()
                if len(groups) == 3:
                    return f"{groups[0]}[REDACTED]{groups[2]}"
                elif len(groups) == 2:
                    return f"{groups[0]}[REDACTED]"
                return "[REDACTED]"

            redacted = pattern.sub(_replacer, redacted)
        return redacted

    @classmethod
    def redact_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact dictionary keys and string values matching sensitive names."""
        result: Dict[str, Any] = {}
        for key, val in data.items():
            key_lower = str(key).lower()
            if key_lower in cls.SENSITIVE_KEYS:
                result[key] = "[REDACTED]"
            elif isinstance(val, dict):
                result[key] = cls.redact_dict(val)
            elif isinstance(val, list):
                result[key] = [
                    cls.redact_dict(item) if isinstance(item, dict) else (cls.redact(item) if isinstance(item, str) else item)
                    for item in val
                ]
            elif isinstance(val, str):
                result[key] = cls.redact(val)
            else:
                result[key] = val
        return result

    @classmethod
    def redact_headers(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """Redact sensitive header values."""
        if not headers:
            return {}
        redacted = cls.redact_dict(headers)
        return {str(k): str(v) for k, v in redacted.items()}
